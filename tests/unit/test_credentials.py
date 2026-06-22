"""Unit tests for grit/git/credentials.py."""

from __future__ import annotations

import json
import sys
from typing import Any
from unittest.mock import MagicMock, patch, call

import pytest


# ── OS credential store ───────────────────────────────────────────────────────

class TestWindowsCredentialStore:
    """Tests for Windows Credential Manager integration via win32cred."""

    def test_store_credential(self) -> None:
        mock_win32cred = MagicMock()
        mock_win32cred.CRED_TYPE_GENERIC = 1
        mock_win32cred.CRED_PERSIST_LOCAL_MACHINE = 2

        with patch.dict("sys.modules", {"win32cred": mock_win32cred}):
            with patch("sys.platform", "win32"):
                from importlib import import_module, reload
                import grit.git.credentials as creds
                reload(creds)
                creds.store_credential("github.com", "testuser", "ghp_token")

        mock_win32cred.CredWrite.assert_called_once()
        written = mock_win32cred.CredWrite.call_args[0][0]
        assert written["TargetName"] == "gh:github.com:testuser"
        assert written["UserName"] == "testuser"
        assert written["CredentialBlob"] == "ghp_token"

    def test_has_credential_true(self) -> None:
        mock_win32cred = MagicMock()
        mock_win32cred.CRED_TYPE_GENERIC = 1

        with patch.dict("sys.modules", {"win32cred": mock_win32cred}):
            with patch("sys.platform", "win32"):
                import grit.git.credentials as creds
                from importlib import reload
                reload(creds)
                result = creds.has_credential("github.com", "testuser")

        assert result is True
        mock_win32cred.CredRead.assert_called_once_with(
            "gh:github.com:testuser", mock_win32cred.CRED_TYPE_GENERIC, 0
        )

    def test_has_credential_false_on_exception(self) -> None:
        mock_win32cred = MagicMock()
        mock_win32cred.CRED_TYPE_GENERIC = 1
        mock_win32cred.CredRead.side_effect = Exception("not found")

        with patch.dict("sys.modules", {"win32cred": mock_win32cred}):
            with patch("sys.platform", "win32"):
                import grit.git.credentials as creds
                from importlib import reload
                reload(creds)
                result = creds.has_credential("github.com", "testuser")

        assert result is False

    def test_delete_credential(self) -> None:
        mock_win32cred = MagicMock()
        mock_win32cred.CRED_TYPE_GENERIC = 1

        with patch.dict("sys.modules", {"win32cred": mock_win32cred}):
            with patch("sys.platform", "win32"):
                import grit.git.credentials as creds
                from importlib import reload
                reload(creds)
                creds.delete_credential("github.com", "testuser")

        mock_win32cred.CredDelete.assert_called_once_with(
            "gh:github.com:testuser", mock_win32cred.CRED_TYPE_GENERIC, 0
        )

    def test_store_raises_when_pywin32_missing(self) -> None:
        with patch.dict("sys.modules", {"win32cred": None}):
            with patch("sys.platform", "win32"):
                import grit.git.credentials as creds
                from importlib import reload
                reload(creds)
                from grit.exceptions import GritError
                with pytest.raises(GritError, match="pywin32"):
                    creds._win_store("github.com", "user", "token")


class TestMacOSCredentialStore:
    """Tests for macOS Keychain integration via `security` CLI."""

    def test_store_credential(self) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            import grit.git.credentials as creds
            creds._mac_store("github.com", "testuser", "ghp_token")

        calls = mock_run.call_args_list
        # First call is the delete (cleanup), second is the add
        add_call = calls[-1]
        cmd = add_call[0][0]
        assert "security" in cmd
        assert "add-internet-password" in cmd
        assert "testuser" in cmd
        assert "ghp_token" in cmd

    def test_has_credential_true(self) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            import grit.git.credentials as creds
            result = creds._mac_has("github.com", "testuser")
        assert result is True

    def test_has_credential_false(self) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=44)
            import grit.git.credentials as creds
            result = creds._mac_has("github.com", "testuser")
        assert result is False

    def test_store_raises_on_security_failure(self) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)  # delete ok
            # Make the add call fail
            mock_run.side_effect = [
                MagicMock(returncode=0),          # delete
                MagicMock(returncode=1, stderr=b"error msg"),  # add
            ]
            import grit.git.credentials as creds
            from grit.exceptions import GritError
            with pytest.raises(GritError, match="Keychain"):
                creds._mac_store("github.com", "testuser", "token")


