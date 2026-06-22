"""User and subscription database models."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, Boolean, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    github_id: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    google_id: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    tier: Mapped[str] = mapped_column(String(32), default="free")  # free/pro/enterprise
    stripe_customer_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    profile_limit: Mapped[int] = mapped_column(Integer, default=5)  # -1 = unlimited
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class CloudProfile(Base):
    """Server-side copy of a user's profile for sync."""

    __tablename__ = "cloud_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # same as client ID
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    data: Mapped[str] = mapped_column(Text, nullable=False)  # JSON blob
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)


class TeamProfile(Base):
    """Organisation-level shared profile (read-only for members)."""

    __tablename__ = "team_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    org_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    data: Mapped[str] = mapped_column(Text, nullable=False)  # JSON blob
    created_by: Mapped[str] = mapped_column(String(36), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class Organization(Base):
    """Enterprise organisation — owns members, team profiles, and SSO config."""

    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    idp_type: Mapped[str] = mapped_column(String(16), default="none")   # none/saml/oidc
    idp_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    client_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    enforce_sso: Mapped[bool] = mapped_column(Boolean, default=False)
    sso_ttl_hours: Mapped[int] = mapped_column(Integer, default=8)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class OrgMember(Base):
    """Membership link between a User and an Organization, with role."""

    __tablename__ = "org_members"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(32), default="member")  # member/admin/owner
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class AuditEvent(Base):
    """Server-side audit log for enterprise compliance (SIEM export target)."""

    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    repo_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    profile_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    profile_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    extra: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON extras
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)
