import os

from django.http import FileResponse
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.share_common import find_public_share_link
from apps.approvals.models import RequestStatus
from apps.reports.services.archive_builder import build_request_archive_zip


class PublicShareArchiveAPIView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request, token):
        link = find_public_share_link(token)
        if not link or not link.is_valid or link.document_request.status != RequestStatus.APPROVED:
            return Response({"detail": "This share link is invalid or expired."}, status=403)
        if not link.allow_archive_download:
            return Response({"detail": "This link does not allow archive downloads."}, status=403)
        link.mark_accessed()
        document_request = link.document_request
        filename = os.path.basename(f"{document_request.request_number}_shared_archive.zip")
        return FileResponse(
            build_request_archive_zip(document_request),
            as_attachment=True,
            filename=filename,
            content_type="application/zip",
        )
