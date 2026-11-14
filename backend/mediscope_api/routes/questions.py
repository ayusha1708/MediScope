"""Question endpoint that delegates to the existing MediScope AI workflow."""

from fastapi import APIRouter, HTTPException, Request

from mediscope_api.ai_bridge import QuestionServiceError, answer_question
from mediscope_api.schemas import QuestionRequest, QuestionResponse
from mediscope_api.security import get_current_user

router = APIRouter(prefix="/api/questions", tags=["questions"])


@router.post("", response_model=QuestionResponse)
def ask_question(payload: QuestionRequest, request: Request) -> QuestionResponse:
    get_current_user(request)
    try:
        result = answer_question(payload.question, document_id=payload.document_id)
    except QuestionServiceError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    return QuestionResponse(**result)