# ── GitHub device flow ────────────────────────────────────────────────────────

class TestGithubBrowserLogin:
    """Tests for github_browser_login() device flow."""

    def _make_device_response(self) -> bytes:
        return json.dumps({
            "device_code": "devcode123",
            "user_code": "ABCD-1234",
            "verification_uri": "https://github.com/login/device",
            "verification_uri_complete": "https://github.com/login/device?user_code=ABCD-1234",
            "expires_in": 900,
            "interval": 5,
        }).encode()

    def _make_token_response(self, token: str = "ghp_testtoken") -> bytes:
        return json.dumps({"access_token": token, "token_type": "bearer"}).encode()

    def _make_pending_response(self) -> bytes:
        return json.dumps({"error": "authorization_pending"}).encode()

    def test_happy_path(self) -> None:
        device_resp = MagicMock()
        device_resp.__enter__ = lambda s: s
        device_resp.__exit__ = MagicMock(return_value=False)
        device_resp.read.return_value = self._make_device_response()

        token_resp = MagicMock()
        token_resp.__enter__ = lambda s: s
        token_resp.__exit__ = MagicMock(return_value=False)
        token_resp.read.return_value = self._make_token_response()

        with patch("urllib.request.urlopen", side_effect=[device_resp, token_resp]):
            with patch("webbrowser.open") as mock_browser:
                with patch("time.sleep"):
                    import grit.git.credentials as creds
                    result = creds.github_browser_login()

        assert result == "ghp_testtoken"
        mock_browser.assert_called_once_with(
            "https://github.com/login/device?user_code=ABCD-1234"
        )

    def test_polls_on_pending_then_succeeds(self) -> None:
        device_resp = MagicMock()
        device_resp.__enter__ = lambda s: s
        device_resp.__exit__ = MagicMock(return_value=False)
        device_resp.read.return_value = self._make_device_response()

        pending_resp = MagicMock()
        pending_resp.__enter__ = lambda s: s
        pending_resp.__exit__ = MagicMock(return_value=False)
        pending_resp.read.return_value = self._make_pending_response()

        token_resp = MagicMock()
        token_resp.__enter__ = lambda s: s
        token_resp.__exit__ = MagicMock(return_value=False)
        token_resp.read.return_value = self._make_token_response()

        with patch("urllib.request.urlopen", side_effect=[device_resp, pending_resp, token_resp]):
            with patch("webbrowser.open"):
                with patch("time.sleep"):
                    import grit.git.credentials as creds
                    result = creds.github_browser_login()

        assert result == "ghp_testtoken"

    def test_raises_on_access_denied(self) -> None:
        device_resp = MagicMock()
        device_resp.__enter__ = lambda s: s
        device_resp.__exit__ = MagicMock(return_value=False)
        device_resp.read.return_value = self._make_device_response()

        denied_resp = MagicMock()
        denied_resp.__enter__ = lambda s: s
        denied_resp.__exit__ = MagicMock(return_value=False)
        denied_resp.read.return_value = json.dumps({"error": "access_denied"}).encode()

        with patch("urllib.request.urlopen", side_effect=[device_resp, denied_resp]):
            with patch("webbrowser.open"):
                with patch("time.sleep"):
                    import grit.git.credentials as creds
                    from grit.exceptions import GritError
                    with pytest.raises(GritError, match="denied"):
                        creds.github_browser_login()

    def test_raises_on_network_error(self) -> None:
        with patch("urllib.request.urlopen", side_effect=OSError("no network")):
            import grit.git.credentials as creds
            from grit.exceptions import GritError
            with pytest.raises(GritError, match="device flow"):
                creds.github_browser_login()
