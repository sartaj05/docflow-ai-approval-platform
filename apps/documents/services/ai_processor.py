import logging

from django.db import transaction

from apps.audit.models import AuditAction
from apps.audit.services.audit_logger import create_audit_log
from apps.documents.services.ai_client import AIServiceError, analyze_document_text


logger = logging.getLogger(__name__)


def process_attachment_with_ai(*, attachment, request=None):
    """
    Process one uploaded attachment with AI service.

    Saves AI response into:
        DocumentAttachment.ai_summary
        DocumentAttachment.ai_category
        DocumentAttachment.ai_extracted_data
        DocumentAttachment.risk_level
        DocumentAttachment.risk_notes
        DocumentAttachment.ai_processed
        DocumentAttachment.processing_error

    Also updates parent DocumentRequest AI fields.
    """

    document_request = attachment.request

    if not attachment.extracted_text:
        attachment.ai_processed = False
        attachment.processing_error = "No extracted text available for AI analysis."
        attachment.save(
            update_fields=[
                "ai_processed",
                "processing_error",
            ]
        )

        return {
            "success": False,
            "error": attachment.processing_error,
        }

    try:
        ai_data = analyze_document_text(
            text=attachment.extracted_text,
            filename=attachment.original_filename,
            category=document_request.category,
        )

    except AIServiceError as exc:
        error_message = str(exc)

        attachment.ai_processed = False
        attachment.processing_error = error_message
        attachment.save(
            update_fields=[
                "ai_processed",
                "processing_error",
            ]
        )

        if request:
            create_audit_log(
                request=request,
                organization=document_request.organization,
                action=AuditAction.UPDATED,
                model_name="DocumentAttachment",
                object_id=attachment.pk,
                message=f"AI processing failed for document '{attachment.original_filename}'.",
                extra_data={
                    "request_id": document_request.pk,
                    "file_name": attachment.original_filename,
                    "error": error_message,
                },
            )

        logger.warning("AI processing failed for attachment %s: %s", attachment.pk, error_message)

        return {
            "success": False,
            "error": error_message,
        }

    save_ai_result_to_attachment(
        attachment=attachment,
        ai_data=ai_data,
    )

    update_request_ai_fields_from_attachment(
        document_request=document_request,
        attachment=attachment,
    )

    if request:
        create_audit_log(
            request=request,
            organization=document_request.organization,
            action=AuditAction.UPDATED,
            model_name="DocumentAttachment",
            object_id=attachment.pk,
            message=f"AI processing completed for document '{attachment.original_filename}'.",
            extra_data={
                "request_id": document_request.pk,
                "file_name": attachment.original_filename,
                "summary": attachment.ai_summary,
                "category": attachment.ai_category,
                "risk_level": attachment.risk_level,
                "extracted_fields": attachment.ai_extracted_data,
            },
        )

    return {
        "success": True,
        "ai_data": ai_data,
    }


@transaction.atomic
def save_ai_result_to_attachment(*, attachment, ai_data):
    attachment.ai_summary = ai_data.get("summary", "")
    attachment.ai_category = ai_data.get("category", "")
    attachment.ai_extracted_data = ai_data.get("extracted_fields", {})
    attachment.risk_level = ai_data.get("risk_level", "LOW")
    attachment.risk_notes = ai_data.get("risk_notes", "")
    attachment.ai_processed = True
    attachment.processing_error = ""

    attachment.save(
        update_fields=[
            "ai_summary",
            "ai_category",
            "ai_extracted_data",
            "risk_level",
            "risk_notes",
            "ai_processed",
            "processing_error",
        ]
    )


@transaction.atomic
def update_request_ai_fields_from_attachment(*, document_request, attachment):
    """
    Updates parent request with latest processed attachment AI result.

    This keeps request list/detail searchable and visible at request level.
    """

    document_request.ai_summary = attachment.ai_summary
    document_request.ai_category = attachment.ai_category
    document_request.ai_extracted_data = attachment.ai_extracted_data
    document_request.risk_level = attachment.risk_level
    document_request.risk_notes = attachment.risk_notes

    document_request.save(
        update_fields=[
            "ai_summary",
            "ai_category",
            "ai_extracted_data",
            "risk_level",
            "risk_notes",
            "updated_at",
        ]
    )