"""Unit tests for CLI commands: grit session pin/unpin."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from grit.cli.main import cli
from grit.exceptions import DaemonNotRunningError
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


class TestSessionPin:
    def test_pin_sends_ipc_request(
        self, runner: CliRunner, tmp_config_dir: Path, work_profile: Profile
    ) -> None:
        mock_resp = {
            "payload": {
                "session": {"repo_path": str(tmp_config_dir), "profile_id": work_profile.id}
            }
        }
        with patch(
            "grit.ipc.client.send_request", return_value=mock_resp
        ) as mock_send:
            result = runner.invoke(
                cli,
                [
                    "--config-dir", str(tmp_config_dir),
                    "session", "pin", "Work", "--repo", str(tmp_config_dir),
                ],
            )
        assert result.exit_code == 0, result.output
        assert "Pinned" in result.output
        mock_send.assert_called_once_with(
            "pin-session",
            {"repo_path": str(tmp_config_dir), "profile_id": work_profile.id},
        )

    def test_pin_unknown_profile_fails(self, runner: CliRunner, tmp_config_dir: Path) -> None:
        result = runner.invoke(
            cli,
            [
                "--config-dir", str(tmp_config_dir),
                "session", "pin", "Ghost", "--repo", str(tmp_config_dir),
            ],
        )
        assert result.exit_code == 1

    def test_pin_daemon_not_running(
        self, runner: CliRunner, tmp_config_dir: Path, work_profile: Profile
    ) -> None:
        with patch("grit.ipc.client.send_request", side_effect=DaemonNotRunningError()):
            result = runner.invoke(
                cli,
                [
                    "--config-dir", str(tmp_config_dir),
                    "session", "pin", "Work", "--repo", str(tmp_config_dir),
                ],
            )
        assert result.exit_code == 2


class TestSessionUnpin:
    def test_unpin_removed(self, runner: CliRunner, tmp_config_dir: Path) -> None:
        mock_resp = {"payload": {"unpinned": True}}
        with patch("grit.ipc.client.send_request", return_value=mock_resp):
            result = runner.invoke(
                cli,
                [
                    "--config-dir", str(tmp_config_dir),
                    "session", "unpin", "--repo", str(tmp_config_dir),
                ],
            )
        assert result.exit_code == 0
        assert "removed" in result.output

    def test_unpin_none_set(self, runner: CliRunner, tmp_config_dir: Path) -> None:
        mock_resp = {"payload": {"unpinned": False}}
        with patch("grit.ipc.client.send_request", return_value=mock_resp):
            result = runner.invoke(
                cli,
                [
                    "--config-dir", str(tmp_config_dir),
                    "session", "unpin", "--repo", str(tmp_config_dir),
                ],
            )
        assert result.exit_code == 0
        assert "No pin set" in result.output
