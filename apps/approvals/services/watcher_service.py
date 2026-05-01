from django.urls import reverse

from apps.approvals.models import RequestWatcher
from apps.notifications.models import NotificationType
from apps.notifications.services.notification_service import create_notification
from apps.notifications.services.preference_service import (
    CATEGORY_APPROVAL,
    CATEGORY_AI,
    CATEGORY_CERTIFICATE,
    CATEGORY_COMMENT,
    CATEGORY_DOCUMENT,
    CATEGORY_GENERAL,
    CATEGORY_REMINDER,
    CATEGORY_WATCHED_REQUEST,
)

ACTIVITY_COMMENT = "comment"
ACTIVITY_DOCUMENT = "document"
ACTIVITY_APPROVAL = "approval"
ACTIVITY_AI = "ai"
ACTIVITY_CERTIFICATE = "certificate"
ACTIVITY_REMINDER = "reminder"
ACTIVITY_GENERAL = "general"
def get_preference_category_for_activity(activity_type):
    if activity_type == ACTIVITY_COMMENT:
        return CATEGORY_COMMENT

    if activity_type == ACTIVITY_DOCUMENT:
        return CATEGORY_DOCUMENT

    if activity_type == ACTIVITY_APPROVAL:
        return CATEGORY_APPROVAL

    if activity_type == ACTIVITY_AI:
        return CATEGORY_AI

    if activity_type == ACTIVITY_CERTIFICATE:
        return CATEGORY_CERTIFICATE

    if activity_type == ACTIVITY_REMINDER:
        return CATEGORY_REMINDER

    if activity_type == ACTIVITY_GENERAL:
        return CATEGORY_WATCHED_REQUEST

    return CATEGORY_GENERAL

def get_request_detail_url(document_request):
    return reverse(
        "approvals:request_detail",
        args=[document_request.pk],
    )


def get_or_create_watcher(document_request, user):
    watcher, created = RequestWatcher.objects.get_or_create(
        request=document_request,
        user=user,
        defaults={
            "is_active": True,
        },
    )

    if not watcher.is_active:
        watcher.is_active = True
        watcher.save(update_fields=["is_active", "updated_at"])

    return watcher, created


def toggle_request_watch(document_request, user):
    watcher, created = RequestWatcher.objects.get_or_create(
        request=document_request,
        user=user,
        defaults={
            "is_active": True,
        },
    )

    if created:
        return watcher, True

    watcher.is_active = not watcher.is_active
    watcher.save(update_fields=["is_active", "updated_at"])

    return watcher, watcher.is_active


def user_is_watching_request(document_request, user):
    if not user or not user.is_authenticated:
        return False

    return RequestWatcher.objects.filter(
        request=document_request,
        user=user,
        is_active=True,
    ).exists()


def get_active_watchers(document_request):
    return (
        RequestWatcher.objects.select_related("user")
        .filter(
            request=document_request,
            is_active=True,
            user__is_active=True,
        )
    )


def watcher_allows_activity(watcher, activity_type):
    if activity_type == ACTIVITY_COMMENT:
        return watcher.receive_comment_notifications

    if activity_type == ACTIVITY_DOCUMENT:
        return watcher.receive_document_notifications

    if activity_type == ACTIVITY_APPROVAL:
        return watcher.receive_approval_notifications

    if activity_type == ACTIVITY_AI:
        return watcher.receive_ai_notifications

    if activity_type == ACTIVITY_CERTIFICATE:
        return watcher.receive_certificate_notifications

    if activity_type == ACTIVITY_REMINDER:
        return watcher.receive_reminder_notifications

    return True
def notify_request_watchers(
    document_request,
    actor=None,
    activity_type=ACTIVITY_GENERAL,
    title="Request updated",
    message="An update was made on a watched approval request.",
    target_url="",
    object_type="DocumentRequest",
    object_id="",
    exclude_actor=True,
    send_email=True,
):
    if not target_url:
        target_url = get_request_detail_url(document_request)

    preference_category = get_preference_category_for_activity(activity_type)

    sent_count = 0

    for watcher in get_active_watchers(document_request):
        recipient = watcher.user

        if exclude_actor and actor and recipient.id == actor.id:
            continue

        if not watcher_allows_activity(watcher, activity_type):
            continue

        notification = create_notification(
            recipient=recipient,
            actor=actor,
            organization=document_request.organization,
            notification_type=NotificationType.INFO,
            title=title,
            message=message,
            target_url=target_url,
            object_type=object_type,
            object_id=str(object_id) if object_id else str(document_request.pk),
            preference_category=preference_category,
            send_email=send_email,
        )

        if notification:
            sent_count += 1

    return sent_count