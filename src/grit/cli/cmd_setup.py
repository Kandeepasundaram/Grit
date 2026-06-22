"""grit setup — first-run onboarding wizard."""

from __future__ import annotations

import sys

import click

from grit.config.app_config import AppConfig
from grit.config.paths import config_dir, data_dir, log_dir


@click.command("setup")
@click.option("--no-autostart", is_flag=True, help="Skip installing daemon autostart.")
def setup(no_autostart: bool) -> None:
    """Run the first-time setup wizard."""
    click.echo("Welcome to Grit — session-based Git profile manager\n")

    # 1. Create config directories
    config_dir()
    data_dir()
    log_dir()
    click.echo("✓ Config directories created")

    # 2. Create default config if absent
    cfg_file = config_dir() / "config.json"
    if not cfg_file.exists():
        AppConfig().save()
        click.echo("✓ Default configuration written")

    # 3. Create first profile
    click.echo("\nLet's create your first profile.")
    name = click.prompt("Profile name (e.g. Work)")
    email = click.prompt("Git email address")
    gpg = click.prompt("GPG signing key ID (leave blank to skip)", default="")
    ssh = click.prompt("SSH private key path (leave blank to skip)", default="")
    pattern = click.prompt(
        "Repository path pattern (e.g. ~/work/*, leave blank to skip)", default=""
    )

    from grit.exceptions import ProfileExistsError
    from grit.models.profile import Profile
    from grit.storage.profile_store import ProfileStore

    profile = Profile(
        name=name,
        email=email,
        gpg_key_id=gpg or None,
        ssh_key_path=ssh or None,
        path_patterns=[pattern] if pattern else [],
    )
    try:
        ProfileStore().add(profile)
        click.echo(f"✓ Profile {name!r} created")
    except ProfileExistsError:
        click.echo(f"  Profile {name!r} already exists — skipping")

    # 4. Install autostart
    if not no_autostart:
        try:
            from grit.platform.base import get_platform
            platform = get_platform()
            if not platform.is_autostart_installed():
                platform.install_autostart()
                click.echo("✓ Daemon autostart installed")
            else:
                click.echo("  Daemon autostart already configured")
        except Exception as exc:
            click.echo(f"  Could not install autostart: {exc}", err=True)

    # 5. Start the daemon
    if click.confirm("\nStart the Grit daemon now?", default=True):
        from grit.daemon import pid as pid_mod
        if pid_mod.get_running_pid():
            click.echo("  Daemon already running.")
        else:
            import subprocess
            subprocess.Popen(
                [sys.executable, "-m", "grit.daemon.server"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            click.echo("✓ Daemon started")

    click.echo("\nSetup complete! Run `grit profile list` to see your profiles.")
    click.echo("Use `grit session set <profile>` in a repository to activate a profile.")
    click.echo("")
    click.echo("Free tier: up to 5 profiles, local only.")
    click.echo("Grit Pro is coming soon — unlimited profiles, cloud sync, team profiles & more.")
    click.echo("  grit upgrade              → see full feature comparison")
    click.echo("  Pre-register for launch:  kandeepasundaram+GRIT@gmail.com")
