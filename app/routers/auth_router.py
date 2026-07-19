"""
app/routers/auth_router.py — Authentication endpoints.

POST /api/auth/register  → create account, return tokens
POST /api/auth/login     → verify credentials, return tokens
POST /api/auth/refresh   → exchange refresh token for new pair

All responses use the standard error shape from app/errors.py.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.dependencies import get_db
from app.errors import AppError
from app.models import User

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ── Request / Response schemas ────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: str
    email: str
    username: str
    created_at: str

    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    user: UserResponse
    access_token: str
    refresh_token: str


class TokenPairResponse(BaseModel):
    access_token: str
    refresh_token: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_auth_response(user: User) -> AuthResponse:
    """Build the standard auth response with tokens for a user."""
    user_id = str(user.id)
    return AuthResponse(
        user=UserResponse(
            id=user_id,
            email=user.email,
            username=user.username,
            created_at=user.created_at.isoformat(),
        ),
        access_token=create_access_token(user_id),
        refresh_token=create_refresh_token(user_id),
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/register", status_code=201)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)) -> AuthResponse:
    """
    Create a new user account.

    Returns 201 with user info + JWT tokens.
    Raises 409 if email or username already taken.
    """
    # Check for duplicate email
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise AppError("Email already registered", status_code=409, code="DUPLICATE_EMAIL")

    # Check for duplicate username
    existing = await db.execute(select(User).where(User.username == body.username))
    if existing.scalar_one_or_none():
        raise AppError("Username already taken", status_code=409, code="DUPLICATE_USERNAME")

    # Create user
    user = User(
        id=uuid.uuid4(),
        email=body.email,
        username=body.username,
        password_hash=hash_password(body.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return _build_auth_response(user)


@router.post("/login")
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)) -> AuthResponse:
    """
    Authenticate with email + password.

    Returns 200 with user info + JWT tokens.
    Raises 401 if credentials are invalid.
    """
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(body.password, user.password_hash):
        # Intentionally vague — don't reveal whether the email exists
        raise AppError("Invalid email or password", status_code=401, code="INVALID_CREDENTIALS")

    return _build_auth_response(user)


@router.post("/refresh")
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)) -> TokenPairResponse:
    """
    Exchange a valid refresh token for a new access + refresh token pair.

    The old refresh token is not revoked (stateless JWT — see Excluded Features).
    Raises 401 if the refresh token is expired or invalid.
    """
    payload = decode_token(body.refresh_token, token_type="refresh")
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise AppError("Invalid token payload", status_code=401, code="INVALID_TOKEN")

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise AppError("Invalid token payload", status_code=401, code="INVALID_TOKEN")

    # Verify user still exists (could have been deleted since token was issued)
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise AppError("User not found", status_code=401, code="USER_NOT_FOUND")

    return TokenPairResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )
