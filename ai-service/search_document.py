"""Search one saved local index and print its three closest passages."""

import argparse
from pathlib import Path

from app.retrieval.search import RetrievalError, find_relevant_passages
from app.retrieval.storage import IndexStorageError, load_tfidf_index


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INDEX_ROOT = PROJECT_ROOT / "data" / "tfidf_index"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Find the three passages most similar to a question."
    )
    parser.add_argument("document_id", help="ID used in the approved review record")
    parser.add_argument("question", help="Question to search for in the document")
    args = parser.parse_args()

    safe_id = "".join(char for char in args.document_id if char.isalnum() or char in "-_")
    if not safe_id or safe_id != args.document_id:
        parser.exit(status=2, message="Use a document ID containing only letters, numbers, - or _.\n")

    try:
        index = load_tfidf_index(INDEX_ROOT / safe_id)
        results = find_relevant_passages(args.question, index, limit=3)
    except (IndexStorageError, RetrievalError) as error:
        parser.exit(status=1, message=f"Could not search document: {error}\n")

    if not results or results[0].score == 0:
        print("No matching terms were found in this document.")
        return

    print("Top matching passages (score ranges from 0 to 1):")
    for rank, result in enumerate(results, start=1):
        page = result.chunk.get("page_number")
        page_label = f"Page {page}" if page is not None else "Page unavailable"
        print(f"\n{rank}. {page_label} | score: {result.score:.3f}")
        print(result.chunk.get("text", ""))


if __name__ == "__main__":
    main()
