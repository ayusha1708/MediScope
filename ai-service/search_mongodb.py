"""Search the shared MongoDB TF-IDF corpus and print cited passages."""

import argparse

from pymongo.errors import PyMongoError

from app.retrieval.mongodb_search import MongoRetrievalError, search_mongodb_passages
from app.storage.mongodb import MongoConfigurationError, create_mongo_client


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Find the closest passages in the shared MongoDB TF-IDF index."
    )
    parser.add_argument("question", help="Question or search terms")
    parser.add_argument("--limit", type=int, default=3, help="Number of passages to show (default: 3)")
    parser.add_argument("--document-id", help="Optionally search only one document")
    parser.add_argument("--full-text", action="store_true", help="Print each full retrieved passage")
    args = parser.parse_args()

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
        parser.exit(status=1, message=f"MongoDB search failed: {error}\n")
    except PyMongoError:
        parser.exit(
            status=1,
            message=(
                "Could not read the MongoDB search index. Check Atlas Network Access, "
                "database-user permissions, and the URI in ai-service/.env.\n"
            ),
        )

    if not results:
        print("No passages matched that document ID in the active index.")
        return

    print("MongoDB search results (cosine similarity is word overlap, not confidence):")
    for position, result in enumerate(results, start=1):
        page = f"Page {result.page_number}" if result.page_number is not None else "Page not available"
        print()
        print(
            f"[R{position}] {result.document_title} | {page} | "
            f"passage {result.passage_id} | score: {result.score:.3f}"
        )
        print(f"Source: {result.source_locator}")
        passage_text = " ".join(result.text.split())
        if args.full_text:
            print(f"Full passage: {passage_text}")
        else:
            if len(passage_text) > 500:
                passage_text = passage_text[:497].rstrip() + "..."
            print(f"Excerpt: {passage_text}")


if __name__ == "__main__":
    main()
