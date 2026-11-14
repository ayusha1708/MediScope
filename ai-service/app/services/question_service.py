"""Reusable safety, classifier, retrieval, and answer flow for CLI and API."""

from pathlib import Path
from typing import Any

import joblib
from pymongo.errors import PyMongoError

from app.classification.data import LABELS
from app.generation.ollama import (
    FALLBACK_ANSWER,
    OllamaGenerationError,
    generate_general_answer,
    generate_mongodb_grounded_answer,
)
from app.retrieval.mongodb_search import MongoRetrievalError, search_mongodb_passages
from app.safety.screening import safety_message
from app.storage.mongodb import (
    MongoConfigurationError,
    create_mongo_client,
)


AI_SERVICE_ROOT = Path(__file__).resolve().parents[2]
MODEL_FILE = AI_SERVICE_ROOT / "models" / "query_classifier.joblib"
GENERAL_FALLBACK = "A general educational answer is unavailable right now. Please try again."


class QuestionServiceError(RuntimeError):
    """Raised when the shared question-answering workflow cannot run."""


def answer_question(question: str, document_id: str | None = None) -> dict[str, Any]:
    """Run the same safety/classifier/answer workflow for command line and API."""
    if not isinstance(question, str) or not question.strip():
        raise QuestionServiceError("Enter a question.")
    if document_id is not None:
        safe_id = "".join(char for char in document_id if char.isalnum() or char in "-_")
        if not safe_id or safe_id != document_id:
            raise QuestionServiceError("Document ID may contain only letters, numbers, - or _.")

    boundary = safety_message(question)
    if boundary:
        return {
            "route": "SAFETY",
            "answer": boundary,
            "references": [],
            "fallback": False,
            "safety_response": True,
        }

    if not MODEL_FILE.exists():
        raise QuestionServiceError(
            "Query classifier model not found. Run `python train_query_classifier.py` first."
        )
    try:
        classifier = joblib.load(MODEL_FILE)
        route = str(classifier.predict([question])[0])
    except (OSError, ValueError, AttributeError) as error:
        raise QuestionServiceError("Could not load or run the query classifier.") from error
    if route not in LABELS:
        raise QuestionServiceError(f"Classifier returned an unknown route: {route}")

    if route == "GENERAL_INFORMATION":
        try:
            answer = generate_general_answer(question)
            fallback = False
        except OllamaGenerationError:
            answer = GENERAL_FALLBACK
            fallback = True
        return {
            "route": route,
            "answer": answer,
            "references": [],
            "fallback": fallback,
            "safety_response": False,
        }

    try:
        with create_mongo_client() as client:
            client.admin.command("ping")
            results = search_mongodb_passages(
                client, question, limit=3, document_id=document_id
            )
    except (MongoConfigurationError, MongoRetrievalError) as error:
        raise QuestionServiceError(str(error)) from error
    except PyMongoError as error:
        raise QuestionServiceError(
            "Could not read the shared MongoDB index. Check Atlas access and ai-service/.env."
        ) from error

    references = [
        {
            "reference_id": f"R{rank}",
            "document_id": result.document_id,
            "document_title": result.document_title,
            "page_number": result.page_number,
            "passage_id": result.passage_id,
            "source": result.source_locator,
            "excerpt": _make_excerpt(result.text),
            "similarity_score": result.score,
        }
        for rank, result in enumerate(results, start=1)
    ]
    if not results:
        return {
            "route": route,
            "answer": FALLBACK_ANSWER,
            "references": [],
            "fallback": True,
            "safety_response": False,
        }

    try:
        grounded = generate_mongodb_grounded_answer(question, results)
        answer = grounded.text
        fallback = not grounded.sufficient_evidence
    except OllamaGenerationError:
        answer = FALLBACK_ANSWER
        fallback = True
    return {
        "route": route,
        "answer": answer,
        "references": references,
        "fallback": fallback,
        "safety_response": False,
    }


def _make_excerpt(text: str, limit: int = 260) -> str:
    """Return a compact passage preview for CLI/API references."""
    excerpt = " ".join(text.split())
    if len(excerpt) > limit:
        excerpt = excerpt[: limit - 3].rsplit(" ", 1)[0] + "..."
    return excerpt
