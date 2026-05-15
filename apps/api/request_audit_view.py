from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.audit_feed_view import audit_queryset
from apps.api.permissions import HasActiveWorkspace, scoped_requests
from apps.audit.models import AuditLog
from apps.accounts.models import UserRole


class RequestAuditHistoryView(APIView):
    permission_classes = [IsAuthenticated, HasActiveWorkspace]

    def get(self, request, pk):
        document_request = scoped_requests(request.user).filter(pk=pk).first()
        if not document_request:
            return Response({"detail": "Not found."}, status=404)
        profile = getattr(request.user, "profile", None)
        if not request.user.is_superuser and (not profile or profile.role not in {UserRole.ORG_ADMIN, UserRole.AUDITOR}):
            return Response({"detail": "You do not have access to audit logs."}, status=403)
        rows = audit_queryset(request.user).filter(
            organization=document_request.organization,
        ).filter(
            model_name="DocumentRequest",
            object_id=str(document_request.pk),
        ).order_by("-created_at")
        return Response([{
            "id": item.pk,
            "action": item.action,
            "message": item.message,
            "actor": item.user.display_name if item.user_id else None,
            "created_at": item.created_at.isoformat(),
        } for item in rows[:100]])
