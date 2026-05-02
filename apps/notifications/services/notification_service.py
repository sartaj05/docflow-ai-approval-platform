from django.conf import settings
from django.urls import reverse

from apps.notifications.models import Notification, NotificationType

from apps.notifications.models import Notification
from apps.notifications.services.preference_service import (
    CATEGORY_GENERAL,
    is_in_app_allowed,
    send_email_notification_if_allowed,
)

from apps.notifications.models import (
    Notification,
    NotificationDeliveryChannel,
    NotificationDeliveryStatus,
)
from apps.notifications.services.delivery_service import create_delivery_log
from apps.notifications.services.preference_service import (
    CATEGORY_GENERAL,
    is_in_app_allowed,
    send_email_notification_if_allowed,
)


def create_notification(
    recipient,
    title,
    message,
    notification_type,
    organization=None,
    actor=None,
    target_url="",
    object_type="",
    object_id="",
    preference_category=CATEGORY_GENERAL,
    send_email=False,
):
    if not recipient:
        return None

    notification = None

    if is_in_app_allowed(
        user=recipient,
        category=preference_category,
    ):
        notification = Notification.objects.create(
            organization=organization,
            recipient=recipient,
            actor=actor,
            notification_type=notification_type,
            title=title,
            message=message,
            target_url=target_url,
            object_type=object_type,
            object_id=str(object_id) if object_id else "",
        )

        create_delivery_log(
            recipient=recipient,
            notification=notification,
            organization=organization,
            channel=NotificationDeliveryChannel.IN_APP,
            status=NotificationDeliveryStatus.SENT,
            notification_type=notification_type,
            preference_category=preference_category,
            subject=title,
            message=message,
            target_url=target_url,
            metadata={
                "object_type": object_type,
                "object_id": str(object_id) if object_id else "",
            },
        )
    else:
        create_delivery_log(
            recipient=recipient,
            organization=organization,
            channel=NotificationDeliveryChannel.IN_APP,
            status=NotificationDeliveryStatus.SKIPPED,
            notification_type=notification_type,
            preference_category=preference_category,
            subject=title,
            message=message,
            target_url=target_url,
            metadata={
                "reason": "In-app notification disabled by user preference.",
                "object_type": object_type,
                "object_id": str(object_id) if object_id else "",
            },
        )

    if send_email:
        send_email_notification_if_allowed(
            user=recipient,
            category=preference_category,
            subject=title,
            message=message,
            target_url=target_url,
            notification=notification,
            organization=organization,
            notification_type=notification_type,
            metadata={
                "object_type": object_type,
                "object_id": str(object_id) if object_id else "",
            },
        )

    return notification

def notify_approval_assigned(*, approval_step, actor=None):
    document_request = approval_step.request

    if not approval_step.assigned_to:
        return None

    target_url = reverse(
        "approvals:request_detail",
        kwargs={"pk": document_request.pk},
    )

    notification = create_notification(
        recipient=approval_step.assigned_to,
        actor=actor,
        organization=document_request.organization,
        notification_type=NotificationType.REQUEST_ASSIGNED,
        title=f"Approval assigned: {document_request.request_number}",
        message=(
            f"You have been assigned Step {approval_step.step_order} "
            f"for request '{document_request.title}'."
        ),
        target_url=target_url,
        object_type="ApprovalStep",
        object_id=approval_step.pk,
    )

    send_email_for_approval_assigned(approval_step)

    return notification


def notify_request_approved(*, document_request, actor=None):
    if not document_request.created_by:
        return None

    target_url = reverse(
        "approvals:request_detail",
        kwargs={"pk": document_request.pk},
    )

    notification = create_notification(
        recipient=document_request.created_by,
        actor=actor,
        organization=document_request.organization,
        notification_type=NotificationType.REQUEST_APPROVED,
        title=f"Request approved: {document_request.request_number}",
        message=f"Your request '{document_request.title}' has been approved.",
        target_url=target_url,
        object_type="DocumentRequest",
        object_id=document_request.pk,
    )

    send_email_for_request_approved(document_request, actor)

    return notification


def notify_request_rejected(*, document_request, actor=None, comment=""):
    if not document_request.created_by:
        return None

    target_url = reverse(
        "approvals:request_detail",
        kwargs={"pk": document_request.pk},
    )

    message = f"Your request '{document_request.title}' has been rejected."

    if comment:
        message = f"{message} Reason: {comment}"

    notification = create_notification(
        recipient=document_request.created_by,
        actor=actor,
        organization=document_request.organization,
        notification_type=NotificationType.REQUEST_REJECTED,
        title=f"Request rejected: {document_request.request_number}",
        message=message,
        target_url=target_url,
        object_type="DocumentRequest",
        object_id=document_request.pk,
    )

    send_email_for_request_rejected(document_request, actor, comment)

    return notification


def notify_request_commented(*, document_request, approval_step, actor=None, comment=""):
    if not document_request.created_by:
        return None

    if actor and document_request.created_by_id == actor.id:
        return None

    target_url = reverse(
        "approvals:request_detail",
        kwargs={"pk": document_request.pk},
    )

    return create_notification(
        recipient=document_request.created_by,
        actor=actor,
        organization=document_request.organization,
        notification_type=NotificationType.REQUEST_COMMENTED,
        title=f"Comment on request: {document_request.request_number}",
        message=(
            f"A comment was added on Step {approval_step.step_order} "
            f"for request '{document_request.title}'."
        ),
        target_url=target_url,
        object_type="ApprovalStep",
        object_id=approval_step.pk,
    )


def email_notifications_enabled():
    return getattr(settings, "ENABLE_EMAIL_NOTIFICATIONS", True)


def send_email_for_approval_assigned(approval_step):
    if not email_notifications_enabled():
        return False

    if getattr(settings, "SEND_EMAIL_ASYNC", False):
        from apps.notifications.tasks import send_approval_assigned_email_task

        send_approval_assigned_email_task.delay(approval_step.pk)
        return True

    from apps.notifications.emails.approval_emails import send_approval_assigned_email

    return send_approval_assigned_email(approval_step)


def send_email_for_request_approved(document_request, actor=None):
    if not email_notifications_enabled():
        return False

    if getattr(settings, "SEND_EMAIL_ASYNC", False):
        from apps.notifications.tasks import send_request_approved_email_task

        send_request_approved_email_task.delay(
            document_request.pk,
            actor.pk if actor else None,
        )
        return True

    from apps.notifications.emails.approval_emails import send_request_approved_email

    return send_request_approved_email(
        document_request=document_request,
        actor=actor,
    )


def send_email_for_request_rejected(document_request, actor=None, comment=""):
    if not email_notifications_enabled():
        return False

    if getattr(settings, "SEND_EMAIL_ASYNC", False):
        from apps.notifications.tasks import send_request_rejected_email_task

        send_request_rejected_email_task.delay(
            document_request.pk,
            actor.pk if actor else None,
            comment,
        )
        return True

    from apps.notifications.emails.approval_emails import send_request_rejected_email

    return send_request_rejected_email(
        document_request=document_request,
        actor=actor,
        comment=comment,
    )