"""Persist one shared sparse TF-IDF index in MongoDB."""

from datetime import datetime, timezone
from uuid import uuid4

from pymongo import MongoClient, UpdateOne

from app.retrieval.tfidf import TfidfIndex
from app.storage.mongodb import get_database_name


class TfidfStorageError(ValueError):
    """Raised when a shared TF-IDF index cannot be stored consistently."""


def save_corpus_tfidf_index(
    client: MongoClient,
    index: TfidfIndex,
    passage_records: list[dict],
    document_record_ids: list[str],
) -> tuple[str, int]:
    """Save sparse passage vectors, then publish fitted vocabulary/IDF metadata."""
    if not passage_records or len(passage_records) != index.vectors.shape[0]:
        raise TfidfStorageError("The fitted vectors do not match the MongoDB passages.")

    database = client[get_database_name()]
    index_id = f"corpus-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid4().hex[:8]}"
    vector_collection = database["chunks"]
    operations = []
    for row_number, passage in enumerate(passage_records):
        row = index.vectors.getrow(row_number)
        sparse_vector = {
            "index_id": index_id,
            "dimension": int(index.vectors.shape[1]),
            "indices": [int(value) for value in row.indices],
            "values": [float(value) for value in row.data],
        }
        operations.append(
            UpdateOne(
                {"_id": passage["_id"]},
                {"$set": {"tfidf_vector": sparse_vector}},
            )
        )

    result = vector_collection.bulk_write(operations, ordered=True)
    vocabulary = [
        term
        for term, _ in sorted(index.vectorizer.vocabulary_.items(), key=lambda item: item[1])
    ]
    model_record = {
        "_id": "active",
        "index_id": index_id,
        "method": "TF-IDF",
        "model_parameters": {
            "ngram_range": [1, 2],
            "norm": "l2",
            "use_idf": True,
            "smooth_idf": True,
            "sublinear_tf": False,
            "lowercase": True,
            "token_pattern": r"(?u)\b\w\w+\b",
        },
        "feature_count": len(vocabulary),
        "vocabulary": vocabulary,
        "idf": [float(value) for value in index.vectorizer.idf_],
        "passage_count": len(passage_records),
        "document_record_ids": document_record_ids,
        "indexed_at": datetime.now(timezone.utc),
    }
    database["tfidf_indexes"].replace_one({"_id": "active"}, model_record, upsert=True)
    database["documents"].update_many(
        {"_id": {"$in": document_record_ids}},
        {"$set": {"storage_status": "VECTORS_STORED", "tfidf_index_id": index_id}},
    )
    return index_id, result.modified_count
