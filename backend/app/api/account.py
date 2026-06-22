"""Account endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user

router = APIRouter()


@router.get("/me")
async def get_me(current_user=Depends(get_current_user)) -> dict:
    from app.database import AsyncSessionLocal
    from app.models.user import Subscription
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        stmt = select(Subscription).where(Subscription.user_id == current_user.id)
        result = await db.execute(stmt)
        sub = result.scalar_one_or_none()

    return {
        "id": current_user.id,
        "email": current_user.email,
        "display_name": current_user.display_name,
        "tier": sub.tier if sub else "free",
        "profile_limit": sub.profile_limit if sub else 5,
    }
