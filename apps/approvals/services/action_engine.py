from django.db import transaction
from django.utils import timezone
from apps.approvals.models import ApprovalStep
from apps.approvals.models import (
    ApprovalAction,
    ApprovalActionType,
    ApprovalStepStatus,
    RequestStatus,
)
from apps.approvals.services.delegation_engine import resolve_delegated_approver
from apps.notifications.services.notification_service import (
    notify_approval_assigned,
    notify_request_approved,
    notify_request_commented,
    notify_request_rejected,
)


def create_approval_action(
    *,
    document_request,
    step=None,
    action_by=None,
    action_type,
    comment="",
    old_status="",
    new_status="",
):
    return ApprovalAction.objects.create(
        request=document_request,
        step=step,
        action_by=action_by,
        action_type=action_type,
        comment=comment,
        old_status=old_status,
        new_status=new_status,
    )


def can_user_act_on_step(user, step):
    if not user.is_authenticated:
        return False

    if user.is_superuser:
        return False

    if step.assigned_to_id != user.id:
        return False

    if not step.is_current:
        return False

    return step.status == ApprovalStepStatus.PENDING


def activate_next_step(next_step, actor=None):
    """
    Activates the next pending approval step.

    Extra logic:
    - Re-checks delegation before assigning next active approver.
    - Sets due_at from workflow_step.sla_hours if missing.
    - Resets SLA flags for the active step.
    - Sends assignment notification to the final assigned user.
    """

    if next_step.assigned_to:
        next_step.assigned_to = resolve_delegated_approver(
            user=next_step.assigned_to,
            organization=next_step.request.organization,
        )

    next_step.is_current = True

    if not next_step.due_at:
        sla_hours = 24

        if next_step.workflow_step:
            sla_hours = next_step.workflow_step.sla_hours

        next_step.due_at = timezone.now() + timezone.timedelta(hours=sla_hours)

    next_step.is_overdue = False
    next_step.reminder_sent_at = None
    next_step.escalated_at = None
    next_step.escalation_count = 0

    next_step.save(
        update_fields=[
            "assigned_to",
            "is_current",
            "due_at",
            "is_overdue",
            "reminder_sent_at",
            "escalated_at",
            "escalation_count",
            "updated_at",
        ]
    )

    notify_approval_assigned(
        approval_step=next_step,
        actor=actor,
    )

    return next_step


@transaction.atomic
def approve_current_step(step, user, comment=""):
    if not can_user_act_on_step(user, step):
        raise ValueError("You are not allowed to approve this step.")

    document_request = step.request
    old_request_status = document_request.status

    now = timezone.now()

    step.status = ApprovalStepStatus.APPROVED
    step.approved_at = now
    step.comments = comment
    step.is_current = False
    step.is_overdue = False
    step.save(
        update_fields=[
            "status",
            "approved_at",
            "comments",
            "is_current",
            "is_overdue",
            "updated_at",
        ]
    )

    create_approval_action(
        document_request=document_request,
        step=step,
        action_by=user,
        action_type=ApprovalActionType.APPROVED,
        comment=comment,
        old_status=old_request_status,
        new_status=RequestStatus.IN_REVIEW,
    )

    next_step = (
        document_request.approval_steps
        .filter(
            status=ApprovalStepStatus.PENDING,
            step_order__gt=step.step_order,
        )
        .order_by("step_order")
        .first()
    )

    if next_step:
        activate_next_step(
            next_step=next_step,
            actor=user,
        )

        document_request.status = RequestStatus.IN_REVIEW
        document_request.current_step = next_step.step_order
        document_request.save(
            update_fields=[
                "status",
                "current_step",
                "updated_at",
            ]
        )

        return {
            "is_final": False,
            "next_step": next_step,
        }

    document_request.status = RequestStatus.APPROVED
    document_request.approved_at = now
    document_request.current_step = step.step_order
    document_request.save(
        update_fields=[
            "status",
            "approved_at",
            "current_step",
            "updated_at",
        ]
    )

    create_approval_action(
        document_request=document_request,
        step=step,
        action_by=user,
        action_type=ApprovalActionType.APPROVED,
        comment="Final approval completed.",
        old_status=old_request_status,
        new_status=RequestStatus.APPROVED,
    )

    notify_request_approved(
        document_request=document_request,
        actor=user,
    )

    return {
        "is_final": True,
        "next_step": None,
    }


