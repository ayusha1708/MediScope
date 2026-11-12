"""Find document passages that best match a user's question."""

from dataclasses import dataclass
from typing import Any

from scipy.sparse import csr_matrix
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class RetrievalError(ValueError):
    """Raised when a question cannot be searched against the saved index."""


@dataclass(frozen=True)
class SearchIndex:
    """The saved TF-IDF model, passage vectors, and passage metadata."""

    vectorizer: TfidfVectorizer
    vectors: csr_matrix
    chunks: list[dict[str, Any]]
    document: dict[str, Any]


@dataclass(frozen=True)
class SearchResult:
    """A passage plus its cosine similarity to the question."""

    chunk: dict[str, Any]
    score: float


def find_relevant_passages(
    question: str, index: SearchIndex, *, limit: int = 3
) -> list[SearchResult]:
    """Return up to `limit` passages ranked by TF-IDF cosine similarity."""
    if not question.strip():
        raise RetrievalError("Enter a question to search the document.")
    if limit < 1:
        raise RetrievalError("The result limit must be at least 1.")

    question_vector = index.vectorizer.transform([question])
    scores = cosine_similarity(question_vector, index.vectors).ravel()
    ranked_indexes = scores.argsort()[::-1][:limit]
    return [
        SearchResult(chunk=index.chunks[int(position)], score=float(scores[position]))
        for position in ranked_indexes
    ]
