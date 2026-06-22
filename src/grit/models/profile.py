"""Profile data model."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return uuid.uuid4().hex


@dataclass
class Profile:
    """A named Git identity with associated keys and path patterns."""

    name: str
    email: str
    id: str = field(default_factory=_new_id)
    gpg_key_id: Optional[str] = None
    ssh_key_path: Optional[str] = None
    http_username: Optional[str] = None
    # Glob patterns for automatic assignment, e.g. ["~/work/*", "~/clients/acme/*"]
    path_patterns: List[str] = field(default_factory=list)
    # Remote URL patterns, e.g. ["github.com/myorg/*"]
    remote_patterns: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Profile":
        known = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in data.items() if k in known})

    def touch(self) -> None:
        """Update the updated_at timestamp (call before saving after an edit)."""
        self.updated_at = _now_iso()
