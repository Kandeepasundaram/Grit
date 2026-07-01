"""Unit tests for CLI commands via Click's CliRunner."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from grit.cli.main import cli
from grit.models.profile import Profile
from grit.storage.profile_store import ProfileStore


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture()
def work_profile(tmp_config_dir: Path) -> Profile:
    p = Profile(name="Work", email="work@co.com")
    ProfileStore().add(p)
    return p


# ── Profile commands ───────────────────────────────────────────────────────────

class TestProfileAdd:
    def test_add_profile(self, runner: CliRunner, tmp_config_dir: Path) -> None:
        result = runner.invoke(
            cli,
            [
                "--config-dir", str(tmp_config_dir),
                "profile", "add", "--name", "Work", "--email", "w@co.com",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "Work" in result.output

    def test_add_duplicate_fails(
        self, runner: CliRunner, tmp_config_dir: Path, work_profile: Profile
    ) -> None:
        result = runner.invoke(
            cli,
            [
                "--config-dir", str(tmp_config_dir),
                "profile", "add", "--name", "Work", "--email", "x@co.com",
            ],
        )
        assert result.exit_code == 1

    def test_add_with_patterns(self, runner: CliRunner, tmp_config_dir: Path) -> None:
        result = runner.invoke(
            cli,
            [
                "--config-dir", str(tmp_config_dir),
                "profile", "add",
                "--name", "Client",
                "--email", "c@client.com",
                "--pattern", "~/clients/*",
                "--remote", "github.com/client/*",
            ],
        )
        assert result.exit_code == 0
        p = ProfileStore().get_by_name("Client")
        assert "~/clients/*" in p.path_patterns
        assert "github.com/client/*" in p.remote_patterns

    def test_add_with_repo_name_pattern(self, runner: CliRunner, tmp_config_dir: Path) -> None:
        result = runner.invoke(
            cli,
            [
                "--config-dir", str(tmp_config_dir),
                "profile", "add",
                "--name", "Acme",
                "--email", "a@acme.com",
                "--repo-name", "acme-*",
            ],
        )
        assert result.exit_code == 0
        p = ProfileStore().get_by_name("Acme")
        assert "acme-*" in p.repo_name_patterns


class TestProfileList:
    def test_list_empty(self, runner: CliRunner, tmp_config_dir: Path) -> None:
        result = runner.invoke(cli, ["--config-dir", str(tmp_config_dir), "profile", "list"])
        assert result.exit_code == 0
        assert "No profiles" in result.output

    def test_list_shows_profiles(
        self, runner: CliRunner, tmp_config_dir: Path, work_profile: Profile
    ) -> None:
        result = runner.invoke(cli, ["--config-dir", str(tmp_config_dir), "profile", "list"])
        assert result.exit_code == 0
        assert "Work" in result.output

    def test_list_json(
        self, runner: CliRunner, tmp_config_dir: Path, work_profile: Profile
    ) -> None:
        result = runner.invoke(
            cli, ["--config-dir", str(tmp_config_dir), "profile", "list", "--json"]
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert data[0]["name"] == "Work"


class TestProfileEditRepoName:
    def test_add_repo_name_pattern(
        self, runner: CliRunner, tmp_config_dir: Path, work_profile: Profile
    ) -> None:
        result = runner.invoke(
            cli,
            [
                "--config-dir", str(tmp_config_dir),
                "profile", "edit", "Work",
                "--add-repo-name", "acme-*",
            ],
        )
        assert result.exit_code == 0, result.output
        p = ProfileStore().get_by_name("Work")
        assert "acme-*" in p.repo_name_patterns


class TestProfileDelete:
    def test_delete_with_force(
        self, runner: CliRunner, tmp_config_dir: Path, work_profile: Profile
    ) -> None:
        result = runner.invoke(
            cli,
            ["--config-dir", str(tmp_config_dir), "profile", "delete", "Work", "--force"],
        )
        assert result.exit_code == 0
        assert ProfileStore().count() == 0

    def test_delete_nonexistent(self, runner: CliRunner, tmp_config_dir: Path) -> None:
        result = runner.invoke(
            cli,
            ["--config-dir", str(tmp_config_dir), "profile", "delete", "Ghost", "--force"],
        )
        assert result.exit_code == 1


class TestProfileSetDefault:
    def test_set_default(
        self, runner: CliRunner, tmp_config_dir: Path, work_profile: Profile
    ) -> None:
        result = runner.invoke(
            cli, ["--config-dir", str(tmp_config_dir), "profile", "set-default", "Work"]
        )
        assert result.exit_code == 0, result.output
        assert ProfileStore().get_by_name("Work").is_default is True

    def test_set_default_unknown_profile(
        self, runner: CliRunner, tmp_config_dir: Path
    ) -> None:
        result = runner.invoke(
            cli, ["--config-dir", str(tmp_config_dir), "profile", "set-default", "Ghost"]
        )
        assert result.exit_code == 1

    def test_unset_default(
        self, runner: CliRunner, tmp_config_dir: Path, work_profile: Profile
    ) -> None:
        runner.invoke(cli, ["--config-dir", str(tmp_config_dir), "profile", "set-default", "Work"])
        result = runner.invoke(
            cli, ["--config-dir", str(tmp_config_dir), "profile", "unset-default"]
        )
        assert result.exit_code == 0, result.output
        assert ProfileStore().get_by_name("Work").is_default is False


class TestProfileDeleteCleanup:
    def test_delete_default_profile_warns(
        self, runner: CliRunner, tmp_config_dir: Path, work_profile: Profile
    ) -> None:
        ProfileStore().set_default(work_profile.id)
        result = runner.invoke(
            cli,
            ["--config-dir", str(tmp_config_dir), "profile", "delete", "Work", "--force"],
        )
        assert result.exit_code == 0
        assert "was the default profile" in result.output

    def test_delete_pinned_profile_clears_pins(
        self, runner: CliRunner, tmp_config_dir: Path, work_profile: Profile
    ) -> None:
        from grit.models.session import Session
        from grit.storage.session_store import SessionStore
        SessionStore().set(
            Session(repo_path="/repo/pinned", profile_id=work_profile.id, pinned=True)
        )
        result = runner.invoke(
            cli,
            ["--config-dir", str(tmp_config_dir), "profile", "delete", "Work", "--force"],
        )
        assert result.exit_code == 0
        assert "/repo/pinned" in result.output
        assert SessionStore().get("/repo/pinned") is None

    def test_delete_plain_profile_no_warnings(
        self, runner: CliRunner, tmp_config_dir: Path, work_profile: Profile
    ) -> None:
        result = runner.invoke(
            cli,
            ["--config-dir", str(tmp_config_dir), "profile", "delete", "Work", "--force"],
        )
        assert result.exit_code == 0
        assert "was the default profile" not in result.output
        assert "pin" not in result.output.lower()


# ── Config commands ────────────────────────────────────────────────────────────

class TestConfig:
    def test_get_default_ttl(self, runner: CliRunner, tmp_config_dir: Path) -> None:
        result = runner.invoke(
            cli, ["--config-dir", str(tmp_config_dir), "config", "get", "session_ttl_seconds"]
        )
        assert result.exit_code == 0
        assert "28800" in result.output

    def test_set_and_get(self, runner: CliRunner, tmp_config_dir: Path) -> None:
        runner.invoke(
            cli,
            ["--config-dir", str(tmp_config_dir), "config", "set", "session_ttl_seconds", "3600"],
        )
        result = runner.invoke(
            cli, ["--config-dir", str(tmp_config_dir), "config", "get", "session_ttl_seconds"]
        )
        assert "3600" in result.output

    def test_set_unknown_key_fails(self, runner: CliRunner, tmp_config_dir: Path) -> None:
        result = runner.invoke(
            cli, ["--config-dir", str(tmp_config_dir), "config", "set", "no_such_key", "val"]
        )
        assert result.exit_code == 1

    def test_list_json(self, runner: CliRunner, tmp_config_dir: Path) -> None:
        result = runner.invoke(
            cli, ["--config-dir", str(tmp_config_dir), "config", "list", "--json"]
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "session_ttl_seconds" in data


# ── Daemon status (mocked IPC) ─────────────────────────────────────────────────

class TestDaemonStatus:
    def test_not_running(self, runner: CliRunner, tmp_config_dir: Path) -> None:
        with patch("grit.daemon.pid.get_running_pid", return_value=None):
            result = runner.invoke(cli, ["--config-dir", str(tmp_config_dir), "daemon", "status"])
        assert result.exit_code == 2

    def test_running_shows_info(self, runner: CliRunner, tmp_config_dir: Path) -> None:
        mock_resp = {
            "status": "ok",
            "payload": {"version": "0.1.0-alpha", "active_sessions": 2, "profile_count": 3},
        }
        with patch("grit.daemon.pid.get_running_pid", return_value=12345), \
             patch("grit.ipc.client.send_request", return_value=mock_resp):
            result = runner.invoke(cli, ["--config-dir", str(tmp_config_dir), "daemon", "status"])
        assert result.exit_code == 0
        assert "12345" in result.output
        assert "Active sessions: 2" in result.output
