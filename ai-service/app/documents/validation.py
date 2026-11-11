"""Basic checks for document files before text extraction."""

from dataclasses import dataclass
import hashlib
from pathlib import Path

MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024
SUPPORTED_SUFFIXES = {".pdf", ".txt"}


class DocumentValidationError(ValueError):
    """Raised when a submitted file is outside the supported limits."""


@dataclass(frozen=True)
class ValidatedDocument:
    path: Path
    file_type: str
    size_bytes: int
    sha256: str


def validate_document(file_path: str | Path) -> ValidatedDocument:
    """Check path, extension, size, and basic TXT readability; compute a hash."""
    path = Path(file_path).expanduser()
    if not path.exists():
        raise DocumentValidationError("File does not exist.")
    if not path.is_file():
        raise DocumentValidationError("The supplied path is not a file.")

    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise DocumentValidationError("Only PDF and TXT files are supported.")

    size_bytes = path.stat().st_size
    if size_bytes == 0:
        raise DocumentValidationError("The file is empty.")
    if size_bytes > MAX_FILE_SIZE_BYTES:
        limit_mb = MAX_FILE_SIZE_BYTES // (1024 * 1024)
        raise DocumentValidationError(f"The file exceeds the {limit_mb} MB limit.")

    if suffix == ".txt":
        try:
            text = path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError as error:
            raise DocumentValidationError(
                "TXT files must use UTF-8 text encoding."
            ) from error
        if "\x00" in text:
            raise DocumentValidationError("The TXT file appears to contain binary data.")
        if not text.strip():
            raise DocumentValidationError("The TXT file contains no readable text.")

    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)

    return ValidatedDocument(
        path=path.resolve(),
        file_type=suffix[1:],
        size_bytes=size_bytes,
        sha256=digest.hexdigest(),
    )
