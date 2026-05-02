from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

from apps.approvals.models import (
    ApprovalStep,
    ApprovalStepStatus,
    RequestWatcher,
)
from apps.approvals.services.activity_timeline import build_request_activity_timeline
from apps.notifications.models import (
    Notification,
    NotificationDeliveryChannel,
    NotificationDeliveryStatus,
    NotificationDigestLog,
)
from apps.notifications.services.delivery_service import (
    create_delivery_log,
    send_email_with_delivery_log,
)
from apps.notifications.services.preference_service import (
    CATEGORY_DAILY_SUMMARY,
    is_email_allowed,
)


User = get_user_model()


def get_app_base_url():
    return getattr(
        settings,
        "DOCFLOW_APP_URL",
        "http://127.0.0.1:8000",
    ).rstrip("/")


def get_digest_window(digest_type):
    now = timezone.now()

    if digest_type == NotificationDigestLog.DigestType.WEEKLY:
        return now - timedelta(days=7), now

    return now - timedelta(days=1), now


def get_user_digest_data(
    user,
    digest_type=NotificationDigestLog.DigestType.DAILY,
):
    start_at, end_at = get_digest_window(digest_type)

    unread_notifications = (
        Notification.objects.select_related(
            "actor",
            "organization",
        )
        .filter(
            recipient=user,
            is_read=False,
            created_at__gte=start_at,
            created_at__lte=end_at,
        )
        .order_by("-created_at")
    )

    pending_approvals = (
        ApprovalStep.objects.select_related(
            "request",
            "request__organization",
            "request__department",
            "request__created_by",
            "assigned_to",
        )
        .filter(
            assigned_to=user,
            status=ApprovalStepStatus.PENDING,
            is_current=True,
        )
        .order_by(
            "due_at",
            "-request__priority",
            "-created_at",
        )
    )

    overdue_approvals = pending_approvals.filter(
        Q(is_overdue=True)
        | Q(due_at__lt=timezone.now())
    )

    watched_qs = (
        RequestWatcher.objects.select_related(
            "request",
            "request__organization",
            "request__department",
            "request__created_by",
        )
        .filter(
            user=user,
            is_active=True,
        )
        .order_by("-updated_at")
    )

    watched_requests = [
        watcher.request
        for watcher in watched_qs[:15]
    ]

    watched_activity_items = []

    for document_request in watched_requests[:8]:
        timeline_items = build_request_activity_timeline(
            document_request=document_request,
            limit=10,
        )

        for item in timeline_items:
            if item.timestamp and start_at <= item.timestamp <= end_at:
                item.meta = item.meta or {}
                item.meta["request_id"] = document_request.pk
                item.meta["request_number"] = document_request.request_number
                item.meta["request_title"] = document_request.title
                watched_activity_items.append(item)

    watched_activity_items = sorted(
        watched_activity_items,
        key=lambda item: item.timestamp,
        reverse=True,
    )[:25]

    base_url = get_app_base_url()

    return {
        "user": user,
        "digest_type": digest_type,
        "start_at": start_at,
        "end_at": end_at,
        "base_url": base_url,
        "my_activity_url": f"{base_url}{reverse('dashboard:my_activity')}",
        "approval_inbox_url": f"{base_url}{reverse('approvals:approval_inbox')}",
        "notifications_url": f"{base_url}{reverse('notifications:list')}",
        "preferences_url": f"{base_url}{reverse('notifications:preferences')}",
        "unread_notifications": unread_notifications[:20],
        "unread_notification_count": unread_notifications.count(),
        "pending_approvals": pending_approvals[:20],
        "pending_approval_count": pending_approvals.count(),
        "overdue_approvals": overdue_approvals[:20],
        "overdue_approval_count": overdue_approvals.count(),
        "watched_requests": watched_requests,
        "watched_request_count": watched_qs.count(),
        "watched_activity_items": watched_activity_items,
        "watched_activity_count": len(watched_activity_items),
    }


def user_has_digest_content(data):
    return any(
        [
            data["unread_notification_count"],
            data["pending_approval_count"],
            data["overdue_approval_count"],
            data["watched_activity_count"],
        ]
    )


