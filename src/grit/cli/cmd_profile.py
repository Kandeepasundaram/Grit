"""CLI commands: grit profile <subcommand>"""

from __future__ import annotations

import json
import sys

import click

from grit.exceptions import ProfileExistsError, ProfileNotFoundError
from grit.models.profile import Profile
from grit.storage.profile_store import ProfileStore


@click.group()
def profile() -> None:
    """Manage Git identity profiles."""


def _store() -> ProfileStore:
    return ProfileStore()


def _print_profile(p: Profile, verbose: bool = False) -> None:
    click.echo(f"  Name:     {p.name}")
    click.echo(f"  Email:    {p.email}")
    if p.http_username:
        click.echo(f"  HTTP user:{p.http_username}")
    if p.gpg_key_id:
        click.echo(f"  GPG Key:  {p.gpg_key_id}")
    if p.ssh_key_path:
        click.echo(f"  SSH Key:  {p.ssh_key_path}")
    if p.path_patterns:
        click.echo(f"  Paths:    {', '.join(p.path_patterns)}")
    if p.repo_name_patterns:
        click.echo(f"  Repo names: {', '.join(p.repo_name_patterns)}")
    if p.remote_patterns:
        click.echo(f"  Remotes:  {', '.join(p.remote_patterns)}")
    if p.is_default:
        click.echo("  Default:  yes")
    if verbose:
        click.echo(f"  ID:       {p.id}")
        click.echo(f"  Created:  {p.created_at}")


@profile.command("add")
@click.option("--name", "-n", default=None, help="Profile display name.")
@click.option("--email", "-e", default=None, help="Git author email.")
@click.option("--http-username", default=None, help="GitHub/HTTPS username for this identity.")
@click.option("--gpg-key", default=None, help="GPG signing key ID.")
@click.option("--ssh-key", default=None, help="Path to SSH private key.")
@click.option("--pattern", "-p", multiple=True, help="Path glob pattern (repeatable).")
@click.option("--remote", "-r", multiple=True, help="Remote URL pattern (repeatable).")
@click.option("--repo-name", multiple=True, help="Repo folder-name glob pattern (repeatable).")
def add(
    name: str | None,
    email: str | None,
    http_username: str | None,
    gpg_key: str | None,
    ssh_key: str | None,
    pattern: tuple[str, ...],
    remote: tuple[str, ...],
    repo_name: tuple[str, ...],
) -> None:
    """Create a new profile (interactive if options are omitted)."""
    interactive = not name and not email

    if interactive:
        click.echo("")
        click.echo("New profile — press Enter to skip optional fields.\n")

    # ── Required fields ────────────────────────────────────────────────────────
    if not name:
        while True:
            name = click.prompt("  Profile name (e.g. Work, Personal)").strip()
            if name:
                break
            click.echo("  Name cannot be empty.", err=True)

    if not email:
        while True:
            email = click.prompt("  Git email").strip()
            if email:
                break
            click.echo("  Email cannot be empty.", err=True)

    # ── Optional fields (interactive only) ────────────────────────────────────
    if interactive:
        # HTTP username
        if http_username is None:
            http_username = (
                click.prompt(
                    "  GitHub/HTTPS username (for credential routing)",
                    default="",
                    show_default=False,
                ).strip()
                or None
            )

        # GPG key
        if gpg_key is None:
            _show_gpg_hint()
            gpg_key = click.prompt("  GPG key ID", default="", show_default=False).strip() or None

        # SSH key
        if ssh_key is None:
            ssh_key = click.prompt("  SSH key path", default="", show_default=False).strip() or None

        # Path patterns
        if not pattern:
            click.echo(
                "  Path patterns let Grit auto-apply this profile in matching repos.\n"
                "  Example: ~/work/*    (one per line, empty line to finish)"
            )
            collected: list[str] = []
            while True:
                val = click.prompt("  Path pattern", default="", show_default=False).strip()
                if not val:
                    break
                collected.append(val)
            pattern = tuple(collected)

        # Remote patterns
        if not pattern:  # only ask if no path patterns were entered
            click.echo(
                "  Remote patterns match on the repo's git remote origin URL.\n"
                "  Example: github.com/my-company/*    (empty line to finish)"
            )
            collected = []
            while True:
                val = click.prompt("  Remote pattern", default="", show_default=False).strip()
                if not val:
                    break
                collected.append(val)
            remote = tuple(collected)

        # Summary
        click.echo("")
        click.echo("  Summary:")
        click.echo(f"    Name:     {name}")
        click.echo(f"    Email:    {email}")
        if http_username:
            click.echo(f"    HTTP user:{http_username}")
        if gpg_key:
            click.echo(f"    GPG:      {gpg_key}")
        if ssh_key:
            click.echo(f"    SSH:      {ssh_key}")
        if pattern:
            click.echo(f"    Paths: {', '.join(pattern)}")
        if remote:
            click.echo(f"    Remotes: {', '.join(remote)}")
        click.echo("")
        if not click.confirm("  Create this profile?", default=True):
            click.echo("Cancelled.")
            return

    # ── Save ──────────────────────────────────────────────────────────────────
    p = Profile(
        name=name,
        email=email,
        http_username=http_username,
        gpg_key_id=gpg_key,
        ssh_key_path=ssh_key,
        path_patterns=list(pattern),
        remote_patterns=list(remote),
        repo_name_patterns=list(repo_name),
    )
    store = _store()
    try:
        store.add(p)
    except ValueError as exc:
        # Free tier profile limit reached
        click.echo(str(exc), err=True)
        sys.exit(1)
    except ProfileExistsError as exc:
        click.echo(str(exc), err=True)
        sys.exit(1)
    click.echo(f"\nProfile {name!r} created (id: {p.id[:8]})")
    from grit.config.subscription import warn_profile_limit
    warn_profile_limit(len(store.get_all()))


