# Metadata Mutation Checker

A small FastAPI-based service that accepts a document (PDF) and returns a structured metadata analysis report. The goal is **not** to prove tampering, but to highlight metadata patterns that may indicate post‑creation editing or conversion and present them in a careful, non‑dramatic way. 

---

## Features

- `POST /analyze` endpoint to upload and analyze a **PDF** file.
- Extracts key PDF metadata using `pypdf`, including:
  - File name
  - Page count
  - Created date
  - Modified date
  - Author
  - Creator
  - Producer
  - Title
  - Subject
  - Encryption status
- Rule-based metadata checks:
  - Created date exists but modified date is missing
  - Modified date earlier than created date
  - Modified date significantly later than created date (configurable threshold)
  - Creator and producer mismatch
  - Creator/producer mention common editing/export tools (Acrobat, Preview, Canva, scanner, online editors, etc.)
  - Missing author metadata
- Risk scoring based on:
  - Severity and confidence of each finding
  - Number of findings
  - Grouping of related findings (e.g., multiple date-related findings)
- Returns a JSON report with:
  - `document_name`
  - `file_type`
  - `file_size`
  - `extracted_metadata`
  - `findings` (list of structured rule results)
  - `metadata_risk_score` (0–100)
  - `metadata_risk_level` (`Low`, `Medium`, `High`)
  - `summary`
  - `recommended_action`

---

## Tech Stack

- **Language**: Python
- **Web Framework**: FastAPI
- **PDF Library**: pypdf
- **Server**: Uvicorn
- **Upload Handling**: FastAPI `UploadFile` with `python-multipart`

---

## Project Structure

```text
metadata-checker/
  app/
    __init__.py
    main.py                # FastAPI app and HTTP endpoints
    metadata_analyzer.py   # Extraction, rule checks, risk scoring
  venv/                    # (optional, local virtualenv)
  README.md
  requirements.txt
```

---

## Setup Instructions

### 1. Clone the repository

```bash
git clone <YOUR_REPO_URL> metadata-checker
cd metadata-checker
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv