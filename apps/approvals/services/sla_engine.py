from django.db.models import Q
from django.utils import timezone

from apps.accounts.models import User, UserRole
from apps.approvals.models import ApprovalStep, ApprovalStepStatus, RequestStatus
from apps.audit.models import AuditAction
from apps.audit.services.audit_logger import create_audit_log
from apps.notifications.emails.sla_emails import (
    send_sla_escalated_email,
    send_sla_overdue_email,
    send_sla_reminder_email,
)
from apps.notifications.services.sla_notification_service import (
    notify_sla_escalated,
    notify_sla_overdue,
    notify_sla_reminder,
)


def get_pending_current_steps():
    return (
        ApprovalStep.objects.select_related(
            "request",
            "request__organization",
            "request__department",
            "assigned_to",
        )
        .filter(
            status=ApprovalStepStatus.PENDING,
            is_current=True,
            request__status__in=[
                RequestStatus.SUBMITTED,
                RequestStatus.IN_REVIEW,
            ],
            due_at__isnull=False,
        )
        .order_by("due_at")
    )


def get_escalation_user(approval_step):
    document_request = approval_step.request
    organization = document_request.organization

    if not organization:
        return None

    if document_request.department and document_request.department.head:
        department_head = document_request.department.head

        if approval_step.assigned_to_id != department_head.id:
            return department_head

    org_admin = (
        User.objects.filter(
            profile__organization=organization,
            profile__role=UserRole.ORG_ADMIN,
            is_active=True,
            profile__is_active=True,
        )
        .exclude(pk=approval_step.assigned_to_id)
        .first()
    )

    return org_admin


def should_send_reminder(approval_step, now):
    if approval_step.reminder_sent_at:
        return False

    if not approval_step.due_at:
        return False

    workflow_step = approval_step.request.workflow.steps.filter(
        step_order=approval_step.step_order,
    ).first()

    reminder_before_hours = workflow_step.reminder_before_hours if workflow_step else 4

    reminder_time = approval_step.due_at - timezone.timedelta(
        hours=reminder_before_hours,
    )

    return now >= reminder_time and now < approval_step.due_at


def should_escalate(approval_step, now):
    if not approval_step.due_at:
        return False

    if now <= approval_step.due_at:
        return False

    if approval_step.escalated_at:
        return False

    return True


def process_sla_step(approval_step, now=None):
    now = now or timezone.now()

    result = {
        "step_id": approval_step.pk,
        "reminder_sent": False,
        "overdue_marked": False,
        "escalated": False,
    }

    if should_send_reminder(approval_step, now):
        notify_sla_reminder(approval_step=approval_step)
        send_sla_reminder_email(approval_step)

        approval_step.reminder_sent_at = now
        approval_step.save(
            update_fields=[
                "reminder_sent_at",
                "updated_at",
            ]
        )

        create_audit_log(
            request=None,
            organization=approval_step.request.organization,
            action=AuditAction.UPDATED,
            model_name="ApprovalStep",
            object_id=approval_step.pk,
            message=(
                f"SLA reminder sent for Step {approval_step.step_order} "
                f"of {approval_step.request.request_number}."
            ),
            extra_data={
                "request_id": approval_step.request_id,
                "due_at": approval_step.due_at.isoformat() if approval_step.due_at else "",
            },
        )

        result["reminder_sent"] = True

    if approval_step.is_due_passed and not approval_step.is_overdue:
        approval_step.is_overdue = True
        approval_step.save(
            update_fields=[
                "is_overdue",
                "updated_at",
            ]
        )

        notify_sla_overdue(approval_step=approval_step)
        send_sla_overdue_email(approval_step)

        create_audit_log(
            request=None,
            organization=approval_step.request.organization,
            action=AuditAction.UPDATED,
            model_name="ApprovalStep",
            object_id=approval_step.pk,
            message=(
                f"Approval Step {approval_step.step_order} "
                f"for {approval_step.request.request_number} marked overdue."
            ),
            extra_data={
                "request_id": approval_step.request_id,
                "due_at": approval_step.due_at.isoformat() if approval_step.due_at else "",
            },
        )

        result["overdue_marked"] = True

    if should_escalate(approval_step, now):
        escalation_user = get_escalation_user(approval_step)

        if escalation_user:
            notify_sla_escalated(
                approval_step=approval_step,
                escalation_user=escalation_user,
            )

            send_sla_escalated_email(
                approval_step,
                escalation_user,
            )

            approval_step.escalated_at = now
            approval_step.escalation_count = approval_step.escalation_count + 1
            approval_step.save(
                update_fields=[
                    "escalated_at",
                    "escalation_count",
                    "updated_at",
                ]
            )

            create_audit_log(
                request=None,
                organization=approval_step.request.organization,
                action=AuditAction.UPDATED,
                model_name="ApprovalStep",
                object_id=approval_step.pk,
                message=(
                    f"Approval Step {approval_step.step_order} "
                    f"for {approval_step.request.request_number} escalated to "
                    f"{escalation_user.display_name}."
                ),
                extra_data={
                    "request_id": approval_step.request_id,
                    "escalation_user_id": escalation_user.pk,
                    "escalation_user": escalation_user.display_name,
                    "due_at": approval_step.due_at.isoformat() if approval_step.due_at else "",
                },
            )

            result["escalated"] = True

    return result


def run_sla_monitor():
    now = timezone.now()

    summary = {
        "checked": 0,
        "reminders_sent": 0,
        "overdue_marked": 0,
        "escalated": 0,
    }

    for approval_step in get_pending_current_steps():
        summary["checked"] += 1

        result = process_sla_step(
            approval_step=approval_step,
            now=now,
        )

        if result["reminder_sent"]:
            summary["reminders_sent"] += 1

        if result["overdue_marked"]:
            summary["overdue_marked"] += 1

        if result["escalated"]:
            summary["escalated"] += 1

    return summary