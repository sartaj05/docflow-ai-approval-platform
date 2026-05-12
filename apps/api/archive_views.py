import os

from django.http import FileResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.permissions import HasActiveWorkspace, scoped_requests
from apps.audit.models import AuditAction
from apps.audit.services.audit_logger import create_audit_log
from apps.approvals.models import RequestStatus
from apps.reports.services.archive_builder import build_request_archive_zip


class RequestArchiveDownloadView(APIView):
    permission_classes = [IsAuthenticated, HasActiveWorkspace]

    def get(self, request, pk):
        document_request = scoped_requests(request.user).filter(pk=pk).first()
        if not document_request:
            return Response({"detail": "Not found."}, status=404)
        if document_request.status != RequestStatus.APPROVED:
            return Response(
                {"detail": "The final archive is available after request approval."},
                status=409,
            )

        archive_buffer = build_request_archive_zip(document_request)
        filename = os.path.basename(
            f"{document_request.request_number}_final_archive.zip".replace("/", "-")
        )
        create_audit_log(
            request=request,
            organization=document_request.organization,
            action=AuditAction.DOWNLOADED,
            model_name="DocumentRequestArchive",
            object_id=document_request.pk,
            message=f"Final archive downloaded through the API for {document_request.request_number}.",
            extra_data={
                "request_number": document_request.request_number,
                "filename": filename,
                "status": document_request.status,
            },
        )
        return FileResponse(
            archive_buffer,
            as_attachment=True,
            filename=filename,
            content_type="application/zip",
        )
