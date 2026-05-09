from datetime import datetime
from io import BytesIO
from typing import Optional
from pypdf import PdfReader

SEVERITY_WEIGHTS = {
    "Low": 1,
    "Medium": 3,
    "High": 5,
}


def extract_pdf_metadata(content: bytes, filename: str) -> dict:
    """
    Extract basic metadata from a PDF using pypdf.
    """
    pdf_file = BytesIO(content)
    reader = PdfReader(pdf_file)
    doc_meta = reader.metadata or {}
    num_pages = len(reader.pages)

    created = getattr(doc_meta, "creation_date", None)
    modified = getattr(doc_meta, "mod_date", None)

    created_str = str(created) if created is not None else None
    modified_str = str(modified) if modified is not None else None

    metadata = {
        "file_name": filename,
        "page_count": num_pages,
        "created_date": created_str,
        "modified_date": modified_str,
        "author": getattr(doc_meta, "author", None),
        "creator": getattr(doc_meta, "creator", None),
        "producer": getattr(doc_meta, "producer", None),
        "title": getattr(doc_meta, "title", None),
        "subject": getattr(doc_meta, "subject", None),
        "encrypted": reader.is_encrypted,
    }
    return metadata


def parse_iso_like_datetime(value: Optional[str]) -> Optional[datetime]:
    """
    Try to parse a datetime string into a datetime object.
    Returns None if parsing fails or value is None.
    """
    if not value:
        return None

    for fmt in ("%Y-%m-%d %H:%M:%S%z", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue

    return None


def check_missing_modified_date(meta: dict) -> Optional[dict]:
    created = parse_iso_like_datetime(meta.get("created_date"))
    modified_raw = meta.get("modified_date")
    modified = parse_iso_like_datetime(modified_raw) if modified_raw else None

    if created and not modified:
        return {
            "title": "Missing modified date",
            "severity": "Low",
            "confidence": 0.4,
            "explanation": (
                "The document metadata includes a created date but no modified date. "
                "This can be normal depending on how the PDF was generated."
            ),
            "category": "dates",
        }
    return None


def check_modified_before_created(meta: dict) -> Optional[dict]:
    created = parse_iso_like_datetime(meta.get("created_date"))
    modified = parse_iso_like_datetime(meta.get("modified_date"))

    if created and modified and modified < created:
        return {
            "title": "Modified date earlier than created date",
            "severity": "Medium",
            "confidence": 0.7,
            "explanation": (
                "The modified date in the metadata is earlier than the created date. "
                "This is unusual and may indicate incorrect metadata or post-processing."
            ),
            "category": "dates",
        }
    return None


def check_modified_much_later(meta: dict, days_threshold: int = 30) -> Optional[dict]:
    """
    Modified date is significantly later than created date.
    """
    created = parse_iso_like_datetime(meta.get("created_date"))
    modified = parse_iso_like_datetime(meta.get("modified_date"))

    if not created or not modified:
        return None

    delta = modified - created
    if delta.days > days_threshold:
        return {
            "title": "Modified significantly after creation",
            "severity": "Medium",
            "confidence": 0.6,
            "explanation": (
                f"The modified date in the metadata is more than {days_threshold} days "
                "later than the created date. This can result from normal editing or "
                "conversion workflows but may be relevant in sensitive contexts."
            ),
            "category": "dates",
        }
    return None


def check_creator_producer_mismatch(meta: dict) -> Optional[dict]:
    creator = (meta.get("creator") or "").strip()
    producer = (meta.get("producer") or "").strip()

    if creator and producer and creator != producer:
        return {
            "title": "Creator and producer differ",
            "severity": "Low",
            "confidence": 0.6,
            "explanation": (
                "The PDF appears to have been created with one tool and processed or "
                "exported with another. This often happens during normal editing or conversion."
            ),
            "category": "tools",
        }
    return None


def check_suspicious_tools(meta: dict) -> Optional[dict]:
    """
    Look for common editing/export tools in creator/producer fields.
    Treated as a soft signal, not proof.
    """
    creator = (meta.get("creator") or "").lower()
    producer = (meta.get("producer") or "").lower()

    keywords = [
        "acrobat",
        "preview",
        "photoshop",
        "illustrator",
        "canva",
        "online pdf",
        "pdfescape",
        "smallpdf",
        "scanner",
        "scansnap",
        "pdf editor",
    ]

    matched = set()
    for kw in keywords:
        if kw in creator or kw in producer:
            matched.add(kw)

    if not matched:
        return None

    return {
        "title": "Metadata shows common editing or export tools",
        "severity": "Low",
        "confidence": 0.5,
        "explanation": (
            "The creator/producer fields reference tools commonly used for editing, "
            "exporting, or scanning PDFs. This is very common in normal document "
            "handling and should not be treated as proof of tampering by itself."
        ),
        "category": "tools",
        "matched_tools": sorted(list(matched)),
    }


def check_missing_author(meta: dict) -> Optional[dict]:
    author = meta.get("author")
    if not author:
        return {
            "title": "Missing author metadata",
            "severity": "Low",
            "confidence": 0.3,
            "explanation": (
                "The author field in the metadata is empty. "
                "This is common and usually not a strong indicator of tampering."
            ),
            "category": "fields",
        }
    return None


def run_metadata_checks(meta: dict) -> list[dict]:
    checks = [
        check_missing_modified_date,
        check_modified_before_created,
        check_modified_much_later,
        check_creator_producer_mismatch,
        check_suspicious_tools,
        check_missing_author,
    ]

    findings: list[dict] = []
    for check in checks:
        result = check(meta)
        if result is not None:
            findings.append(result)

    return findings


def compute_risk(findings: list[dict]) -> dict:
    """
    Given a list of findings, compute an overall risk score and level.
    """
    if not findings:
        return {
            "metadata_risk_score": 0,
            "metadata_risk_level": "Low",
            "summary": (
                "The metadata does not show strong unusual patterns. "
                "This does not prove authenticity, but there are no significant metadata signals."
            ),
            "recommended_action": (
                "No immediate action is required based on metadata alone. "
                "Review the document manually if it is part of a high-value or sensitive process."
            ),
        }

    raw_score = 0.0
    category_counts: dict[str, int] = {}

    for f in findings:
        severity = f.get("severity", "Low")
        confidence = f.get("confidence", 0.5)
        weight = SEVERITY_WEIGHTS.get(severity, 1)

        raw_score += weight * confidence

        category = f.get("category")
        if category:
            category_counts[category] = category_counts.get(category, 0) + 1

    for count in category_counts.values():
        if count > 1:
            raw_score += 0.5 * (count - 1)

    normalized = min(raw_score / 15 * 100, 100)

    if normalized <= 30:
        level = "Low"
        summary = (
            "The document metadata contains mostly weak or common signals. "
            "These findings alone do not strongly suggest unusual editing."
        )
        recommended_action = (
            "No immediate action is required based on metadata alone. "
            "Consider manual review if the document is important."
        )
    elif normalized <= 65:
        level = "Medium"
        summary = (
            "The document metadata shows some patterns that may suggest post-creation "
            "editing or conversion. These signals should be reviewed with other evidence."
        )
        recommended_action = (
            "If this file is used in a high-value or sensitive process, perform a manual "
            "review of both the content and its context."
        )
    else:
        level = "High"
        summary = (
            "The document metadata includes multiple or stronger indicators that may be "
            "consistent with significant post-creation modification. This is not proof of "
            "tampering but should be treated with caution."
        )
        recommended_action = (
            "Perform a detailed manual review, consider comparing with original sources, "
            "and correlate with other technical or contextual evidence."
        )

    return {
        "metadata_risk_score": int(round(normalized)),
        "metadata_risk_level": level,
        "summary": summary,
        "recommended_action": recommended_action,
    }