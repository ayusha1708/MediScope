"""Extract plain text from supported PDF and TXT files."""

from dataclasses import dataclass
from pathlib import Path

import pymupdf

from app.documents.validation import (
    DocumentValidationError,
    validate_document,
)
from app.documents.preprocessor import clean_extracted_text


class DocumentProcessingError(ValueError):
    """Raised when a supported file cannot provide usable text."""


@dataclass(frozen=True)
class ExtractedPage:
    """Text from one PDF page; TXT documents use no page number."""

    page_number: int | None
    text: str


@dataclass(frozen=True)
class ExtractedDocument:
    filename: str
    file_type: str
    size_bytes: int
    sha256: str
    page_count: int | None
    text: str
    pages: tuple[ExtractedPage, ...]


def extract_document(file_path: str | Path) -> ExtractedDocument:
    """Validate and extract text in memory; this function does not save it."""
    validated = validate_document(file_path)

    if validated.file_type == "txt":
        text = clean_extracted_text(validated.path.read_text(encoding="utf-8-sig"))
        page_count = None
        pages = (ExtractedPage(page_number=None, text=text),)
    else:
        try:
            with pymupdf.open(validated.path) as document:
                if not document.is_pdf:
                    raise DocumentProcessingError("The file extension says PDF, but the file is not a PDF.")
                if document.needs_pass:
                    raise DocumentProcessingError("Password-protected PDFs are not supported.")
                page_count = document.page_count
                pages = tuple(
                    ExtractedPage(
                        page_number=page_number,
                        text=clean_extracted_text(page.get_text("text", sort=True)),
                    )
                    for page_number, page in enumerate(document, start=1)
                )
                text = "\n\n".join(page.text for page in pages if page.text)
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
        pages=pages,
    )
