"""Unit tests for SessionEngine."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

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


class TestResolveNewTiers:
    def test_repo_name_detected_and_session_created(self, tmp_config_dir: Path) -> None:
        acme = Profile(name="Acme", email="a@co.com", repo_name_patterns=["acme-*"])
        ProfileStore().add(acme)
        engine = SessionEngine()
        repo = "/home/user/acme-backend"
        with patch("grit.git.config.apply_profile"):
            result = engine.resolve(repo)
        assert result is not None
        assert result.profile_id == acme.id

    def test_pin_checked_after_auto_detect_fails(
        self, engine: SessionEngine, profile: Profile, tmp_config_dir: Path
    ) -> None:
        with patch("grit.git.config.apply_profile"):
            engine.pin(REPO, profile.id)
        with patch("grit.git.config.apply_profile"):
            result = engine.resolve(REPO)
        assert result is not None
        assert result.profile_id == profile.id
        assert result.pinned is True

    def test_auto_detect_overrides_stale_pin(self, tmp_config_dir: Path) -> None:
        stale = Profile(name="Stale", email="s@co.com")
        fresh = Profile(name="Fresh", email="f@co.com", repo_name_patterns=["acme-*"])
        ProfileStore().add(stale)
        ProfileStore().add(fresh)
        engine = SessionEngine()
        repo = "/home/user/acme-backend"
        with patch("grit.git.config.apply_profile"):
            engine.pin(repo, stale.id)
        with patch("grit.git.config.apply_profile"):
            result = engine.resolve(repo)
        assert result is not None
        assert result.profile_id == fresh.id

    def test_default_profile_used_when_nothing_else_matches(
        self, engine: SessionEngine, profile: Profile, tmp_config_dir: Path
    ) -> None:
        ProfileStore().set_default(profile.id)
        with patch("grit.git.config.apply_profile"):
            result = engine.resolve("/home/user/unrelated-repo")
        assert result is not None
        assert result.profile_id == profile.id

    def test_prompts_when_nothing_matches_and_no_default(
        self, engine: SessionEngine, tmp_config_dir: Path
    ) -> None:
        result = engine.resolve("/home/user/unrelated-repo")
        assert result is None

    def test_dangling_pin_falls_through_to_default(
        self, engine: SessionEngine, profile: Profile, tmp_config_dir: Path
    ) -> None:
        # Simulate a pin whose profile was deleted out of band (hand-edited
        # JSON, or a profile removed without going through `profile delete`).
        SessionStore().set(
            Session(repo_path=REPO, profile_id="deleted-profile-id", pinned=True)
        )
        ProfileStore().set_default(profile.id)
        with patch("grit.git.config.apply_profile"):
            result = engine.resolve(REPO)
        assert result is not None
        assert result.profile_id == profile.id

    def test_dangling_pin_falls_through_to_prompt_when_no_default(
        self, engine: SessionEngine, tmp_config_dir: Path
    ) -> None:
        SessionStore().set(
            Session(repo_path=REPO, profile_id="deleted-profile-id", pinned=True)
        )
        result = engine.resolve(REPO)
        assert result is None


class TestUnpin:
    def test_unpin_removes_pin(
        self, engine: SessionEngine, profile: Profile, tmp_config_dir: Path
    ) -> None:
        with patch("grit.git.config.apply_profile"):
            engine.pin(REPO, profile.id)
        assert engine.unpin(REPO) is True
        assert SessionStore().get(REPO) is None

    def test_unpin_nonexistent_returns_false(
        self, engine: SessionEngine, tmp_config_dir: Path
    ) -> None:
        assert engine.unpin("/no/such/repo") is False


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
