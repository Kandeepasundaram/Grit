"""Enterprise API endpoints.

Routes:
  POST   /v1/enterprise/orgs                  — create organisation (owner)
  GET    /v1/enterprise/orgs/{org_id}         — get org details
  PATCH  /v1/enterprise/orgs/{org_id}         — update org config (SSO, name)
  GET    /v1/enterprise/orgs/{org_id}/members — list members
  POST   /v1/enterprise/orgs/{org_id}/members — invite / add member
  DELETE /v1/enterprise/orgs/{org_id}/members/{user_id} — remove member

  GET    /v1/enterprise/orgs/{org_id}/profiles        — list team profiles
  POST   /v1/enterprise/orgs/{org_id}/profiles        — create team profile
  PUT    /v1/enterprise/orgs/{org_id}/profiles/{pid}  — update team profile
  DELETE /v1/enterprise/orgs/{org_id}/profiles/{pid}  — delete team profile

  GET    /v1/enterprise/orgs/{org_id}/audit           — query audit log
  POST   /v1/enterprise/audit                         — ingest client audit events

  GET    /v1/enterprise/sso/{org_id}/config           — get SSO config (client onboarding)
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select, delete

from app.api.deps import get_current_user
from app.database import AsyncSessionLocal
from app.models.user import AuditEvent, OrgMember, Organization, TeamProfile, User

router = APIRouter()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _get_org(org_id: str) -> Organization:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Organization).where(Organization.id == org_id))
        org = result.scalar_one_or_none()
    if org is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    return org


async def _require_org_role(org_id: str, user: User, min_role: str = "member") -> OrgMember:
    """Raise 403 if user doesn't have at least *min_role* in the org."""
    roles = {"member": 0, "admin": 1, "owner": 2}
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(OrgMember).where(
                OrgMember.org_id == org_id,
                OrgMember.user_id == user.id,
            )
        )
        membership = result.scalar_one_or_none()
    if membership is None or roles.get(membership.role, -1) < roles.get(min_role, 0):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    return membership


# ── Schemas ───────────────────────────────────────────────────────────────────

class OrgCreate(BaseModel):
    name: str
    slug: str


class OrgUpdate(BaseModel):
    name: Optional[str] = None
    idp_type: Optional[str] = None
    idp_url: Optional[str] = None
    client_id: Optional[str] = None
    enforce_sso: Optional[bool] = None
    sso_ttl_hours: Optional[int] = None


class MemberAdd(BaseModel):
    email: str
    role: str = "member"


class TeamProfileUpsert(BaseModel):
    id: Optional[str] = None
    name: str
    email: str
    gpg_key_id: Optional[str] = None
    ssh_key_path: Optional[str] = None
    path_patterns: List[str] = []
    remote_patterns: List[str] = []


class AuditIngest(BaseModel):
    events: List[Dict[str, Any]]
    org_id: Optional[str] = None


# ── Organisation CRUD ─────────────────────────────────────────────────────────

