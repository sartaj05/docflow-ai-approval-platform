from django.urls import reverse

from apps.notifications.models import NotificationType
from apps.notifications.services.notification_service import create_notification


def notify_sla_reminder(*, approval_step):
    document_request = approval_step.request

    if not approval_step.assigned_to:
        return None

    target_url = reverse(
        "approvals:request_detail",
        kwargs={"pk": document_request.pk},
    )

    return create_notification(
        recipient=approval_step.assigned_to,
        actor=None,
        organization=document_request.organization,
        notification_type=NotificationType.SLA_REMINDER,
        title=f"SLA reminder: {document_request.request_number}",
        message=(
            f"Approval Step {approval_step.step_order} for "
            f"'{document_request.title}' is due soon."
        ),
        target_url=target_url,
        object_type="ApprovalStep",
        object_id=approval_step.pk,
    )


def notify_sla_overdue(*, approval_step):
    document_request = approval_step.request

    if not approval_step.assigned_to:
        return None

    target_url = reverse(
        "approvals:request_detail",
        kwargs={"pk": document_request.pk},
    )

    return create_notification(
        recipient=approval_step.assigned_to,
        actor=None,
        organization=document_request.organization,
        notification_type=NotificationType.SLA_OVERDUE,
        title=f"Approval overdue: {document_request.request_number}",
        message=(
            f"Approval Step {approval_step.step_order} for "
            f"'{document_request.title}' is overdue."
        ),
        target_url=target_url,
        object_type="ApprovalStep",
        object_id=approval_step.pk,
    )


def notify_sla_escalated(*, approval_step, escalation_user):
    document_request = approval_step.request

    if not escalation_user:
        return None

    target_url = reverse(
        "approvals:request_detail",
        kwargs={"pk": document_request.pk},
    )

    return create_notification(
        recipient=escalation_user,
        actor=None,
        organization=document_request.organization,
        notification_type=NotificationType.SLA_ESCALATED,
        title=f"Approval escalated: {document_request.request_number}",
        message=(
            f"Approval Step {approval_step.step_order} assigned to "
            f"{approval_step.assigned_to.display_name if approval_step.assigned_to else 'an approver'} "
            f"is overdue and needs attention."
        ),
        target_url=target_url,
        object_type="ApprovalStep",
        object_id=approval_step.pk,
    )