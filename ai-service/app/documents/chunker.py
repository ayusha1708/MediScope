"""Split extracted document text into small, overlapping passages."""

from dataclasses import dataclass


class ChunkingError(ValueError):
    """Raised when text or chunk settings cannot produce valid passages."""


@dataclass(frozen=True)
class TextChunk:
    """One passage, with zero-based word offsets into the extracted text."""

    index: int
    start_word: int
    end_word: int
    text: str


def chunk_text(
    text: str,
    *,
    chunk_size_words: int = 250,
    overlap_words: int = 40,
) -> list[TextChunk]:
    """Create word-count chunks with overlap, without saving or indexing them."""
    if not isinstance(text, str) or not text.strip():
        raise ChunkingError("Text must contain at least one non-whitespace character.")
    if chunk_size_words < 1:
        raise ChunkingError("chunk_size_words must be at least 1.")
    if overlap_words < 0:
        raise ChunkingError("overlap_words cannot be negative.")
    if overlap_words >= chunk_size_words:
        raise ChunkingError("overlap_words must be smaller than chunk_size_words.")

    words = text.split()
    chunks: list[TextChunk] = []
    step = chunk_size_words - overlap_words

    for index, start in enumerate(range(0, len(words), step)):
        end = min(start + chunk_size_words, len(words))
        chunks.append(
            TextChunk(
                index=index,
                start_word=start,
                end_word=end,
                text=" ".join(words[start:end]),
            )
        )

    return chunks