@transaction.atomic
def reject_current_step(step, user, comment=""):
    if not can_user_act_on_step(user, step):
        raise ValueError("You are not allowed to reject this step.")

    if not comment.strip():
        raise ValueError("Rejection comment is required.")

    document_request = step.request
    old_request_status = document_request.status

    now = timezone.now()

    step.status = ApprovalStepStatus.REJECTED
    step.rejected_at = now
    step.comments = comment
    step.is_current = False
    step.is_overdue = False
    step.save(
        update_fields=[
            "status",
            "rejected_at",
            "comments",
            "is_current",
            "is_overdue",
            "updated_at",
        ]
    )

    pending_steps = document_request.approval_steps.filter(
        status=ApprovalStepStatus.PENDING,
    )

    pending_steps.update(
        status=ApprovalStepStatus.SKIPPED,
        is_current=False,
        is_overdue=False,
        updated_at=now,
    )

    document_request.status = RequestStatus.REJECTED
    document_request.rejected_at = now
    document_request.current_step = step.step_order
    document_request.save(
        update_fields=[
            "status",
            "rejected_at",
            "current_step",
            "updated_at",
        ]
    )

    create_approval_action(
        document_request=document_request,
        step=step,
        action_by=user,
        action_type=ApprovalActionType.REJECTED,
        comment=comment,
        old_status=old_request_status,
        new_status=RequestStatus.REJECTED,
    )

    notify_request_rejected(
        document_request=document_request,
        actor=user,
        comment=comment,
    )

    return document_request


@transaction.atomic
def comment_on_current_step(step, user, comment=""):
    if not can_user_act_on_step(user, step):
        raise ValueError("You are not allowed to comment on this step.")

    if not comment.strip():
        raise ValueError("Comment cannot be empty.")

    document_request = step.request

    existing_comment = step.comments.strip()

    if existing_comment:
        step.comments = f"{existing_comment}\n\n{comment}"
    else:
        step.comments = comment

    step.save(
        update_fields=[
            "comments",
            "updated_at",
        ]
    )

    create_approval_action(
        document_request=document_request,
        step=step,
        action_by=user,
        action_type=ApprovalActionType.COMMENTED,
        comment=comment,
        old_status=document_request.status,
        new_status=document_request.status,
    )

    notify_request_commented(
        document_request=document_request,
        approval_step=step,
        actor=user,
        comment=comment,
    )

    return step

@transaction.atomic
def perform_bulk_step_action(*, user, step_ids, action, comment=""):
    """
    Bulk action for approval inbox.

    Supported:
    - approve
    - reject
    - comment

    Reminder bulk is handled in reminder_engine because it creates reminder records.
    """

    steps = (
        ApprovalStep.objects.select_related(
            "request",
            "request__organization",
            "assigned_to",
            "workflow_step",
        )
        .filter(
            pk__in=step_ids,
            assigned_to=user,
            status=ApprovalStepStatus.PENDING,
            is_current=True,
        )
        .order_by("request__created_at")
    )

    summary = {
        "requested": len(step_ids),
        "processed": 0,
        "failed": 0,
        "errors": [],
    }

    for step in steps:
        try:
            if action == "approve":
                approve_current_step(
                    step=step,
                    user=user,
                    comment=comment,
                )

            elif action == "reject":
                reject_current_step(
                    step=step,
                    user=user,
                    comment=comment,
                )

            elif action == "comment":
                comment_on_current_step(
                    step=step,
                    user=user,
                    comment=comment,
                )

            else:
                raise ValueError("Invalid bulk action.")

            summary["processed"] += 1

        except ValueError as exc:
            summary["failed"] += 1
            summary["errors"].append(
                f"{step.request.request_number}: {str(exc)}"
            )

    return summary