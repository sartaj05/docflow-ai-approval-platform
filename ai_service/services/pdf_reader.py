import fitz


def extract_text_from_pdf(file_path: str):
    text_parts = []

    with fitz.open(file_path) as document:
        for page in document:
            page_text = page.get_text()
            text_parts.append(page_text)

    return "\n".join(text_parts).strip()