"""Save a local TF-IDF index and the source details needed for citations."""

import json
from pathlib import Path
from typing import Any

import joblib
from scipy.sparse import save_npz

from app.retrieval.tfidf import TfidfIndex


class IndexStorageError(ValueError):
    """Raised when a local retrieval index cannot be saved safely."""


def save_tfidf_index(
    index: TfidfIndex,
    *,
    document_metadata: dict[str, Any],
    index_root: str | Path,
    processing_metadata: dict[str, Any],
) -> Path:
    """Save vectorizer, sparse matrix, and chunk/source metadata by document ID."""
    document_id = str(document_metadata.get("document_id", "")).strip()
    safe_id = "".join(char for char in document_id if char.isalnum() or char in "-_")
    if not safe_id:
        raise IndexStorageError("The approved document has no safe document_id.")
    if not index.chunks or index.vectors.shape[0] != len(index.chunks):
        raise IndexStorageError("The vector matrix and chunk metadata do not match.")

    output_dir = Path(index_root) / safe_id
    output_dir.mkdir(parents=True, exist_ok=True)

    chunks_payload = {
        "document": document_metadata,
        "processing": processing_metadata,
        "vectorization": {
            "method": "TF-IDF",
            "ngram_range": [1, 2],
            "feature_count": index.feature_count,
            "chunk_count": len(index.chunks),
        },
        "chunks": [
            {
                "index": chunk.index,
                "page_number": chunk.page_number,
                "start_word": chunk.start_word,
                "end_word": chunk.end_word,
                "text": chunk.text,
            }
            for chunk in index.chunks
        ],
    }

    try:
        joblib.dump(index.vectorizer, output_dir / "vectorizer.joblib")
        save_npz(output_dir / "vectors.npz", index.vectors)
        (output_dir / "chunks.json").write_text(
            json.dumps(chunks_payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    except OSError as error:
        raise IndexStorageError(f"Could not write the local index: {error}") from error

    return output_dir
