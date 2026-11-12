"""Require an approved review record for a specific unchanged document file."""

import json
from pathlib import Path

from app.documents.approval import (
    ApprovalRecord,
    ApprovalRecordError,
    ReviewDecision,
)
from app.documents.validation import (
    DocumentValidationError,
    ValidatedDocument,
    validate_document,
)


class ApprovalGateError(ValueError):
    """Raised when a file is not eligible for a later indexing step."""


def require_approved_document(
    document_path: str | Path,
    review_record_path: str | Path,
) -> ValidatedDocument:
    """Return file details only if its review is approved and hash matches."""
    try:
        validated = validate_document(document_path)
    except DocumentValidationError as error:
        raise ApprovalGateError(f"Document failed technical validation: {error}") from error

    record_path = Path(review_record_path)
    try:
        review_data = json.loads(record_path.read_text(encoding="utf-8"))
        record = ApprovalRecord.from_dict(review_data)
    except OSError as error:
        raise ApprovalGateError(f"Cannot read review record: {error}") from error
    except json.JSONDecodeError as error:
        raise ApprovalGateError("Review record is not valid JSON.") from error
    except ApprovalRecordError as error:
        raise ApprovalGateError(f"Review record is invalid: {error}") from error

    if record.decision != ReviewDecision.APPROVED:
        raise ApprovalGateError(
            f"Review decision is {record.decision.value}; only APPROVED documents can proceed."
        )

    approved_hash = str(record.document.get("file_sha256", "")).strip().lower()
    if not approved_hash:
        raise ApprovalGateError("Review record has no approved file SHA-256 hash.")
    if approved_hash != validated.sha256.lower():
        raise ApprovalGateError(
            "The document hash does not match the approved file. Review this exact file again."
        )

    return validated
