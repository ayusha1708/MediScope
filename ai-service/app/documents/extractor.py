"""Extract plain text from supported PDF and TXT files."""

from dataclasses import dataclass
from pathlib import Path

import pymupdf

from app.documents.validation import (
    DocumentValidationError,
    validate_document,
)


class DocumentProcessingError(ValueError):
    """Raised when a supported file cannot provide usable text."""


@dataclass(frozen=True)
class ExtractedDocument:
    filename: str
    file_type: str
    size_bytes: int
    sha256: str
    page_count: int | None
    text: str


def extract_document(file_path: str | Path) -> ExtractedDocument:
    """Validate and extract text in memory; this function does not save it."""
    validated = validate_document(file_path)

    if validated.file_type == "txt":
        text = validated.path.read_text(encoding="utf-8-sig").strip()
        page_count = None
    else:
        try:
            with pymupdf.open(validated.path) as document:
                if not document.is_pdf:
                    raise DocumentProcessingError("The file extension says PDF, but the file is not a PDF.")
                if document.needs_pass:
                    raise DocumentProcessingError("Password-protected PDFs are not supported.")
                page_count = document.page_count
                page_text = [page.get_text("text", sort=True).strip() for page in document]
                text = "\n\n".join(part for part in page_text if part)
        except DocumentProcessingError:
            raise
        except Exception as error:
            raise DocumentProcessingError(
                "The PDF is damaged or could not be read."
            ) from error

    if not text:
        raise DocumentProcessingError(
            "No selectable text was found. Scanned/image-only PDFs need OCR, which is not included yet."
        )

    return ExtractedDocument(
        filename=validated.path.name,
        file_type=validated.file_type,
        size_bytes=validated.size_bytes,
        sha256=validated.sha256,
        page_count=page_count,
        text=text,
    )
