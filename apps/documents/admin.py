from django.contrib import admin

from apps.documents.models import DocumentAttachment, DocumentAttachmentVersion

from apps.documents.models import (
    DocumentAIProcessingHistory,
    DocumentAttachment,
    DocumentAttachmentVersion,
)
@admin.register(DocumentAttachment)
class DocumentAttachmentAdmin(admin.ModelAdmin):
    list_display = [
        "original_filename",
        "request",
        "uploaded_by",
        "file_type",
        "file_size",
        "ocr_used",
        "ocr_confidence",
        "ocr_status",
        "ai_processed",
        "risk_level",
        "created_at",
    ]

    search_fields = [
        "original_filename",
        "request__title",
        "request__organization__name",
        "uploaded_by__username",
        "uploaded_by__email",
        "uploaded_by__full_name",
        "extracted_text",
        "manual_corrected_text",
    ]

    list_filter = [
        "file_type",
        "ocr_used",
        "ocr_status",
        "ai_processed",
        "risk_level",
        "created_at",
    ]

    readonly_fields = [
        "original_filename",
        "file_type",
        "file_size",
        "extracted_text",
        "processing_error",
        "ocr_confidence",
        "manual_corrected_at",
        "created_at",
    ]

    autocomplete_fields = [
        "request",
        "uploaded_by",
        "manual_corrected_by",
    ]

    fieldsets = (
        (
            "Attachment Info",
            {
                "fields": (
                    "request",
                    "uploaded_by",
                    "file",
                    "original_filename",
                    "file_type",
                    "file_size",
                    "created_at",
                )
            },
        ),
        (
            "Text Extraction / OCR",
            {
                "fields": (
                    "extracted_text",
                    "processing_error",
                    "ocr_used",
                    "ocr_confidence",
                    "ocr_status",
                    "manual_corrected_text",
                    "manual_corrected_by",
                    "manual_corrected_at",
                )
            },
        ),
        (
            "AI Fields",
            {
                "fields": (
                    "ai_processed",
                    "ai_summary",
                    "ai_category",
                    "ai_extracted_data",
                    "risk_level",
                    "risk_notes",
                )
            },
        ),
    )


@admin.register(DocumentAttachmentVersion)
class DocumentAttachmentVersionAdmin(admin.ModelAdmin):
    list_display = [
        "attachment",
        "version_number",
        "original_filename",
        "file_type",
        "file_size",
        "ocr_used",
        "ocr_confidence",
        "ocr_status",
        "replaced_by",
        "is_current_snapshot",
        "created_at",
    ]

    search_fields = [
        "attachment__original_filename",
        "attachment__request__title",
        "attachment__request__organization__name",
        "original_filename",
        "change_note",
        "extracted_text",
        "manual_corrected_text",
        "replaced_by__username",
        "replaced_by__email",
        "replaced_by__full_name",
    ]

    list_filter = [
        "file_type",
        "ocr_used",
        "ocr_status",
        "ai_processed",
        "is_current_snapshot",
        "created_at",
    ]

    readonly_fields = [
        "version_number",
        "file_size",
        "ocr_confidence",
        "manual_corrected_at",
        "created_at",
    ]

    autocomplete_fields = [
        "attachment",
        "replaced_by",
        "manual_corrected_by",
    ]
@admin.register(DocumentAIProcessingHistory)
class DocumentAIProcessingHistoryAdmin(admin.ModelAdmin):
    list_display = [
        "attachment",
        "version",
        "processed_by",
        "source_text_type",
        "success",
        "risk_level",
        "processing_time_ms",
        "created_at",
    ]

    search_fields = [
        "attachment__original_filename",
        "attachment__request__title",
        "attachment__request__organization__name",
        "version__original_filename",
        "processed_by__username",
        "processed_by__email",
        "processed_by__full_name",
        "ai_summary",
        "ai_category",
        "risk_notes",
        "error_message",
    ]

    list_filter = [
        "source_text_type",
        "success",
        "risk_level",
        "created_at",
    ]

    readonly_fields = [
        "attachment",
        "version",
        "processed_by",
        "source_text_type",
        "source_text",
        "success",
        "ai_summary",
        "ai_category",
        "ai_extracted_data",
        "risk_level",
        "risk_notes",
        "error_message",
        "processing_time_ms",
        "created_at",
    ]

    autocomplete_fields = [
        "attachment",
        "version",
        "processed_by",
    ]

    fieldsets = (
        (
            "Processing Info",
            {
                "fields": (
                    "attachment",
                    "version",
                    "processed_by",
                    "source_text_type",
                    "success",
                    "processing_time_ms",
                    "created_at",
                )
            },
        ),
        (
            "Source Text Snapshot",
            {
                "fields": (
                    "source_text",
                ),
                "classes": (
                    "collapse",
                ),
            },
        ),
        (
            "AI Result",
            {
                "fields": (
                    "ai_summary",
                    "ai_category",
                    "ai_extracted_data",
                    "risk_level",
                    "risk_notes",
                )
            },
        ),
        (
            "Error Details",
            {
                "fields": (
                    "error_message",
                )
            },
        ),
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False