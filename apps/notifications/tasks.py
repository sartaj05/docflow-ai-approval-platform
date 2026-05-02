from celery import shared_task

from apps.accounts.models import User
from apps.approvals.models import ApprovalStep, ApprovalStepStatus, DocumentRequest
from apps.notifications.emails.approval_emails import (
    send_approval_assigned_email,
    send_daily_pending_approval_summary_email,
    send_request_approved_email,
    send_request_rejected_email,
)


@shared_task(bind=True, max_retries=3)
def send_approval_assigned_email_task(self, approval_step_id):
    try:
        approval_step = ApprovalStep.objects.select_related(
            "request",
            "request__organization",
            "request__department",
            "assigned_to",
        ).get(pk=approval_step_id)

        return send_approval_assigned_email(approval_step)

    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def send_request_approved_email_task(self, document_request_id, actor_id=None):
    try:
        document_request = DocumentRequest.objects.select_related(
            "organization",
            "department",
            "created_by",
        ).get(pk=document_request_id)

        actor = None

        if actor_id:
            actor = User.objects.filter(pk=actor_id).first()

        return send_request_approved_email(
            document_request=document_request,
            actor=actor,
        )

    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def send_request_rejected_email_task(self, document_request_id, actor_id=None, comment=""):
    try:
        document_request = DocumentRequest.objects.select_related(
            "organization",
            "department",
            "created_by",
        ).get(pk=document_request_id)

        actor = None

        if actor_id:
            actor = User.objects.filter(pk=actor_id).first()

        return send_request_rejected_email(
            document_request=document_request,
            actor=actor,
            comment=comment,
        )

    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)


@shared_task
def send_daily_pending_approval_summary_task():
    approver_ids = (
        ApprovalStep.objects.filter(
            status=ApprovalStepStatus.PENDING,
            is_current=True,
            assigned_to__isnull=False,
            assigned_to__is_active=True,
        )
        .values_list("assigned_to_id", flat=True)
        .distinct()
    )

    sent_count = 0

    for user in User.objects.filter(id__in=approver_ids, is_active=True):
        pending_steps = ApprovalStep.objects.select_related(
            "request",
            "request__organization",
            "request__department",
            "request__created_by",
        ).filter(
            assigned_to=user,
            status=ApprovalStepStatus.PENDING,
            is_current=True,
        ).order_by("-request__priority", "request__created_at")

        if pending_steps.exists():
            sent = send_daily_pending_approval_summary_email(
                user=user,
                pending_steps=pending_steps,
            )

            if sent:
                sent_count += 1

    return {
        "sent_count": sent_count,
    }
from celery import shared_task

from apps.notifications.models import NotificationDigestLog
from apps.notifications.services.digest_service import send_digest_to_all_users
from apps.notifications.services.delivery_service import retry_delivery
from apps.notifications.models import NotificationDeliveryLog

@shared_task
def send_daily_notification_digest_task():
    return send_digest_to_all_users(
        digest_type=NotificationDigestLog.DigestType.DAILY,
        force=False,
    )


@shared_task
def send_weekly_notification_digest_task():
    return send_digest_to_all_users(
        digest_type=NotificationDigestLog.DigestType.WEEKLY,
        force=False,
    )  
@shared_task
def run_sla_monitor_task():
    from apps.approvals.services.sla_engine import run_sla_monitor

    return run_sla_monitor()

@shared_task
def retry_notification_delivery_task(delivery_log_id):
    try:
        delivery_log = NotificationDeliveryLog.objects.get(pk=delivery_log_id)
    except NotificationDeliveryLog.DoesNotExist:
        return {
            "success": False,
            "error": "Delivery log not found.",
        }

    result = retry_delivery(delivery_log)

    return {
        "success": result.status == "SENT",
        "delivery_log_id": result.pk,
        "status": result.status,
        "retry_count": result.retry_count,
    }