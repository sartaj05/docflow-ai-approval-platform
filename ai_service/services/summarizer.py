def get_category_display(category: str):
    mapping = {
        "VENDOR_PAYMENT": "Vendor Payment",
        "LEAVE": "Leave",
        "PURCHASE": "Purchase",
        "CONTRACT": "Contract",
        "HR_DOCUMENT": "HR Document",
        "MEDICAL": "Medical",
        "TENDER": "Tender",
        "GENERAL": "General",
    }

    return mapping.get(category, "General")


def generate_summary(text: str, extracted_fields: dict):
    safe_text = text or ""

    category = extracted_fields.get("category") or "GENERAL"
    amount = extracted_fields.get("amount")
    date = extracted_fields.get("date")

    summary_parts = [
        f"This document appears to be related to {get_category_display(category)}."
    ]

    if amount:
        summary_parts.append(f"An amount of Rs. {amount} was detected.")

    if date:
        summary_parts.append(f"The document contains date {date}.")

    if len(safe_text) > 300:
        summary_parts.append(
            "The document contains detailed information and may require manual review."
        )

    if len(safe_text.strip()) == 0:
        summary_parts.append(
            "No readable text was provided for analysis."
        )

    return " ".join(summary_parts)