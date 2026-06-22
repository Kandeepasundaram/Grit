"""Integration tests for the sync flow with a mocked cloud API."""

from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from grit.cloud.sync import SyncEngine, get_team_profiles
from grit.models.profile import Profile
from grit.storage.profile_store import ProfileStore


def _future_iso() -> str:
    return (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()


def _make_pro_license(tmp_config_dir: Path) -> None:
    """Set up a pro license so sync calls pass require_pro()."""
    from grit.config.subscription import save_license
    claims = {
        "user_id": "u1", "email": "u@t.com", "tier": "pro",
        "profile_limit": -1, "expires_at": _future_iso(), "issued_at": "",
    }
    save_license("tok", claims)


@pytest.mark.integration
class TestSyncEngine:
    def test_push_profiles_sends_local_to_cloud(self, tmp_config_dir: Path) -> None:
        _make_pro_license(tmp_config_dir)
        store = ProfileStore()
        store.add(Profile(name="Work", email="work@co.com"))
        store.add(Profile(name="Personal", email="me@gmail.com"))

        engine = SyncEngine()
        mock_client = MagicMock()
        mock_client.push_profiles.return_value = {"profiles": []}
        engine._client = mock_client

        with patch("grit.config.subscription._verify_jwt", return_value=None):
            count = engine.push_profiles()

        assert count == 2
        mock_client.push_profiles.assert_called_once()
        pushed = mock_client.push_profiles.call_args[0][0]
        names = {p["name"] for p in pushed}
        assert names == {"Work", "Personal"}

    def test_pull_profiles_merges_remote(self, tmp_config_dir: Path) -> None:
        _make_pro_license(tmp_config_dir)
        store = ProfileStore()
        local_profile = Profile(name="Work", email="work@co.com")
        store.add(local_profile)

        remote_profiles = [
            {
                "id": local_profile.id,
                "name": "Work",
                "email": "work-updated@co.com",
                "gpg_key_id": None,
                "ssh_key_path": None,
                "path_patterns": [],
                "remote_patterns": [],
                "created_at": _future_iso(),
                "updated_at": _future_iso(),  # newer than local
            },
            {
                "id": "new-id",
                "name": "Client",
                "email": "client@co.com",
                "gpg_key_id": None,
                "ssh_key_path": None,
                "path_patterns": [],
                "remote_patterns": [],
                "created_at": _future_iso(),
                "updated_at": _future_iso(),
            },
        ]

        engine = SyncEngine()
        mock_client = MagicMock()
        mock_client.pull_profiles.return_value = remote_profiles
        engine._client = mock_client

        with patch("grit.config.subscription._verify_jwt", return_value=None):
            count = engine.pull_profiles()

        assert count >= 1  # at least the new "Client" profile
        # Verify local storage was updated
        updated_store = ProfileStore()
        all_profiles = updated_store.get_all()
        emails = {p.email for p in all_profiles}
        assert "work-updated@co.com" in emails
        assert "client@co.com" in emails

    def test_pull_team_profiles_caches_locally(self, tmp_config_dir: Path) -> None:
        _make_pro_license(tmp_config_dir)

        team_data = [
            {
                "id": "t1", "name": "TeamWork", "email": "team@co.com",
                "gpg_key_id": None, "ssh_key_path": None,
                "path_patterns": [], "remote_patterns": [],
                "created_at": _future_iso(), "updated_at": _future_iso(),
            }
        ]

        engine = SyncEngine()
        mock_client = MagicMock()
        mock_client.get_team_profiles.return_value = team_data
        engine._client = mock_client

        with patch("grit.config.subscription._verify_jwt", return_value=None):
            count = engine.pull_team_profiles()

        assert count == 1
        cached = get_team_profiles()
        assert len(cached) == 1
        assert cached[0].name == "TeamWork"

    def test_sync_blocked_on_free_tier(self, tmp_config_dir: Path) -> None:
        # No license saved → free tier
        engine = SyncEngine()
        with pytest.raises(ValueError, match="requires Grit Pro"):
            engine.push_profiles()
