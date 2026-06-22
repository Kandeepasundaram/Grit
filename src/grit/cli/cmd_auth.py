"""CLI commands: grit auth <subcommand>

Manages cloud authentication for Grit Pro / Enterprise features.
Uses device-flow OAuth2 so users never type passwords into the terminal.
"""

from __future__ import annotations

import json
import sys

import click


@click.group("auth")
def auth() -> None:
    """Authenticate with Grit Cloud for Pro/Enterprise features."""


@auth.command("login")
@click.option("--provider", type=click.Choice(["github", "google"]), default="github",
              help="OAuth provider to use.")
def login(provider: str) -> None:
    """Log in to Grit Cloud via browser-based device flow."""
    from grit.config.subscription import require_pro_installed
    require_pro_installed("Grit Cloud login")
    from grit.cloud.auth import start_device_flow, poll_device_flow, save_tokens

    click.echo(f"Starting device-flow login with {provider}...")
    try:
        flow = start_device_flow(provider)
    except Exception as exc:
        click.echo(f"Login failed: {exc}", err=True)
        sys.exit(1)

    click.echo(f"\nOpen this URL in your browser:\n\n  {flow['verification_uri']}\n")
    click.echo(f"Enter code: {flow['user_code']}\n")
    click.echo("Waiting for authorization...", nl=False)

    try:
        tokens = poll_device_flow(provider, flow["device_code"], flow["interval"])
    except TimeoutError:
        click.echo("\nLogin timed out. Please try again.")
        sys.exit(1)
    except Exception as exc:
        click.echo(f"\nLogin failed: {exc}", err=True)
        sys.exit(1)

    save_tokens(tokens)
    click.echo(" done!")

    # Fetch and store license
    try:
        from grit.cloud.client import GritCloudClient
        client = GritCloudClient()
        license_data = client.get_license_status()
        from grit.config.subscription import save_license
        save_license(license_data["token"], license_data["claims"])
        tier = license_data["claims"].get("tier", "free")
        click.echo(f"Logged in. Plan: {tier.upper()}")
    except Exception as exc:
        click.echo(f"Could not fetch license: {exc}", err=True)


@auth.command("logout")
def logout() -> None:
    """Log out and remove stored credentials."""
    from grit.config.subscription import require_pro_installed
    require_pro_installed("Grit Cloud login")
    from grit.cloud.auth import clear_tokens
    from grit.config.subscription import clear_license
    clear_tokens()
    clear_license()
    click.echo("Logged out. Grit will operate in free tier mode.")


@auth.command("status")
@click.option("--json", "as_json", is_flag=True)
def status(as_json: bool) -> None:
    """Show current authentication and subscription status."""
    from grit.config.subscription import require_pro_installed
    require_pro_installed("Grit Cloud login")
    from grit.cloud.auth import load_tokens
    from grit.config.subscription import load_license

    tokens = load_tokens()
    lic = load_license()

    if as_json:
        data = {
            "authenticated": tokens is not None,
            "tier": lic.tier,
            "email": lic.email,
            "expires_at": lic.expires_at,
            "is_valid": lic.is_valid,
            "in_grace_period": lic.is_in_grace_period,
        }
        click.echo(json.dumps(data, indent=2))
        return

    if not tokens:
        click.echo("Not logged in. Run `grit auth login` to authenticate.")
    else:
        click.echo(f"Logged in as: {lic.email or 'unknown'}")

    click.echo(f"Plan:         {lic.tier.upper()}")
    click.echo(f"Expires:      {lic.expires_at}")
    if lic.is_in_grace_period:
        click.echo("  (License expired — within 30-day grace period)")
    elif not lic.is_valid:
        click.echo("  (License expired — operating in free tier)")
    click.echo(f"Profile limit: {'unlimited' if lic.profile_limit == -1 else lic.profile_limit}")
    click.echo(f"Cloud sync:   {'yes' if lic.allows_cloud_sync() else 'no (Pro)'}")
    click.echo(f"Team profiles:{'yes' if lic.allows_team_profiles() else 'no (Pro)'}")
