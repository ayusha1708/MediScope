"""Store one approved document's catalog and review metadata in MongoDB."""

import argparse
import json
from pathlib import Path

from pymongo.errors import PyMongoError

from app.documents.approval import ApprovalRecord, ApprovalRecordError
from app.documents.approval_gate import ApprovalGateError, require_approved_document
from app.storage.documents import DocumentStorageError, save_approved_document
from app.storage.mongodb import (
    MongoConfigurationError,
    create_mongo_client,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Store metadata for one approved document in MongoDB. "
            "This does not upload the original file, chunks, or vectors."
        )
    )
    parser.add_argument("document", help="Path to the approved PDF or TXT file")
    parser.add_argument("review_record", help="Path to its approved JSON review record")
    args = parser.parse_args()

    try:
        validated_file = require_approved_document(args.document, args.review_record)
        review_data = json.loads(Path(args.review_record).read_text(encoding="utf-8"))
        record = ApprovalRecord.from_dict(review_data)
        with create_mongo_client() as client:
            client.admin.command("ping")
            mongo_id = save_approved_document(client, record, validated_file)
    except (
        ApprovalGateError,
        ApprovalRecordError,
        DocumentStorageError,
        MongoConfigurationError,
        OSError,
        json.JSONDecodeError,
    ) as error:
        parser.exit(status=1, message=f"Could not store approved document: {error}\n")
    except PyMongoError:
        parser.exit(
            status=1,
            message=(
                "Could not store the document in MongoDB. Check Atlas Network Access, "
                "database-user permissions, and the URI in ai-service/.env.\n"
            ),
        )

    print("Approved document metadata stored in MongoDB.")
    print(f"Document: {record.document.get('title', '(untitled)')}")
    print(f"Document ID/version: {record.document.get('document_id')} / {record.document.get('version')}")
    print(f"MongoDB record ID: {mongo_id}")
    print("Stored: catalog metadata, file hash/details, and admin review evidence.")
    print("Not stored yet: original file, extracted text, chunks, and TF-IDF vectors.")


if __name__ == "__main__":
    main()
