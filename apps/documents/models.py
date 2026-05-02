import os

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


def document_upload_path(instance, filename):
    request_id = instance.request_id or "draft"
    return f"approval_documents/request_{request_id}/{filename}"


def validate_document_file(file):
    allowed_extensions = getattr(
        settings,
        "ALLOWED_DOCUMENT_EXTENSIONS",
        [".pdf", ".jpg", ".jpeg", ".png", ".doc", ".docx"],
    )

    max_upload_size = getattr(
        settings,
        "MAX_UPLOAD_SIZE",
        10 * 1024 * 1024,
    )

    ext = os.path.splitext(file.name)[1].lower()

    if ext not in allowed_extensions:
        raise ValidationError(
            f"Unsupported file type '{ext}'. Allowed types: {', '.join(allowed_extensions)}"
        )

    if file.size > max_upload_size:
        max_size_mb = max_upload_size / (1024 * 1024)
        raise ValidationError(
            f"File size cannot exceed {max_size_mb:.0f} MB."
        )


class DocumentAttachment(models.Model):
    request = models.ForeignKey(
        "approvals.DocumentRequest",
        on_delete=models.CASCADE,
        related_name="attachments",
    )

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="uploaded_documents",
        blank=True,
        null=True,
    )

    file = models.FileField(
        upload_to=document_upload_path,
        validators=[validate_document_file],
    )

    original_filename = models.CharField(max_length=255)

    file_type = models.CharField(max_length=50, blank=True)

    file_size = models.PositiveIntegerField(default=0)

    extracted_text = models.TextField(blank=True)

    ai_processed = models.BooleanField(default=False)

    ai_summary = models.TextField(blank=True)

    ai_category = models.CharField(max_length=100, blank=True)

    ai_extracted_data = models.JSONField(default=dict, blank=True)
    ocr_used = models.BooleanField(default=False)

    ocr_confidence = models.FloatField(
        blank=True,
        null=True,
        help_text="Average OCR confidence score.",
    )

    ocr_status = models.CharField(
        max_length=30,
        default="NOT_REQUIRED",
        choices=[
            ("NOT_REQUIRED", "Not Required"),
            ("PENDING", "Pending"),
            ("SUCCESS", "Success"),
            ("LOW_CONFIDENCE", "Low Confidence"),
            ("FAILED", "Failed"),
            ("MANUAL_CORRECTED", "Manual Corrected"),
        ],
    )

    manual_corrected_text = models.TextField(blank=True)

    manual_corrected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="manual_corrected_documents",
        blank=True,
        null=True,
    )

    manual_corrected_at = models.DateTimeField(blank=True, null=True)
    risk_level = models.CharField(max_length=20, blank=True)

    risk_notes = models.TextField(blank=True)

    processing_error = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["request", "created_at"]),
            models.Index(fields=["uploaded_by", "created_at"]),
            models.Index(fields=["ai_processed"]),
            models.Index(fields=["risk_level"]),
        ]

    def __str__(self):
        return self.original_filename

    @property
    def file_extension(self):
        return os.path.splitext(self.original_filename)[1].lower()

    @property
    def file_size_mb(self):
        if not self.file_size:
            return 0

        return round(self.file_size / (1024 * 1024), 2)

    @property
    def is_pdf(self):
        return self.file_extension == ".pdf"

    @property
    def is_image(self):
        return self.file_extension in [".jpg", ".jpeg", ".png"]

    @property
    def display_file_type(self):
        if self.file_type:
            return self.file_type.upper()

        ext = self.file_extension.replace(".", "")
        return ext.upper() if ext else "FILE"
    @property
    def current_version_number(self):
        latest_version = self.versions.order_by("-version_number").first()

        if latest_version:
            return latest_version.version_number + 1

        return 1

    @property
    def total_versions(self):
        return self.versions.count() + 1
    
    
from django.conf import settings
from django.db import models


