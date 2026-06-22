"""CLI commands: grit credential <subcommand>

Manages per-profile HTTPS credentials in the OS credential store so that
git push/pull authenticates as the right GitHub account when a Grit session
is active.
"""

from __future__ import annotations

import sys

import click

from grit.exceptions import GritError, ProfileNotFoundError
from grit.models.profile import Profile
from grit.storage.profile_store import ProfileStore


@click.group()
def credential() -> None:
    """Manage HTTPS credentials for Git profiles."""


def _store() -> ProfileStore:
    return ProfileStore()


def _require_http_username(profile_name: str) -> tuple[Profile, str]:
    """Load profile and return (profile, http_username), exiting on error."""
    store = _store()
    try:
        p = store.get_by_name(profile_name)
    except ProfileNotFoundError as exc:
        click.echo(str(exc), err=True)
        sys.exit(1)

    if not p.http_username:
        click.echo(
            f"Profile {profile_name!r} has no HTTP username set.\n"
            f"Set one first with:\n\n"
            f"  grit profile edit {profile_name} --http-username <your-github-username>\n",
            err=True,
        )
        sys.exit(1)

    return p, p.http_username


@credential.command("login")
@click.argument("profile_name", metavar="PROFILE")
@click.option(
    "--host", default="github.com", show_default=True, help="Git host to authenticate with."
)
def login(profile_name: str, host: str) -> None:
    """Open a browser to authenticate with GitHub and store the credential.

    Triggers GitHub's device flow: a browser tab opens with the authorization
    code pre-filled so you just need to click Authorize.
    """
    from grit.git.credentials import github_browser_login, store_credential

    p, username = _require_http_username(profile_name)

    click.echo(f"Authenticating profile {profile_name!r} ({username}@{host}) via browser...")
    try:
        token = github_browser_login(username_hint=username)
    except GritError as exc:
        click.echo(str(exc), err=True)
        sys.exit(1)

    try:
        store_credential(host, username, token)
    except GritError as exc:
        click.echo(f"Failed to store credential: {exc}", err=True)
        sys.exit(1)

    click.echo(f"Authorized as {username} — credential stored.")
    click.echo(f"\nNext time you run `grit session set {profile_name}`, git push will")
    click.echo(f"authenticate as {username} automatically.")


@credential.command("set")
@click.argument("profile_name", metavar="PROFILE")
@click.option("--token", required=True, prompt=True, hide_input=True, help="Personal access token.")
@click.option("--host", default="github.com", show_default=True, help="Git host.")
def set_credential(profile_name: str, token: str, host: str) -> None:
    """Store a Personal Access Token for a profile (manual alternative to login).

    Use `grit credential login` for the browser-based flow instead.
    """
    from grit.git.credentials import store_credential

    p, username = _require_http_username(profile_name)

    try:
        store_credential(host, username, token)
    except GritError as exc:
        click.echo(f"Failed to store credential: {exc}", err=True)
        sys.exit(1)

    click.echo(f"Credential stored for {username}@{host}.")


@credential.command("clear")
@click.argument("profile_name", metavar="PROFILE")
@click.option("--host", default="github.com", show_default=True, help="Git host.")
def clear(profile_name: str, host: str) -> None:
    """Remove the stored credential for a profile."""
    from grit.git.credentials import delete_credential

    p, username = _require_http_username(profile_name)

    delete_credential(host, username)
    click.echo(f"Credential for {username}@{host} cleared.")


@credential.command("show")
@click.argument("profile_name", metavar="PROFILE")
@click.option("--host", default="github.com", show_default=True, help="Git host.")
def show(profile_name: str, host: str) -> None:
    """Show whether a credential is stored for a profile (never shows the value)."""
    from grit.git.credentials import has_credential

    store = _store()
    try:
        p = store.get_by_name(profile_name)
    except ProfileNotFoundError as exc:
        click.echo(str(exc), err=True)
        sys.exit(1)

    click.echo(f"\n[{p.name}]")
    click.echo(f"  HTTP user:         {p.http_username or '(not set)'}")
    click.echo(f"  Host:              {host}")

    if not p.http_username:
        click.echo("  Credential stored: N/A (no HTTP username configured)")
        return

    stored = has_credential(host, p.http_username)
    click.echo(f"  Credential stored: {'Yes' if stored else 'No'}")
    if not stored:
        click.echo(f"\n  Run `grit credential login {profile_name}` to authenticate.")
