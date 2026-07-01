"""Unit tests for SessionStore."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from grit.exceptions import StorageCorruptError
from grit.models.session import Session
from grit.storage.session_store import SessionStore

REPO = "/home/user/work/myrepo"
PROFILE_ID = "abc123"


@pytest.fixture()
def store(tmp_config_dir: Path) -> SessionStore:
    return SessionStore()


def _active_session(repo: str = REPO, profile_id: str = PROFILE_ID) -> Session:
    return Session(repo_path=repo, profile_id=profile_id)


def _expired_session(repo: str = REPO, profile_id: str = PROFILE_ID) -> Session:
    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    return Session(repo_path=repo, profile_id=profile_id, expires_at=past)


class TestSetAndGet:
    def test_set_then_get(self, store: SessionStore) -> None:
        s = _active_session()
        store.set(s)
        result = store.get(REPO)
        assert result is not None
        assert result.profile_id == PROFILE_ID

    def test_get_missing_returns_none(self, store: SessionStore) -> None:
        assert store.get("/no/such/repo") is None

    def test_upsert_replaces(self, store: SessionStore) -> None:
        store.set(_active_session(profile_id="first"))
        store.set(_active_session(profile_id="second"))
        assert store.get(REPO).profile_id == "second"  # type: ignore[union-attr]


class TestExpiry:
    def test_expired_session_returns_none(self, store: SessionStore) -> None:
        store.set(_expired_session())
        assert store.get(REPO) is None

    def test_expired_session_purged_from_file(self, store: SessionStore) -> None:
        store.set(_expired_session())
        store.get(REPO)  # triggers purge
        assert store.get_all() == []

    def test_locked_session_never_expires(self, store: SessionStore) -> None:
        past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        s = Session(repo_path=REPO, profile_id=PROFILE_ID, expires_at=past, locked=True)
        store.set(s)
        assert store.get(REPO) is not None


class TestPinned:
    def test_pinned_session_never_expires(self, store: SessionStore) -> None:
        past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        s = Session(repo_path=REPO, profile_id=PROFILE_ID, expires_at=past, pinned=True)
        store.set(s)
        assert store.get(REPO) is not None

    def test_pinned_session_survives_purge(self, store: SessionStore) -> None:
        past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        s = Session(repo_path=REPO, profile_id=PROFILE_ID, expires_at=past, pinned=True)
        store.set(s)
        removed = store.purge_expired()
        assert removed == 0
        assert store.get(REPO) is not None

    def test_find_pinned_repos_for_profile(self, store: SessionStore) -> None:
        store.set(Session(repo_path="/repo/a", profile_id="p1", pinned=True))
        store.set(Session(repo_path="/repo/b", profile_id="p2", pinned=True))
        store.set(Session(repo_path="/repo/c", profile_id="p1", pinned=False))
        result = store.find_pinned_repos_for_profile("p1")
        assert result == ["/repo/a"]

    def test_find_pinned_repos_for_profile_no_match(self, store: SessionStore) -> None:
        store.set(Session(repo_path="/repo/a", profile_id="p1", pinned=True))
        assert store.find_pinned_repos_for_profile("nonexistent") == []


class TestDelete:
    def test_delete_existing(self, store: SessionStore) -> None:
        store.set(_active_session())
        store.delete(REPO)
        assert store.get(REPO) is None

    def test_delete_missing_is_noop(self, store: SessionStore) -> None:
        store.delete("/no/such/repo")  # should not raise


class TestPurge:
    def test_purge_removes_expired(self, store: SessionStore) -> None:
        store.set(_active_session("/repo/a", "p1"))
        store.set(_expired_session("/repo/b", "p2"))
        removed = store.purge_expired()
        assert removed == 1
        assert store.get("/repo/a") is not None

    def test_purge_returns_zero_when_none_expired(self, store: SessionStore) -> None:
        store.set(_active_session())
        assert store.purge_expired() == 0


class TestGetAll:
    def test_returns_only_active(self, store: SessionStore) -> None:
        store.set(_active_session("/repo/a", "p1"))
        store.set(_expired_session("/repo/b", "p2"))
        sessions = store.get_all()
        assert len(sessions) == 1
        assert sessions[0].repo_path == "/repo/a"


class TestCorruptFile:
    def test_corrupt_json_raises(self, tmp_config_dir: Path) -> None:
        sessions_path = tmp_config_dir / "data" / "sessions.json"
        sessions_path.parent.mkdir(parents=True, exist_ok=True)
        sessions_path.write_text("INVALID", encoding="utf-8")
        store = SessionStore()
        with pytest.raises(StorageCorruptError):
            store.get(REPO)