@router.post("/orgs", status_code=status.HTTP_201_CREATED)
async def create_org(
    body: OrgCreate,
    user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    org = Organization(
        id=str(uuid.uuid4()),
        name=body.name,
        slug=body.slug,
    )
    membership = OrgMember(
        org_id=org.id,
        user_id=user.id,
        role="owner",
    )
    async with AsyncSessionLocal() as db:
        db.add(org)
        db.add(membership)
        await db.commit()
        await db.refresh(org)
    return {"id": org.id, "name": org.name, "slug": org.slug, "role": "owner"}


@router.get("/orgs/{org_id}")
async def get_org(
    org_id: str,
    user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    await _require_org_role(org_id, user)
    org = await _get_org(org_id)
    return {
        "id": org.id, "name": org.name, "slug": org.slug,
        "idp_type": org.idp_type, "idp_url": org.idp_url,
        "client_id": org.client_id, "enforce_sso": org.enforce_sso,
        "sso_ttl_hours": org.sso_ttl_hours,
    }


@router.patch("/orgs/{org_id}")
async def update_org(
    org_id: str,
    body: OrgUpdate,
    user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    await _require_org_role(org_id, user, min_role="admin")
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Organization).where(Organization.id == org_id))
        org = result.scalar_one_or_none()
        if org is None:
            raise HTTPException(status_code=404, detail="Organization not found")
        if body.name is not None:
            org.name = body.name
        if body.idp_type is not None:
            org.idp_type = body.idp_type
        if body.idp_url is not None:
            org.idp_url = body.idp_url
        if body.client_id is not None:
            org.client_id = body.client_id
        if body.enforce_sso is not None:
            org.enforce_sso = body.enforce_sso
        if body.sso_ttl_hours is not None:
            org.sso_ttl_hours = body.sso_ttl_hours
        org.updated_at = _now()
        await db.commit()
    return {"updated": True}


# ── Members ───────────────────────────────────────────────────────────────────

@router.get("/orgs/{org_id}/members")
async def list_members(
    org_id: str,
    user: User = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    await _require_org_role(org_id, user)
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(OrgMember, User)
            .join(User, OrgMember.user_id == User.id)
            .where(OrgMember.org_id == org_id)
        )
        rows = result.all()
    return [
        {"user_id": m.user_id, "email": u.email, "name": u.display_name, "role": m.role,
         "joined_at": m.joined_at.isoformat()}
        for m, u in rows
    ]


@router.post("/orgs/{org_id}/members", status_code=status.HTTP_201_CREATED)
async def add_member(
    org_id: str,
    body: MemberAdd,
    user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    await _require_org_role(org_id, user, min_role="admin")
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == body.email))
        target = result.scalar_one_or_none()
        if target is None:
            raise HTTPException(status_code=404, detail=f"No user with email {body.email!r}")
        existing = await db.execute(
            select(OrgMember).where(OrgMember.org_id == org_id, OrgMember.user_id == target.id)
        )
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(status_code=409, detail="User already a member")
        membership = OrgMember(org_id=org_id, user_id=target.id, role=body.role)
        db.add(membership)
        await db.commit()
    return {"added": True, "email": body.email, "role": body.role}


@router.delete("/orgs/{org_id}/members/{target_user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    org_id: str,
    target_user_id: str,
    user: User = Depends(get_current_user),
) -> None:
    await _require_org_role(org_id, user, min_role="admin")
    async with AsyncSessionLocal() as db:
        await db.execute(
            delete(OrgMember).where(
                OrgMember.org_id == org_id,
                OrgMember.user_id == target_user_id,
            )
        )
        await db.commit()


# ── Team profiles ─────────────────────────────────────────────────────────────

@router.get("/orgs/{org_id}/profiles")
async def list_team_profiles(
    org_id: str,
    user: User = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    await _require_org_role(org_id, user)
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(TeamProfile).where(TeamProfile.org_id == org_id))
        profiles = result.scalars().all()
    return [json.loads(p.data) for p in profiles]


