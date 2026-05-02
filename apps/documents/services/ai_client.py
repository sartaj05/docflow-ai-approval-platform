import logging
import time

import requests
from django.conf import settings


logger = logging.getLogger(__name__)


class AIServiceError(Exception):
    """Raised when DocFlow AI FastAPI service fails."""


def get_ai_service_url():
    return getattr(settings, "AI_SERVICE_URL", "http://localhost:8001").rstrip("/")


def get_ai_service_timeout():
    return getattr(settings, "AI_SERVICE_TIMEOUT", 15)


def analyze_document_text(
    *,
    text,
    filename="",
    category="",
    retries=2,
    retry_delay=1,
):
    """
    Sends extracted document text to FastAPI AI service.

    Returns:
        {
            "success": True,
            "summary": "...",
            "category": "VENDOR_PAYMENT",
            "extracted_fields": {...},
            "missing_fields": [...],
            "risk_level": "LOW",
            "risk_notes": "..."
        }

    Raises:
        AIServiceError
    """

    safe_text = (text or "").strip()

    if not safe_text:
        raise AIServiceError("No readable text available for AI analysis.")

    endpoint = f"{get_ai_service_url()}/ai/analyze-document/"

    payload = {
        "text": safe_text,
        "filename": filename or "",
        "category": category or None,
    }

    last_error = None

    for attempt in range(1, retries + 2):
        try:
            response = requests.post(
                endpoint,
                json=payload,
                timeout=get_ai_service_timeout(),
            )

            response.raise_for_status()

            data = response.json()

            if not data.get("success", False):
                raise AIServiceError("AI service returned unsuccessful response.")

            return normalize_ai_response(data)

        except requests.exceptions.ConnectionError as exc:
            last_error = f"AI service connection failed: {exc}"
            logger.warning(last_error)

        except requests.exceptions.Timeout as exc:
            last_error = f"AI service timeout: {exc}"
            logger.warning(last_error)

        except requests.exceptions.HTTPError as exc:
            last_error = f"AI service HTTP error: {exc}"
            logger.warning(last_error)

        except ValueError as exc:
            last_error = f"Invalid JSON response from AI service: {exc}"
            logger.warning(last_error)

        except AIServiceError as exc:
            last_error = str(exc)
            logger.warning(last_error)

        if attempt <= retries:
            time.sleep(retry_delay)

    raise AIServiceError(last_error or "AI service failed.")


def normalize_ai_response(data):
    """
    Makes FastAPI response safe for Django model fields.
    """

    extracted_fields = data.get("extracted_fields") or {}

    risk_level = (data.get("risk_level") or "LOW").upper()

    if risk_level not in ["LOW", "MEDIUM", "HIGH"]:
        risk_level = "LOW"

    category = data.get("category") or extracted_fields.get("category") or "GENERAL"

    return {
        "summary": data.get("summary") or "",
        "category": category,
        "extracted_fields": extracted_fields,
        "missing_fields": data.get("missing_fields") or [],
        "risk_level": risk_level,
        "risk_notes": data.get("risk_notes") or "No major risk found.",
        "raw_response": data,
    }