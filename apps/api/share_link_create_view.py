from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.permissions import HasActiveWorkspace
from apps.api.share_common import (
    can_manage_share_links,
    get_share_request,
    serialize_share_link,
)
from apps.approvals.models import RequestStatus
from apps.audit.models import AuditAction
from apps.audit.services.audit_logger import create_audit_log
from apps.reports.models import RequestShareLink


class ShareLinkCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=150, required=False, allow_blank=True)
    expires_in_days = serializers.IntegerField(min_value=1, max_value=30, default=7)
    allow_summary_view = serializers.BooleanField(default=True)
    allow_archive_download = serializers.BooleanField(default=False)


class RequestShareLinkCreateAPIView(APIView):
    permission_classes = [IsAuthenticated, HasActiveWorkspace]

    def post(self, request, pk):
        document_request = get_share_request(request.user, pk)
        if not document_request:
            return Response({"detail": "Not found."}, status=404)
        if not can_manage_share_links(request.user, document_request):
            return Response({"detail": "You cannot create share links for this request."}, status=403)
        if document_request.status != RequestStatus.APPROVED:
            return Response({"detail": "Share links can be created only for approved requests."}, status=409)
        serializer = ShareLinkCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        link = RequestShareLink.objects.create(
            document_request=document_request,
            created_by=request.user,
            title=values.get("title", "").strip() or "Public Share Link",
            expires_at=timezone.now() + timedelta(days=values["expires_in_days"]),
            allow_summary_view=values["allow_summary_view"],
            allow_archive_download=values["allow_archive_download"],
        )
        create_audit_log(
            request=request,
            organization=document_request.organization,
            action=AuditAction.CREATED,
            model_name="RequestShareLink",
            object_id=link.pk,
            message=f"Secure share link created for {document_request.request_number} through the API.",
            extra_data={
                "request_id": document_request.pk,
                "expires_at": link.expires_at.isoformat(),
                "allow_summary_view": link.allow_summary_view,
                "allow_archive_download": link.allow_archive_download,
            },
        )
        return Response(serialize_share_link(link, request), status=201)