@router.post("/orgs/{org_id}/profiles", status_code=status.HTTP_201_CREATED)
async def create_team_profile(
    org_id: str,
    body: TeamProfileUpsert,
    user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    await _require_org_role(org_id, user, min_role="admin")
    profile_id = body.id or str(uuid.uuid4())
    now = _now().isoformat()
    data = {
        "id": profile_id, "name": body.name, "email": body.email,
        "gpg_key_id": body.gpg_key_id, "ssh_key_path": body.ssh_key_path,
        "path_patterns": body.path_patterns, "remote_patterns": body.remote_patterns,
        "created_at": now, "updated_at": now,
    }
    tp = TeamProfile(id=profile_id, org_id=org_id, data=json.dumps(data), created_by=user.id)
    async with AsyncSessionLocal() as db:
        db.add(tp)
        await db.commit()
    return data


@router.put("/orgs/{org_id}/profiles/{profile_id}")
async def update_team_profile(
    org_id: str,
    profile_id: str,
    body: TeamProfileUpsert,
    user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    await _require_org_role(org_id, user, min_role="admin")
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(TeamProfile).where(TeamProfile.id == profile_id, TeamProfile.org_id == org_id)
        )
        tp = result.scalar_one_or_none()
        if tp is None:
            raise HTTPException(status_code=404, detail="Team profile not found")
        existing = json.loads(tp.data)
        existing.update({
            "name": body.name, "email": body.email,
            "gpg_key_id": body.gpg_key_id, "ssh_key_path": body.ssh_key_path,
            "path_patterns": body.path_patterns, "remote_patterns": body.remote_patterns,
            "updated_at": _now().isoformat(),
        })
        tp.data = json.dumps(existing)
        await db.commit()
    return existing


@router.delete("/orgs/{org_id}/profiles/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_team_profile(
    org_id: str,
    profile_id: str,
    user: User = Depends(get_current_user),
) -> None:
    await _require_org_role(org_id, user, min_role="admin")
    async with AsyncSessionLocal() as db:
        await db.execute(
            delete(TeamProfile).where(TeamProfile.id == profile_id, TeamProfile.org_id == org_id)
        )
        await db.commit()


# ── Audit events ──────────────────────────────────────────────────────────────

@router.get("/orgs/{org_id}/audit")
async def query_audit(
    org_id: str,
    since: Optional[str] = Query(None, description="ISO timestamp lower bound"),
    action: Optional[str] = Query(None),
    limit: int = Query(100, le=1000),
    user: User = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    await _require_org_role(org_id, user, min_role="admin")
    async with AsyncSessionLocal() as db:
        stmt = select(AuditEvent).where(AuditEvent.org_id == org_id).order_by(
            AuditEvent.timestamp.desc()
        ).limit(limit)
        if since:
            try:
                since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
                stmt = stmt.where(AuditEvent.timestamp >= since_dt)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid ISO timestamp for 'since'")
        if action:
            stmt = stmt.where(AuditEvent.action == action)
        result = await db.execute(stmt)
        events = result.scalars().all()

    return [
        {
            "id": e.id, "action": e.action, "timestamp": e.timestamp.isoformat(),
            "user_id": e.user_id, "repo_path": e.repo_path,
            "profile_id": e.profile_id, "profile_name": e.profile_name,
            "extra": json.loads(e.extra) if e.extra else None,
        }
        for e in events
    ]


@router.post("/audit", status_code=status.HTTP_202_ACCEPTED)
async def ingest_audit_events(
    body: AuditIngest,
    user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Receive a batch of client-side audit events and persist them server-side."""
    if body.org_id:
        await _require_org_role(body.org_id, user)

    async with AsyncSessionLocal() as db:
        for event in body.events:
            ae = AuditEvent(
                org_id=body.org_id,
                user_id=user.id,
                action=event.get("action", "unknown"),
                repo_path=event.get("repo_path"),
                profile_id=event.get("profile_id"),
                profile_name=event.get("profile_name"),
                extra=json.dumps({k: v for k, v in event.items()
                                  if k not in ("action", "repo_path", "profile_id", "profile_name")}),
            )
            db.add(ae)
        await db.commit()

    return {"ingested": len(body.events)}


# ── SSO config endpoint (client onboarding) ───────────────────────────────────

@router.get("/sso/{org_id}/config")
async def get_sso_config(org_id: str) -> Dict[str, Any]:
    """Public endpoint — returns SSO config for org so clients can self-configure."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Organization).where(Organization.id == org_id))
        org = result.scalar_one_or_none()
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    return {
        "org_id": org.id,
        "org_name": org.name,
        "idp_type": org.idp_type,
        "idp_url": org.idp_url,
        "client_id": org.client_id,
        "enforce_sso": org.enforce_sso,
        "sso_ttl_hours": org.sso_ttl_hours,
    }
