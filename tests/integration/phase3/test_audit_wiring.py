"""Integration tests: audit log is populated by session engine and git config writes."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from grit.enterprise.audit import export_entries
from grit.models.profile import Profile
from grit.session.engine import SessionEngine
from grit.storage.profile_store import ProfileStore


@pytest.mark.integration
class TestAuditWiring:
    def test_session_create_writes_audit_entry(self, tmp_config_dir: Path) -> None:
        store = ProfileStore()
        profile = store.add(Profile(name="Work", email="work@co.com"))

        engine = SessionEngine()

        with patch("grit.git.config.apply_profile"):
            engine.create("/repos/test", profile.id)

        entries = export_entries()
        actions = [e["action"] for e in entries]
        assert "session_create" in actions

    def test_apply_writes_profile_switch_audit(self, tmp_config_dir: Path) -> None:
        store = ProfileStore()
        profile = store.add(Profile(name="Work", email="work@co.com"))

        engine = SessionEngine()

        from grit.models.session import Session
        s = Session(repo_path="/repos/x", profile_id=profile.id)

        with patch("grit.git.config.apply_profile"):
            engine.apply(s)

        entries = export_entries()
        actions = [e["action"] for e in entries]
        assert "profile_switch" in actions

    def test_git_config_apply_writes_audit_entries(
        self, tmp_config_dir: Path, git_repo: Path
    ) -> None:
        from grit.git.config import apply_profile

        profile = Profile(name="Dev", email="dev@co.com")
        apply_profile(str(git_repo), profile)

        entries = export_entries()
        keys_logged = {e.get("key") for e in entries if e.get("action") == "git_config_write"}
        assert "user.name" in keys_logged
        assert "user.email" in keys_logged
