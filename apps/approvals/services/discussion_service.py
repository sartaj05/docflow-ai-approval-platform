import re

from django.conf import settings
from django.urls import reverse

from apps.accounts.models import User
from apps.notifications.models import NotificationType
from apps.notifications.services.notification_service import create_notification


MENTION_PATTERN = r"@([A-Za-z0-9_.-]+)"


def extract_mentioned_usernames(message):
    usernames = re.findall(MENTION_PATTERN, message or "")
    return list(dict.fromkeys(usernames))


def get_mention_users_for_request(document_request, message):
    usernames = extract_mentioned_usernames(message)

    if not usernames:
        return User.objects.none()

    queryset = User.objects.filter(
        username__in=usernames,
        is_active=True,
    )

    if document_request.organization:
        queryset = queryset.filter(
            profile__organization=document_request.organization,
        )

    return queryset.distinct()


def get_request_discussion_url(document_request):
    return reverse(
        "approvals:request_detail",
        args=[document_request.pk],
    ) + "#discussion"


def notify_discussion_comment_created(comment, request_user=None):
    document_request = comment.request
    actor = comment.author
    target_url = get_request_discussion_url(document_request)

    recipients = set()

    if document_request.created_by and document_request.created_by_id != getattr(actor, "id", None):
        recipients.add(document_request.created_by)

    for step in document_request.approval_steps.select_related("assigned_to").all():
        if step.assigned_to and step.assigned_to_id != getattr(actor, "id", None):
            recipients.add(step.assigned_to)

    for user in comment.mentioned_users.all():
        if user.id != getattr(actor, "id", None):
            recipients.add(user)

    for recipient in recipients:
        title = f"New comment on {document_request.request_number}"

        if recipient in comment.mentioned_users.all():
            title = f"You were mentioned on {document_request.request_number}"

        create_notification(
            recipient=recipient,
            actor=actor,
            organization=document_request.organization,
            notification_type=NotificationType.REQUEST_COMMENTED,
            title=title,
            message=(
                f"{actor.display_name if actor else 'Someone'} commented on "
                f"{document_request.request_number}: {document_request.title}"
            ),
            target_url=target_url,
            object_type="RequestDiscussionComment",
            object_id=str(comment.pk),
        )