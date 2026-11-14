"""Create a MongoDB Atlas client from local environment configuration."""

import os
from pathlib import Path

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import ConfigurationError


AI_SERVICE_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(AI_SERVICE_ROOT / ".env")


class MongoConfigurationError(ValueError):
    """Raised when the local MongoDB connection settings are missing."""


def get_database_name() -> str:
    """Return the configured database name, defaulting to the project database."""
    return os.getenv("MONGODB_DB_NAME", "medscope").strip() or "medscope"


def create_mongo_client() -> MongoClient:
    """Create a client without printing or exposing the secret connection URI."""
    uri = os.getenv("MONGODB_URI", "").strip()
    if not uri:
        raise MongoConfigurationError(
            "MONGODB_URI is missing. Add your Atlas connection URI to ai-service/.env."
        )
    try:
        return MongoClient(uri, serverSelectionTimeoutMS=5000, connectTimeoutMS=5000)
    except ConfigurationError as error:
        raise MongoConfigurationError(
            "MONGODB_URI is not a valid MongoDB connection URI. Check ai-service/.env."
        ) from error
