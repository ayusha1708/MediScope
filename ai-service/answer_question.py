"""CLI entry point for the reusable question-answering workflow."""

import argparse

from app.generation.ollama import FALLBACK_ANSWER
from app.services.question_service import QuestionServiceError, answer_question


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Route a question through safety, classification, MongoDB retrieval, and Ollama."
    )
    parser.add_argument("question", help="Question to ask")
    parser.add_argument(
        "--document-id",
        help="Optionally restrict document retrieval to one approved document",
    )
    args = parser.parse_args()

    try:
        result = answer_question(args.question, document_id=args.document_id)
    except QuestionServiceError as error:
        parser.exit(status=1, message=f"Could not answer the question: {error}\n")

    route = result["route"]
    print(f"Route: {route}")
    if result["safety_response"]:
        print("Safety response:")
        print(result["answer"])
        return

    if route == "GENERAL_INFORMATION":
        print("Answer type: General educational information; not sourced from indexed documents.")
        print(f"\nAnswer:\n{result['answer']}")
        return

    print("Three closest references (cosine similarity is word overlap, not confidence):")
    for reference in result["references"]:
        page = reference["page_number"]
        page_label = f"Page {page}" if page is not None else "Page unavailable"
        print(
            f"\n[{reference['reference_id']}] {reference['document_title']} | {page_label} | "
            f"passage {reference['passage_id']} | "
            f"score: {reference['similarity_score']:.3f}"
        )
        if reference["source"]:
            print(f"Source: {reference['source']}")
        print(f"Excerpt: {reference['excerpt']}")

    print(f"\nAnswer:\n{result['answer']}")
    if result["fallback"] and result["answer"] == FALLBACK_ANSWER:
        print("The retrieved passages were insufficient or Ollama was unavailable.")


if __name__ == "__main__":
    main()
