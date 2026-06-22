"""Profile and session sync endpoints."""

from __future__ import annotations

import json
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.api.deps import get_current_user

router = APIRouter()


class ProfilesPayload(BaseModel):
    profiles: List[dict]


class SessionsPayload(BaseModel):
    sessions: List[dict]


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _require_pro(user) -> None:
    from app.database import AsyncSessionLocal
    from app.models.user import Subscription
    from sqlalchemy import select
    from datetime import datetime, timezone

    async with AsyncSessionLocal() as db:
        stmt = select(Subscription).where(Subscription.user_id == user.id)
        result = await db.execute(stmt)
        sub = result.scalar_one_or_none()

    if sub is None or sub.tier == "free":
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Cloud sync requires Grit Pro. Upgrade at https://grit.dev/upgrade",
        )
    if sub.expires_at and datetime.now(timezone.utc) > sub.expires_at.replace(tzinfo=timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Your Grit Pro subscription has expired.",
        )


# ── Profile sync ──────────────────────────────────────────────────────────────

@router.post("/profiles")
async def push_profiles(
    payload: ProfilesPayload, current_user=Depends(get_current_user)
) -> dict:
    """Accept client profiles, merge server-side, return merged list."""
    await _require_pro(current_user)

    from app.database import AsyncSessionLocal
    from app.models.user import CloudProfile
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        # Load existing server profiles
        stmt = select(CloudProfile).where(
            CloudProfile.user_id == current_user.id,
            CloudProfile.deleted == False,
        )
        result = await db.execute(stmt)
        server_rows = result.scalars().all()
        server_map = {r.id: json.loads(r.data) for r in server_rows}

        # Merge: last-write-wins by updated_at
        for p in payload.profiles:
            pid = p.get("id")
            if not pid:
                continue
            server_p = server_map.get(pid)
            if server_p is None or p.get("updated_at", "") >= server_p.get("updated_at", ""):
                server_map[pid] = p
                # Upsert in DB
                existing = next((r for r in server_rows if r.id == pid), None)
                if existing:
                    existing.data = json.dumps(p)
                else:
                    db.add(CloudProfile(
                        id=pid,
                        user_id=current_user.id,
                        data=json.dumps(p),
                    ))
        await db.commit()

    return {"profiles": list(server_map.values())}


@router.get("/profiles")
async def pull_profiles(current_user=Depends(get_current_user)) -> dict:
    """Return all server-side profiles for the authenticated user."""
    await _require_pro(current_user)

    from app.database import AsyncSessionLocal
    from app.models.user import CloudProfile
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        stmt = select(CloudProfile).where(
            CloudProfile.user_id == current_user.id,
            CloudProfile.deleted == False,
        )
        result = await db.execute(stmt)
        rows = result.scalars().all()

    return {"profiles": [json.loads(r.data) for r in rows]}


# ── Session sync ──────────────────────────────────────────────────────────────

@router.post("/sessions")
async def push_sessions(
    payload: SessionsPayload, current_user=Depends(get_current_user)
) -> dict:
    """Store active sessions server-side for multi-machine awareness."""
    await _require_pro(current_user)
    # Sessions are ephemeral — store in Redis with TTL matching session expiry
    # Simplified: store as JSON in Redis key `sessions:{user_id}`
    try:
        import redis.asyncio as aioredis
        from app.config import settings

        r = aioredis.from_url(settings.redis_url)
        await r.set(
            f"sessions:{current_user.id}",
            json.dumps(payload.sessions),
            ex=8 * 3600,  # 8 hours
        )
        await r.aclose()
    except Exception:
        pass  # Redis failure is non-fatal for sessions
    return {"stored": len(payload.sessions)}


@router.get("/sessions")
async def pull_sessions(current_user=Depends(get_current_user)) -> dict:
    """Return server-stored sessions for the authenticated user."""
    await _require_pro(current_user)
    try:
        import redis.asyncio as aioredis
        from app.config import settings

        r = aioredis.from_url(settings.redis_url)
        data = await r.get(f"sessions:{current_user.id}")
        await r.aclose()
        sessions = json.loads(data) if data else []
    except Exception:
        sessions = []
    return {"sessions": sessions}


# ── Team profiles ─────────────────────────────────────────────────────────────

@router.get("/team/profiles", tags=["team"])
async def get_team_profiles(current_user=Depends(get_current_user)) -> dict:
    """Return read-only organisation profiles for the authenticated user."""
    await _require_pro(current_user)
    # Phase 2: org membership lookup not yet implemented — return empty
    return {"profiles": []}
