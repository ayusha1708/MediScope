"""Split extracted document text into small, overlapping passages."""

from dataclasses import dataclass


class ChunkingError(ValueError):
    """Raised when text or chunk settings cannot produce valid passages."""


@dataclass(frozen=True)
class TextChunk:
    """One passage with its source page and zero-based page-local word offsets."""

    index: int
    page_number: int | None
    start_word: int
    end_word: int
    text: str


def chunk_text(
    text: str,
    *,
    page_number: int | None = None,
    first_chunk_index: int = 0,
    chunk_size_words: int = 250,
    overlap_words: int = 40,
) -> list[TextChunk]:
    """Chunk one page of text; chunks never cross page boundaries."""
    if not isinstance(text, str):
        raise ChunkingError("Text must be a string.")
    if page_number is not None and page_number < 1:
        raise ChunkingError("page_number must be 1 or greater, or None for TXT.")
    if first_chunk_index < 0:
        raise ChunkingError("first_chunk_index cannot be negative.")
    if chunk_size_words < 1:
        raise ChunkingError("chunk_size_words must be at least 1.")
    if overlap_words < 0:
        raise ChunkingError("overlap_words cannot be negative.")
    if overlap_words >= chunk_size_words:
        raise ChunkingError("overlap_words must be smaller than chunk_size_words.")

    words = text.split()
    if not words:
        return []

    chunks: list[TextChunk] = []
    step = chunk_size_words - overlap_words

    for local_index, start in enumerate(range(0, len(words), step)):
        end = min(start + chunk_size_words, len(words))
        chunks.append(
            TextChunk(
                index=first_chunk_index + local_index,
                page_number=page_number,
                start_word=start,
                end_word=end,
                text=" ".join(words[start:end]),
            )
        )

    return chunks
