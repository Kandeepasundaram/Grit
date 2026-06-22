"""Unit tests for git/config.py — uses a real git repo in tmp_path."""

from __future__ import annotations

from pathlib import Path

import pytest

from grit.git import config as git_config
from grit.models.profile import Profile


@pytest.mark.integration
class TestReadWrite:
    def test_write_and_read_local(self, git_repo: Path) -> None:
        git_config.write_local(str(git_repo), "user.email", "test@example.com")
        assert git_config.read_local(str(git_repo), "user.email") == "test@example.com"

    def test_read_missing_key_returns_none(self, git_repo: Path) -> None:
        assert git_config.read_local(str(git_repo), "user.signingkey") is None

    def test_unset_removes_key(self, git_repo: Path) -> None:
        git_config.write_local(str(git_repo), "user.signingkey", "ABCDEF01")
        git_config.unset_local(str(git_repo), "user.signingkey")
        assert git_config.read_local(str(git_repo), "user.signingkey") is None

    def test_unset_missing_key_is_noop(self, git_repo: Path) -> None:
        git_config.unset_local(str(git_repo), "user.signingkey")  # no error


@pytest.mark.integration
class TestApplyProfile:
    def test_apply_basic_profile(self, git_repo: Path) -> None:
        profile = Profile(name="Work", email="work@co.com")
        git_config.apply_profile(str(git_repo), profile)
        assert git_config.read_local(str(git_repo), "user.name") == "Work"
        assert git_config.read_local(str(git_repo), "user.email") == "work@co.com"

    def test_apply_profile_with_gpg(self, git_repo: Path) -> None:
        profile = Profile(name="Work", email="work@co.com", gpg_key_id="ABCDEF01")
        git_config.apply_profile(str(git_repo), profile)
        assert git_config.read_local(str(git_repo), "user.signingkey") == "ABCDEF01"
        assert git_config.read_local(str(git_repo), "commit.gpgsign") == "true"

    def test_apply_profile_clears_previous_gpg(self, git_repo: Path) -> None:
        # First set a profile with GPG
        profile_with_gpg = Profile(name="Work", email="w@co.com", gpg_key_id="ABCDEF01")
        git_config.apply_profile(str(git_repo), profile_with_gpg)
        # Then apply one without GPG — should clear the signing config
        profile_no_gpg = Profile(name="Personal", email="me@gmail.com")
        git_config.apply_profile(str(git_repo), profile_no_gpg)
        assert git_config.read_local(str(git_repo), "user.signingkey") is None

    def test_apply_profile_with_ssh(self, git_repo: Path) -> None:
        profile = Profile(name="Work", email="w@co.com", ssh_key_path="/home/user/.ssh/id_work")
        git_config.apply_profile(str(git_repo), profile)
        ssh_cmd = git_config.read_local(str(git_repo), "core.sshCommand")
        assert ssh_cmd is not None
        assert "/home/user/.ssh/id_work" in ssh_cmd


    def test_apply_profile_with_http_username(self, git_repo: Path) -> None:
        profile = Profile(name="Work", email="w@co.com", http_username="workuser")
        git_config.apply_profile(str(git_repo), profile)
        assert git_config.read_local(str(git_repo), "credential.username") == "workuser"

    def test_apply_profile_clears_http_username(self, git_repo: Path) -> None:
        profile_with = Profile(name="Work", email="w@co.com", http_username="workuser")
        git_config.apply_profile(str(git_repo), profile_with)
        profile_without = Profile(name="Personal", email="me@gmail.com")
        git_config.apply_profile(str(git_repo), profile_without)
        assert git_config.read_local(str(git_repo), "credential.username") is None


@pytest.mark.integration
class TestBackupRestore:
    def test_backup_and_restore(self, git_repo: Path) -> None:
        git_config.write_local(str(git_repo), "user.email", "original@co.com")
        backup = git_config.backup_local(str(git_repo))
        assert backup.get("user.email") == "original@co.com"

        git_config.write_local(str(git_repo), "user.email", "changed@co.com")
        git_config.restore_local(str(git_repo), backup)
        assert git_config.read_local(str(git_repo), "user.email") == "original@co.com"

    def test_http_username_backup_restore(self, git_repo: Path) -> None:
        git_config.write_local(str(git_repo), "credential.username", "myuser")
        backup = git_config.backup_local(str(git_repo))
        assert backup.get("credential.username") == "myuser"

        git_config.write_local(str(git_repo), "credential.username", "otheruser")
        git_config.restore_local(str(git_repo), backup)
        assert git_config.read_local(str(git_repo), "credential.username") == "myuser"
