"""CRUD storage for Session objects backed by sessions.json."""

from __future__ import annotations

import json
from typing import Any

from grit.config.paths import sessions_file
from grit.exceptions import StorageCorruptError
from grit.models.session import Session
from grit.storage._lock import file_lock


class SessionStore:
    """Thread-safe store for per-repository sessions.

    Sessions are keyed by canonical repository path.  Expired sessions are
    purged lazily on every read, ensuring the file stays clean without a
    background cleanup task.
    """

    def __init__(self) -> None:
        self._path = sessions_file()

    # ── Private helpers ───────────────────────────────────────────────────────

    def _load_raw(self) -> dict[str, dict[str, Any]]:
        if not self._path.exists():
            return {}
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            raise StorageCorruptError(str(self._path), str(exc)) from exc
        if not isinstance(data, dict):
            raise StorageCorruptError(str(self._path), "expected a JSON object")
        return data

    def _save_raw(self, sessions: dict[str, Session]) -> None:
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(
                {k: v.to_dict() for k, v in sessions.items()},
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        tmp.replace(self._path)

    def _purge_expired_in_place(self, sessions: dict[str, Session]) -> dict[str, Session]:
        return {k: v for k, v in sessions.items() if not v.is_expired()}

    # ── Public API ────────────────────────────────────────────────────────────

    def get(self, repo_path: str) -> Session | None:
        """Return the active session for a repository, or None if absent/expired."""
        with file_lock(self._path):
            raw = self._load_raw()
            sessions = {k: Session.from_dict(v) for k, v in raw.items()}
            sessions = self._purge_expired_in_place(sessions)
            self._save_raw(sessions)
            return sessions.get(repo_path)

    def set(self, session: Session) -> None:
        """Upsert a session."""
        with file_lock(self._path):
            raw = self._load_raw()
            sessions = {k: Session.from_dict(v) for k, v in raw.items()}
            sessions = self._purge_expired_in_place(sessions)
            sessions[session.repo_path] = session
            self._save_raw(sessions)

    def delete(self, repo_path: str) -> None:
        """Remove a session. No-op if it doesn't exist."""
        with file_lock(self._path):
            raw = self._load_raw()
            sessions = {k: Session.from_dict(v) for k, v in raw.items()}
            sessions.pop(repo_path, None)
            self._save_raw(sessions)

    def purge_expired(self) -> int:
        """Explicitly purge all expired sessions. Returns number removed."""
        with file_lock(self._path):
            raw = self._load_raw()
            sessions = {k: Session.from_dict(v) for k, v in raw.items()}
            before = len(sessions)
            sessions = self._purge_expired_in_place(sessions)
            self._save_raw(sessions)
            return before - len(sessions)

    def get_all(self) -> list[Session]:
        """Return all non-expired sessions."""
        with file_lock(self._path):
            raw = self._load_raw()
            sessions = {k: Session.from_dict(v) for k, v in raw.items()}
            sessions = self._purge_expired_in_place(sessions)
            self._save_raw(sessions)
            return list(sessions.values())

    def find_pinned_repos_for_profile(self, profile_id: str) -> list[str]:
        """Return repo_paths with a pinned session referencing *profile_id*."""
        return [s.repo_path for s in self.get_all() if s.pinned and s.profile_id == profile_id]

    def invalidate_all(self) -> None:
        """Remove all sessions (e.g. for testing or manual reset)."""
        with file_lock(self._path):
            self._save_raw({})
