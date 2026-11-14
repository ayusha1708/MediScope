"""Request and response shapes for the HTTP API."""

from pydantic import BaseModel, Field


class QuestionRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    document_id: str | None = None


class ReferenceResponse(BaseModel):
    reference_id: str
    document_id: str
    document_title: str
    page_number: int | None
    passage_id: str
    source: str
    excerpt: str
    similarity_score: float


class QuestionResponse(BaseModel):
    route: str
    answer: str
    references: list[ReferenceResponse]
    fallback: bool
    safety_response: bool


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=12, max_length=128)
    display_name: str = Field(default="", max_length=80)


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)


class UserResponse(BaseModel):
    user_id: str
    email: str
    display_name: str
    role: str


class AuthResponse(BaseModel):
    user: UserResponse
