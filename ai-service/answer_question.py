"""Screen and classify a question, then route it to the appropriate answer path."""

import argparse
from pathlib import Path

import joblib

from app.classification.data import LABELS
from app.generation.ollama import (
    FALLBACK_ANSWER,
    OllamaGenerationError,
    generate_general_answer,
    generate_grounded_answer,
)
from app.retrieval.search import RetrievalError, find_relevant_passages
from app.retrieval.storage import IndexStorageError, load_tfidf_index
from app.safety.screening import safety_message


AI_SERVICE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = AI_SERVICE_ROOT.parent
MODEL_FILE = AI_SERVICE_ROOT / "models" / "query_classifier.joblib"
INDEX_ROOT = PROJECT_ROOT / "data" / "tfidf_index"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Route a question through MediScope's safety, classifier, and answer flow."
    )
    parser.add_argument("question", help="Question to ask")
    parser.add_argument(
        "--document-id",
        help="Approved document index to search for KNOWLEDGE_RAG or LITERATURE_CONTEXT",
    )
    args = parser.parse_args()

    boundary = safety_message(args.question)
    if boundary:
        print("Safety response:")
        print(boundary)
        return

    if not MODEL_FILE.exists():
        parser.exit(
            status=1,
            message="Query classifier model not found. Run `python train_query_classifier.py` first.\n",
        )
    try:
        classifier = joblib.load(MODEL_FILE)
        route = str(classifier.predict([args.question])[0])
    except (OSError, ValueError, AttributeError) as error:
        parser.exit(status=1, message=f"Could not load the query classifier: {error}\n")
    if route not in LABELS:
        parser.exit(status=1, message=f"Classifier returned an unknown route: {route}\n")

    print(f"Route: {route}")
    if route == "GENERAL_INFORMATION":
        print("Answer type: General educational information; not sourced from indexed documents.")
        try:
            answer = generate_general_answer(args.question)
        except OllamaGenerationError as error:
            print(f"Fallback: general answer unavailable. {error}")
            return
        print(f"\nAnswer:\n{answer}")
        return

    if not args.document_id:
        parser.exit(
            status=2,
            message=(
                f"This question was routed to {route}; provide an approved document index with "
                "--document-id <id>.\n"
            ),
        )

    safe_id = "".join(char for char in args.document_id if char.isalnum() or char in "-_")
    if not safe_id or safe_id != args.document_id:
        parser.exit(status=2, message="Document ID may contain only letters, numbers, - or _.\n")

    try:
        index = load_tfidf_index(INDEX_ROOT / safe_id)
        results = find_relevant_passages(args.question, index, limit=3)
    except (IndexStorageError, RetrievalError) as error:
        parser.exit(status=1, message=f"Could not search the approved index: {error}\n")

    document = index.document
    title = str(document.get("title") or document.get("document_id") or safe_id)
    source = document.get("full_text_url") or document.get("source_locator")
    print("Three closest references (similarity is word overlap, not confidence):")
    for rank, result in enumerate(results, start=1):
        page = result.chunk.get("page_number")
        page_label = f"Page {page}" if page is not None else "Page unavailable"
        passage_id = f"{safe_id}:passage-{int(result.chunk.get('index', 0)) + 1}"
        print(f"\n[R{rank}] {title} | {page_label} | {passage_id} | score: {result.score:.3f}")
        if source:
            print(f"Source: {source}")
        excerpt = " ".join(str(result.chunk.get("text", "")).split())
        if len(excerpt) > 260:
            excerpt = excerpt[:257].rsplit(" ", 1)[0] + "..."
        print(f"Excerpt: {excerpt}")

    try:
        answer = generate_grounded_answer(args.question, results, index)
    except OllamaGenerationError as error:
        print(f"\nFallback: answer generation failed. {error}")
        print("Review the retrieved references above; no unsupported answer was guessed.")
        return
    print(f"\nAnswer:\n{answer.text}")
    if answer.text == FALLBACK_ANSWER:
        print("The retrieved passages were insufficient for a grounded answer.")


if __name__ == "__main__":
    main()
