"""Unit tests for subscription tier enforcement."""

from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from grit.config.subscription import (
    License,
    _FREE_LICENSE,
    load_license,
    save_license,
    clear_license,
    enforce_profile_limit,
    require_pro,
)
from grit.constants import FREE_TIER_MAX_PROFILES


# ── License dataclass ─────────────────────────────────────────────────────────

class TestLicense:
    def test_free_license_is_valid(self) -> None:
        assert _FREE_LICENSE.is_valid

    def test_expired_license(self) -> None:
        past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        lic = License(
            user_id="u1", email="u@t.com", tier="pro",
            profile_limit=-1, expires_at=past, issued_at="",
        )
        assert lic.is_expired

    def test_grace_period(self) -> None:
        # Expired 5 days ago — within 30-day grace period
        past = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
        lic = License(
            user_id="u1", email="u@t.com", tier="pro",
            profile_limit=-1, expires_at=past, issued_at="",
        )
        assert lic.is_expired
        assert lic.is_in_grace_period
        assert lic.is_valid  # valid because in grace period

    def test_grace_period_expired(self) -> None:
        # Expired 31 days ago — beyond grace period
        past = (datetime.now(timezone.utc) - timedelta(days=31)).isoformat()
        lic = License(
            user_id="u1", email="u@t.com", tier="pro",
            profile_limit=-1, expires_at=past, issued_at="",
        )
        assert not lic.is_valid

    def test_pro_feature_flags(self) -> None:
        future = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()
        lic = License(
            user_id="u1", email="u@t.com", tier="pro",
            profile_limit=-1, expires_at=future, issued_at="",
        )
        assert lic.allows_cloud_sync()
        assert lic.allows_team_profiles()
        assert not lic.allows_sso()

    def test_enterprise_feature_flags(self) -> None:
        future = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()
        lic = License(
            user_id="u1", email="u@t.com", tier="enterprise",
            profile_limit=-1, expires_at=future, issued_at="",
        )
        assert lic.allows_sso()
        assert lic.allows_audit_log()

    def test_unlimited_profile_limit(self) -> None:
        future = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()
        lic = License(
            user_id="u1", email="u@t.com", tier="pro",
            profile_limit=-1, expires_at=future, issued_at="",
        )
        assert lic.allows_profile_count(1000)

    def test_free_profile_limit(self) -> None:
        assert not _FREE_LICENSE.allows_profile_count(FREE_TIER_MAX_PROFILES + 1)
        assert _FREE_LICENSE.allows_profile_count(FREE_TIER_MAX_PROFILES)


# ── Storage ───────────────────────────────────────────────────────────────────

class TestLicenseStorage:
    def test_no_license_returns_free(self, tmp_config_dir: Path) -> None:
        lic = load_license()
        assert lic.tier == "free"
        assert lic.profile_limit == FREE_TIER_MAX_PROFILES

    def test_save_and_load_without_crypto(self, tmp_config_dir: Path) -> None:
        claims = {
            "user_id": "u1",
            "email": "u@t.com",
            "tier": "pro",
            "profile_limit": -1,
            "expires_at": "9999-12-31T23:59:59+00:00",
            "issued_at": "2026-01-01T00:00:00+00:00",
        }
        save_license("placeholder.token.here", claims)
        # When verification fails (no crypto lib), must return free tier — no unverified fallback
        with patch("grit.config.subscription._verify_jwt", return_value=None):
            lic = load_license()
        assert lic.tier == "free"

    def test_save_and_load_with_verified_claims(self, tmp_config_dir: Path) -> None:
        claims = {
            "user_id": "u1",
            "email": "u@t.com",
            "tier": "pro",
            "profile_limit": -1,
            "expires_at": "9999-12-31T23:59:59+00:00",
            "issued_at": "2026-01-01T00:00:00+00:00",
        }
        save_license("placeholder.token.here", claims)
        # Simulate successful JWT verification returning the claims
        with patch("grit.config.subscription._verify_jwt", return_value=claims):
            lic = load_license()
        assert lic.tier == "pro"
        assert lic.profile_limit == -1

    def test_clear_license_reverts_to_free(self, tmp_config_dir: Path) -> None:
        save_license("tok", {"tier": "pro", "profile_limit": -1,
                             "user_id": "u1", "email": "e", "expires_at": "", "issued_at": ""})
        clear_license()
        lic = load_license()
        assert lic.tier == "free"


# ── Enforcement ───────────────────────────────────────────────────────────────

class TestEnforcement:
    def test_free_tier_allows_up_to_limit(self, tmp_config_dir: Path) -> None:
        # Should not raise for counts within the free limit
        for i in range(FREE_TIER_MAX_PROFILES):
            enforce_profile_limit(i)  # current count before adding

    def test_free_tier_blocks_beyond_limit(self, tmp_config_dir: Path) -> None:
        with pytest.raises(ValueError, match="Free tier"):
            enforce_profile_limit(FREE_TIER_MAX_PROFILES)

    def test_pro_tier_allows_unlimited(self, tmp_config_dir: Path) -> None:
        future = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()
        claims = {
            "user_id": "u1", "email": "u@t.com", "tier": "pro",
            "profile_limit": -1, "expires_at": future, "issued_at": "",
        }
        save_license("tok", claims)
        with patch("grit.config.subscription._verify_jwt", return_value=claims):
            enforce_profile_limit(1000)  # should not raise

    def test_require_pro_blocks_on_free(self, tmp_config_dir: Path) -> None:
        with pytest.raises(ValueError, match="requires Grit Pro"):
            require_pro("cloud_sync")

    def test_require_pro_passes_on_pro_tier(self, tmp_config_dir: Path) -> None:
        future = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()
        claims = {
            "user_id": "u1", "email": "u@t.com", "tier": "pro",
            "profile_limit": -1, "expires_at": future, "issued_at": "",
        }
        save_license("tok", claims)
        with patch("grit.config.subscription._verify_jwt", return_value=claims):
            require_pro("cloud_sync")  # should not raise