def build_digest_subject(data):
    digest_label = (
        "Weekly"
        if data["digest_type"] == NotificationDigestLog.DigestType.WEEKLY
        else "Daily"
    )

    return (
        f"DocFlow AI {digest_label} Digest: "
        f"{data['pending_approval_count']} pending, "
        f"{data['unread_notification_count']} unread"
    )


def get_digest_template(digest_type):
    if digest_type == NotificationDigestLog.DigestType.WEEKLY:
        return "notifications/email/weekly_digest.txt"

    return "notifications/email/daily_digest.txt"


def create_digest_log(user, digest_type, subject, data):
    return NotificationDigestLog.objects.create(
        user=user,
        digest_type=digest_type,
        subject=subject,
        sent_to_email=user.email,
        unread_notification_count=data["unread_notification_count"],
        pending_approval_count=data["pending_approval_count"],
        overdue_approval_count=data["overdue_approval_count"],
        watched_request_count=data["watched_request_count"],
        watched_activity_count=data["watched_activity_count"],
        success=False,
    )


def create_digest_delivery_log(user, digest_log, digest_type, subject, message, data):
    return create_delivery_log(
        recipient=user,
        digest_log=digest_log,
        organization=None,
        channel=NotificationDeliveryChannel.EMAIL,
        status=NotificationDeliveryStatus.PENDING,
        notification_type="DIGEST",
        preference_category=CATEGORY_DAILY_SUMMARY,
        subject=subject,
        message=message,
        target_url=data["my_activity_url"],
        metadata={
            "digest_type": digest_type,
            "unread_notification_count": data["unread_notification_count"],
            "pending_approval_count": data["pending_approval_count"],
            "overdue_approval_count": data["overdue_approval_count"],
            "watched_request_count": data["watched_request_count"],
            "watched_activity_count": data["watched_activity_count"],
        },
    )


def update_digest_log_from_delivery(digest_log, delivery_log):
    if delivery_log.status == NotificationDeliveryStatus.SENT:
        digest_log.success = True
        digest_log.error_message = ""
        digest_log.save(
            update_fields=[
                "success",
                "error_message",
            ]
        )
        return digest_log

    digest_log.success = False
    digest_log.error_message = delivery_log.error_message
    digest_log.save(
        update_fields=[
            "success",
            "error_message",
        ]
    )

    return digest_log


def send_user_digest(
    user,
    digest_type=NotificationDigestLog.DigestType.DAILY,
    force=False,
):
    if not user.email:
        return None

    if not force and not is_email_allowed(user, CATEGORY_DAILY_SUMMARY):
        return None

    data = get_user_digest_data(
        user=user,
        digest_type=digest_type,
    )

    if not force and not user_has_digest_content(data):
        return None

    subject = build_digest_subject(data)
    template_name = get_digest_template(digest_type)
    message = render_to_string(template_name, data)

    digest_log = create_digest_log(
        user=user,
        digest_type=digest_type,
        subject=subject,
        data=data,
    )

    delivery_log = create_digest_delivery_log(
        user=user,
        digest_log=digest_log,
        digest_type=digest_type,
        subject=subject,
        message=message,
        data=data,
    )

    delivery_log = send_email_with_delivery_log(delivery_log)

    update_digest_log_from_delivery(
        digest_log=digest_log,
        delivery_log=delivery_log,
    )

    return digest_log


def get_digest_eligible_users():
    return (
        User.objects.filter(
            is_active=True,
            email__isnull=False,
        )
        .exclude(email="")
        .select_related("notification_preferences")
        .order_by("id")
    )


def send_digest_to_all_users(
    digest_type=NotificationDigestLog.DigestType.DAILY,
    force=False,
):
    total_users = 0
    sent_count = 0
    skipped_count = 0
    failed_count = 0

    for user in get_digest_eligible_users():
        total_users += 1

        digest_log = send_user_digest(
            user=user,
            digest_type=digest_type,
            force=force,
        )

        if digest_log is None:
            skipped_count += 1
            continue

        if digest_log.success:
            sent_count += 1
        else:
            failed_count += 1

    return {
        "total_users": total_users,
        "sent_count": sent_count,
        "skipped_count": skipped_count,
        "failed_count": failed_count,
        "digest_type": digest_type,
    }