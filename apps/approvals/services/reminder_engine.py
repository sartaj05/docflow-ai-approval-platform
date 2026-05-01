from django.urls import reverse

from apps.approvals.models import ApprovalReminder, ApprovalStepStatus
from apps.notifications.models import NotificationType
from apps.notifications.services.notification_service import create_notification


def can_send_reminder_for_step(user, approval_step):
    if not user.is_authenticated:
        return False

    if approval_step.status != ApprovalStepStatus.PENDING:
        return False

    if not approval_step.is_current:
        return False

    document_request = approval_step.request

    if user.is_superuser:
        return True

    if document_request.created_by_id == user.id:
        return True

    profile = getattr(user, "profile", None)

    if not profile:
        return False

    if profile.role in ["ORG_ADMIN", "DEPARTMENT_HEAD", "AUDITOR"]:
        if profile.organization_id == document_request.organization_id:
            return True

    return False


def send_approval_reminder(*, approval_step, sent_by, message=""):
    if not approval_step.assigned_to:
        raise ValueError("This approval step does not have an assigned approver.")

    if approval_step.status != ApprovalStepStatus.PENDING or not approval_step.is_current:
        raise ValueError("Reminder can be sent only for current pending approval step.")

    document_request = approval_step.request

    reminder = ApprovalReminder.objects.create(
        request=document_request,
        step=approval_step,
        sent_to=approval_step.assigned_to,
        sent_by=sent_by,
        message=message,
    )

    target_url = reverse(
        "approvals:request_detail",
        kwargs={"pk": document_request.pk},
    )

    create_notification(
        recipient=approval_step.assigned_to,
        actor=sent_by,
        organization=document_request.organization,
        notification_type=NotificationType.APPROVAL_REMINDER,
        title=f"Approval reminder: {document_request.request_number}",
        message=(
            message
            or f"Reminder: approval is pending for {document_request.request_number}."
        ),
        target_url=target_url,
        object_type="ApprovalStep",
        object_id=approval_step.pk,
    )

    return reminder