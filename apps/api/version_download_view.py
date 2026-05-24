import os

from django.http import FileResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.document_common import can_view_version_history, get_visible_attachment
from apps.api.permissions import HasActiveWorkspace
from apps.audit.models import AuditAction
from apps.audit.services.audit_logger import create_audit_log
from apps.documents.models import DocumentAttachmentVersion


class AttachmentVersionDownloadAPIView(APIView):
    permission_classes = [IsAuthenticated, HasActiveWorkspace]

    def get(self, request, attachment_pk, version_pk):
        attachment = get_visible_attachment(request.user, attachment_pk)
        if not attachment:
            return Response({"detail": "Not found."}, status=404)
        if not can_view_version_history(request.user, attachment):
            return Response({"detail": "You do not have access to version history."}, status=403)
        version = DocumentAttachmentVersion.objects.filter(
            pk=version_pk, attachment=attachment
        ).first()
        if not version or not version.file:
            return Response({"detail": "Version file not found."}, status=404)
        create_audit_log(
            request=request,
            organization=attachment.request.organization,
            action=AuditAction.DOWNLOADED,
            model_name="DocumentAttachmentVersion",
            object_id=version.pk,
            message=f"Historical document version {version.version_number} downloaded through the API.",
            extra_data={"attachment_id": attachment.pk, "request_id": attachment.request_id},
        )
        return FileResponse(
            version.file.open("rb"),
            as_attachment=True,
            filename=os.path.basename(version.original_filename),
        )
