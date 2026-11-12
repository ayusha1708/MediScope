"""Build local sparse TF-IDF vectors for page-aware document chunks."""

from dataclasses import dataclass
from typing import Sequence

from scipy.sparse import csr_matrix
from sklearn.feature_extraction.text import TfidfVectorizer

from app.documents.chunker import TextChunk


class TfidfVectorizationError(ValueError):
    """Raised when text chunks cannot be converted to TF-IDF vectors."""


@dataclass(frozen=True)
class TfidfIndex:
    """The fitted vocabulary, sparse chunk vectors, and their source chunks."""

    vectorizer: TfidfVectorizer
    chunks: tuple[TextChunk, ...]
    vectors: csr_matrix

    @property
    def feature_count(self) -> int:
        """Number of terms/features in the fitted vocabulary."""
        return self.vectors.shape[1]

    def vectorize_query(self, query: str) -> csr_matrix:
        """Convert a search question using the same vocabulary and weights."""
        if not isinstance(query, str) or not query.strip():
            raise TfidfVectorizationError("The search query must contain text.")
        return self.vectorizer.transform([query])


def fit_tfidf(chunks: Sequence[TextChunk]) -> TfidfIndex:
    """Fit TF-IDF on chunks and return sparse vectors without saving them."""
    if not chunks:
        raise TfidfVectorizationError("There are no chunks to vectorize.")
    if any(not chunk.text.strip() for chunk in chunks):
        raise TfidfVectorizationError("Every chunk must contain text.")

    vectorizer = TfidfVectorizer(ngram_range=(1, 2))
    try:
        vectors = vectorizer.fit_transform([chunk.text for chunk in chunks]).tocsr()
    except ValueError as error:
        raise TfidfVectorizationError(
            "The chunks do not contain enough usable words to build a vocabulary."
        ) from error

    return TfidfIndex(
        vectorizer=vectorizer,
        chunks=tuple(chunks),
        vectors=vectors,
    )
