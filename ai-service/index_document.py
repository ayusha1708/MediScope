"""Build and save a local TF-IDF index for an approved document."""

import argparse
import json
from datetime import datetime
from pathlib import Path

from app.documents.approval_gate import ApprovalGateError, require_approved_document
from app.documents.approval import ApprovalRecord, ApprovalRecordError
from app.documents.chunker import ChunkingError, chunk_text
from app.documents.extractor import DocumentProcessingError, extract_document
from app.documents.validation import DocumentValidationError
from app.retrieval.storage import IndexStorageError, save_tfidf_index
from app.retrieval.tfidf import TfidfVectorizationError, fit_tfidf


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INDEX_ROOT = PROJECT_ROOT / "data" / "tfidf_index"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build and save a local TF-IDF index for an approved document."
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
        index = fit_tfidf(chunks)
        output_dir = save_tfidf_index(
            index,
            document_metadata=record.document,
            index_root=INDEX_ROOT,
            processing_metadata={
                "file_name": extracted.filename,
                "file_type": extracted.file_type,
                "file_size_bytes": extracted.size_bytes,
                "file_sha256": extracted.sha256,
                "page_count": extracted.page_count,
                "indexed_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                "chunk_size_words": args.chunk_size_words,
                "overlap_words": args.overlap_words,
            },
        )
    except (
        ApprovalGateError,
        ApprovalRecordError,
        ChunkingError,
        DocumentProcessingError,
        DocumentValidationError,
        IndexStorageError,
        TfidfVectorizationError,
        OSError,
        json.JSONDecodeError,
    ) as error:
        parser.exit(status=1, message=f"Could not build local index: {error}\n")

    print("Approval gate passed; local TF-IDF index saved.")
    print(f"File: {extracted.filename}")
    print(f"Chunks and sparse vectors: {len(index.chunks)}")
    print(f"Vocabulary features: {index.feature_count}")
    print(f"Saved to: {output_dir}")
    print("The index contains source-page metadata for later citations.")


if __name__ == "__main__":
    main()
