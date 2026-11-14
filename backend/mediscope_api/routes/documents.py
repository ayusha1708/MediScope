"""User-facing document submission routes."""

import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile, status
from pymongo.errors import PyMongoError

from mediscope_api.ai_bridge import (
    MongoConfigurationError,
    create_mongo_client,
)
from mediscope_api.security import get_current_user
from mediscope_api.services.document_submissions import (
    SubmissionStorageError,
    create_submission,
    list_user_submissions,
)

# Importing ai_bridge first adds ai-service to the Python path.
from app.documents.extractor import DocumentProcessingError, extract_document
from app.documents.validation import (
    MAX_FILE_SIZE_BYTES,
    DocumentValidationError,
    validate_document,
)

router = APIRouter(prefix="/api/documents", tags=["documents"])


def _submission_response(item: dict) -> dict:
    submitted_at = item.get("submitted_at")
    return {
        "submission_id": str(item.get("_id", "")),
        "status": item.get("status", "PENDING_ADMIN_REVIEW"),
        "title": item.get("metadata", {}).get("title", ""),
        "file_name": item.get("file", {}).get("file_name", ""),
        "submitted_at": submitted_at.isoformat() if submitted_at else None,
        "identity_choice": item.get("identity_choice", "ANONYMOUS"),
        "review": item.get("review"),
    }


@router.post("/submissions", status_code=status.HTTP_201_CREATED)
async def submit_document(
    request: Request,
    file: UploadFile = File(...),
    title: str = Form(..., min_length=3, max_length=300),
    source_url: str = Form(default="", max_length=2000),
    scope_reason: str = Form(default="", max_length=2000),
    reveal_identity: bool = Form(...),
) -> dict:
    """Submit a PDF/TXT for admin review; this route never approves or indexes it."""
    user = get_current_user(request)
    filename = Path(file.filename or "").name
    suffix = Path(filename).suffix.lower()
    if suffix not in {".pdf", ".txt"}:
        raise HTTPException(status_code=422, detail="Upload a PDF or UTF-8 TXT file.")

    content = await file.read(MAX_FILE_SIZE_BYTES + 1)
    await file.close()
    if not content:
        raise HTTPException(status_code=422, detail="The uploaded file is empty.")
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="The file must be 25 MB or smaller.")

    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temporary_file:
            temporary_file.write(content)
            temp_path = Path(temporary_file.name)
        validated = validate_document(temp_path)
        extracted = extract_document(temp_path)
        metadata = {
            "title": title.strip(),
            "source_locator": source_url.strip(),
            "full_text_url": source_url.strip(),
            "scope_reason": scope_reason.strip(),
        }
        with create_mongo_client() as client:
            client.admin.command("ping")
            item = create_submission(
                client,
                user=user,
                metadata=metadata,
                file_name=filename,
                file_type=validated.file_type,
                file_size=validated.size_bytes,
                file_sha256=validated.sha256,
                file_bytes=content,
                reveal_identity=reveal_identity,
                extraction={
                    "page_count": extracted.page_count,
                    "character_count": len(extracted.text),
                    "status": "TECHNICALLY_READABLE",
                },
            )
    except (DocumentValidationError, DocumentProcessingError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except SubmissionStorageError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except (MongoConfigurationError, PyMongoError) as error:
        raise HTTPException(status_code=503, detail="Could not save the submission to MongoDB.") from error
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)

    response = _submission_response(item)
    response["extraction"] = {
        "page_count": extracted.page_count,
        "character_count": len(extracted.text),
        "status": "TECHNICALLY_READABLE",
    }
    response["message"] = "Submitted for admin review. It is not searchable unless an admin approves it."
    response["identity_note"] = (
        "Your name and email are visible to admins for this submission."
        if reveal_identity
        else "Your identity is hidden from the admin review API. Your account remains privately linked so you can track this submission."
    )
    return response


@router.get("/submissions")
def my_submissions(request: Request, limit: int = 50) -> dict:
    user = get_current_user(request)
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=422, detail="Limit must be between 1 and 100.")
    try:
        with create_mongo_client() as client:
            items = list_user_submissions(client, user["_id"], limit)
    except (MongoConfigurationError, PyMongoError) as error:
        raise HTTPException(status_code=503, detail="Could not load your submissions.") from error
    return {"count": len(items), "items": [_submission_response(item) for item in items]}
