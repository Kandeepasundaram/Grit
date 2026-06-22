"""Unit tests for the enterprise audit log."""

from __future__ import annotations

from pathlib import Path

from grit.config.paths import audit_log_file
from grit.enterprise.audit import (
    export_entries,
    log_git_config_write,
    log_profile_switch,
    log_session_create,
)


class TestAuditLog:
    def test_log_and_export(self, tmp_config_dir: Path) -> None:
        log_profile_switch("/repos/work", "pid-1", "Work")
        log_session_create("/repos/work", "pid-1")
        log_git_config_write("/repos/work", "user.email")

        entries = export_entries()
        assert len(entries) == 3
        assert entries[0]["action"] == "profile_switch"
        assert entries[1]["action"] == "session_create"
        assert entries[2]["action"] == "git_config_write"

    def test_export_since_filter(self, tmp_config_dir: Path) -> None:
        from datetime import datetime, timedelta, timezone

        log_profile_switch("/repos/a", "pid-1", "Work")

        future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        entries = export_entries(since=future)
        assert entries == []

        past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        entries = export_entries(since=past)
        assert len(entries) == 1

    def test_export_returns_empty_when_no_log(self, tmp_config_dir: Path) -> None:
        entries = export_entries()
        assert entries == []

    def test_log_file_is_append_only(self, tmp_config_dir: Path) -> None:
        for i in range(5):
            log_profile_switch(f"/repos/{i}", "pid-1", f"Profile{i}")

        path = audit_log_file()
        lines = [line for line in path.read_text().splitlines() if line.strip()]
        assert len(lines) == 5

    def test_malformed_lines_are_skipped(self, tmp_config_dir: Path) -> None:
        path = audit_log_file()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            '{"action":"ok","timestamp":"2025-01-01T00:00:00Z"}\n'
            "NOT JSON\n"
            '{"action":"ok2","timestamp":"2025-01-02T00:00:00Z"}\n'
        )

        entries = export_entries()
        assert len(entries) == 2
        assert entries[0]["action"] == "ok"
        assert entries[1]["action"] == "ok2"

    def test_entries_have_required_fields(self, tmp_config_dir: Path) -> None:
        log_profile_switch("/repos/x", "pid-abc", "MyProfile")
        entries = export_entries()
        assert len(entries) == 1
        e = entries[0]
        assert "timestamp" in e
        assert "action" in e
        assert e["profile_name"] == "MyProfile"
        assert e["repo_path"] == "/repos/x"
