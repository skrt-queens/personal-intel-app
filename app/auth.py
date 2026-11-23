import hashlib
import hmac
import secrets

from fastapi import Header, HTTPException

from app.config import settings
from app.db import get_db


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000)
    return f"{salt}${digest.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        salt, digest = password_hash.split("$", 1)
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000)
        return hmac.compare_digest(candidate.hex(), digest)
    except (ValueError, AttributeError):
        return False


def get_current_user(authorization: str | None = Header(default=None)) -> str | None:
    if not settings.auth_token:
        return None
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")
    token = authorization.removeprefix("Bearer ").strip()
    if not hmac.compare_digest(token, settings.auth_token):
        raise HTTPException(status_code=401, detail="Invalid authentication token")
    return "authenticated-user"