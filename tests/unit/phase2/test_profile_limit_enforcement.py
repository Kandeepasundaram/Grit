"""Integration test: ProfileStore enforces free-tier profile limit."""

from __future__ import annotations

from pathlib import Path

import pytest

from grit.constants import FREE_TIER_MAX_PROFILES
from grit.models.profile import Profile
from grit.storage.profile_store import ProfileStore


def _add_profiles(store: ProfileStore, count: int) -> None:
    for i in range(count):
        store.add(Profile(name=f"Profile{i}", email=f"p{i}@test.com"))


class TestProfileLimitEnforcement:
    def test_can_add_up_to_free_limit(self, tmp_config_dir: Path) -> None:
        store = ProfileStore()
        _add_profiles(store, FREE_TIER_MAX_PROFILES)
        assert store.count() == FREE_TIER_MAX_PROFILES

    def test_cannot_exceed_free_limit(self, tmp_config_dir: Path) -> None:
        store = ProfileStore()
        _add_profiles(store, FREE_TIER_MAX_PROFILES)
        with pytest.raises(ValueError, match="Free tier"):
            store.add(Profile(name="TooMany", email="too@test.com"))

    def test_pro_tier_allows_more_than_five(self, tmp_config_dir: Path) -> None:
        from datetime import datetime, timedelta, timezone
        from unittest.mock import patch

        from grit.config.subscription import save_license

        future = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()
        claims = {
            "user_id": "u1", "email": "u@t.com", "tier": "pro",
            "profile_limit": -1, "expires_at": future, "issued_at": "",
        }
        save_license("tok", claims)

        with patch("grit.config.subscription._verify_jwt", return_value=claims):
            store = ProfileStore()
            _add_profiles(store, FREE_TIER_MAX_PROFILES + 2)
            assert store.count() == FREE_TIER_MAX_PROFILES + 2
