"""Search passage vectors stored in MongoDB with the active fitted TF-IDF model."""

from dataclasses import dataclass
from typing import Any

import numpy as np
from pymongo import MongoClient
from scipy.sparse import csr_matrix
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.storage.mongodb import get_database_name


class MongoRetrievalError(ValueError):
    """Raised when the active MongoDB retrieval index cannot be searched."""


@dataclass(frozen=True)
class MongoSearchResult:
    """A ranked MongoDB passage with its citation metadata."""

    passage_id: str
    document_id: str
    document_title: str
    page_number: int | None
    source_locator: str
    text: str
    score: float


def search_mongodb_passages(
    client: MongoClient,
    question: str,
    *,
    limit: int = 3,
    document_id: str | None = None,
) -> list[MongoSearchResult]:
    """Vectorize a query with the stored model and rank stored sparse vectors."""
    if not isinstance(question, str) or not question.strip():
        raise MongoRetrievalError("Enter a question to search.")
    if limit < 1:
        raise MongoRetrievalError("The result limit must be at least 1.")

    database = client[get_database_name()]
    model = database["tfidf_indexes"].find_one({"_id": "active"})
    if not model:
        raise MongoRetrievalError(
            "No active TF-IDF index is stored. Run build_mongodb_tfidf_index.py first."
        )

    vocabulary_terms = model.get("vocabulary")
    idf_values = model.get("idf")
    feature_count = model.get("feature_count")
    if (
        not isinstance(vocabulary_terms, list)
        or not isinstance(idf_values, list)
        or not isinstance(feature_count, int)
        or len(vocabulary_terms) != feature_count
        or len(idf_values) != feature_count
    ):
        raise MongoRetrievalError("The saved TF-IDF vocabulary or IDF weights are invalid.")

    parameters = model.get("model_parameters", {})
    try:
        vectorizer = TfidfVectorizer(
            ngram_range=tuple(parameters.get("ngram_range", [1, 2])),
            norm=parameters.get("norm", "l2"),
            use_idf=parameters.get("use_idf", True),
            smooth_idf=parameters.get("smooth_idf", True),
            sublinear_tf=parameters.get("sublinear_tf", False),
            lowercase=parameters.get("lowercase", True),
            token_pattern=parameters.get("token_pattern", r"(?u)\b\w\w+\b"),
            vocabulary={term: position for position, term in enumerate(vocabulary_terms)},
        )
        # Setting idf_ initializes the supplied fixed vocabulary as well.
        vectorizer.idf_ = np.asarray(idf_values, dtype=np.float64)
        query_vector = vectorizer.transform([question])
    except (TypeError, ValueError, KeyError) as error:
        raise MongoRetrievalError("Could not rebuild the saved TF-IDF query model.") from error

    vector_filter: dict[str, Any] = {"tfidf_vector.index_id": model["index_id"]}
    if document_id:
        vector_filter["document_id"] = document_id
    passages = list(
        database["chunks"]
        .find(vector_filter)
        .sort([("document_id", 1), ("document_version", 1), ("chunk_index", 1)])
    )
    if not passages:
        if document_id:
            return []
        raise MongoRetrievalError("The active index has no passage vectors.")

    row_indices: list[int] = []
    values: list[float] = []
    indptr = [0]
    for passage in passages:
        vector = passage.get("tfidf_vector", {})
        indices = vector.get("indices", [])
        row_values = vector.get("values", [])
        if (
            vector.get("index_id") != model["index_id"]
            or vector.get("dimension") != feature_count
            or len(indices) != len(row_values)
        ):
            raise MongoRetrievalError("A stored passage vector does not match the active index.")
        row_indices.extend(int(index) for index in indices)
        values.extend(float(value) for value in row_values)
        indptr.append(len(row_indices))

    passage_vectors = csr_matrix(
        (
            np.asarray(values, dtype=np.float64),
            np.asarray(row_indices, dtype=np.int32),
            np.asarray(indptr, dtype=np.int32),
        ),
        shape=(len(passages), feature_count),
    )
    scores = cosine_similarity(query_vector, passage_vectors).ravel()
    ranked = scores.argsort()[::-1][:limit]

    return [
        MongoSearchResult(
            passage_id=str(passages[int(position)].get("passage_id", "")),
            document_id=str(passages[int(position)].get("document_id", "")),
            document_title=str(passages[int(position)].get("document_title", "")),
            page_number=passages[int(position)].get("page_number"),
            source_locator=str(passages[int(position)].get("source_locator", "")),
            text=str(passages[int(position)].get("text", "")),
            score=float(scores[position]),
        )
        for position in ranked
    ]
