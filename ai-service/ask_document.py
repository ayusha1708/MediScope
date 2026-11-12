"""Retrieve three passages and ask local Ollama for an evidence-grounded answer."""

import argparse
from pathlib import Path

from app.generation.ollama import OllamaGenerationError, generate_grounded_answer
from app.retrieval.search import RetrievalError, find_relevant_passages
from app.retrieval.storage import IndexStorageError, load_tfidf_index


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INDEX_ROOT = PROJECT_ROOT / "data" / "tfidf_index"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Answer a question using three passages from an approved document."
    )
    parser.add_argument("document_id", help="ID used in the approved review record")
    parser.add_argument("question", help="Question to ask about the document")
    args = parser.parse_args()

    safe_id = "".join(char for char in args.document_id if char.isalnum() or char in "-_")
    if not safe_id or safe_id != args.document_id:
        parser.exit(status=2, message="Use a document ID containing only letters, numbers, - or _.\n")

    try:
        index = load_tfidf_index(INDEX_ROOT / safe_id)
        results = find_relevant_passages(args.question, index, limit=3)
    except (IndexStorageError, RetrievalError) as error:
        parser.exit(status=1, message=f"Could not search document: {error}\n")

    document = index.document
    title = str(document.get("title") or document.get("document_id") or safe_id)
    source = document.get("full_text_url") or document.get("source_locator")
    print("Three closest references (similarity is word overlap, not confidence):")
    for rank, result in enumerate(results, start=1):
        page = result.chunk.get("page_number")
        page_label = f"Page {page}" if page is not None else "Page unavailable"
        passage_id = f"{safe_id}:passage-{int(result.chunk.get('index', 0)) + 1}"
        print(
            f"\n[R{rank}] {title} | {page_label} | passage {passage_id} "
            f"| similarity score: {result.score:.3f}"
        )
        if source:
            print(f"Source: {source}")
        excerpt = " ".join(str(result.chunk.get("text", "")).split())
        if len(excerpt) > 260:
            excerpt = excerpt[:257].rsplit(" ", 1)[0] + "..."
        print(f"Excerpt: {excerpt}")

    try:
        answer = generate_grounded_answer(args.question, results, index)
    except OllamaGenerationError as error:
        print("\nFallback: I could not generate a reliable answer because Ollama was unavailable or returned an unusable response.")
        print(f"Details: {error}")
        print("Review the retrieved passages above directly; no answer was guessed.")
        return

    print("\nAnswer:")
    print(answer.text)


if __name__ == "__main__":
    main()
