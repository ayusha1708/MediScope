"""Check the Atlas connection and confirm the selected database is reachable."""

import argparse

from pymongo.errors import PyMongoError

from app.storage.mongodb import (
    MongoConfigurationError,
    create_mongo_client,
    get_database_name,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check the configured MongoDB Atlas connection without changing data."
    )
    try:
        with create_mongo_client() as client:
            client.admin.command("ping")
            database = client[get_database_name()]
            collections = sorted(database.list_collection_names())
            document_count = database["documents"].count_documents({})
            chunk_count = database["chunks"].count_documents({})
            active_index = database["tfidf_indexes"].find_one({"_id": "active"})
            vector_count = (
                database["chunks"].count_documents(
                    {"tfidf_vector.index_id": active_index["index_id"]}
                )
                if active_index
                else 0
            )
    except MongoConfigurationError as error:
        parser.exit(status=1, message=f"MongoDB configuration error: {error}\n")
    except PyMongoError:
        parser.exit(
            status=1,
            message=(
                "Could not connect to MongoDB Atlas. Check the URI in ai-service/.env, "
                "the database user's permissions, and Atlas Network Access.\n"
            ),
        )

    print("MongoDB Atlas connection successful.")
    print(f"Database: {get_database_name()}")
    print(f"Collections: {', '.join(collections) if collections else '(none yet)'}")
    print(f"Documents collection records: {document_count}")
    print(f"Chunks collection records: {chunk_count}")
    print(f"Sparse vectors for active index: {vector_count}")
    print(f"Active TF-IDF index: {active_index['index_id'] if active_index else '(none yet)'}")
    print("No data was inserted or changed.")


if __name__ == "__main__":
    main()
