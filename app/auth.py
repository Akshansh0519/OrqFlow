"""
app/auth.py — JWT and password hashing utilities.

Provides:
  - hash_password / verify_password  → bcrypt
  - create_access_token / create_refresh_token / decode_token → PyJWT

JWT payload: {"sub": user_id, "exp": expiry, "type": "access"|"refresh"}

Uses separate secrets for access and refresh tokens so a leaked refresh
token cannot be used as an access token and vice versa.
"""

from __future__ import annotations

from datetime import datetime, timedelta, UTC

import bcrypt
import jwt

from app.config import settings
from app.errors import AppError


# ── Password Hashing ─────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Check a plaintext password against a bcrypt hash."""
    return bcrypt.checkpw(
        plain.encode("utf-8"),
        hashed.encode("utf-8"),
    )


# ── JWT ───────────────────────────────────────────────────────────────────────

def create_access_token(user_id: str) -> str:
    """Create a short-lived access token."""
    payload = {
        "sub": user_id,
        "type": "access",
        "exp": datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        "iat": datetime.now(UTC),
    }
    return jwt.encode(payload, settings.ACCESS_TOKEN_SECRET, algorithm="HS256")


def create_refresh_token(user_id: str) -> str:
    """Create a longer-lived refresh token (different secret)."""
    payload = {
        "sub": user_id,
        "type": "refresh",
        "exp": datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        "iat": datetime.now(UTC),
    }
    return jwt.encode(payload, settings.REFRESH_TOKEN_SECRET, algorithm="HS256")


def decode_token(token: str, *, token_type: str = "access") -> dict:
    """
    Decode and validate a JWT.

    Args:
        token: The JWT string.
        token_type: "access" or "refresh" — determines which secret to use.

    Returns:
        The decoded payload dict.

    Raises:
        AppError(401): If the token is expired, invalid, or of the wrong type.
    """
    secret = (
        settings.ACCESS_TOKEN_SECRET
        if token_type == "access"
        else settings.REFRESH_TOKEN_SECRET
    )
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise AppError("Token has expired", status_code=401, code="TOKEN_EXPIRED")
    except jwt.InvalidTokenError:
        raise AppError("Invalid token", status_code=401, code="INVALID_TOKEN")

    # Verify token type matches expected
    if payload.get("type") != token_type:
        raise AppError(
            f"Expected {token_type} token, got {payload.get('type')}",
            status_code=401,
            code="WRONG_TOKEN_TYPE",
        )

    return payload
