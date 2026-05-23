from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.document_common import (
    can_view_version_history,
    get_visible_attachment,
    serialize_document_version,
)
from apps.api.permissions import HasActiveWorkspace


class AttachmentVersionListAPIView(APIView):
    permission_classes = [IsAuthenticated, HasActiveWorkspace]

    def get(self, request, attachment_pk):
        attachment = get_visible_attachment(request.user, attachment_pk)
        if not attachment:
            return Response({"detail": "Not found."}, status=404)
        if not can_view_version_history(request.user, attachment):
            return Response({"detail": "You do not have access to version history."}, status=403)
        versions = attachment.versions.select_related("replaced_by").order_by("-version_number")
        return Response({
            "attachment_id": attachment.pk,
            "current": {
                "filename": attachment.original_filename,
                "file_size": attachment.file_size,
                "extracted_text_length": len(attachment.extracted_text or ""),
                "version_number": attachment.current_version_number,
            },
            "versions": [serialize_document_version(item) for item in versions],
        })
