"""FastAPI application entry point."""

import os
import secrets
import warnings
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from mediscope_api.routes.admin import router as admin_router
from mediscope_api.routes.auth import router as auth_router
from mediscope_api.routes.documents import router as documents_router
from mediscope_api.routes.health import router as health_router
from mediscope_api.routes.questions import router as questions_router

app = FastAPI(
    title="MediScope API",
    description="Question API connected to the existing MongoDB and Ollama AI workflow.",
    version="0.1.0",
)
session_secret = os.getenv("MEDISCOPE_SESSION_SECRET")
if not session_secret:
    session_secret = secrets.token_urlsafe(48)
    warnings.warn(
        "MEDISCOPE_SESSION_SECRET is missing; sessions will be invalidated when the API restarts. "
        "Set a private stable value in ai-service/.env before sharing or deploying the API.",
        RuntimeWarning,
    )

app.add_middleware(
    SessionMiddleware,
    secret_key=session_secret,
    session_cookie="mediscope_session",
    max_age=60 * 60 * 12,
    same_site="lax",
    https_only=os.getenv("MEDISCOPE_COOKIE_SECURE", "false").lower() == "true",
)
app.include_router(admin_router)
app.include_router(auth_router)
app.include_router(documents_router)
app.include_router(health_router)
app.include_router(questions_router)

# Keep frontend and API same-origin so the signed session cookie works without CORS setup.
FRONTEND_ROOT = Path(__file__).resolve().parents[2] / "frontend"
app.mount("/", StaticFiles(directory=FRONTEND_ROOT, html=True), name="frontend")
