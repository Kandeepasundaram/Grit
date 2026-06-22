"""SSH key utilities for per-profile git operations."""

from __future__ import annotations


def get_ssh_command(key_path: str) -> str:
    """Return the GIT_SSH_COMMAND value for a given private key path."""
    return f"ssh -i {key_path} -o IdentitiesOnly=yes"


def write_ssh_config(repo_path: str, key_path: str) -> None:
    """Set core.sshCommand in the repo's local git config."""
    from grit.git.config import write_local
    write_local(repo_path, "core.sshCommand", get_ssh_command(key_path))


def clear_ssh_config(repo_path: str) -> None:
    """Remove core.sshCommand from the repo's local git config."""
    from grit.git.config import unset_local
    unset_local(repo_path, "core.sshCommand")
