import os

from django.http import FileResponse
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.permissions import (
    HasActiveWorkspace,
    can_manage_request,
    get_user_organization,
    scoped_requests,
)
from apps.audit.models import AuditAction
from apps.audit.services.audit_logger import create_audit_log
from apps.documents.models import DocumentAttachment
from apps.documents.services.ai_processor import process_attachment_with_ai
from apps.documents.services.document_processor import process_document_file


class AttachmentUploadInputSerializer(serializers.Serializer):
    file = serializers.FileField()

    def validate_file(self, uploaded_file):
        organization = get_user_organization(self.context["request"].user)
        if not organization:
            raise serializers.ValidationError("An active organization is required.")

        extension = os.path.splitext(uploaded_file.name)[1].lower()
        allowed = {
            item.strip().lower()
            for item in organization.allowed_file_extensions.split(",")
            if item.strip()
        }
        if extension not in allowed:
            raise serializers.ValidationError(
                f"Unsupported file type. Allowed extensions: {', '.join(sorted(allowed))}."
            )

        maximum_size = organization.max_upload_size_mb * 1024 * 1024
        if uploaded_file.size > maximum_size:
            raise serializers.ValidationError(
                f"File size cannot exceed {organization.max_upload_size_mb} MB."
            )
        return uploaded_file


class AttachmentSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.SerializerMethodField()
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = DocumentAttachment
        fields = [
            "id",
            "original_filename",
            "file_type",
            "file_size",
            "ai_processed",
            "ai_summary",
            "ai_category",
            "risk_level",
            "risk_notes",
            "ocr_used",
            "ocr_confidence",
            "ocr_status",
            "processing_error",
            "uploaded_by_name",
            "created_at",
            "download_url",
        ]

    def get_uploaded_by_name(self, obj):
        return obj.uploaded_by.display_name if obj.uploaded_by_id else None

    def get_download_url(self, obj):
        request = self.context.get("request")
        path = f"/api/v1/attachments/{obj.pk}/download/"
        return request.build_absolute_uri(path) if request else path


class RequestAttachmentListView(APIView):
    permission_classes = [IsAuthenticated, HasActiveWorkspace]

    def get_request(self, user, request_pk):
        return scoped_requests(user).filter(pk=request_pk).first()

    def get(self, request, request_pk):
        document_request = self.get_request(request.user, request_pk)
        if not document_request:
            return Response({"detail": "Not found."}, status=404)
        attachments = document_request.attachments.select_related("uploaded_by")
        return Response(AttachmentSerializer(
            attachments,
            many=True,
            context={"request": request},
        ).data)

    def post(self, request, request_pk):
        document_request = self.get_request(request.user, request_pk)
        if not document_request:
            return Response({"detail": "Not found."}, status=404)
        if not can_manage_request(request.user, document_request):
            return Response(
                {"detail": "Documents can be uploaded only to your own draft requests."},
                status=403,
            )

        serializer = AttachmentUploadInputSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        uploaded_file = serializer.validated_data["file"]
        attachment = DocumentAttachment.objects.create(
            request=document_request,
            uploaded_by=request.user,
            file=uploaded_file,
            original_filename=os.path.basename(uploaded_file.name),
            file_type=os.path.splitext(uploaded_file.name)[1].lower().lstrip("."),
            file_size=uploaded_file.size,
        )

        processing = process_document_file(
            attachment.file.path,
            attachment.original_filename,
        )
        if isinstance(processing, dict):
            attachment.extracted_text = processing.get("text", "") or ""
            attachment.ocr_used = processing.get("ocr_used", False)
            attachment.ocr_confidence = processing.get("ocr_confidence")
            attachment.ocr_status = processing.get("ocr_status", "NOT_REQUIRED")
            attachment.processing_error = processing.get("error", "") or ""
        else:
            attachment.extracted_text = processing or ""
        attachment.save(update_fields=[
            "extracted_text",
            "ocr_used",
            "ocr_confidence",
            "ocr_status",
            "processing_error",
        ])

        ai_result = None
        if attachment.extracted_text:
            ai_result = process_attachment_with_ai(attachment=attachment, request=request)

        create_audit_log(
            request=request,
            organization=document_request.organization,
            action=AuditAction.UPLOADED,
            model_name="DocumentAttachment",
            object_id=attachment.pk,
            message=f"Document '{attachment.original_filename}' uploaded through the API.",
            extra_data={
                "request_id": document_request.pk,
                "file_size": attachment.file_size,
                "ocr_used": attachment.ocr_used,
                "ai_processed": bool(ai_result and ai_result.get("success")),
            },
        )
        attachment.refresh_from_db()
        return Response(
            AttachmentSerializer(attachment, context={"request": request}).data,
            status=201,
        )


class AttachmentDownloadView(APIView):
    permission_classes = [IsAuthenticated, HasActiveWorkspace]

    def get(self, request, attachment_pk):
        attachment = (
            DocumentAttachment.objects.select_related("request")
            .filter(pk=attachment_pk)
            .first()
        )
        if not attachment or not scoped_requests(request.user).filter(pk=attachment.request_id).exists():
            return Response({"detail": "Not found."}, status=404)

        create_audit_log(
            request=request,
            organization=attachment.request.organization,
            action=AuditAction.DOWNLOADED,
            model_name="DocumentAttachment",
            object_id=attachment.pk,
            message=f"Document '{attachment.original_filename}' downloaded through the API.",
            extra_data={"request_id": attachment.request_id},
        )
        filename = os.path.basename(attachment.original_filename)
        return FileResponse(
            attachment.file.open("rb"),
            as_attachment=True,
            filename=filename,
        )
