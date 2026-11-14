"""Store and list user-submitted source documents in MongoDB."""

from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from gridfs import GridFSBucket
from pymongo import ASCENDING

from mediscope_api.ai_bridge import get_database_name


class SubmissionStorageError(RuntimeError):
    """Raised when a submission cannot be stored consistently."""


def create_submission(
    client,
    *,
    user: dict[str, Any],
    metadata: dict[str, str],
    file_name: str,
    file_type: str,
    file_size: int,
    file_sha256: str,
    file_bytes: bytes,
    reveal_identity: bool,
    extraction: dict[str, Any],
) -> dict[str, Any]:
    """Save the original file and a pending review record; never index it here."""
    database = client[get_database_name()]
    bucket = GridFSBucket(database, bucket_name="submission_files")
    safe_name = "".join(
        character
        for character in file_name.replace("\\", "_").replace("/", "_")
        if character >= " " and character not in {'"', "<", ">", "|"}
    )[:200] or "document"
    gridfs_id = bucket.upload_from_stream(
        safe_name,
        file_bytes,
        metadata={
            "submitted_by": str(user["_id"]),
            "file_sha256": file_sha256,
            "file_type": file_type,
        },
    )
    submission = {
        # Retained privately so the signed-in user can view their own submission status.
        "submitted_by": user["_id"],
        "identity_choice": "REVEAL" if reveal_identity else "ANONYMOUS",
        "submitter_identity": (
            {
                "display_name": user.get("display_name", ""),
                "email": user["email"],
            }
            if reveal_identity
            else None
        ),
        "status": "PENDING_ADMIN_REVIEW",
        "metadata": metadata,
        "file": {
            "gridfs_id": gridfs_id,
            "file_name": safe_name,
            "file_type": file_type,
            "size_bytes": file_size,
            "sha256": file_sha256,
        },
        "extraction": extraction,
        "submitted_at": datetime.now(timezone.utc),
        "review": None,
    }
    try:
        result = database["document_submissions"].insert_one(submission)
    except Exception as error:
        # Avoid leaving an orphaned upload when the queue record could not be created.
        bucket.delete(gridfs_id)
        raise SubmissionStorageError("Could not add the submission to the review queue.") from error
    submission["_id"] = result.inserted_id
    return submission


def list_user_submissions(client, user_id: ObjectId, limit: int = 50) -> list[dict[str, Any]]:
    """Return the signed-in user's recent submissions without file contents."""
    collection = client[get_database_name()]["document_submissions"]
    collection.create_index([("submitted_by", ASCENDING), ("submitted_at", -1)])
    return list(
        collection.find(
            {"submitted_by": user_id},
            {"file.gridfs_id": 0},
        )
        .sort("submitted_at", -1)
        .limit(limit)
    )
