import re
from datetime import datetime


def extract_amount(text: str):
    patterns = [
        r"(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d{1,2})?)",
        r"amount[:\s]+(?:Rs\.?|INR|₹)?\s*([\d,]+(?:\.\d{1,2})?)",
        r"total[:\s]+(?:Rs\.?|INR|₹)?\s*([\d,]+(?:\.\d{1,2})?)",
        r"grand\s+total[:\s]+(?:Rs\.?|INR|₹)?\s*([\d,]+(?:\.\d{1,2})?)",
        r"net\s+amount[:\s]+(?:Rs\.?|INR|₹)?\s*([\d,]+(?:\.\d{1,2})?)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            return match.group(1).replace(",", "")

    return None


def normalize_date(raw_date: str):
    date_formats = [
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y-%m-%d",
        "%d.%m.%Y",
    ]

    for fmt in date_formats:
        try:
            parsed = datetime.strptime(raw_date, fmt)
            return parsed.date().isoformat()
        except ValueError:
            continue

    return raw_date


def extract_date(text: str):
    patterns = [
        r"\b\d{2}/\d{2}/\d{4}\b",
        r"\b\d{2}-\d{2}-\d{4}\b",
        r"\b\d{4}-\d{2}-\d{2}\b",
        r"\b\d{2}\.\d{2}\.\d{4}\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)

        if match:
            return normalize_date(match.group(0))

    return None


def detect_category(text: str):
    lowered = text.lower()

    if any(word in lowered for word in ["invoice", "payment", "vendor", "bill"]):
        return "VENDOR_PAYMENT"

    if "leave" in lowered:
        return "LEAVE"

    if any(word in lowered for word in ["purchase", "quotation", "procurement"]):
        return "PURCHASE"

    if any(word in lowered for word in ["contract", "agreement", "mou"]):
        return "CONTRACT"

    if any(word in lowered for word in ["medical", "hospital", "doctor", "clinic"]):
        return "MEDICAL"

    if "tender" in lowered:
        return "TENDER"

    return "GENERAL"


def extract_fields(text: str):
    safe_text = text or ""

    return {
        "amount": extract_amount(safe_text),
        "date": extract_date(safe_text),
        "category": detect_category(safe_text),
    }