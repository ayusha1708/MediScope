"""Administrator-only dashboard and document-submission queue endpoints."""

from datetime import datetime, timezone
import tempfile
from pathlib import Path
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Body, HTTPException, Query, Request
from fastapi.responses import Response
from gridfs import GridFSBucket
from gridfs.errors import NoFile
from pymongo.errors import PyMongoError

from mediscope_api.ai_bridge import MongoConfigurationError, create_mongo_client, get_database_name
from mediscope_api.services.document_approval import (
    DocumentApprovalError,
    process_approved_upload,
)
from mediscope_api.security import require_admin
from app.documents.approval import ApprovalRecord, ApprovalRecordError

router = APIRouter(prefix="/api/admin", tags=["admin"])
ALLOWED_STATUSES = {
    "PENDING_ADMIN_REVIEW",
    "NEEDS_REVISION",
    "APPROVED",
    "REJECTED",
}


def _iso(value: Any) -> str | None:
    return value.isoformat() if isinstance(value, datetime) else None


def _submission_summary(item: dict[str, Any]) -> dict[str, Any]:
    metadata = item.get("metadata", {})
    file_info = item.get("file", {})
    identity_choice = item.get("identity_choice", "ANONYMOUS")
    result = {
        "submission_id": str(item.get("_id", "")),
        "status": item.get("status", "PENDING_ADMIN_REVIEW"),
        "title": metadata.get("title", ""),
        "source_url": metadata.get("full_text_url") or metadata.get("source_locator", ""),
        "file_name": file_info.get("file_name", ""),
        "submitted_at": _iso(item.get("submitted_at")),
        "identity_choice": identity_choice,
        "submitter": (
            item.get("submitter_identity") or {"display_name": "", "email": ""}
            if identity_choice == "REVEAL"
            else "Anonymous"
        ),
    }
    return result


@router.get("/dashboard")
def dashboard(request: Request) -> dict[str, Any]:
    require_admin(request)
    try:
        with create_mongo_client() as client:
            client.admin.command("ping")
            database = client[get_database_name()]
            documents = database["documents"]
            submissions = database["document_submissions"]
            active_index = database["tfidf_indexes"].find_one({"_id": "active"})
            return {
                "documents": {
                    "approved": documents.count_documents({"approval.decision": "APPROVED"}),
                    "needs_revision": documents.count_documents({"approval.decision": "NEEDS_REVISION"}),
                    "rejected": documents.count_documents({"approval.decision": "REJECTED"}),
                },
                "submissions": {
                    "pending_review": submissions.count_documents(
                        {"status": "PENDING_ADMIN_REVIEW"}
                    ),
                    "needs_revision": submissions.count_documents(
                        {"status": "NEEDS_REVISION"}
                    ),
                },
                "users": database["users"].count_documents({"active": True}),
                "stored_passages": database["chunks"].count_documents({}),
                "active_tfidf_index": active_index.get("index_id") if active_index else None,
            }
    except (MongoConfigurationError, PyMongoError) as error:
        raise HTTPException(status_code=503, detail="Could not load admin dashboard data.") from error


@router.get("/document-submissions")
def list_submissions(
    request: Request,
    status: str = Query(default="PENDING_ADMIN_REVIEW"),
    limit: int = Query(default=50, ge=1, le=100),
) -> dict[str, Any]:
    require_admin(request)
    if status not in ALLOWED_STATUSES:
        raise HTTPException(
            status_code=422,
            detail="Status must be PENDING_ADMIN_REVIEW, NEEDS_REVISION, APPROVED, or REJECTED.",
        )
    try:
        with create_mongo_client() as client:
            client.admin.command("ping")
            items = list(
                client[get_database_name()]["document_submissions"]
                .find({"status": status})
                .sort("submitted_at", -1)
                .limit(limit)
            )
    except (MongoConfigurationError, PyMongoError) as error:
        raise HTTPException(status_code=503, detail="Could not load document submissions.") from error
    return {"status": status, "count": len(items), "items": [_submission_summary(i) for i in items]}


@router.get("/document-submissions/{submission_id}")
def get_submission(submission_id: str, request: Request) -> dict[str, Any]:
    require_admin(request)
    try:
        object_id = ObjectId(submission_id)
    except (InvalidId, TypeError) as error:
        raise HTTPException(status_code=404, detail="Document submission not found.") from error
    try:
        with create_mongo_client() as client:
            item = client[get_database_name()]["document_submissions"].find_one(
                {"_id": object_id}, {"file.gridfs_id": 0}
            )
    except (MongoConfigurationError, PyMongoError) as error:
        raise HTTPException(status_code=503, detail="Could not load document submission.") from error
    if item is None:
        raise HTTPException(status_code=404, detail="Document submission not found.")
    result = _submission_summary(item)
    result["metadata"] = item.get("metadata", {})
    result["file"] = {
        key: value
        for key, value in item.get("file", {}).items()
        if key != "gridfs_id"
    }
    result["review"] = item.get("review")
    result["extraction"] = item.get("extraction", {})
    return result