def _show_gpg_hint() -> None:
    """Print available GPG keys as a hint, silently skip if gpg is not installed."""
    try:
        from grit.git.gpg import list_keys
        keys = list_keys()
        if keys:
            click.echo("  Available GPG keys:")
            for k in keys:
                click.echo(f"    {k['key_id']}  {k.get('uid', '')}")
    except Exception:
        pass


@profile.command("list")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
def list_profiles(as_json: bool) -> None:
    """List all profiles."""
    profiles = _store().get_all()
    if as_json:
        click.echo(json.dumps([p.to_dict() for p in profiles], indent=2))
        return
    if not profiles:
        click.echo("No profiles configured. Use `grit profile add` to create one.")
        return

    # Detect active profile for the current repo (best-effort, silent on failure)
    active_profile_id: str | None = None
    try:
        from grit.git.repo import find_repo_root
        from grit.storage.session_store import SessionStore
        repo = find_repo_root()
        if repo:
            session = SessionStore().get(repo)
            if session:
                active_profile_id = session.profile_id
    except Exception:
        pass

    for p in profiles:
        active = p.id == active_profile_id
        marker = " (active)" if active else ""
        click.echo(f"\n[{p.name}]{marker}")
        _print_profile(p)

    from grit.config.subscription import load_license
    lic = load_license()
    if lic.tier == "free" and lic.profile_limit != -1:
        used = len(profiles)
        click.echo(f"\n{used}/{lic.profile_limit} profiles used (free tier). "
                   "Grit Pro (coming soon) removes this limit — kandeepasundaram+GRIT@gmail.com")


@profile.command("show")
@click.argument("name")
@click.option("--json", "as_json", is_flag=True)
def show(name: str, as_json: bool) -> None:
    """Show details of a single profile."""
    try:
        p = _store().get_by_name(name)
    except ProfileNotFoundError as exc:
        click.echo(str(exc), err=True)
        sys.exit(1)
    if as_json:
        click.echo(json.dumps(p.to_dict(), indent=2))
        return
    click.echo(f"\n[{p.name}]")
    _print_profile(p, verbose=True)


@profile.command("delete")
@click.argument("name")
@click.option("--force", is_flag=True, help="Skip confirmation prompt.")
def delete(name: str, force: bool) -> None:
    """Delete a profile."""
    store = _store()
    try:
        p = store.get_by_name(name)
    except ProfileNotFoundError as exc:
        click.echo(str(exc), err=True)
        sys.exit(1)
    if not force:
        click.confirm(f"Delete profile {name!r}?", abort=True)

    was_default = p.is_default
    from grit.storage.session_store import SessionStore
    session_store = SessionStore()
    affected_repos = session_store.find_pinned_repos_for_profile(p.id)
    for repo_path in affected_repos:
        session_store.delete(repo_path)

    store.delete(p.id)

    if was_default:
        click.echo(
            f"Warning: {name!r} was the default profile; no default is set now.",
            err=True,
        )
    if affected_repos:
        click.echo(
            f"Warning: removed the pin on {len(affected_repos)} "
            f"repo(s) that were pinned to {name!r}: {', '.join(affected_repos)}",
            err=True,
        )
    click.echo(f"Profile {name!r} deleted.")


@profile.command("set-default")
@click.argument("name")
def set_default(name: str) -> None:
    """Mark a profile as the fallback default when nothing else matches."""
    store = _store()
    try:
        p = store.get_by_name(name)
    except ProfileNotFoundError as exc:
        click.echo(str(exc), err=True)
        sys.exit(1)
    store.set_default(p.id)
    click.echo(f"Profile {name!r} set as default.")


@profile.command("unset-default")
def unset_default() -> None:
    """Clear the default profile, if any."""
    _store().clear_default()
    click.echo("Default profile cleared.")


@profile.command("edit")
@click.argument("name")
@click.option("--new-name", default=None, help="Rename the profile.")
@click.option("--email", default=None, help="New email address.")
@click.option("--http-username", default=None, help="GitHub/HTTPS username (use '' to clear).")
@click.option("--gpg-key", default=None, help="New GPG key ID (use '' to clear).")
@click.option("--ssh-key", default=None, help="New SSH key path (use '' to clear).")
@click.option("--add-pattern", multiple=True, help="Add path pattern.")
@click.option("--add-remote", multiple=True, help="Add remote pattern.")
@click.option("--add-repo-name", multiple=True, help="Add repo folder-name pattern.")
def edit(
    name: str,
    new_name: str | None,
    email: str | None,
    http_username: str | None,
    gpg_key: str | None,
    ssh_key: str | None,
    add_pattern: tuple[str, ...],
    add_remote: tuple[str, ...],
    add_repo_name: tuple[str, ...],
) -> None:
    """Edit an existing profile."""
    store = _store()
    try:
        p = store.get_by_name(name)
    except ProfileNotFoundError as exc:
        click.echo(str(exc), err=True)
        sys.exit(1)

    if new_name:
        p.name = new_name
    if email:
        p.email = email
    if http_username is not None:
        p.http_username = http_username or None
    if gpg_key is not None:
        p.gpg_key_id = gpg_key or None
    if ssh_key is not None:
        p.ssh_key_path = ssh_key or None
    if add_pattern:
        p.path_patterns = list(set(p.path_patterns) | set(add_pattern))
    if add_remote:
        p.remote_patterns = list(set(p.remote_patterns) | set(add_remote))
    if add_repo_name:
        p.repo_name_patterns = list(set(p.repo_name_patterns) | set(add_repo_name))

    store.update(p)
    click.echo(f"Profile {p.name!r} updated.")
