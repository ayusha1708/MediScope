"""Fit TF-IDF over all approved stored passages and save sparse vectors to MongoDB."""

import argparse

from pymongo.errors import PyMongoError

from app.documents.chunker import TextChunk
from app.retrieval.tfidf import TfidfVectorizationError, fit_tfidf
from app.storage.mongodb import MongoConfigurationError, create_mongo_client, get_database_name
from app.storage.tfidf_index import TfidfStorageError, save_corpus_tfidf_index


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Fit one shared TF-IDF model across approved MongoDB passages and "
            "save sparse vectors for retrieval."
        )
    )
    parser.add_argument("--chunk-size-words", type=int, default=250)
    parser.add_argument("--overlap-words", type=int, default=40)
    args = parser.parse_args()

    try:
        with create_mongo_client() as client:
            client.admin.command("ping")
            database = client[get_database_name()]
            documents = list(
                database["documents"].find(
                    {
                        "approval.decision": "APPROVED",
                        "storage_status": {"$in": ["CHUNKS_STORED", "VECTORS_STORED"]},
                        "chunking.chunk_size_words": args.chunk_size_words,
                        "chunking.overlap_words": args.overlap_words,
                    },
                    {"_id": 1},
                )
            )
            document_record_ids = [item["_id"] for item in documents]
            if not document_record_ids:
                raise TfidfStorageError(
                    "No approved documents with stored passages match these chunk settings. "
                    "Store their approved metadata and passages first."
                )

            passage_records = list(
                database["chunks"]
                .find(
                    {
                        "document_record_id": {"$in": document_record_ids},
                        "chunking.chunk_size_words": args.chunk_size_words,
                        "chunking.overlap_words": args.overlap_words,
                    }
                )
                .sort(
                    [
                        ("document_id", 1),
                        ("document_version", 1),
                        ("chunk_index", 1),
                    ]
                )
            )
            if not passage_records:
                raise TfidfStorageError("No passages were found for the approved documents.")

            chunks = [
                TextChunk(
                    index=int(item["chunk_index"]),
                    page_number=item.get("page_number"),
                    start_word=int(item["start_word"]),
                    end_word=int(item["end_word"]),
                    text=str(item["text"]),
                )
                for item in passage_records
            ]
            index = fit_tfidf(chunks)
            index_id, updated_count = save_corpus_tfidf_index(
                client, index, passage_records, document_record_ids
            )
    except (MongoConfigurationError, TfidfStorageError, TfidfVectorizationError) as error:
        parser.exit(status=1, message=f"Could not build MongoDB TF-IDF index: {error}\n")
    except PyMongoError:
        parser.exit(
            status=1,
            message=(
                "Could not save the TF-IDF index in MongoDB. Check Atlas Network Access, "
                "database-user permissions, and the URI in ai-service/.env.\n"
            ),
        )
    except (KeyError, TypeError, ValueError) as error:
        parser.exit(status=1, message=f"Stored passages have invalid fields: {error}\n")

    print("Shared TF-IDF index saved in MongoDB.")
    print(f"Active index: {index_id}")
    print(f"Approved documents included: {len(document_record_ids)}")
    print(f"Passages vectorized: {len(passage_records)}")
    print(f"Vocabulary features: {index.feature_count}")
    print(f"Passage records updated with sparse vectors: {updated_count}")
    print("The fitted vocabulary and IDF weights are saved in tfidf_indexes.")


if __name__ == "__main__":
    main()
