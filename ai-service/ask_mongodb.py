"""Retrieve MongoDB passages and answer through local, grounded Ollama."""

import argparse

from pymongo.errors import PyMongoError

from app.generation.ollama import (
    FALLBACK_ANSWER,
    OllamaGenerationError,
    generate_mongodb_grounded_answer,
)
from app.retrieval.mongodb_search import MongoRetrievalError, search_mongodb_passages
from app.storage.mongodb import MongoConfigurationError, create_mongo_client
from app.safety.screening import safety_message


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Search the shared MongoDB TF-IDF index and generate a grounded answer "
            "with local Ollama."
        )
    )
    parser.add_argument("question", help="Question to answer from approved documents")
    parser.add_argument("--limit", type=int, default=3, help="Number of passages to retrieve")
    parser.add_argument("--document-id", help="Optionally search only one document")
    args = parser.parse_args()

    boundary = safety_message(args.question)
    if boundary:
        print("Safety response:")
        print(boundary)
        return

    try:
        with create_mongo_client() as client:
            client.admin.command("ping")
            results = search_mongodb_passages(
                client,
                args.question,
                limit=args.limit,
                document_id=args.document_id,
            )
    except (MongoConfigurationError, MongoRetrievalError) as error:
        parser.exit(status=1, message=f"Could not search MongoDB: {error}\n")
    except PyMongoError:
        parser.exit(
            status=1,
            message=(
                "Could not read the MongoDB search index. Check Atlas Network Access, "
                "database-user permissions, and the URI in ai-service/.env.\n"
            ),
        )

    if not results:
        print(FALLBACK_ANSWER)
        return

    print("Retrieved references (cosine similarity is word overlap, not confidence):")
    for rank, result in enumerate(results, start=1):
        page_label = (
            f"Page {result.page_number}"
            if result.page_number is not None
            else "Page unavailable"
        )
        print(
            f"\n[R{rank}] {result.document_title} | {page_label} | "
            f"passage {result.passage_id} | similarity score: {result.score:.3f}"
        )
        if result.source_locator:
            print(f"Source: {result.source_locator}")
        excerpt = " ".join(result.text.split())
        if len(excerpt) > 260:
            excerpt = excerpt[:257].rsplit(" ", 1)[0] + "..."
        print(f"Excerpt: {excerpt}")

    try:
        answer = generate_mongodb_grounded_answer(args.question, results)
    except OllamaGenerationError as error:
        print("\nAnswer:")
        print(FALLBACK_ANSWER)
        print(f"Ollama details: {error}")
        return

    print("\nAnswer:")
    print(answer.text)


if __name__ == "__main__":
    main()
