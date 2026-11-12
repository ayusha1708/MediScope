"""Apply conservative, page-safe cleanup to extracted document text."""

import re
import unicodedata


def clean_extracted_text(text: str) -> str:
    """Normalize whitespace and common PDF artifacts without removing content."""
    if not isinstance(text, str):
        raise TypeError("Extracted text must be a string.")

    cleaned = unicodedata.normalize("NFC", text)
    cleaned = cleaned.replace("\u00ad", "")
    cleaned = cleaned.replace("\u00a0", " ").replace("\u202f", " ")
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")
    cleaned = "".join(
        character
        for character in cleaned
        if character in "\n\t" or unicodedata.category(character) != "Cc"
    )
    cleaned = re.sub(r"[\t ]+", " ", cleaned)
    cleaned = re.sub(r" *\n *", "\n", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()
