"""MongoDB-backed account registration and login operations."""

from datetime import datetime, timezone
from typing import Any

from pymongo import ASCENDING
from pymongo.errors import DuplicateKeyError, PyMongoError

from mediscope_api.ai_bridge import MongoConfigurationError, create_mongo_client, get_database_name
from mediscope_api.security import DUMMY_PASSWORD_HASH, hash_password, normalize_email, verify_password


class AuthServiceError(RuntimeError):
    """Raised when an account operation cannot be completed."""


class EmailAlreadyRegistered(AuthServiceError):
    """Raised when registration uses an existing email address."""


class InvalidLogin(AuthServiceError):
    """Raised for any invalid email/password combination."""


def _users_collection(client):
    users = client[get_database_name()]["users"]
    users.create_index([("email", ASCENDING)], unique=True)
    return users


def register_user(email: str, password: str, display_name: str = "") -> dict[str, Any]:
    try:
        normalized_email = normalize_email(email)
    except ValueError as error:
        raise AuthServiceError(str(error)) from error
    user = {
        "email": normalized_email,
        "display_name": display_name.strip(),
        "password_hash": hash_password(password),
        "role": "user",
        "active": True,
        "created_at": datetime.now(timezone.utc),
    }
    try:
        with create_mongo_client() as client:
            users = _users_collection(client)
            result = users.insert_one(user)
            user["_id"] = result.inserted_id
    except DuplicateKeyError as error:
        raise EmailAlreadyRegistered("An account with that email already exists.") from error
    except (MongoConfigurationError, PyMongoError) as error:
        raise AuthServiceError("Could not create the account in MongoDB; check ai-service/.env.") from error
    return user


def authenticate_user(email: str, password: str) -> dict[str, Any]:
    try:
        normalized_email = normalize_email(email)
    except ValueError:
        normalized_email = email.strip().lower()
    try:
        with create_mongo_client() as client:
            user = _users_collection(client).find_one({"email": normalized_email})
    except (MongoConfigurationError, PyMongoError) as error:
        raise AuthServiceError("Could not check the account in MongoDB; check ai-service/.env.") from error

    saved_hash = user.get("password_hash") if user else DUMMY_PASSWORD_HASH
    password_matches = verify_password(password, saved_hash)
    if not user or not user.get("active", False) or not password_matches:
        raise InvalidLogin("Email or password is incorrect.")
    return user


def create_admin_account(email: str, password: str) -> dict[str, Any]:
    """Create the initial admin account; never changes an existing account's role."""
    try:
        normalized_email = normalize_email(email)
    except ValueError as error:
        raise AuthServiceError(str(error)) from error
    user = {
        "email": normalized_email,
        "display_name": "Administrator",
        "password_hash": hash_password(password),
        "role": "admin",
        "active": True,
        "created_at": datetime.now(timezone.utc),
    }
    try:
        with create_mongo_client() as client:
            users = _users_collection(client)
            result = users.insert_one(user)
            user["_id"] = result.inserted_id
    except DuplicateKeyError as error:
        raise EmailAlreadyRegistered(
            "That email already has an account; this command does not change its role."
        ) from error
    except (MongoConfigurationError, PyMongoError) as error:
        raise AuthServiceError("Could not create the admin account in MongoDB; check ai-service/.env.") from error
    return user
