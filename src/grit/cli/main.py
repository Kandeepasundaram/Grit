"""Root CLI entry point for the `grit` command."""

from __future__ import annotations

import os

import click

from grit import __version__


@click.group()
@click.version_option(__version__, prog_name="grit")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output.")
@click.option(
    "--config-dir",
    envvar="GRIT_CONFIG_DIR",
    default=None,
    metavar="PATH",
    help="Override the Grit config directory (default: platform-specific).",
)
@click.pass_context
def cli(ctx: click.Context, verbose: bool, config_dir: str) -> None:
    """Grit — session-based Git profile manager."""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    if config_dir:
        os.environ["GRIT_CONFIG_DIR"] = config_dir

    if verbose:
        import logging
        logging.basicConfig(level=logging.DEBUG)


@cli.command("about")
def about() -> None:
    """Show information about Grit."""
    from grit import __version__
    from grit.config.subscription import load_license, pro_is_installed

    lic = load_license()

    click.echo(f"""
  Grit  v{__version__}
  Session-based Git profile manager

  Commit as the right person, every time. Grit runs as a background
  daemon and automatically applies the correct Git identity (name,
  email, GPG key, SSH key) per repository using session memory and
  git hooks — no more wrong-account commits.

  Plan:       {lic.tier.upper()}{"  (grit-pro installed)" if pro_is_installed() else ""}
  Free tier:  up to 5 profiles, local only
  Coming soon: Grit Pro — cloud sync, team profiles & more

  License:    MIT (open source)
  Contact:    kandeepasundaram+GRIT@gmail.com

  Commands:
    grit profile add        create a Git identity profile
    grit session set NAME   activate a profile in the current repo
    grit daemon start       start the background daemon
    grit upgrade            compare Free / Pro / Enterprise features
""")


@cli.command("upgrade")
def upgrade() -> None:
    """Show what's available at each Grit tier."""
    from grit.config.subscription import load_license, pro_is_installed

    lic = load_license()
    tier = lic.tier
    pro = pro_is_installed()

    def _row(label: str, free: bool, pro_: bool, ent: bool) -> None:
        def _mark(ok: bool) -> str:
            return "+" if ok else "-"
        click.echo(f"  {_mark(free)}  {_mark(pro_)}  {_mark(ent)}  {label}")

    click.echo("")
    click.echo(f"  Current plan: {tier.upper()}" + (" (grit-pro installed)" if pro else ""))
    click.echo("")
    click.echo("        FREE   PRO   ENT")
    click.echo("  " + "-" * 46)
    _row("Up to 5 profiles",                   True,  False, False)
    _row("Unlimited profiles",                  False, True,  True)
    _row("Git hooks & session management",      True,  True,  True)
    _row("System tray + desktop notifications", True,  True,  True)
    _row("Cloud sync across machines",          False, True,  True)
    _row("Team profiles (org-wide, read-only)", False, True,  True)
    _row("SSO login (OIDC / SAML)",             False, False, True)
    _row("Audit logs (SIEM-ready)",             False, False, True)
    _row("Compliance reporting",                False, False, True)
    _row("Windows Service (multi-user)",        False, False, True)
    click.echo("")
    click.echo("  Grit Pro and Enterprise are coming soon.")
    click.echo("  Pre-register to be notified at launch:")
    click.echo("    kandeepasundaram+GRIT@gmail.com")
    click.echo("")


# Import and register sub-commands
from grit.cli.cmd_audit import audit  # noqa: E402
from grit.cli.cmd_auth import auth  # noqa: E402
from grit.cli.cmd_compliance import compliance  # noqa: E402
from grit.cli.cmd_config import config  # noqa: E402
from grit.cli.cmd_credential import credential  # noqa: E402
from grit.cli.cmd_daemon import daemon  # noqa: E402
from grit.cli.cmd_enterprise import enterprise  # noqa: E402
from grit.cli.cmd_hook import hook  # noqa: E402
from grit.cli.cmd_profile import profile  # noqa: E402
from grit.cli.cmd_service import service  # noqa: E402
from grit.cli.cmd_session import session  # noqa: E402
from grit.cli.cmd_setup import setup  # noqa: E402
from grit.cli.cmd_sync import sync  # noqa: E402

cli.add_command(profile)
cli.add_command(session)
cli.add_command(daemon)
cli.add_command(config)
cli.add_command(hook)
cli.add_command(setup)
cli.add_command(auth)
cli.add_command(sync)
cli.add_command(enterprise)
cli.add_command(audit)
cli.add_command(compliance)
cli.add_command(service)
cli.add_command(credential)
