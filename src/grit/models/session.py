"""Session data model."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from grit.constants import DEFAULT_SESSION_TTL_SECONDS


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _expiry_iso(ttl_seconds: int = DEFAULT_SESSION_TTL_SECONDS) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)).isoformat()


@dataclass
class Session:
    """Associates a repository path with a profile for a TTL-bounded window."""

    repo_path: str      # canonical, absolute path
    profile_id: str
    created_at: str = field(default_factory=_now_iso)
    last_used_at: str = field(default_factory=_now_iso)
    expires_at: str = field(default_factory=_expiry_iso)
    locked: bool = False  # locked sessions never expire automatically

    # ── Convenience ──────────────────────────────────────────────────────────

    def is_expired(self) -> bool:
        if self.locked:
            return False
        now = datetime.now(timezone.utc)
        expiry = datetime.fromisoformat(self.expires_at)
        return now >= expiry

    def ttl_remaining_seconds(self) -> int:
        """Seconds until expiry; 0 if already expired; -1 if locked."""
        if self.locked:
            return -1
        now = datetime.now(timezone.utc)
        expiry = datetime.fromisoformat(self.expires_at)
        remaining = (expiry - now).total_seconds()
        return max(0, int(remaining))

    def touch(self, ttl_seconds: int = DEFAULT_SESSION_TTL_SECONDS) -> None:
        """Update last_used_at and extend the expiry window."""
        self.last_used_at = _now_iso()
        if not self.locked:
            self.expires_at = _expiry_iso(ttl_seconds)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Session:
        known = set(cls.__dataclass_fields__)
        return cls(**{k: v for k, v in data.items() if k in known})
