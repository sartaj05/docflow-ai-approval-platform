from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import UserRole
from apps.api.permissions import HasActiveWorkspace, scoped_requests
from apps.audit.models import AuditAction
from apps.audit.services.audit_logger import create_audit_log
from apps.approvals.models import RequestDiscussionComment


class RequestDiscussionDeleteView(APIView):
    permission_classes = [IsAuthenticated, HasActiveWorkspace]

    def post(self, request, pk, comment_pk):
        document_request = scoped_requests(request.user).filter(pk=pk).first()
        if not document_request:
            return Response({"detail": "Not found."}, status=404)
        comment = RequestDiscussionComment.objects.filter(
            pk=comment_pk, request=document_request
        ).first()
        if not comment:
            return Response({"detail": "Comment not found."}, status=404)
        profile = getattr(request.user, "profile", None)
        is_admin = bool(
            profile
            and profile.role == UserRole.ORG_ADMIN
            and profile.organization_id == document_request.organization_id
        )
        if comment.author_id != request.user.pk and not is_admin and not request.user.is_superuser:
            return Response({"detail": "You cannot delete this comment."}, status=403)
        if comment.is_deleted:
            return Response({"detail": "Comment is already deleted."}, status=409)
        comment.is_deleted = True
        comment.deleted_at = timezone.now()
        comment.deleted_by = request.user
        comment.save(update_fields=["is_deleted", "deleted_at", "deleted_by", "updated_at"])
        create_audit_log(
            request=request,
            organization=document_request.organization,
            action=AuditAction.DELETED,
            model_name="RequestDiscussionComment",
            object_id=comment.pk,
            message=f"Comment deleted from {document_request.request_number} through the API.",
            extra_data={"request_id": document_request.pk},
        )
        return Response({"deleted": True, "comment_id": comment.pk})
