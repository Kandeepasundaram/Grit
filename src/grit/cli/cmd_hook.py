"""CLI commands: grit hook <subcommand>

These are internal commands called by installed git hooks, not intended for
direct end-user invocation.
"""

from __future__ import annotations

import sys

import click


@click.group("hook", hidden=True)
def hook() -> None:
    """Internal commands called by installed git hooks."""


@hook.command("pre-commit")
@click.option("--repo", required=True, help="Repository root path.")
def pre_commit(repo: str) -> None:
    """Called by the git pre-commit hook.

    Contacts the daemon to resolve/create a session.  If the daemon is not
    running or no profile is configured, exits non-zero to block the commit
    only when absolutely necessary.
    """
    from grit.exceptions import DaemonNotRunningError
    from grit.ipc.client import send_request

    try:
        resp = send_request("pre-commit", {"repo_path": repo})
    except DaemonNotRunningError:
        # Daemon not running — allow the commit to proceed rather than
        # blocking the developer.  Grit should be transparent.
        sys.exit(0)

    payload = resp.get("payload", {})

    if payload.get("needs_profile"):
        # Ask the user to pick a profile via the UI (tray popup).
        # In Phase 1A/B (no UI yet) we just print a message and allow the commit.
        click.echo(
            "Grit: no profile set for this repository. "
            "Use `grit session set <profile>` to configure one.",
            err=True,
        )
        # Exit 0 to allow commit (non-blocking by default in alpha)
        sys.exit(0)

    session = payload.get("session")
    if session:
        from grit.storage.profile_store import ProfileStore
        try:
            p = ProfileStore().get_by_id(session["profile_id"])
            click.echo(f"Grit: using profile {p.name!r} <{p.email}>", err=True)
        except Exception:
            pass

    sys.exit(0)
