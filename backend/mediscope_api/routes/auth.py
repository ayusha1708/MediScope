"""Registration, login, logout, and current-user endpoints."""

from fastapi import APIRouter, HTTPException, Request, status

from mediscope_api.schemas import (
    AuthResponse,
    LoginRequest,
    RegisterRequest,
    UserResponse,
)
from mediscope_api.security import get_current_user, public_user
from mediscope_api.services.auth import (
    AuthServiceError,
    EmailAlreadyRegistered,
    InvalidLogin,
    authenticate_user,
    register_user,
)

router = APIRouter(prefix="/api/auth", tags=["authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(request: RegisterRequest) -> UserResponse:
    try:
        user = register_user(request.email, request.password, request.display_name)
    except EmailAlreadyRegistered as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except AuthServiceError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    return UserResponse(**public_user(user))


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, request: Request) -> AuthResponse:
    try:
        user = authenticate_user(payload.email, payload.password)
    except InvalidLogin as error:
        raise HTTPException(status_code=401, detail=str(error)) from error
    except AuthServiceError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    request.session.clear()
    request.session["user_id"] = str(user["_id"])
    return AuthResponse(user=UserResponse(**public_user(user)))


@router.post("/logout")
def logout(request: Request) -> dict[str, str]:
    request.session.clear()
    return {"status": "logged_out"}


@router.get("/me", response_model=UserResponse)
def me(request: Request) -> UserResponse:
    return UserResponse(**public_user(get_current_user(request)))
