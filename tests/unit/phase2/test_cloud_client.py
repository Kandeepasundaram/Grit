"""Unit tests for the cloud API client (all HTTP calls mocked)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from grit.cloud.client import AuthRequiredError, GritCloudClient, OfflineError


@pytest.fixture()
def client() -> GritCloudClient:
    return GritCloudClient(base_url="https://api.test.grit.dev")


def _mock_response(data: dict, status: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    resp.read.return_value = json.dumps(data).encode()
    resp.status = status
    return resp


class TestGetLicenseStatus:
    def test_returns_license_data(self, client: GritCloudClient, tmp_config_dir: Path) -> None:
        expected = {"token": "jwt.tok.here", "claims": {"tier": "pro"}}
        with patch("grit_pro.cloud.auth.get_access_token", return_value="test-token"), \
             patch("urllib.request.urlopen", return_value=_mock_response(expected)):
            result = client.get_license_status()
        assert result["claims"]["tier"] == "pro"

    def test_raises_auth_required_when_no_token(
        self, client: GritCloudClient, tmp_config_dir: Path
    ) -> None:
        with patch(
            "grit_pro.cloud.auth.get_access_token", return_value=None
        ), pytest.raises(AuthRequiredError):
            client.get_license_status()

    def test_raises_offline_error_on_network_failure(
        self, client: GritCloudClient, tmp_config_dir: Path
    ) -> None:
        import urllib.error
        with patch(
            "grit_pro.cloud.auth.get_access_token", return_value="test-token"
        ), patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.URLError("connection refused"),
        ), pytest.raises(OfflineError):
            client.get_license_status()


class TestPushProfiles:
    def test_push_profiles(self, client: GritCloudClient, tmp_config_dir: Path) -> None:
        profiles = [{"id": "abc", "name": "Work", "email": "w@co.com", "updated_at": "2026-01-01"}]
        expected = {"profiles": profiles}
        with patch("grit_pro.cloud.auth.get_access_token", return_value="test-token"), \
             patch("urllib.request.urlopen", return_value=_mock_response(expected)):
            result = client.push_profiles(profiles)
        assert result["profiles"] == profiles


class TestPullProfiles:
    def test_pull_profiles(self, client: GritCloudClient, tmp_config_dir: Path) -> None:
        profiles = [{"id": "abc", "name": "Work", "email": "w@co.com", "updated_at": "2026-01-01"}]
        with patch("grit_pro.cloud.auth.get_access_token", return_value="test-token"), \
             patch("urllib.request.urlopen", return_value=_mock_response({"profiles": profiles})):
            result = client.pull_profiles()
        assert len(result) == 1
        assert result[0]["name"] == "Work"
