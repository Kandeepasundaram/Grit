"""Unit tests for git/hook.py — uses a real git repo."""

from __future__ import annotations

from pathlib import Path

import pytest

from grit.constants import GRIT_HOOK_SENTINEL
from grit.git.hook import install, uninstall, is_installed
from grit.exceptions import HookInstallError


@pytest.mark.integration
class TestInstall:
    def test_installs_hook(self, git_repo: Path) -> None:
        install(str(git_repo))
        assert is_installed(str(git_repo))

    @pytest.mark.skipif(
        __import__("sys").platform == "win32",
        reason="Windows does not support POSIX execute bits",
    )
    def test_hook_file_is_executable(self, git_repo: Path) -> None:
        install(str(git_repo))
        import stat
        mode = (git_repo / ".git" / "hooks" / "pre-commit").stat().st_mode
        assert mode & stat.S_IXUSR

    def test_idempotent_install(self, git_repo: Path) -> None:
        install(str(git_repo))
        install(str(git_repo))  # second call should not duplicate
        content = (git_repo / ".git" / "hooks" / "pre-commit").read_text()
        assert content.count(GRIT_HOOK_SENTINEL) == 1

    def test_appends_to_existing_hook(self, git_repo: Path) -> None:
        hook_file = git_repo / ".git" / "hooks" / "pre-commit"
        hook_file.write_text("#!/usr/bin/env sh\necho existing\n", encoding="utf-8")
        install(str(git_repo))
        content = hook_file.read_text()
        assert "echo existing" in content
        assert GRIT_HOOK_SENTINEL in content

    def test_raises_on_missing_hooks_dir(self, tmp_path: Path) -> None:
        with pytest.raises(HookInstallError):
            install(str(tmp_path))


@pytest.mark.integration
class TestUninstall:
    def test_uninstall_removes_hook_file(self, git_repo: Path) -> None:
        install(str(git_repo))
        uninstall(str(git_repo))
        assert not is_installed(str(git_repo))

    def test_uninstall_preserves_existing_content(self, git_repo: Path) -> None:
        hook_file = git_repo / ".git" / "hooks" / "pre-commit"
        hook_file.write_text("#!/usr/bin/env sh\necho existing\n", encoding="utf-8")
        install(str(git_repo))
        uninstall(str(git_repo))
        content = hook_file.read_text()
        assert "echo existing" in content
        assert GRIT_HOOK_SENTINEL not in content

    def test_uninstall_when_not_installed_is_noop(self, git_repo: Path) -> None:
        uninstall(str(git_repo))  # should not raise
