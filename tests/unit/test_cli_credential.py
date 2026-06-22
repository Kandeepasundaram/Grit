"""Unit tests for grit credential CLI commands."""

from __future__ import annotations

from unittest.mock import patch

from click.testing import CliRunner

from grit.cli.main import cli
from grit.models.profile import Profile
from grit.storage.profile_store import ProfileStore


def _profile(name: str = "Work", http_username: str = "workuser") -> Profile:
    return Profile(name=name, email="work@co.com", http_username=http_username)


def _profile_no_http(name: str = "Work") -> Profile:
    return Profile(name=name, email="work@co.com")


class TestCredentialLogin:
    def test_login_opens_browser_and_stores(self, tmp_config_dir) -> None:
        store = ProfileStore()
        store.add(_profile())

        runner = CliRunner()
        with patch(
            "grit.git.credentials.github_browser_login", return_value="ghp_token"
        ) as mock_login, patch("grit.git.credentials.store_credential") as mock_store:
            result = runner.invoke(cli, ["credential", "login", "Work"])

        assert result.exit_code == 0, result.output
        mock_login.assert_called_once()
        mock_store.assert_called_once_with("github.com", "workuser", "ghp_token")
        assert "Authorized as workuser" in result.output

    def test_login_fails_when_no_http_username(self, tmp_config_dir) -> None:
        store = ProfileStore()
        store.add(_profile_no_http())

        runner = CliRunner()
        result = runner.invoke(cli, ["credential", "login", "Work"])

        assert result.exit_code != 0
        assert "no HTTP username" in result.output

    def test_login_fails_on_unknown_profile(self, tmp_config_dir) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["credential", "login", "Unknown"])
        assert result.exit_code != 0

    def test_login_handles_auth_error(self, tmp_config_dir) -> None:
        from grit.exceptions import GritError
        store = ProfileStore()
        store.add(_profile())

        runner = CliRunner()
        with patch("grit.git.credentials.github_browser_login", side_effect=GritError("denied")):
            result = runner.invoke(cli, ["credential", "login", "Work"])

        assert result.exit_code != 0
        assert "denied" in result.output


class TestCredentialSet:
    def test_set_stores_credential(self, tmp_config_dir) -> None:
        store = ProfileStore()
        store.add(_profile())

        runner = CliRunner()
        with patch("grit.git.credentials.store_credential") as mock_store:
            result = runner.invoke(cli, ["credential", "set", "Work", "--token", "ghp_abc"])

        assert result.exit_code == 0, result.output
        mock_store.assert_called_once_with("github.com", "workuser", "ghp_abc")
        assert "ghp_abc" not in result.output  # token must not be echoed

    def test_set_custom_host(self, tmp_config_dir) -> None:
        store = ProfileStore()
        store.add(_profile())

        runner = CliRunner()
        with patch("grit.git.credentials.store_credential") as mock_store:
            result = runner.invoke(
                cli, ["credential", "set", "Work", "--token", "tok", "--host", "gitlab.com"]
            )

        assert result.exit_code == 0
        mock_store.assert_called_once_with("gitlab.com", "workuser", "tok")


class TestCredentialClear:
    def test_clear_calls_delete(self, tmp_config_dir) -> None:
        store = ProfileStore()
        store.add(_profile())

        runner = CliRunner()
        with patch("grit.git.credentials.delete_credential") as mock_del:
            result = runner.invoke(cli, ["credential", "clear", "Work"])

        assert result.exit_code == 0, result.output
        mock_del.assert_called_once_with("github.com", "workuser")


class TestCredentialShow:
    def test_show_stored(self, tmp_config_dir) -> None:
        store = ProfileStore()
        store.add(_profile())

        runner = CliRunner()
        with patch("grit.git.credentials.has_credential", return_value=True):
            result = runner.invoke(cli, ["credential", "show", "Work"])

        assert result.exit_code == 0
        assert "Yes" in result.output
        assert "workuser" in result.output

    def test_show_not_stored(self, tmp_config_dir) -> None:
        store = ProfileStore()
        store.add(_profile())

        runner = CliRunner()
        with patch("grit.git.credentials.has_credential", return_value=False):
            result = runner.invoke(cli, ["credential", "show", "Work"])

        assert result.exit_code == 0
        assert "No" in result.output

    def test_show_no_http_username(self, tmp_config_dir) -> None:
        store = ProfileStore()
        store.add(_profile_no_http())

        runner = CliRunner()
        result = runner.invoke(cli, ["credential", "show", "Work"])

        assert result.exit_code == 0
        assert "not set" in result.output
        assert "N/A" in result.output
