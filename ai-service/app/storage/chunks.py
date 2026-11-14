"""Store approved-document passages in MongoDB, linked to catalog metadata."""

from typing import Any

from pymongo import MongoClient, UpdateOne

from app.documents.approval import ApprovalRecord
from app.documents.chunker import TextChunk
from app.documents.validation import ValidatedDocument
from app.storage.mongodb import get_database_name


class ChunkStorageError(ValueError):
    """Raised when passage storage does not match an approved catalog record."""


def save_document_chunks(
    client: MongoClient,
    record: ApprovalRecord,
    validated_file: ValidatedDocument,
    chunks: list[TextChunk],
    *,
    chunk_size_words: int,
    overlap_words: int,
) -> tuple[str, int, int]:
    """Upsert deterministic passage records and report inserted/existing counts."""
    metadata = record.document
    document_id = str(metadata.get("document_id", "")).strip()
    version = str(metadata.get("version", "")).strip()
    if record.decision.value != "APPROVED":
        raise ChunkStorageError("Only APPROVED documents can have passages stored.")
    if not document_id or not version:
        raise ChunkStorageError("The approved record needs a document_id and version.")
    if str(metadata.get("file_sha256", "")).lower() != validated_file.sha256.lower():
        raise ChunkStorageError("The file hash does not match the approved review record.")
    if not chunks:
        raise ChunkStorageError("No passages were produced; nothing was stored.")

    database = client[get_database_name()]
    mongo_id = f"{document_id}:v{version}"
    catalog_record = database["documents"].find_one(
        {"_id": mongo_id, "file.sha256": validated_file.sha256, "approval.decision": "APPROVED"}
    )
    if catalog_record is None:
        raise ChunkStorageError(
            "The matching approved document metadata is not in MongoDB yet. "
            "Run store_approved_document.py first."
        )

    chunk_collection = database["chunks"]
    operations = []
    for chunk in chunks:
        passage_number = chunk.index + 1
        passage_id = f"{document_id}:passage-{passage_number}"
        mongo_chunk_id = (
            f"{mongo_id}:c{chunk_size_words}-o{overlap_words}:p{passage_number}"
        )
        chunk_record: dict[str, Any] = {
            "_id": mongo_chunk_id,
            "document_id": document_id,
            "document_version": version,
            "document_record_id": mongo_id,
            "passage_id": passage_id,
            "chunk_index": chunk.index,
            "page_number": chunk.page_number,
            "start_word": chunk.start_word,
            "end_word": chunk.end_word,
            "word_count": len(chunk.text.split()),
            "text": chunk.text,
            "document_title": metadata.get("title", ""),
            "source_locator": metadata.get("full_text_url") or metadata.get("source_locator", ""),
            "file_sha256": validated_file.sha256,
            "chunking": {
                "chunk_size_words": chunk_size_words,
                "overlap_words": overlap_words,
            },
        }
        operations.append(
            UpdateOne(
                {"_id": mongo_chunk_id},
                {"$setOnInsert": chunk_record},
                upsert=True,
            )
        )

    result = chunk_collection.bulk_write(operations, ordered=True)
    database["documents"].update_one(
        {"_id": mongo_id, "file.sha256": validated_file.sha256},
        {
            "$set": {
                "storage_status": "CHUNKS_STORED",
                "chunk_count": len(chunks),
                "chunking": {
                    "chunk_size_words": chunk_size_words,
                    "overlap_words": overlap_words,
                },
            }
        },
    )
    return mongo_id, result.upserted_count, len(chunks) - result.upserted_count
