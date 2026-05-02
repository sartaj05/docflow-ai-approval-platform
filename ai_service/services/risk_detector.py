def detect_risk(text: str, extracted_fields: dict):
    safe_text = text or ""
    lowered = safe_text.lower()

    missing_fields = []

    if not extracted_fields.get("amount"):
        missing_fields.append("amount")

    if not extracted_fields.get("date"):
        missing_fields.append("date")

    risk_notes = []

    suspicious_keywords = [
        "urgent payment",
        "without approval",
        "cash payment",
        "duplicate invoice",
        "advance payment",
    ]

    for keyword in suspicious_keywords:
        if keyword in lowered:
            risk_notes.append(f"Suspicious keyword found: {keyword}.")

    if "signature" not in lowered and "signed" not in lowered:
        risk_notes.append("Signature keyword not found.")

    if "approved" not in lowered and "approval" not in lowered:
        risk_notes.append("Approval keyword not found.")

    if len(missing_fields) >= 2 or len(risk_notes) >= 3:
        risk_level = "HIGH"
    elif missing_fields or risk_notes:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    return {
        "missing_fields": missing_fields,
        "risk_level": risk_level,
        "risk_notes": " ".join(risk_notes) if risk_notes else "No major risk found.",
    }