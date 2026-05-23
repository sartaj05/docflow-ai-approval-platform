from difflib import unified_diff

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.document_common import can_view_version_history, get_visible_attachment
from apps.api.permissions import HasActiveWorkspace
from apps.documents.models import DocumentAttachmentVersion


class AttachmentVersionCompareAPIView(APIView):
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
        if not version:
            return Response({"detail": "Version not found."}, status=404)
        lines = list(unified_diff(
            (version.extracted_text or "").splitlines(),
            (attachment.extracted_text or "").splitlines(),
            fromfile=f"version-{version.version_number}",
            tofile="current",
            lineterm="",
        ))
        return Response({
            "version_id": version.pk,
            "version_number": version.version_number,
            "current_filename": attachment.original_filename,
            "previous_text_length": len(version.extracted_text or ""),
            "current_text_length": len(attachment.extracted_text or ""),
            "diff": lines[:2000],
            "diff_truncated": len(lines) > 2000,
        })
