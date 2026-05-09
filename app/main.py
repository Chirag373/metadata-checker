from fastapi import FastAPI, UploadFile, File, HTTPException

from .metadata_analyzer import (
    extract_pdf_metadata,
    run_metadata_checks,
    compute_risk,
)

app = FastAPI(title="Metadata Mutation Checker")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/analyze")
async def analyze_document(file: UploadFile = File(...)):
    if file.content_type not in ("application/pdf",):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}. Only PDF is supported at this stage."
        )

    content = await file.read()
    file_size = len(content)

    extracted_metadata = extract_pdf_metadata(content, file.filename)
    findings = run_metadata_checks(extracted_metadata)
    risk = compute_risk(findings)

    return {
        "document_name": file.filename,
        "file_type": file.content_type,
        "file_size": file_size,
        "extracted_metadata": extracted_metadata,
        "findings": findings,
        "metadata_risk_score": risk["metadata_risk_score"],
        "metadata_risk_level": risk["metadata_risk_level"],
        "summary": risk["summary"],
        "recommended_action": risk["recommended_action"],
    }