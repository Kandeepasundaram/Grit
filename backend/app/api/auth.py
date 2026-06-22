"""OAuth device-flow endpoints proxied to GitHub / Google."""

from __future__ import annotations

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import settings

router = APIRouter()


class DeviceFlowRequest(BaseModel):
    provider: str
    scope: str


class TokenPollRequest(BaseModel):
    provider: str
    device_code: str


class TokenRefreshRequest(BaseModel):
    provider: str
    refresh_token: str


# ── Device authorization ───────────────────────────────────────────────────────

@router.post("/{provider}/device")
async def start_device_flow(provider: str, body: DeviceFlowRequest) -> dict:
    """Proxy device-flow initiation to the OAuth provider."""
    if provider == "github":
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://github.com/login/device/code",
                json={"client_id": settings.github_client_id, "scope": body.scope},
                headers={"Accept": "application/json"},
                timeout=10,
            )
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail="GitHub device flow failed")
        return resp.json()
    raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider!r}")


@router.post("/{provider}/token")
async def poll_device_token(provider: str, body: TokenPollRequest) -> dict:
    """Proxy device-flow token poll to the OAuth provider.

    Returns access_token + refresh_token on success, or error codes while pending.
    """
    if provider == "github":
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://github.com/login/oauth/access_token",
                json={
                    "client_id": settings.github_client_id,
                    "client_secret": settings.github_client_secret,
                    "device_code": body.device_code,
                    "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                },
                headers={"Accept": "application/json"},
                timeout=10,
            )
        data = resp.json()
        if "access_token" in data:
            # Exchange for a Grit-internal session token and return with user info
            user = await _get_github_user(data["access_token"])
            db_user = await _upsert_user(user, provider="github")
            grit_token = _issue_session_token(db_user)
            return {
                "access_token": grit_token,
                "refresh_token": data.get("refresh_token", ""),
                "user_id": db_user.id,
                "email": db_user.email,
            }
        return data  # forward error codes (authorization_pending, slow_down, etc.)
    raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider!r}")


async def _get_github_user(access_token: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"token {access_token}", "Accept": "application/json"},
            timeout=10,
        )
        user = resp.json()
        # Also fetch primary email if not public
        if not user.get("email"):
            emails_resp = await client.get(
                "https://api.github.com/user/emails",
                headers={"Authorization": f"token {access_token}"},
                timeout=10,
            )
            emails = emails_resp.json()
            primary = next((e["email"] for e in emails if e.get("primary")), None)
            user["email"] = primary
    return user


async def _upsert_user(provider_user: dict, provider: str):
    """Find or create a User record from OAuth user info."""
    from app.database import AsyncSessionLocal
    from app.models.user import User
    from sqlalchemy import select
    from datetime import datetime, timezone

    async with AsyncSessionLocal() as db:
        email = provider_user.get("email", "")
        stmt = select(User).where(User.email == email)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        if user is None:
            user = User(
                email=email,
                display_name=provider_user.get("name") or provider_user.get("login", ""),
                github_id=str(provider_user.get("id", "")) if provider == "github" else None,
            )
            db.add(user)
        user.last_login_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(user)
        return user


def _issue_session_token(user) -> str:
    """Issue a short-lived Grit internal JWT for the user."""
    import jwt  # PyJWT
    from datetime import datetime, timezone, timedelta

    payload = {
        "sub": user.id,
        "email": user.email,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")
