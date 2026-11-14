"""Recreate and store page-aware passages for an approved document."""

import argparse
import json
from pathlib import Path

from pymongo.errors import PyMongoError

from app.documents.approval import ApprovalRecord, ApprovalRecordError
from app.documents.approval_gate import ApprovalGateError, require_approved_document
from app.documents.chunker import ChunkingError, chunk_text
from app.documents.extractor import DocumentProcessingError, extract_document
from app.storage.chunks import ChunkStorageError, save_document_chunks
from app.storage.mongodb import MongoConfigurationError, create_mongo_client


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Store page-aware passages for an approved document in MongoDB. "
            "This does not store TF-IDF vectors."
        )
    )
    parser.add_argument("document", help="Path to the approved PDF or TXT file")
    parser.add_argument("review_record", help="Path to its approved JSON review record")
    parser.add_argument("--chunk-size-words", type=int, default=250)
    parser.add_argument("--overlap-words", type=int, default=40)
    args = parser.parse_args()

    try:
        approved_file = require_approved_document(args.document, args.review_record)
        review_data = json.loads(Path(args.review_record).read_text(encoding="utf-8"))
        record = ApprovalRecord.from_dict(review_data)
        extracted = extract_document(args.document)
        if extracted.sha256.lower() != approved_file.sha256.lower():
            raise ApprovalGateError(
                "The file changed after approval verification. Review this exact file again."
            )
        chunks = []
        for page in extracted.pages:
            chunks.extend(
                chunk_text(
                    page.text,
                    page_number=page.page_number,
                    first_chunk_index=len(chunks),
                    chunk_size_words=args.chunk_size_words,
                    overlap_words=args.overlap_words,
                )
            )
        with create_mongo_client() as client:
            client.admin.command("ping")
            mongo_id, inserted, existing = save_document_chunks(
                client,
                record,
                approved_file,
                chunks,
                chunk_size_words=args.chunk_size_words,
                overlap_words=args.overlap_words,
            )
    except (
        ApprovalGateError,
        ApprovalRecordError,
        ChunkingError,
        ChunkStorageError,
        DocumentProcessingError,
        MongoConfigurationError,
        OSError,
        json.JSONDecodeError,
    ) as error:
        parser.exit(status=1, message=f"Could not store passages: {error}\n")
    except PyMongoError:
        parser.exit(
            status=1,
            message=(
                "Could not store passages in MongoDB. Check Atlas Network Access, "
                "database-user permissions, and the URI in ai-service/.env.\n"
            ),
        )

    print("Approval gate passed; page-aware passages stored in MongoDB.")
    print(f"Document record: {mongo_id}")
    print(f"Passages generated: {len(chunks)}")
    print(f"New passages stored: {inserted}")
    print(f"Already stored unchanged: {existing}")
    print(f"Settings: {args.chunk_size_words} words per passage, {args.overlap_words} words overlap")
    print("Page numbers and passage IDs are stored for citations.")
    print("TF-IDF vectors are not stored yet.")


if __name__ == "__main__":
    main()
