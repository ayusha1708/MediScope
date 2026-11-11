"""Run the local PDF/TXT validation and extraction workflow."""

import argparse

from app.documents.extractor import DocumentProcessingError, extract_document
from app.documents.validation import DocumentValidationError


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate a PDF/TXT file and report extracted-text details."
    )
    parser.add_argument("file", help="Path to a PDF or UTF-8 TXT file")
    args = parser.parse_args()

    try:
        document = extract_document(args.file)
    except (DocumentValidationError, DocumentProcessingError) as error:
        parser.exit(status=1, message=f"Could not process document: {error}\n")

    print("Document accepted for technical processing.")
    print(f"File: {document.filename}")
    print(f"Type: {document.file_type.upper()}")
    print(f"Size: {document.size_bytes} bytes")
    if document.page_count is not None:
        print(f"Pages: {document.page_count}")
    print(f"Extracted characters: {len(document.text)}")
    print(f"SHA-256: {document.sha256}")
    print("Extracted text was kept in memory; nothing was indexed or saved.")


if __name__ == "__main__":
    main()
