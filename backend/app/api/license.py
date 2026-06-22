"""License endpoints — issue and refresh license JWTs."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user

router = APIRouter()


@router.get("/status")
async def get_license_status(current_user=Depends(get_current_user)) -> dict:
    """Return the user's current license as a signed JWT + claims."""
    from app.database import AsyncSessionLocal
    from app.models.user import Subscription
    from app.services.license_service import issue_license_jwt
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        stmt = select(Subscription).where(Subscription.user_id == current_user.id)
        result = await db.execute(stmt)
        subscription = result.scalar_one_or_none()

    try:
        token, claims = issue_license_jwt(current_user, subscription)
    except FileNotFoundError:
        # Private key not generated yet (dev environment)
        claims = {
            "user_id": current_user.id,
            "email": current_user.email,
            "tier": "free",
            "profile_limit": 5,
            "expires_at": "9999-12-31T23:59:59+00:00",
            "issued_at": "",
        }
        token = ""

    return {"token": token, "claims": claims}
