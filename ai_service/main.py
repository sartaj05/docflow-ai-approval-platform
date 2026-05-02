import os
import tempfile

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from services.extractor import extract_fields
from services.pdf_reader import extract_text_from_pdf
from services.risk_detector import detect_risk
from services.summarizer import generate_summary


app = FastAPI(
    title="DocFlow AI Service",
    description="AI microservice for document summary, field extraction, and risk detection.",
    version="1.0.0",
)


class AnalyzeDocumentRequest(BaseModel):
    text: str = Field(..., min_length=1)
    filename: str | None = None
    category: str | None = None


@app.get("/")
def health_check():
    return {
        "service": "DocFlow AI Service",
        "status": "running",
        "version": "1.0.0",
    }


@app.get("/health/")
def health():
    return {
        "status": "ok",
    }


@app.post("/ai/analyze-document/")
def analyze_document(payload: AnalyzeDocumentRequest):
    extracted_fields = extract_fields(payload.text)

    final_category = payload.category or extracted_fields.get("category", "GENERAL")

    extracted_fields["category"] = final_category

    summary = generate_summary(payload.text, extracted_fields)
    risk = detect_risk(payload.text, extracted_fields)

    return {
        "success": True,
        "filename": payload.filename,
        "summary": summary,
        "category": final_category,
        "extracted_fields": extracted_fields,
        "missing_fields": risk.get("missing_fields", []),
        "risk_level": risk.get("risk_level", "LOW"),
        "risk_notes": risk.get("risk_notes", "No major risk found."),
    }


@app.post("/ai/analyze-pdf/")
async def analyze_pdf(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported.",
        )

    suffix = os.path.splitext(file.filename)[1]

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        temp_file.write(await file.read())
        temp_path = temp_file.name

    try:
        extracted_text = extract_text_from_pdf(temp_path)

        if not extracted_text:
            raise HTTPException(
                status_code=400,
                detail="No readable text found in PDF.",
            )

        extracted_fields = extract_fields(extracted_text)
        summary = generate_summary(extracted_text, extracted_fields)
        risk = detect_risk(extracted_text, extracted_fields)

        return {
            "success": True,
            "filename": file.filename,
            "text": extracted_text,
            "summary": summary,
            "category": extracted_fields.get("category", "GENERAL"),
            "extracted_fields": extracted_fields,
            "missing_fields": risk.get("missing_fields", []),
            "risk_level": risk.get("risk_level", "LOW"),
            "risk_notes": risk.get("risk_notes", "No major risk found."),
        }

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)