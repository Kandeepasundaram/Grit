"""GPG key utilities for profile signing configuration."""

from __future__ import annotations

import subprocess


def list_keys() -> list[dict[str, str]]:
    """Return secret GPG keys available to the current user.

    Each dict has keys: ``key_id``, ``fingerprint``, ``uid`` (name + email).
    Returns an empty list if gpg is not installed or no keys exist.
    """
    try:
        result = subprocess.run(
            ["gpg", "--list-secret-keys", "--with-colons"],
            capture_output=True, text=True, check=False,
        )
    except FileNotFoundError:
        return []  # gpg not installed

    keys: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for line in result.stdout.splitlines():
        parts = line.split(":")
        if not parts:
            continue
        record_type = parts[0]
        if record_type == "sec":
            # New secret key block
            current = {"key_id": parts[4] if len(parts) > 4 else "", "fingerprint": ""}
        elif record_type == "fpr" and current:
            current["fingerprint"] = parts[9] if len(parts) > 9 else ""
        elif record_type == "uid" and current:
            current["uid"] = parts[9] if len(parts) > 9 else ""
            keys.append(dict(current))
            current = {}
    return keys


def configure_signing(repo_path: str, key_id: str) -> None:
    """Enable GPG signing with *key_id* for *repo_path*."""
    from grit.git.config import write_local
    write_local(repo_path, "user.signingkey", key_id)
    write_local(repo_path, "commit.gpgsign", "true")


def clear_signing(repo_path: str) -> None:
    """Remove GPG signing configuration from *repo_path*."""
    from grit.git.config import unset_local
    unset_local(repo_path, "user.signingkey")
    unset_local(repo_path, "commit.gpgsign")
