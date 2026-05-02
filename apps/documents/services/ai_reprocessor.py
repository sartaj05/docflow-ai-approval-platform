import time

from django.db import transaction

from apps.documents.models import DocumentAIProcessingHistory
from apps.documents.services.ai_processor import process_attachment_with_ai


def get_attachment_ai_source_text(attachment):
    if getattr(attachment, "manual_corrected_text", ""):
        return attachment.manual_corrected_text, "MANUAL_CORRECTED_TEXT"

    if getattr(attachment, "ocr_used", False):
        return attachment.extracted_text or "", "OCR_TEXT"

    return attachment.extracted_text or "", "EXTRACTED_TEXT"


def get_version_ai_source_text(version):
    if getattr(version, "manual_corrected_text", ""):
        return version.manual_corrected_text, "MANUAL_CORRECTED_TEXT"

    if getattr(version, "ocr_used", False):
        return version.extracted_text or "", "OCR_TEXT"

    return version.extracted_text or "", "VERSION_TEXT"


@transaction.atomic
def create_ai_history_from_attachment(
    *,
    attachment,
    processed_by=None,
    source_text="",
    source_text_type="EXTRACTED_TEXT",
    result=None,
    processing_time_ms=0,
):
    result = result or {}

    return DocumentAIProcessingHistory.objects.create(
        attachment=attachment,
        processed_by=processed_by,
        source_text=source_text,
        source_text_type=source_text_type,
        ai_summary=attachment.ai_summary or "",
        ai_category=attachment.ai_category or "",
        ai_extracted_data=attachment.ai_extracted_data or {},
        risk_level=attachment.risk_level or "",
        risk_notes=attachment.risk_notes or "",
        success=result.get("success", False),
        error_message=result.get("error", ""),
        processing_time_ms=processing_time_ms,
    )


@transaction.atomic
def rerun_ai_for_attachment(
    *,
    attachment,
    request=None,
    processed_by=None,
):
    source_text, source_text_type = get_attachment_ai_source_text(attachment)

    if not source_text:
        history = DocumentAIProcessingHistory.objects.create(
            attachment=attachment,
            processed_by=processed_by,
            source_text="",
            source_text_type=source_text_type,
            success=False,
            error_message="No extracted, OCR, or manually corrected text available for AI processing.",
        )

        return {
            "success": False,
            "error": history.error_message,
            "history": history,
        }

    attachment.extracted_text = source_text
    attachment.save(update_fields=["extracted_text"])

    started_at = time.perf_counter()

    result = process_attachment_with_ai(
        attachment=attachment,
        request=request,
    )

    processing_time_ms = int((time.perf_counter() - started_at) * 1000)

    attachment.refresh_from_db()

    history = create_ai_history_from_attachment(
        attachment=attachment,
        processed_by=processed_by,
        source_text=source_text,
        source_text_type=source_text_type,
        result=result,
        processing_time_ms=processing_time_ms,
    )

    return {
        "success": result.get("success", False),
        "error": result.get("error", ""),
        "history": history,
    }


@transaction.atomic
def create_ai_history_for_version(
    *,
    attachment,
    version,
    processed_by=None,
    result=None,
    processing_time_ms=0,
):
    result = result or {}
    source_text, source_text_type = get_version_ai_source_text(version)

    return DocumentAIProcessingHistory.objects.create(
        attachment=attachment,
        version=version,
        processed_by=processed_by,
        source_text=source_text,
        source_text_type=source_text_type,
        ai_summary=version.ai_summary or "",
        ai_category=version.ai_category or "",
        ai_extracted_data=version.ai_extracted_data or {},
        risk_level=version.risk_level or "",
        risk_notes=version.risk_notes or "",
        success=result.get("success", False),
        error_message=result.get("error", ""),
        processing_time_ms=processing_time_ms,
    )