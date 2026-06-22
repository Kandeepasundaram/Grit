"""Shared FastAPI dependencies — auth, DB session, etc."""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings

_bearer = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
):
    """Decode the Grit session JWT and return the User ORM object."""
    import jwt
    from app.database import AsyncSessionLocal
    from app.models.user import User
    from sqlalchemy import select

    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user_id = payload.get("sub")
    async with AsyncSessionLocal() as db:
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user