@router.get("/document-submissions/{submission_id}/file")
def download_submission_file(submission_id: str, request: Request) -> Response:
    """Let admins inspect the original uploaded document before making a decision."""
    require_admin(request)
    try:
        object_id = ObjectId(submission_id)
    except (InvalidId, TypeError) as error:
        raise HTTPException(status_code=404, detail="Document submission not found.") from error
    try:
        with create_mongo_client() as client:
            database = client[get_database_name()]
            item = database["document_submissions"].find_one({"_id": object_id})
            if item is None:
                raise HTTPException(status_code=404, detail="Document submission not found.")
            gridfs_id = item.get("file", {}).get("gridfs_id")
            if not gridfs_id:
                raise HTTPException(status_code=404, detail="The uploaded file is unavailable.")
            try:
                file_bytes = GridFSBucket(database, bucket_name="submission_files").open_download_stream(
                    gridfs_id
                ).read()
            except NoFile as error:
                raise HTTPException(status_code=404, detail="The uploaded file is unavailable.") from error
            file_name = str(item.get("file", {}).get("file_name", "document"))
            file_type = item.get("file", {}).get("file_type", "")
    except (MongoConfigurationError, PyMongoError) as error:
        raise HTTPException(status_code=503, detail="Could not download the submitted file.") from error

    media_type = "application/pdf" if file_type == "pdf" else "text/plain; charset=utf-8"
    safe_name = "".join(
        character for character in file_name if character >= " " and character not in {'"', "\\"}
    )[:200] or "document"
    return Response(
        content=file_bytes,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{safe_name}"',
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.post("/document-submissions/{submission_id}/decision")
def decide_submission(
    submission_id: str,
    request: Request,
    review_data: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    """Record an admin decision; approved uploads use the established indexing pipeline."""
    admin = require_admin(request)
    try:
        object_id = ObjectId(submission_id)
    except (InvalidId, TypeError) as error:
        raise HTTPException(status_code=404, detail="Document submission not found.") from error

    try:
        with create_mongo_client() as client:
            database = client[get_database_name()]
            submission = database["document_submissions"].find_one({"_id": object_id})
            if submission is None:
                raise HTTPException(status_code=404, detail="Document submission not found.")
            if submission.get("status") not in {"PENDING_ADMIN_REVIEW", "NEEDS_REVISION"}:
                raise HTTPException(status_code=409, detail="This submission already has a final decision.")

            review_data = dict(review_data)
            document = review_data.get("document")
            if not isinstance(document, dict):
                raise HTTPException(status_code=422, detail="Review JSON must contain a document object.")
            review_data["reviewer_id"] = admin["email"]
            review_data["reviewed_at"] = datetime.now(timezone.utc).date().isoformat()
            document["file_sha256"] = submission.get("file", {}).get("sha256", "")
            record = ApprovalRecord.from_dict(review_data)
            if record.decision.value == "PENDING_ADMIN_REVIEW":
                raise HTTPException(
                    status_code=422,
                    detail="Choose APPROVED, NEEDS_REVISION, or REJECTED for the admin decision.",
                )

            processing_result = None
            if record.decision.value == "APPROVED":
                gridfs_id = submission.get("file", {}).get("gridfs_id")
                if not gridfs_id:
                    raise HTTPException(status_code=404, detail="The uploaded file is unavailable.")
                try:
                    file_bytes = GridFSBucket(
                        database, bucket_name="submission_files"
                    ).open_download_stream(gridfs_id).read()
                except NoFile as error:
                    raise HTTPException(status_code=404, detail="The uploaded file is unavailable.") from error
                suffix = ".pdf" if submission.get("file", {}).get("file_type") == "pdf" else ".txt"
                temp_path = None
                try:
                    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temporary_file:
                        temporary_file.write(file_bytes)
                        temp_path = Path(temporary_file.name)
                    processing_result = process_approved_upload(client, record.to_dict(), temp_path)
                finally:
                    if temp_path is not None:
                        temp_path.unlink(missing_ok=True)

            database["document_submissions"].update_one(
                {"_id": object_id},
                {
                    "$set": {
                        "status": record.decision.value,
                        "review": record.to_dict(),
                        "reviewed_by": admin["_id"],
                        "updated_at": datetime.now(timezone.utc),
                    }
                },
            )
    except ApprovalRecordError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except DocumentApprovalError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except (MongoConfigurationError, PyMongoError) as error:
        raise HTTPException(status_code=503, detail="Could not complete the document review.") from error

    response: dict[str, Any] = {
        "submission_id": submission_id,
        "decision": record.decision.value,
        "message": "Admin decision saved.",
    }
    if processing_result:
        response["processing"] = processing_result
        response["message"] = "Approved, processed, and added to the shared search index."
    return response
