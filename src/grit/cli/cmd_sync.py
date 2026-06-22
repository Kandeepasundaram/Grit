"""CLI commands: grit sync <subcommand> (Pro tier)"""

from __future__ import annotations

import json
import sys

import click


@click.group("sync")
def sync() -> None:
    """Sync profiles with Grit Cloud (Pro/Enterprise)."""


@sync.command("push")
@click.option("--profiles", "include_profiles", is_flag=True, default=True,
              help="Push profiles (default: on).")
@click.option("--sessions", "include_sessions", is_flag=True, default=False,
              help="Also push active sessions.")
def push(include_profiles: bool, include_sessions: bool) -> None:
    """Upload local data to Grit Cloud."""
    from grit.config.subscription import require_pro_installed
    require_pro_installed("cloud sync")
    from grit.cloud.client import AuthRequiredError, OfflineError
    from grit.cloud.sync import SyncEngine

    engine = SyncEngine()
    try:
        if include_profiles:
            n = engine.push_profiles()
            click.echo(f"Pushed {n} profile(s) to cloud.")
        if include_sessions:
            n = engine.push_sessions()
            click.echo(f"Pushed {n} session(s) to cloud.")
    except AuthRequiredError as exc:
        click.echo(str(exc), err=True)
        sys.exit(1)
    except OfflineError as exc:
        click.echo(str(exc), err=True)
        sys.exit(1)
    except ValueError as exc:
        # Pro feature gate
        click.echo(str(exc), err=True)
        sys.exit(1)


@sync.command("pull")
@click.option("--team", "include_team", is_flag=True, default=False,
              help="Also pull team profiles from your organization.")
def pull(include_team: bool) -> None:
    """Download profiles from Grit Cloud."""
    from grit.config.subscription import require_pro_installed
    require_pro_installed("cloud sync")
    from grit.cloud.client import AuthRequiredError, OfflineError
    from grit.cloud.sync import SyncEngine

    engine = SyncEngine()
    try:
        n = engine.pull_profiles()
        click.echo(f"Pulled {n} new/updated profile(s) from cloud.")
        if include_team:
            n = engine.pull_team_profiles()
            click.echo(f"Fetched {n} team profile(s).")
    except AuthRequiredError as exc:
        click.echo(str(exc), err=True)
        sys.exit(1)
    except OfflineError as exc:
        click.echo(str(exc), err=True)
        sys.exit(1)
    except ValueError as exc:
        click.echo(str(exc), err=True)
        sys.exit(1)


@sync.command("status")
@click.option("--json", "as_json", is_flag=True)
def status(as_json: bool) -> None:
    """Show sync configuration and last sync time."""
    from grit.config.subscription import require_pro_installed
    require_pro_installed("cloud sync")
    from grit.cloud.auth import load_tokens
    from grit.cloud.sync import get_team_profiles
    from grit.config.app_config import AppConfig
    from grit.config.subscription import load_license

    cfg = AppConfig.load()
    lic = load_license()
    tokens = load_tokens()
    team = get_team_profiles()

    data = {
        "cloud_sync_enabled": cfg.cloud_sync_enabled,
        "sync_interval_seconds": cfg.cloud_sync_interval_seconds,
        "authenticated": tokens is not None,
        "tier": lic.tier,
        "cloud_sync_allowed": lic.allows_cloud_sync(),
        "team_profiles_cached": len(team),
    }

    if as_json:
        click.echo(json.dumps(data, indent=2))
        return

    click.echo(f"Cloud sync:    {'enabled' if cfg.cloud_sync_enabled else 'disabled'}")
    click.echo(f"Authenticated: {'yes' if tokens else 'no'}")
    click.echo(f"Tier:          {lic.tier.upper()}")
    click.echo(f"Sync allowed:  {'yes' if lic.allows_cloud_sync() else 'no (requires Pro)'}")
    click.echo(f"Team profiles: {len(team)} cached")
    if not lic.allows_cloud_sync():
        click.echo(
            "\nGrit Pro (coming soon) unlocks cloud sync — "
            "pre-register: kandeepasundaram+GRIT@gmail.com"
        )


@sync.command("team")
@click.option("--json", "as_json", is_flag=True)
def team(as_json: bool) -> None:
    """List team profiles from your organisation."""
    from grit.config.subscription import require_pro_installed
    require_pro_installed("team profiles")
    from grit.cloud.sync import get_team_profiles

    profiles = get_team_profiles()
    if as_json:
        click.echo(json.dumps([p.to_dict() for p in profiles], indent=2))
        return
    if not profiles:
        click.echo("No team profiles. Run `grit sync pull --team` to fetch them.")
        return
    for p in profiles:
        click.echo(f"  [{p.name}]  {p.email}  (read-only)")
