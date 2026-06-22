"""CLI commands: grit enterprise <subcommand>

Enterprise configuration and SSO management.
"""

from __future__ import annotations

import json
import sys

import click


@click.group("enterprise")
def enterprise() -> None:
    """Enterprise configuration and SSO management."""


# ── Config ────────────────────────────────────────────────────────────────────

@enterprise.command("config")
@click.option("--idp-type", type=click.Choice(["saml", "oidc", "none"]), default=None)
@click.option("--idp-url", default=None, help="IdP SSO URL or OIDC issuer URL.")
@click.option("--client-id", default=None, help="OIDC client ID.")
@click.option("--org-id", default=None, help="Organisation identifier.")
@click.option("--org-name", default=None, help="Organisation display name.")
@click.option("--ttl-hours", type=int, default=None, help="SSO session TTL in hours.")
@click.option("--enforce-sso/--no-enforce-sso", default=None,
              help="Block commits without a valid SSO session.")
@click.option("--show", is_flag=True, help="Print current enterprise config.")
@click.option("--json", "as_json", is_flag=True)
def config(
    idp_type, idp_url, client_id, org_id, org_name, ttl_hours,
    enforce_sso, show, as_json
) -> None:
    """Get or set enterprise SSO configuration."""
    from grit.config.subscription import require_pro_installed
    require_pro_installed("enterprise SSO")
    from grit.enterprise.sso import load_enterprise_config, save_enterprise_config
    from dataclasses import asdict

    cfg = load_enterprise_config()

    if show or all(v is None for v in [idp_type, idp_url, client_id, org_id,
                                        org_name, ttl_hours, enforce_sso]):
        if as_json:
            click.echo(json.dumps(asdict(cfg), indent=2))
        else:
            click.echo(f"IdP type:    {cfg.idp_type}")
            click.echo(f"IdP URL:     {cfg.idp_url or '(not set)'}")
            click.echo(f"Client ID:   {cfg.client_id or '(not set)'}")
            click.echo(f"Org:         {cfg.org_name or '(not set)'} ({cfg.org_id or 'no id'})")
            click.echo(f"SSO TTL:     {cfg.sso_ttl_hours}h")
            click.echo(f"Enforce SSO: {cfg.enforce_sso}")
        return

    if idp_type is not None:
        cfg.idp_type = idp_type
    if idp_url is not None:
        cfg.idp_url = idp_url
    if client_id is not None:
        cfg.client_id = client_id
    if org_id is not None:
        cfg.org_id = org_id
    if org_name is not None:
        cfg.org_name = org_name
    if ttl_hours is not None:
        cfg.sso_ttl_hours = ttl_hours
    if enforce_sso is not None:
        cfg.enforce_sso = enforce_sso

    save_enterprise_config(cfg)
    click.echo("Enterprise configuration saved.")


# ── SSO login ─────────────────────────────────────────────────────────────────

@enterprise.command("sso-login")
def sso_login() -> None:
    """Authenticate via enterprise SSO (OIDC or SAML)."""
    from grit.config.subscription import require_pro_installed
    require_pro_installed("enterprise SSO")
    from grit.enterprise.sso import (
        load_enterprise_config, save_sso_session,
        start_oidc_login, poll_oidc_token, get_saml_login_url,
    )
    from grit.exceptions import GritError

    cfg = load_enterprise_config()
    if not cfg.is_configured():
        click.echo(
            "Enterprise SSO is not configured. Run:\n"
            "  grit enterprise config --idp-type oidc --idp-url https://... --org-id myorg",
            err=True,
        )
        sys.exit(1)

    try:
        if cfg.idp_type == "oidc":
            flow = start_oidc_login(cfg)
            click.echo(f"\nOpen this URL in your browser:\n\n  {flow['verification_uri']}\n")
            click.echo(f"Enter code: {flow['user_code']}\n")
            click.echo("Waiting for authorization...", nl=False)
            session = poll_oidc_token(cfg, flow["device_code"], flow.get("interval", 5))
            save_sso_session(session)
            click.echo(f" done!\nLogged in as: {session.user_email}")

        elif cfg.idp_type == "saml":
            url = get_saml_login_url(cfg)
            click.echo(f"\nOpen this SAML SSO URL in your browser:\n\n  {url}\n")
            click.echo("After authenticating, paste the SAMLResponse here:")
            saml_response = click.prompt("SAMLResponse")
            from grit.enterprise.sso import process_saml_response
            session = process_saml_response(cfg, saml_response)
            save_sso_session(session)
            click.echo(f"Authenticated as: {session.user_email}")

    except GritError as exc:
        click.echo(str(exc), err=True)
        sys.exit(1)
    except TimeoutError:
        click.echo("SSO login timed out.", err=True)
        sys.exit(1)


@enterprise.command("sso-status")
@click.option("--json", "as_json", is_flag=True)
def sso_status(as_json: bool) -> None:
    """Show current SSO session status."""
    from grit.config.subscription import require_pro_installed
    require_pro_installed("enterprise SSO")
    from grit.enterprise.sso import load_sso_session, load_enterprise_config

    cfg = load_enterprise_config()
    session = load_sso_session()

    if as_json:
        data = {
            "sso_configured": cfg.is_configured(),
            "idp_type": cfg.idp_type,
            "authenticated": session is not None,
            "email": session.user_email if session else None,
            "expires_at": session.expires_at if session else None,
            "org_id": cfg.org_id,
        }
        click.echo(json.dumps(data, indent=2))
        return

    click.echo(f"SSO configured: {cfg.is_configured()} ({cfg.idp_type})")
    if session:
        click.echo(f"Authenticated:  yes")
        click.echo(f"User:           {session.user_name} <{session.user_email}>")
        click.echo(f"Expires:        {session.expires_at}")
        click.echo(f"Organisation:   {cfg.org_name or cfg.org_id}")
    else:
        click.echo("Authenticated:  no (run `grit enterprise sso-login`)")


@enterprise.command("sso-logout")
def sso_logout() -> None:
    """Clear the current SSO session."""
    from grit.config.subscription import require_pro_installed
    require_pro_installed("enterprise SSO")
    from grit.enterprise.sso import clear_sso_session
    clear_sso_session()
    click.echo("SSO session cleared.")
