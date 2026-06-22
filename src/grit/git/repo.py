"""Git repository discovery utilities."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional


def find_repo_root(cwd: Optional[str] = None) -> Optional[str]:
    """Return the canonical absolute path of the git repo root containing *cwd*.

    Handles regular repos and git worktrees.  Returns None if *cwd* is not
    inside a git repository.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        )
        return str(Path(result.stdout.strip()).resolve())
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return None


def get_repo_name(repo_path: str) -> str:
    """Return the directory name of the repository (last path component)."""
    return Path(repo_path).name


def is_git_repo(path: str) -> bool:
    """Return True if *path* is inside (or at the root of) a git repository."""
    return find_repo_root(path) is not None


def get_remote_url(repo_path: str, remote: str = "origin") -> Optional[str]:
    """Return the URL of *remote* for the repository, or None if not set."""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", remote],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip() or None
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return None