class DocumentAttachmentVersion(models.Model):
    attachment = models.ForeignKey(
        "documents.DocumentAttachment",
        on_delete=models.CASCADE,
        related_name="versions",
    )

    version_number = models.PositiveIntegerField()

    file = models.FileField(
        upload_to="document_versions/%Y/%m/%d/",
    )

    original_filename = models.CharField(max_length=255)

    file_type = models.CharField(max_length=50, blank=True)

    file_size = models.PositiveIntegerField(default=0)

    extracted_text = models.TextField(blank=True)

    ai_summary = models.TextField(blank=True)

    ai_category = models.CharField(max_length=100, blank=True)

    ai_extracted_data = models.JSONField(default=dict, blank=True)
    ocr_used = models.BooleanField(default=False)

    ocr_confidence = models.FloatField(
        blank=True,
        null=True,
    )

    ocr_status = models.CharField(
        max_length=30,
        default="NOT_REQUIRED",
        choices=[
            ("NOT_REQUIRED", "Not Required"),
            ("PENDING", "Pending"),
            ("SUCCESS", "Success"),
            ("LOW_CONFIDENCE", "Low Confidence"),
            ("FAILED", "Failed"),
            ("MANUAL_CORRECTED", "Manual Corrected"),
        ],
    )

    manual_corrected_text = models.TextField(blank=True)

    manual_corrected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="manual_corrected_document_versions",
        blank=True,
        null=True,
    )

    manual_corrected_at = models.DateTimeField(blank=True, null=True)
    risk_level = models.CharField(max_length=20, blank=True)

    risk_notes = models.TextField(blank=True)

    processing_error = models.TextField(blank=True)

    ai_processed = models.BooleanField(default=False)

    replaced_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="document_versions_created",
        blank=True,
        null=True,
    )

    change_note = models.TextField(blank=True)

    is_current_snapshot = models.BooleanField(
        default=False,
        help_text="True when this row was created from the active attachment before replacement.",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-version_number"]
        unique_together = ["attachment", "version_number"]
        indexes = [
            models.Index(fields=["attachment", "version_number"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["replaced_by"]),
        ]

    def __str__(self):
        return f"{self.attachment.original_filename} - v{self.version_number}"

    @property
    def file_size_mb(self):
        if not self.file_size:
            return "0.00"

        return f"{self.file_size / (1024 * 1024):.2f}"

    @property
    def display_file_type(self):
        return self.file_type.upper() if self.file_type else "UNKNOWN"
    
    
class DocumentAIProcessingHistory(models.Model):
    attachment = models.ForeignKey(
        "documents.DocumentAttachment",
        on_delete=models.CASCADE,
        related_name="ai_processing_history",
    )

    version = models.ForeignKey(
        "documents.DocumentAttachmentVersion",
        on_delete=models.SET_NULL,
        related_name="ai_processing_history",
        blank=True,
        null=True,
        help_text="Optional version reference if AI was run against a historical version.",
    )

    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="document_ai_processing_runs",
        blank=True,
        null=True,
    )

    source_text = models.TextField(
        blank=True,
        help_text="Text that was sent to AI service.",
    )

    source_text_type = models.CharField(
        max_length=40,
        default="EXTRACTED_TEXT",
        choices=[
            ("EXTRACTED_TEXT", "Extracted Text"),
            ("OCR_TEXT", "OCR Text"),
            ("MANUAL_CORRECTED_TEXT", "Manual Corrected Text"),
            ("VERSION_TEXT", "Version Text"),
        ],
    )

    ai_summary = models.TextField(blank=True)

    ai_category = models.CharField(max_length=100, blank=True)

    ai_extracted_data = models.JSONField(default=dict, blank=True)

    risk_level = models.CharField(max_length=20, blank=True)

    risk_notes = models.TextField(blank=True)

    success = models.BooleanField(default=False)

    error_message = models.TextField(blank=True)

    processing_time_ms = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["attachment", "created_at"]),
            models.Index(fields=["version", "created_at"]),
            models.Index(fields=["processed_by", "created_at"]),
            models.Index(fields=["success"]),
            models.Index(fields=["source_text_type"]),
        ]

    def __str__(self):
        return f"{self.attachment.original_filename} AI Run - {self.created_at}"