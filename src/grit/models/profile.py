"""Profile data model."""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


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
    gpg_key_id: str | None = None
    ssh_key_path: str | None = None
    http_username: str | None = None
    # Glob patterns for automatic assignment, e.g. ["~/work/*", "~/clients/acme/*"]
    path_patterns: list[str] = field(default_factory=list)
    # Remote URL patterns, e.g. ["github.com/myorg/*"]
    remote_patterns: list[str] = field(default_factory=list)
    # Repo folder-name glob patterns, e.g. ["acme-*"] — matched on the repo's
    # directory basename alone, independent of its path or remote.
    repo_name_patterns: list[str] = field(default_factory=list)
    # Fallback profile applied when no other detection tier matches.
    # At most one profile may have this set; enforced by ProfileStore.
    is_default: bool = False
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Profile:
        known = set(cls.__dataclass_fields__)
        return cls(**{k: v for k, v in data.items() if k in known})

    def touch(self) -> None:
        """Update the updated_at timestamp (call before saving after an edit)."""
        self.updated_at = _now_iso()
