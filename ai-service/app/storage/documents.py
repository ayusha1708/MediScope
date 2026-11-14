"""Store approved-document catalog records in MongoDB."""

from datetime import datetime, timezone
from typing import Any

from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError

from app.documents.approval import ApprovalRecord
from app.documents.validation import ValidatedDocument
from app.storage.mongodb import get_database_name


class DocumentStorageError(ValueError):
    """Raised when an approved document record cannot be stored safely."""


def save_approved_document(
    client: MongoClient,
    record: ApprovalRecord,
    validated_file: ValidatedDocument,
) -> str:
    """Insert review and file metadata; never store extracted text or vectors here."""
    document = record.document
    document_id = str(document.get("document_id", "")).strip()
    version = str(document.get("version", "")).strip()
    if not document_id or not version:
        raise DocumentStorageError("The approved record needs a document_id and version.")
    if record.decision.value != "APPROVED":
        raise DocumentStorageError("Only APPROVED review records can be stored.")
    if str(document.get("file_sha256", "")).lower() != validated_file.sha256.lower():
        raise DocumentStorageError("The file hash does not match the approved review record.")

    mongo_id = f"{document_id}:v{version}"
    mongo_record: dict[str, Any] = {
        "_id": mongo_id,
        "document_id": document_id,
        "version": version,
        "metadata": document,
        "approval": {
            "decision": record.decision.value,
            "decision_reason": record.decision_reason,
            "reviewer_id": record.reviewer_id,
            "reviewed_at": record.reviewed_at,
            "checks": record.checks,
            "ai_screening_report": record.ai_screening_report,
        },
        "file": {
            "file_name": validated_file.path.name,
            "file_type": validated_file.file_type,
            "size_bytes": validated_file.size_bytes,
            "sha256": validated_file.sha256,
        },
        "storage_status": "METADATA_STORED",
        "stored_at": datetime.now(timezone.utc),
    }

    collection = client[get_database_name()]["documents"]
    try:
        collection.insert_one(mongo_record)
    except DuplicateKeyError as error:
        raise DocumentStorageError(
            f"Document {document_id} version {version} is already in MongoDB; "
            "no existing record was changed. Use a new version only after review."
        ) from error
    return mongo_id
