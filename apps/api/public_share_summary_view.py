from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.share_common import find_public_share_link
from apps.approvals.models import RequestStatus


class PublicShareSummaryAPIView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request, token):
        link = find_public_share_link(token)
        if not link or not link.is_valid or link.document_request.status != RequestStatus.APPROVED:
            return Response({"detail": "This share link is invalid or expired."}, status=403)
        if not link.allow_summary_view:
            return Response({"detail": "This link does not allow summary viewing."}, status=403)
        link.mark_accessed()
        item = link.document_request
        return Response({
            "request_number": item.request_number,
            "title": item.title,
            "category": item.get_category_display(),
            "status": item.get_status_display(),
            "organization": item.organization.name if item.organization_id else None,
            "department": item.department.name if item.department_id else None,
            "approved_at": item.approved_at.isoformat() if item.approved_at else None,
            "summary": item.ai_summary,
            "attachments": [{
                "filename": attachment.original_filename,
                "file_type": attachment.file_type,
                "file_size": attachment.file_size,
            } for attachment in item.attachments.all()],
            "share_link": {
                "title": link.title,
                "expires_at": link.expires_at.isoformat(),
            },
        })
