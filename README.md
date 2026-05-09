# Metadata Mutation Checker – Summary

## Tools / Libraries Used

- **Python** – core language.
- **FastAPI** – HTTP API framework for the `/analyze` endpoint.
- **Uvicorn** – ASGI server to run the FastAPI app.
- **pypdf** – to read PDF files and extract metadata and page count.
- **python-multipart** – to handle file uploads via `UploadFile` in FastAPI.

---

## Metadata Fields Extracted

For PDF files, the service extracts:

- File name
- Page count
- Created date
- Modified date
- Author
- Creator
- Producer
- Title
- Subject
- Encryption status (encrypted or not)

These fields are returned under the `extracted_metadata` object in the API response.

---

## Rules Implemented

Each rule inspects the normalized metadata and returns a structured finding with `title`, `severity`, `confidence`, `explanation`, and `category`:

1. **Missing modified date**
   - Created date present, modified date missing.
   - Severity: Low; Confidence: 0.4.

2. **Modified date earlier than created date**
   - Modified date is earlier than created date.
   - Severity: Medium; Confidence: 0.7.

3. **Modified significantly after creation**
   - Modified date is more than N days (default 30) after created date.
   - Severity: Medium; Confidence: 0.6.

4. **Creator and producer differ**
   - Creator and producer fields are both set and not equal.
   - Severity: Low; Confidence: 0.6.

5. **Metadata shows common editing/export tools**
   - Creator or producer mentions tools like Acrobat, Preview, Photoshop, Illustrator, Canva, scanner software, or common online PDF editors.
   - Severity: Low; Confidence: 0.5.

6. **Missing author metadata**
   - Author field is empty or missing.
   - Severity: Low; Confidence: 0.3.

All rules are treated as **signals**, not proof of tampering.

---

## Scoring Logic

- Each finding contributes a score of `severity_weight * confidence`, where:
  - Low = 1
  - Medium = 3
  - High = 5
- Findings in the same category (e.g., multiple date-related findings) add a small bonus.
- The raw score is normalized to a 0–100 range and capped at 100.
- Risk levels:
  - 0–30: **Low**
  - 31–65: **Medium**
  - 66–100: **High**
- The final response includes:
  - `metadata_risk_score`
  - `metadata_risk_level`
  - A cautious `summary`
  - A `recommended_action` aligned with the risk level.

The wording is intentionally careful and never claims a document is fake; it only indicates that metadata **may suggest** post‑creation editing or conversion.

---

## Limitations

- Only PDF files are supported; JPG/PNG EXIF and DOCX metadata are not implemented yet.
- Uses high-level metadata exposed by `pypdf` and does not compare XMP vs Document Info or detect incremental updates.
- Date parsing supports a small set of common formats and may treat unusual formats as missing.
- Risk scoring is heuristic and should be combined with manual review and contextual information.

---

## What I Would Improve with More Time

- Add support for additional file types:
  - JPG/PNG (EXIF metadata).
  - DOCX (office document properties).
- Implement more advanced PDF checks:
  - XMP vs Document Info mismatch detection.
  - Detection of incremental updates / multiple revisions.
- Build a simple React UI:
  - Drag‑and‑drop upload.
  - Human-readable table of findings.
  - Button to download the JSON report.
- Provide two explanation modes:
  - “Simple explanation” for non-technical users.
  - “Technical explanation” with more detail about metadata fields and PDF internals.
- Improve date normalization and timezone handling for more edge cases.