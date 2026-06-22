"""Unit tests for cloud sync conflict resolution."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

pytest.importorskip("grit_pro", reason="grit-pro not installed — Phase 2 tests skipped")
from grit_pro.cloud.sync import _merge_profiles, _save_team_profiles_raw  # noqa: E402

from grit.cloud.sync import get_team_profiles  # noqa: E402


def _p(pid: str, name: str, updated_offset_seconds: int = 0) -> dict:
    ts = (datetime.now(timezone.utc) + timedelta(seconds=updated_offset_seconds)).isoformat()
    return {"id": pid, "name": name, "email": f"{name}@test.com",
            "gpg_key_id": None, "ssh_key_path": None,
            "path_patterns": [], "remote_patterns": [],
            "created_at": ts, "updated_at": ts}


class TestMergeProfiles:
    def test_local_only_profile_kept(self) -> None:
        local = [_p("a", "Work")]
        remote: list = []
        merged = _merge_profiles(local, remote)
        assert len(merged) == 1
        assert merged[0]["name"] == "Work"

    def test_remote_only_profile_added(self) -> None:
        local: list = []
        remote = [_p("b", "Personal")]
        merged = _merge_profiles(local, remote)
        assert len(merged) == 1
        assert merged[0]["name"] == "Personal"

    def test_remote_wins_when_newer(self) -> None:
        local = [_p("a", "Work", updated_offset_seconds=-10)]
        remote = [_p("a", "Work-updated", updated_offset_seconds=0)]
        merged = _merge_profiles(local, remote)
        assert merged[0]["name"] == "Work-updated"

    def test_local_wins_when_newer(self) -> None:
        local = [_p("a", "Work-local", updated_offset_seconds=0)]
        remote = [_p("a", "Work-remote", updated_offset_seconds=-10)]
        merged = _merge_profiles(local, remote)
        assert merged[0]["name"] == "Work-local"

    def test_both_lists_combined(self) -> None:
        local = [_p("a", "Work"), _p("b", "Personal")]
        remote = [_p("c", "Client")]
        merged = _merge_profiles(local, remote)
        names = {m["name"] for m in merged}
        assert names == {"Work", "Personal", "Client"}

    def test_no_duplicates_on_same_id(self) -> None:
        local = [_p("a", "Work")]
        remote = [_p("a", "Work")]
        merged = _merge_profiles(local, remote)
        assert len(merged) == 1


class TestTeamProfiles:
    def test_empty_when_no_cache(self, tmp_config_dir) -> None:
        profiles = get_team_profiles()
        assert profiles == []

    def test_load_cached_team_profiles(self, tmp_config_dir) -> None:
        raw = [_p("t1", "TeamWork"), _p("t2", "TeamClient")]
        _save_team_profiles_raw(raw)
        profiles = get_team_profiles()
        assert len(profiles) == 2
        names = {p.name for p in profiles}
        assert names == {"TeamWork", "TeamClient"}
