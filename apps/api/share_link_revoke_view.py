from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.permissions import HasActiveWorkspace
from apps.api.share_common import can_manage_share_links, get_share_request
from apps.audit.models import AuditAction
from apps.audit.services.audit_logger import create_audit_log
from apps.reports.models import RequestShareLink


class RequestShareLinkRevokeAPIView(APIView):
    permission_classes = [IsAuthenticated, HasActiveWorkspace]

    def post(self, request, pk, link_pk):
        document_request = get_share_request(request.user, pk)
        if not document_request:
            return Response({"detail": "Not found."}, status=404)
        if not can_manage_share_links(request.user, document_request):
            return Response({"detail": "You cannot revoke share links for this request."}, status=403)
        link = RequestShareLink.objects.filter(
            pk=link_pk, document_request=document_request
        ).first()
        if not link:
            return Response({"detail": "Share link not found."}, status=404)
        if not link.is_active:
            return Response({"detail": "Share link is already revoked."}, status=409)
        link.revoke(user=request.user)
        create_audit_log(
            request=request,
            organization=document_request.organization,
            action=AuditAction.UPDATED,
            model_name="RequestShareLink",
            object_id=link.pk,
            message=f"Secure share link revoked for {document_request.request_number} through the API.",
            extra_data={"request_id": document_request.pk},
        )
        return Response({"id": link.pk, "is_active": link.is_active, "revoked_at": link.revoked_at.isoformat()})
