"""Connect the HTTP backend to the existing AI-service package."""

import sys
from pathlib import Path

AI_SERVICE_ROOT = Path(__file__).resolve().parents[2] / "ai-service"
if str(AI_SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_SERVICE_ROOT))

from app.services.question_service import QuestionServiceError, answer_question
from app.storage.mongodb import MongoConfigurationError, create_mongo_client, get_database_name

__all__ = [
    "MongoConfigurationError",
    "QuestionServiceError",
    "answer_question",
    "create_mongo_client",
    "get_database_name",
]
