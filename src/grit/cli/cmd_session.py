"""CLI commands: grit session <subcommand>"""

from __future__ import annotations

import json
import os
import sys
from typing import Optional

import click

from grit.exceptions import DaemonNotRunningError


def _ipc(msg_type: str, payload: dict = None) -> dict:
    from grit.ipc.client import send_request
    return send_request(msg_type, payload or {})


def _current_repo() -> Optional[str]:
    from grit.git.repo import find_repo_root
    return find_repo_root(os.getcwd())


@click.group()
def session() -> None:
    """Manage per-repository Git profile sessions."""


@session.command("show")
@click.option("--repo", default=None, help="Repository path (defaults to current directory).")
@click.option("--json", "as_json", is_flag=True)
def show(repo: Optional[str], as_json: bool) -> None:
    """Show the active session for a repository."""
    repo_path = repo or _current_repo()
    if not repo_path:
        click.echo("Not inside a git repository.", err=True)
        sys.exit(1)
    try:
        resp = _ipc("get-session", {"repo_path": repo_path})
    except DaemonNotRunningError as exc:
        click.echo(str(exc), err=True)
        sys.exit(2)

    s = resp.get("payload", {}).get("session")
    if s is None:
        click.echo(f"No active session for {repo_path}")
        return
    if as_json:
        click.echo(json.dumps(s, indent=2))
        return
    from grit.storage.profile_store import ProfileStore
    try:
        p = ProfileStore().get_by_id(s["profile_id"])
        profile_label = f"{p.name} <{p.email}>"
    except Exception:
        profile_label = s["profile_id"]
    click.echo(f"Repository: {repo_path}")
    click.echo(f"Profile:    {profile_label}")
    click.echo(f"Expires:    {s['expires_at']}")
    if s.get("locked"):
        click.echo("Status:     LOCKED")


@session.command("set")
@click.argument("profile_name")
@click.option("--repo", default=None, help="Repository path (defaults to current directory).")
def set_session(profile_name: str, repo: Optional[str]) -> None:
    """Set (or switch) the active profile for a repository."""
    repo_path = repo or _current_repo()
    if not repo_path:
        click.echo("Not inside a git repository.", err=True)
        sys.exit(1)
    from grit.storage.profile_store import ProfileStore
    from grit.exceptions import ProfileNotFoundError
    try:
        p = ProfileStore().get_by_name(profile_name)
    except ProfileNotFoundError as exc:
        click.echo(str(exc), err=True)
        sys.exit(1)
    try:
        _ipc("switch-profile", {"repo_path": repo_path, "profile_id": p.id})
    except DaemonNotRunningError as exc:
        click.echo(str(exc), err=True)
        sys.exit(2)
    click.echo(f"Switched to profile {profile_name!r} for {repo_path}")


@session.command("clear")
@click.option("--repo", default=None, help="Repository path.")
@click.option("--all", "all_repos", is_flag=True, help="Clear all sessions.")
def clear(repo: Optional[str], all_repos: bool) -> None:
    """Invalidate session(s)."""
    if all_repos:
        try:
            _ipc("delete-session", {"repo_path": ""})  # empty path = server handles all
        except DaemonNotRunningError as exc:
            click.echo(str(exc), err=True)
            sys.exit(2)
        click.echo("All sessions cleared.")
        return

    repo_path = repo or _current_repo()
    if not repo_path:
        click.echo("Not inside a git repository.", err=True)
        sys.exit(1)
    try:
        _ipc("delete-session", {"repo_path": repo_path})
    except DaemonNotRunningError as exc:
        click.echo(str(exc), err=True)
        sys.exit(2)
    click.echo(f"Session cleared for {repo_path}")


@session.command("list")
@click.option("--json", "as_json", is_flag=True)
def list_sessions(as_json: bool) -> None:
    """List all active sessions."""
    try:
        resp = _ipc("list-sessions")
    except DaemonNotRunningError as exc:
        click.echo(str(exc), err=True)
        sys.exit(2)

    sessions = resp.get("payload", {}).get("sessions", [])
    if as_json:
        click.echo(json.dumps(sessions, indent=2))
        return
    if not sessions:
        click.echo("No active sessions.")
        return

    from grit.storage.profile_store import ProfileStore
    store = ProfileStore()
    for s in sessions:
        try:
            p = store.get_by_id(s["profile_id"])
            label = f"{p.name} <{p.email}>"
        except Exception:
            label = s["profile_id"]
        locked = " [LOCKED]" if s.get("locked") else ""
        click.echo(f"  {s['repo_path']}")
        click.echo(f"    Profile: {label}{locked}")
        click.echo(f"    Expires: {s['expires_at']}")
