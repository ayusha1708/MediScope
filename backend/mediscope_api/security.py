"""Password hashing and role-aware session lookup."""

import base64
import hashlib
import hmac
import secrets
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException, Request

from mediscope_api.ai_bridge import create_mongo_client, get_database_name


SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 5
SCRYPT_MAXMEM = 64 * 1024 * 1024


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def hash_password(password: str) -> str:
    """Create a salted, memory-hard scrypt password hash."""
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        maxmem=SCRYPT_MAXMEM,
        dklen=32,
    )
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${_encode(salt)}${_encode(digest)}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify a password without storing or returning its plaintext value."""
    try:
        algorithm, n_text, r_text, p_text, salt_text, digest_text = stored_hash.split("$", 5)
        n, r, p = int(n_text), int(r_text), int(p_text)
        if algorithm != "scrypt" or (n, r, p) != (SCRYPT_N, SCRYPT_R, SCRYPT_P):
            return False
        expected = _decode(digest_text)
        actual = hashlib.scrypt(
            password.encode("utf-8"),
            salt=_decode(salt_text),
            n=n,
            r=r,
            p=p,
            maxmem=SCRYPT_MAXMEM,
            dklen=len(expected),
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, expected)


DUMMY_PASSWORD_HASH = hash_password("not-a-real-user-password")


def normalize_email(email: str) -> str:
    """Normalize and minimally validate an email account identifier."""
    normalized = email.strip().lower()
    if len(normalized) > 254 or normalized.count("@") != 1:
        raise ValueError("Enter a valid email address.")
    local, domain = normalized.split("@")
    if not local or not domain or "." not in domain or any(ch.isspace() for ch in normalized):
        raise ValueError("Enter a valid email address.")
    return normalized


def public_user(user: dict[str, Any]) -> dict[str, str]:
    """Return only non-secret account fields."""
    return {
        "user_id": str(user["_id"]),
        "email": user["email"],
        "display_name": user.get("display_name", ""),
        "role": user["role"],
    }


def get_current_user(request: Request) -> dict[str, Any]:
    """Load the current account from its signed session cookie."""
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Sign in to continue.")
    try:
        object_id = ObjectId(user_id)
    except (InvalidId, TypeError):
        request.session.clear()
        raise HTTPException(status_code=401, detail="Your session is invalid. Sign in again.")

    try:
        with create_mongo_client() as client:
            user = client[get_database_name()]["users"].find_one(
                {"_id": object_id, "active": True},
                {"password_hash": 0},
            )
    except Exception as error:
        raise HTTPException(status_code=503, detail="Could not check the account session.") from error
    if user is None:
        request.session.clear()
        raise HTTPException(status_code=401, detail="Account not found. Sign in again.")
    return user


def require_admin(request: Request) -> dict[str, Any]:
    """Reject non-admin users before any protected admin operation."""
    user = get_current_user(request)
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Administrator access is required.")
    return user
