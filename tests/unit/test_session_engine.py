"""Unit tests for SessionEngine."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from grit.config.app_config import AppConfig
from grit.models.profile import Profile
from grit.models.session import Session
from grit.session.engine import SessionEngine
from grit.storage.profile_store import ProfileStore
from grit.storage.session_store import SessionStore

REPO = "/home/user/myrepo"


@pytest.fixture()
def profile(tmp_config_dir: Path) -> Profile:
    p = Profile(name="Work", email="work@co.com")
    ProfileStore().add(p)
    return p


@pytest.fixture()
def engine(tmp_config_dir: Path) -> SessionEngine:
    return SessionEngine()


class TestResolve:
    def test_no_session_returns_none(self, engine: SessionEngine, tmp_config_dir: Path) -> None:
        result = engine.resolve(REPO)
        assert result is None

    def test_active_session_returned(
        self, engine: SessionEngine, profile: Profile, tmp_config_dir: Path
    ) -> None:
        with patch("grit.git.config.apply_profile"):
            engine.create(REPO, profile.id)
        with patch("grit.git.config.apply_profile"):
            resolved = engine.resolve(REPO)
        assert resolved is not None
        assert resolved.profile_id == profile.id

    def test_expired_session_not_returned(
        self, tmp_config_dir: Path, profile: Profile
    ) -> None:
        past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        session = Session(repo_path=REPO, profile_id=profile.id, expires_at=past)
        SessionStore().set(session)
        engine = SessionEngine()
        result = engine.resolve(REPO)
        assert result is None


class TestCreate:
    def test_create_returns_session(
        self, engine: SessionEngine, profile: Profile, tmp_config_dir: Path
    ) -> None:
        with patch("grit.git.config.apply_profile"):
            session = engine.create(REPO, profile.id)
        assert session.repo_path == REPO
        assert session.profile_id == profile.id

    def test_create_persists_session(
        self, engine: SessionEngine, profile: Profile, tmp_config_dir: Path
    ) -> None:
        with patch("grit.git.config.apply_profile"):
            engine.create(REPO, profile.id)
        stored = SessionStore().get(REPO)
        assert stored is not None
        assert stored.profile_id == profile.id


class TestInvalidate:
    def test_invalidate_removes_session(
        self, engine: SessionEngine, profile: Profile, tmp_config_dir: Path
    ) -> None:
        with patch("grit.git.config.apply_profile"):
            engine.create(REPO, profile.id)
        engine.invalidate(REPO)
        assert SessionStore().get(REPO) is None

    def test_invalidate_nonexistent_is_noop(
        self, engine: SessionEngine, tmp_config_dir: Path
    ) -> None:
        engine.invalidate("/no/such/repo")  # should not raise
