import logging
import os
from pathlib import Path

from django.conf import settings
from PIL import Image

logger = logging.getLogger(__name__)


def configure_tesseract():
    try:
        import pytesseract

        tesseract_cmd = getattr(settings, "TESSERACT_CMD", "")

        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

        return pytesseract

    except Exception as exc:
        logger.exception("Failed to configure pytesseract: %s", exc)
        return None


def normalize_confidence(value):
    try:
        confidence = float(value)

        if confidence < 0:
            return None

        return confidence

    except (TypeError, ValueError):
        return None


def calculate_average_confidence(confidences):
    valid_scores = []

    for value in confidences:
        score = normalize_confidence(value)

        if score is not None:
            valid_scores.append(score)

    if not valid_scores:
        return None

    return round(sum(valid_scores) / len(valid_scores), 2)


def extract_text_from_image(image_path):
    pytesseract = configure_tesseract()

    if not pytesseract:
        return {
            "success": False,
            "text": "",
            "confidence": None,
            "error": "pytesseract is not configured.",
        }

    try:
        image = Image.open(image_path)

        data = pytesseract.image_to_data(
            image,
            lang=getattr(settings, "OCR_LANGUAGE", "eng"),
            output_type=pytesseract.Output.DICT,
        )

        words = []

        for word in data.get("text", []):
            cleaned_word = str(word).strip()

            if cleaned_word:
                words.append(cleaned_word)

        text = " ".join(words).strip()
        confidence = calculate_average_confidence(data.get("conf", []))

        return {
            "success": bool(text),
            "text": text,
            "confidence": confidence,
            "error": "" if text else "No OCR text detected.",
        }

    except Exception as exc:
        logger.exception("OCR image extraction failed: %s", exc)

        return {
            "success": False,
            "text": "",
            "confidence": None,
            "error": str(exc),
        }


def extract_text_from_scanned_pdf(pdf_path):
    try:
        from pdf2image import convert_from_path
    except Exception as exc:
        return {
            "success": False,
            "text": "",
            "confidence": None,
            "error": f"pdf2image is not installed or not configured: {exc}",
        }

    pytesseract = configure_tesseract()

    if not pytesseract:
        return {
            "success": False,
            "text": "",
            "confidence": None,
            "error": "pytesseract is not configured.",
        }

    try:
        max_pages = getattr(settings, "OCR_PDF_MAX_PAGES", 5)
        poppler_path = getattr(settings, "POPPLER_PATH", "")

        convert_kwargs = {
            "pdf_path": pdf_path,
            "first_page": 1,
            "last_page": max_pages,
            "dpi": 250,
        }

        if poppler_path:
            convert_kwargs["poppler_path"] = poppler_path

        pages = convert_from_path(**convert_kwargs)

        all_text = []
        all_confidences = []

        for page in pages:
            data = pytesseract.image_to_data(
                page,
                lang=getattr(settings, "OCR_LANGUAGE", "eng"),
                output_type=pytesseract.Output.DICT,
            )

            page_words = []

            for word in data.get("text", []):
                cleaned_word = str(word).strip()

                if cleaned_word:
                    page_words.append(cleaned_word)

            if page_words:
                all_text.append(" ".join(page_words))

            all_confidences.extend(data.get("conf", []))

        text = "\n\n".join(all_text).strip()
        confidence = calculate_average_confidence(all_confidences)

        return {
            "success": bool(text),
            "text": text,
            "confidence": confidence,
            "error": "" if text else "No OCR text detected from scanned PDF.",
        }

    except Exception as exc:
        logger.exception("OCR PDF extraction failed: %s", exc)

        return {
            "success": False,
            "text": "",
            "confidence": None,
            "error": str(exc),
        }


def run_ocr_for_file(file_path, file_type):
    if not getattr(settings, "OCR_ENABLED", True):
        return {
            "success": False,
            "text": "",
            "confidence": None,
            "error": "OCR is disabled.",
        }

    file_type = (file_type or "").lower().strip(".")
    file_path = str(file_path)

    if file_type in ["jpg", "jpeg", "png"]:
        return extract_text_from_image(file_path)

    if file_type == "pdf":
        return extract_text_from_scanned_pdf(file_path)

    return {
        "success": False,
        "text": "",
        "confidence": None,
        "error": f"OCR not supported for .{file_type} files.",
    }


def get_ocr_status(confidence):
    min_confidence = getattr(settings, "OCR_MIN_CONFIDENCE", 60)

    if confidence is None:
        return "FAILED"

    if confidence < min_confidence:
        return "LOW_CONFIDENCE"

    return "SUCCESS"