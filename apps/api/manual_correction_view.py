from django.utils import timezone
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.document_common import can_correct_document_text, get_visible_attachment
from apps.api.permissions import HasActiveWorkspace
from apps.audit.models import AuditAction
from apps.audit.services.audit_logger import create_audit_log


class ManualCorrectionInputSerializer(serializers.Serializer):
    corrected_text = serializers.CharField(max_length=200000, trim_whitespace=True)

    def validate_corrected_text(self, value):
        if not value:
            raise serializers.ValidationError("Corrected text cannot be empty.")
        return value


class AttachmentManualCorrectionAPIView(APIView):
    permission_classes = [IsAuthenticated, HasActiveWorkspace]

    def patch(self, request, attachment_pk):
        attachment = get_visible_attachment(request.user, attachment_pk)
        if not attachment:
            return Response({"detail": "Not found."}, status=404)
        if not can_correct_document_text(request.user, attachment):
            return Response({"detail": "You do not have permission to correct this document."}, status=403)
        serializer = ManualCorrectionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        corrected_text = serializer.validated_data["corrected_text"]
        attachment.extracted_text = corrected_text
        attachment.manual_corrected_text = corrected_text
        attachment.manual_corrected_by = request.user
        attachment.manual_corrected_at = timezone.now()
        attachment.ocr_status = "MANUAL_CORRECTED"
        attachment.processing_error = ""
        attachment.save(update_fields=[
            "extracted_text", "manual_corrected_text", "manual_corrected_by",
            "manual_corrected_at", "ocr_status", "processing_error", "updated_at",
        ])
        create_audit_log(
            request=request,
            organization=attachment.request.organization,
            action=AuditAction.UPDATED,
            model_name="DocumentAttachment",
            object_id=attachment.pk,
            message="Extracted document text manually corrected through the API.",
            extra_data={"request_id": attachment.request_id, "text_length": len(corrected_text)},
        )
        return Response({
            "attachment_id": attachment.pk,
            "ocr_status": attachment.ocr_status,
            "manual_corrected_at": attachment.manual_corrected_at.isoformat(),
            "text_length": len(corrected_text),
        })
