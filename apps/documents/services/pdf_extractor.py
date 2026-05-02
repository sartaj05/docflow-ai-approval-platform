import logging

import fitz

from apps.documents.services.ocr_service import get_ocr_status, run_ocr_for_file

logger = logging.getLogger(__name__)


def extract_text_from_pdf(file_path):
    text = ""

    try:
        with fitz.open(file_path) as document:
            for page in document:
                text += page.get_text()

    except Exception as exc:
        logger.exception("PDF text extraction failed: %s", exc)

        return {
            "text": "",
            "ocr_used": False,
            "ocr_confidence": None,
            "ocr_status": "FAILED",
            "error": str(exc),
        }

    text = text.strip()

    if text:
        return {
            "text": text,
            "ocr_used": False,
            "ocr_confidence": None,
            "ocr_status": "NOT_REQUIRED",
            "error": "",
        }

    ocr_result = run_ocr_for_file(
        file_path=file_path,
        file_type="pdf",
    )

    if ocr_result["success"]:
        confidence = ocr_result.get("confidence")

        return {
            "text": ocr_result["text"],
            "ocr_used": True,
            "ocr_confidence": confidence,
            "ocr_status": get_ocr_status(confidence),
            "error": "",
        }

    return {
        "text": "",
        "ocr_used": True,
        "ocr_confidence": ocr_result.get("confidence"),
        "ocr_status": "FAILED",
        "error": ocr_result.get("error", "OCR failed."),
    }