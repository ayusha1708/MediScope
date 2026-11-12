"""Check approval, extract a document, and preview in-memory text chunks."""

import argparse

from app.documents.approval_gate import ApprovalGateError, require_approved_document
from app.documents.chunker import ChunkingError, chunk_text
from app.documents.extractor import DocumentProcessingError, extract_document
from app.documents.validation import DocumentValidationError


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Chunk an approved PDF/TXT in memory; this command does not save chunks."
    )
    parser.add_argument("document", help="Path to the approved PDF or TXT file")
    parser.add_argument("review_record", help="Path to its approved JSON review record")
    parser.add_argument("--chunk-size-words", type=int, default=250)
    parser.add_argument("--overlap-words", type=int, default=40)
    args = parser.parse_args()

    try:
        approved_file = require_approved_document(args.document, args.review_record)
        extracted = extract_document(args.document)
        if extracted.sha256.lower() != approved_file.sha256.lower():
            raise ApprovalGateError(
                "The file changed after approval verification. Review this exact file again."
            )
        chunks = []
        for page in extracted.pages:
            page_chunks = chunk_text(
                page.text,
                page_number=page.page_number,
                first_chunk_index=len(chunks),
                chunk_size_words=args.chunk_size_words,
                overlap_words=args.overlap_words,
            )
            chunks.extend(page_chunks)
    except (
        ApprovalGateError,
        ChunkingError,
        DocumentProcessingError,
        DocumentValidationError,
    ) as error:
        parser.exit(status=1, message=f"Could not chunk document: {error}\n")

    print("Approval gate passed; text chunking completed in memory.")
    print(f"File: {extracted.filename}")
    print(f"Chunks: {len(chunks)}")
    if extracted.file_type == "pdf":
        print(f"Source pages retained: {extracted.page_count}")
    print(
        f"Settings: {args.chunk_size_words} words per chunk, "
        f"{args.overlap_words} words of overlap"
    )
    print("No chunks were saved, embedded, or added to a vector database.")


if __name__ == "__main__":
    main()
