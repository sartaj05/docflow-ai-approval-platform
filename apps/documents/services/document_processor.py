from pathlib import Path

from apps.documents.services.ocr_service import get_ocr_status, run_ocr_for_file
from apps.documents.services.pdf_extractor import extract_text_from_pdf


def get_file_type(filename):
    return Path(filename).suffix.lower().replace(".", "")


def process_document_file(file_path, filename):
    file_type = get_file_type(filename)

    if file_type == "pdf":
        return extract_text_from_pdf(file_path)

    if file_type in ["jpg", "jpeg", "png"]:
        ocr_result = run_ocr_for_file(
            file_path=file_path,
            file_type=file_type,
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

    return {
        "text": "",
        "ocr_used": False,
        "ocr_confidence": None,
        "ocr_status": "NOT_REQUIRED",
        "error": "",
    }