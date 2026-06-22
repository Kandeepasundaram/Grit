"""Unit tests for the compliance reporting module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from grit.enterprise.compliance import (
    check_gpg_enforcement,
    audit_summary,
    generate_report,
)
from grit.models.profile import Profile
from grit.storage.profile_store import ProfileStore


class TestGPGEnforcement:
    def test_all_profiles_have_gpg(self, tmp_config_dir: Path) -> None:
        store = ProfileStore()
        store.add(Profile(name="Work", email="work@co.com", gpg_key_id="ABCD1234"))
        store.add(Profile(name="Client", email="client@co.com", gpg_key_id="DCBA4321"))

        result = check_gpg_enforcement()
        assert result["total_profiles"] == 2
        assert result["gpg_enabled"] == 2
        assert result["gpg_missing"] == 0
        assert result["profiles_without_gpg"] == []

    def test_some_profiles_missing_gpg(self, tmp_config_dir: Path) -> None:
        store = ProfileStore()
        store.add(Profile(name="Work", email="work@co.com", gpg_key_id="ABCD1234"))
        store.add(Profile(name="Personal", email="me@gmail.com"))  # no GPG

        result = check_gpg_enforcement()
        assert result["gpg_missing"] == 1
        assert "Personal" in result["profiles_without_gpg"]


class TestAuditSummary:
    def test_empty_log_returns_zero_events(self, tmp_config_dir: Path) -> None:
        result = audit_summary()
        assert result["total_events"] == 0
        assert result["by_action"] == {}

    def test_counts_by_action(self, tmp_config_dir: Path) -> None:
        from grit.enterprise.audit import log_profile_switch, log_git_config_write
        log_profile_switch("/r/a", "p1", "Work")
        log_profile_switch("/r/b", "p1", "Work")
        log_git_config_write("/r/a", "user.email")

        result = audit_summary()
        assert result["total_events"] == 3
        assert result["by_action"]["profile_switch"] == 2
        assert result["by_action"]["git_config_write"] == 1


class TestGenerateReport:
    def test_report_structure(self, tmp_config_dir: Path) -> None:
        with patch("grit_pro.enterprise.compliance.check_hook_inventory",
                   return_value={"total_repos": 0, "hooks_installed": 0, "hooks_missing": 0, "missing_repos": [], "repos": []}):
            with patch("grit_pro.enterprise.compliance.check_sso_compliance",
                       return_value={"sso_configured": False, "enforce_sso": False, "active_sso_session": False, "idp_type": "none", "org_id": None, "org_name": None, "sso_user": None}):
                report = generate_report()

        assert "generated_at" in report
        assert "sections" in report
        assert "compliant" in report
        assert "hook_inventory" in report["sections"]
        assert "gpg_enforcement" in report["sections"]
        assert "audit_summary" in report["sections"]

    def test_report_passes_with_zero_repos_and_profiles(self, tmp_config_dir: Path) -> None:
        with patch("grit_pro.enterprise.compliance.check_hook_inventory",
                   return_value={"total_repos": 0, "hooks_installed": 0, "hooks_missing": 0, "missing_repos": [], "repos": []}):
            with patch("grit_pro.enterprise.compliance.check_sso_compliance",
                       return_value={"sso_configured": False, "enforce_sso": False, "active_sso_session": False, "idp_type": "none", "org_id": None, "org_name": None, "sso_user": None}):
                report = generate_report()

        # 0 repos + 0 GPG missing + SSO not enforced = compliant
        assert report["compliant"] is True

    def test_report_fails_with_missing_hooks(self, tmp_config_dir: Path) -> None:
        with patch("grit_pro.enterprise.compliance.check_hook_inventory",
                   return_value={"total_repos": 2, "hooks_installed": 1, "hooks_missing": 1, "missing_repos": ["/r/x"], "repos": []}):
            with patch("grit_pro.enterprise.compliance.check_sso_compliance",
                       return_value={"sso_configured": False, "enforce_sso": False, "active_sso_session": False, "idp_type": "none", "org_id": None, "org_name": None, "sso_user": None}):
                report = generate_report()

        assert report["compliant"] is False
