"""Git configuration read/write utilities."""

from __future__ import annotations

import subprocess
from typing import Dict, List, Optional

from grit.exceptions import GitCommandError
from grit.models.profile import Profile

import logging as _logging

_log = _logging.getLogger(__name__)


def _audit_config_write(repo_path: str, key: str) -> None:
    try:
        from grit.enterprise.audit import log_git_config_write
        log_git_config_write(repo_path, key)
    except Exception:  # noqa: BLE001
        pass


def _git(*args: str, cwd: Optional[str] = None, check: bool = True) -> str:
    """Run a git command and return its stdout.  Raises GitCommandError on failure."""
    cmd = ["git"] + list(args)
    try:
        result = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, check=check
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as exc:
        raise GitCommandError(cmd, exc.returncode, exc.stderr) from exc
    except FileNotFoundError as exc:
        raise GitCommandError(cmd, -1, "git executable not found") from exc


# ── Read ─────────────────────────────────────────────────────────────────────

def read_local(repo_path: str, key: str) -> Optional[str]:
    """Read a key from the repo's local git config.  Returns None if unset."""
    try:
        return _git("config", "--local", key, cwd=repo_path) or None
    except GitCommandError as exc:
        if exc.returncode == 1:
            return None  # key not set
        raise


def read_global(key: str) -> Optional[str]:
    """Read a key from the global git config.  Returns None if unset."""
    try:
        return _git("config", "--global", key) or None
    except GitCommandError as exc:
        if exc.returncode == 1:
            return None
        raise


# ── Write ─────────────────────────────────────────────────────────────────────

def write_local(repo_path: str, key: str, value: str) -> None:
    _git("config", "--local", key, value, cwd=repo_path)


def write_global(key: str, value: str) -> None:
    _git("config", "--global", key, value)


def unset_local(repo_path: str, key: str) -> None:
    """Remove a key from the local git config.  No-op if already absent."""
    try:
        _git("config", "--local", "--unset", key, cwd=repo_path)
    except GitCommandError as exc:
        if exc.returncode == 5:
            return  # key was not set — that's fine
        raise


# ── Backup / restore ──────────────────────────────────────────────────────────

_PROFILE_KEYS = ["user.name", "user.email", "user.signingkey", "commit.gpgsign", "core.sshCommand", "credential.username"]


def backup_local(repo_path: str) -> Dict[str, str]:
    """Read all profile-related local git config values before Grit touches them."""
    result: Dict[str, str] = {}
    for key in _PROFILE_KEYS:
        value = read_local(repo_path, key)
        if value is not None:
            result[key] = value
    return result


def restore_local(repo_path: str, backup: Dict[str, str]) -> None:
    """Restore a backup produced by :func:`backup_local`."""
    for key in _PROFILE_KEYS:
        if key in backup:
            write_local(repo_path, key, backup[key])
        else:
            unset_local(repo_path, key)


# ── Profile application ───────────────────────────────────────────────────────

def apply_profile(repo_path: str, profile: Profile) -> None:
    """Write *profile* settings into *repo_path*'s local git config."""
    write_local(repo_path, "user.name", profile.name)
    write_local(repo_path, "user.email", profile.email)
    _audit_config_write(repo_path, "user.name")
    _audit_config_write(repo_path, "user.email")

    if profile.gpg_key_id:
        write_local(repo_path, "user.signingkey", profile.gpg_key_id)
        write_local(repo_path, "commit.gpgsign", "true")
        _audit_config_write(repo_path, "user.signingkey")
    else:
        unset_local(repo_path, "user.signingkey")
        unset_local(repo_path, "commit.gpgsign")

    if profile.ssh_key_path:
        import shlex
        ssh_cmd = f"ssh -i {shlex.quote(profile.ssh_key_path)} -o IdentitiesOnly=yes"
        write_local(repo_path, "core.sshCommand", ssh_cmd)
        _audit_config_write(repo_path, "core.sshCommand")
    else:
        unset_local(repo_path, "core.sshCommand")

    if profile.http_username:
        write_local(repo_path, "credential.username", profile.http_username)
        _audit_config_write(repo_path, "credential.username")
    else:
        unset_local(repo_path, "credential.username")
