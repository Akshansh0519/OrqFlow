"""
app/dependencies.py — FastAPI dependency injection functions.

Provides:
  - get_db()           → yields an AsyncSession (one per request)
  - get_current_user() → resolves the Bearer JWT to a User ORM object

These are injected via Depends() on protected route handlers.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import decode_token
from app.database import get_async_session
from app.errors import AppError
from app.models import User

# tokenUrl is used by Swagger UI's "Authorize" button (§17.5.7)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Yield a database session scoped to a single request.
    Auto-closes on request completion (even on errors).
    """
    async with get_async_session()() as session:
        yield session


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Decode the Bearer access token and return the corresponding User.

    Raises:
        AppError(401): token expired, invalid, wrong type, or user not found.
    """
    payload = decode_token(token, token_type="access")
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise AppError("Invalid token payload", status_code=401, code="INVALID_TOKEN")

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise AppError("Invalid token payload", status_code=401, code="INVALID_TOKEN")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise AppError("User not found", status_code=401, code="USER_NOT_FOUND")

    return user
