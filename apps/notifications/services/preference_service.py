from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

from apps.notifications.models import NotificationPreference


CATEGORY_GENERAL = "general"
CATEGORY_WATCHED_REQUEST = "watched_request"
CATEGORY_COMMENT = "comment"
CATEGORY_APPROVAL = "approval"
CATEGORY_DOCUMENT = "document"
CATEGORY_AI = "ai"
CATEGORY_REMINDER = "reminder"
CATEGORY_CERTIFICATE = "certificate"
CATEGORY_DAILY_SUMMARY = "daily_summary"


def get_notification_preferences(user):
    preferences, created = NotificationPreference.objects.get_or_create(
        user=user,
    )

    return preferences


def is_in_app_allowed(user, category=CATEGORY_GENERAL):
    if not user or not user.is_authenticated:
        return False

    preferences = get_notification_preferences(user)

    if not preferences.in_app_enabled:
        return False

    if category == CATEGORY_WATCHED_REQUEST:
        return preferences.watched_request_in_app

    if category == CATEGORY_COMMENT:
        return preferences.comments_in_app

    if category == CATEGORY_APPROVAL:
        return preferences.approvals_in_app

    if category == CATEGORY_DOCUMENT:
        return preferences.documents_in_app

    if category == CATEGORY_AI:
        return preferences.ai_in_app

    if category == CATEGORY_REMINDER:
        return preferences.reminders_in_app

    if category == CATEGORY_CERTIFICATE:
        return preferences.certificates_in_app

    return True


def is_email_allowed(user, category=CATEGORY_GENERAL):
    if not user or not user.is_authenticated:
        return False

    if not getattr(settings, "ENABLE_EMAIL_NOTIFICATIONS", True):
        return False

    if not user.email:
        return False

    preferences = get_notification_preferences(user)

    if not preferences.email_enabled:
        return False

    if category == CATEGORY_WATCHED_REQUEST:
        return preferences.watched_request_email

    if category == CATEGORY_COMMENT:
        return preferences.comments_email

    if category == CATEGORY_APPROVAL:
        return preferences.approvals_email

    if category == CATEGORY_DOCUMENT:
        return preferences.documents_email

    if category == CATEGORY_AI:
        return preferences.ai_email

    if category == CATEGORY_REMINDER:
        return preferences.reminders_email

    if category == CATEGORY_CERTIFICATE:
        return preferences.certificates_email

    if category == CATEGORY_DAILY_SUMMARY:
        return preferences.daily_summary_email

    return True

def send_email_notification_if_allowed(
    user,
    category,
    subject,
    message,
    target_url="",
    notification=None,
    organization=None,
    notification_type="",
    metadata=None,
):
    from apps.notifications.models import (
        NotificationDeliveryChannel,
        NotificationDeliveryStatus,
    )
    from apps.notifications.services.delivery_service import (
        create_delivery_log,
        mark_delivery_skipped,
        send_email_with_delivery_log,
    )

    delivery_log = create_delivery_log(
        recipient=user,
        notification=notification,
        organization=organization,
        channel=NotificationDeliveryChannel.EMAIL,
        status=NotificationDeliveryStatus.PENDING,
        notification_type=notification_type,
        preference_category=category,
        subject=subject,
        message=message,
        target_url=target_url,
        metadata=metadata or {},
    )

    if not is_email_allowed(user, category):
        mark_delivery_skipped(
            delivery_log,
            reason="Email notification disabled by user preference or global setting.",
        )
        return False

    result_log = send_email_with_delivery_log(delivery_log)

    return result_log.status == NotificationDeliveryStatus.SENT