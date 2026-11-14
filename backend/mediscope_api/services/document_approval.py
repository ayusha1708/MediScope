"""Run the existing approved-document pipeline for an admin-approved upload."""

from pathlib import Path

from app.documents.approval import ApprovalRecord
from app.documents.chunker import ChunkingError, TextChunk, chunk_text
from app.documents.extractor import DocumentProcessingError, extract_document
from app.documents.validation import DocumentValidationError, validate_document
from app.retrieval.tfidf import TfidfVectorizationError, fit_tfidf
from app.storage.chunks import ChunkStorageError, save_document_chunks
from app.storage.documents import DocumentStorageError, save_approved_document
from app.storage.tfidf_index import TfidfStorageError, save_corpus_tfidf_index
from mediscope_api.ai_bridge import get_database_name


CHUNK_SIZE_WORDS = 250
OVERLAP_WORDS = 40


class DocumentApprovalError(ValueError):
    """Raised when an approved submission cannot be safely indexed."""


def process_approved_upload(client, review_data: dict, file_path: Path) -> dict:
    """Validate approval, store metadata/passages, and publish a refreshed TF-IDF index."""
    record = ApprovalRecord.from_dict(review_data)
    if record.decision.value != "APPROVED":
        raise DocumentApprovalError("Only an APPROVED review can enter document processing.")

    try:
        validated = validate_document(file_path)
        if record.document.get("file_sha256", "").lower() != validated.sha256.lower():
            raise DocumentApprovalError("The uploaded file hash differs from the review record.")
        extracted = extract_document(file_path)
        chunks = []
        for page in extracted.pages:
            chunks.extend(
                chunk_text(
                    page.text,
                    page_number=page.page_number,
                    first_chunk_index=len(chunks),
                    chunk_size_words=CHUNK_SIZE_WORDS,
                    overlap_words=OVERLAP_WORDS,
                )
            )
        if not chunks:
            raise DocumentApprovalError("No usable text passages were produced from this file.")

        database = client[get_database_name()]
        document_id = str(record.document.get("document_id", "")).strip()
        version = str(record.document.get("version", "")).strip()
        document_record_id = f"{document_id}:v{version}"
        existing = database["documents"].find_one({"_id": document_record_id})
        if existing is None:
            save_approved_document(client, record, validated)
        elif (
            existing.get("file", {}).get("sha256", "").lower() != validated.sha256.lower()
            or existing.get("approval", {}).get("decision") != "APPROVED"
            or existing.get("metadata") != record.document
            or existing.get("approval", {}).get("checks") != record.checks
            or existing.get("approval", {}).get("decision_reason") != record.decision_reason
            or existing.get("approval", {}).get("reviewer_id") != record.reviewer_id
        ):
            raise DocumentApprovalError(
                "That document ID and version already has different approval details or belongs to another file."
            )

        save_document_chunks(
            client,
            record,
            validated,
            chunks,
            chunk_size_words=CHUNK_SIZE_WORDS,
            overlap_words=OVERLAP_WORDS,
        )

        approved_ids = [
            item["_id"]
            for item in database["documents"].find(
                {
                    "approval.decision": "APPROVED",
                    "storage_status": {"$in": ["CHUNKS_STORED", "VECTORS_STORED"]},
                    "chunking.chunk_size_words": CHUNK_SIZE_WORDS,
                    "chunking.overlap_words": OVERLAP_WORDS,
                },
                {"_id": 1},
            )
        ]
        passages = list(
            database["chunks"]
            .find(
                {
                    "document_record_id": {"$in": approved_ids},
                    "chunking.chunk_size_words": CHUNK_SIZE_WORDS,
                    "chunking.overlap_words": OVERLAP_WORDS,
                }
            )
            .sort([("document_id", 1), ("document_version", 1), ("chunk_index", 1)])
        )
        index = fit_tfidf(
            [
                TextChunk(
                    index=int(item["chunk_index"]),
                    page_number=item.get("page_number"),
                    start_word=int(item["start_word"]),
                    end_word=int(item["end_word"]),
                    text=str(item["text"]),
                )
                for item in passages
            ]
        )
        index_id, _ = save_corpus_tfidf_index(client, index, passages, approved_ids)
    except (DocumentValidationError, DocumentProcessingError, ChunkingError,
            TfidfVectorizationError, ChunkStorageError, DocumentStorageError,
            TfidfStorageError, OSError, KeyError, TypeError, ValueError) as error:
        if isinstance(error, DocumentApprovalError):
            raise
        raise DocumentApprovalError(str(error)) from error
    return {
        "document_record_id": document_record_id,
        "passage_count": len(chunks),
        "index_id": index_id,
    }
