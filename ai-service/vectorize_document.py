"""Create local TF-IDF vectors for an approved PDF/TXT document."""

import argparse

from app.documents.approval_gate import ApprovalGateError, require_approved_document
from app.documents.chunker import ChunkingError, chunk_text
from app.documents.extractor import DocumentProcessingError, extract_document
from app.documents.validation import DocumentValidationError
from app.retrieval.tfidf import TfidfVectorizationError, fit_tfidf


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Vectorize an approved document locally; vectors are not saved."
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
    except (
        ApprovalGateError,
        ChunkingError,
        DocumentProcessingError,
        DocumentValidationError,
        TfidfVectorizationError,
    ) as error:
        parser.exit(status=1, message=f"Could not vectorize document: {error}\n")

    print("Approval gate passed; local TF-IDF vectors created in memory.")
    print(f"File: {extracted.filename}")
    print(f"Chunks and sparse vectors: {len(index.chunks)}")
    print(f"Vocabulary features: {index.feature_count}")
    print(f"Non-zero term weights: {index.vectors.nnz}")
    print("No chunks or vectors were saved or added to a vector database.")


if __name__ == "__main__":
    main()
