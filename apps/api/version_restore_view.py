from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.document_common import (
    can_restore_document_version,
    get_visible_attachment,
)
from apps.api.permissions import HasActiveWorkspace
from apps.audit.models import AuditAction
from apps.audit.services.audit_logger import create_audit_log
from apps.documents.models import DocumentAttachmentVersion
from apps.documents.services.versioning import rollback_attachment_to_version


class VersionRestoreInputSerializer(serializers.Serializer):
    reason = serializers.CharField(min_length=3, max_length=500, trim_whitespace=True)


class AttachmentVersionRestoreAPIView(APIView):
    permission_classes = [IsAuthenticated, HasActiveWorkspace]

    def post(self, request, attachment_pk, version_pk):
        attachment = get_visible_attachment(request.user, attachment_pk)
        if not attachment:
            return Response({"detail": "Not found."}, status=404)
        if not can_restore_document_version(request.user, attachment):
            return Response({"detail": "Only the creator can restore a version on their draft request."}, status=403)
        version = DocumentAttachmentVersion.objects.filter(
            pk=version_pk, attachment=attachment
        ).first()
        if not version:
            return Response({"detail": "Version not found."}, status=404)
        serializer = VersionRestoreInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        snapshot = rollback_attachment_to_version(
            attachment=attachment,
            version=version,
            user=request.user,
            reason=serializer.validated_data["reason"],
        )
        create_audit_log(
            request=request,
            organization=attachment.request.organization,
            action=AuditAction.UPDATED,
            model_name="DocumentAttachment",
            object_id=attachment.pk,
            message=f"Document restored to version {version.version_number} through the API.",
            extra_data={
                "request_id": attachment.request_id,
                "restored_version": version.version_number,
                "snapshot_version": snapshot.version_number,
            },
        )
        attachment.refresh_from_db()
        return Response({
            "attachment_id": attachment.pk,
            "restored_version": version.version_number,
            "snapshot_version": snapshot.version_number,
            "filename": attachment.original_filename,
        })
