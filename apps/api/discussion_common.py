from rest_framework import serializers

from apps.approvals.models import RequestDiscussionComment


class DiscussionCommentInputSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=10000, trim_whitespace=True)

    def validate_message(self, value):
        if not value.strip():
            raise serializers.ValidationError("A comment cannot be empty.")
        return value.strip()


def serialize_comment(comment):
    return {
        "id": comment.pk,
        "parent_id": comment.parent_id,
        "message": "[deleted]" if comment.is_deleted else comment.message,
        "is_deleted": comment.is_deleted,
        "author": comment.author.display_name if comment.author_id else None,
        "mentioned_users": list(comment.mentioned_users.values_list("username", flat=True)),
        "attachments": [{
            "id": item.pk,
            "filename": item.original_filename,
            "file_size": item.file_size,
            "created_at": item.created_at.isoformat(),
        } for item in comment.attachments.all()],
        "created_at": comment.created_at.isoformat(),
        "updated_at": comment.updated_at.isoformat(),
    }


def create_comment(*, request, document_request, message, parent=None):
    from apps.approvals.services.discussion_service import (
        get_mention_users_for_request,
        notify_discussion_comment_created,
    )
    from apps.audit.models import AuditAction
    from apps.audit.services.audit_logger import create_audit_log

    comment = RequestDiscussionComment.objects.create(
        request=document_request,
        parent=parent,
        author=request.user,
        message=message,
        is_internal=True,
    )
    mentioned = get_mention_users_for_request(document_request, message)
    if mentioned.exists():
        comment.mentioned_users.set(mentioned)
    notify_discussion_comment_created(comment=comment, request_user=request.user)
    create_audit_log(
        request=request,
        organization=document_request.organization,
        action=AuditAction.COMMENTED,
        model_name="RequestDiscussionComment",
        object_id=comment.pk,
        message=f"Comment added on {document_request.request_number} through the API.",
        extra_data={
            "request_id": document_request.pk,
            "parent_id": parent.pk if parent else None,
            "mentioned_users": list(mentioned.values_list("username", flat=True)),
        },
    )
    return comment
