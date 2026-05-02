import traceback

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from apps.notifications.models import (
    NotificationDeliveryChannel,
    NotificationDeliveryLog,
    NotificationDeliveryStatus,
)


def create_delivery_log(
    recipient,
    subject,
    message,
    channel=NotificationDeliveryChannel.EMAIL,
    notification=None,
    digest_log=None,
    organization=None,
    notification_type="",
    preference_category="",
    target_url="",
    metadata=None,
    status=NotificationDeliveryStatus.PENDING,
):
    recipient_email = getattr(recipient, "email", "") or ""

    delivery_log = NotificationDeliveryLog.objects.create(
        recipient=recipient,
        notification=notification,
        digest_log=digest_log,
        organization=organization,
        channel=channel,
        status=status,
        notification_type=notification_type or "",
        preference_category=preference_category or "",
        subject=subject,
        message=message or "",
        target_url=target_url or "",
        recipient_email=recipient_email,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "") or "",
        provider="SMTP",
        queued_at=timezone.now() if status == NotificationDeliveryStatus.PENDING else None,
        skipped_at=timezone.now() if status == NotificationDeliveryStatus.SKIPPED else None,
        metadata=metadata or {},
    )

    return delivery_log


def mark_delivery_sent(delivery_log):
    delivery_log.status = NotificationDeliveryStatus.SENT
    delivery_log.sent_at = timezone.now()
    delivery_log.last_attempt_at = timezone.now()
    delivery_log.error_message = ""
    delivery_log.traceback_text = ""
    delivery_log.save(
        update_fields=[
            "status",
            "sent_at",
            "last_attempt_at",
            "error_message",
            "traceback_text",
            "updated_at",
        ]
    )

    return delivery_log


def mark_delivery_failed(delivery_log, exc):
    delivery_log.status = NotificationDeliveryStatus.FAILED
    delivery_log.failed_at = timezone.now()
    delivery_log.last_attempt_at = timezone.now()
    delivery_log.error_message = str(exc)
    delivery_log.traceback_text = traceback.format_exc()
    delivery_log.save(
        update_fields=[
            "status",
            "failed_at",
            "last_attempt_at",
            "error_message",
            "traceback_text",
            "updated_at",
        ]
    )

    return delivery_log


def mark_delivery_retrying(delivery_log, celery_task_id=""):
    delivery_log.status = NotificationDeliveryStatus.RETRYING
    delivery_log.retry_count += 1
    delivery_log.last_attempt_at = timezone.now()

    if celery_task_id:
        delivery_log.celery_task_id = celery_task_id

    delivery_log.save(
        update_fields=[
            "status",
            "retry_count",
            "last_attempt_at",
            "celery_task_id",
            "updated_at",
        ]
    )

    return delivery_log


def mark_delivery_skipped(delivery_log, reason=""):
    delivery_log.status = NotificationDeliveryStatus.SKIPPED
    delivery_log.skipped_at = timezone.now()
    delivery_log.error_message = reason
    delivery_log.save(
        update_fields=[
            "status",
            "skipped_at",
            "error_message",
            "updated_at",
        ]
    )

    return delivery_log


def send_email_with_delivery_log(delivery_log):
    if not delivery_log.recipient_email:
        mark_delivery_skipped(
            delivery_log,
            reason="Recipient email is missing.",
        )
        return delivery_log

    try:
        send_mail(
            subject=delivery_log.subject,
            message=delivery_log.message,
            from_email=delivery_log.from_email or getattr(settings, "DEFAULT_FROM_EMAIL", None),
            recipient_list=[delivery_log.recipient_email],
            fail_silently=False,
        )

        return mark_delivery_sent(delivery_log)

    except Exception as exc:
        return mark_delivery_failed(delivery_log, exc)


def retry_delivery(delivery_log):
    if not delivery_log.can_retry:
        return delivery_log

    mark_delivery_retrying(delivery_log)

    return send_email_with_delivery_log(delivery_log)