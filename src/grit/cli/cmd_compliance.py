"""CLI commands: grit compliance <subcommand>

Enterprise compliance reporting.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click


@click.group("compliance")
def compliance() -> None:
    """Enterprise compliance checks and reporting."""


@compliance.command("report")
@click.option("--since", default=None, metavar="ISO_DATETIME",
              help="Include audit events since this ISO timestamp.")
@click.option("--output", "-o", default=None, metavar="FILE",
              help="Write JSON report to FILE (default: print to stdout).")
@click.option("--json", "as_json", is_flag=True, help="Always output raw JSON.")
def report(since: str, output: str, as_json: bool) -> None:
    """Generate a compliance report (hooks, GPG, SSO, audit summary)."""
    from grit.enterprise.compliance import generate_report, write_report

    if output:
        path = Path(output)
        data = write_report(path, since=since)
        click.echo(f"Report written to {output} (compliant={data['compliant']})")
        if not data["compliant"]:
            sys.exit(1)
        return

    data = generate_report(since=since)

    if as_json:
        click.echo(json.dumps(data, indent=2))
        return

    click.echo(f"Compliance report — {data['generated_at']}")
    click.echo(f"Overall: {'PASS' if data['compliant'] else 'FAIL'}")
    click.echo("")

    hooks = data["sections"].get("hook_inventory", {})
    click.echo(
        f"Hook inventory:  {hooks.get('hooks_installed', '?')}/"
        f"{hooks.get('total_repos', '?')} repos have Grit hook"
    )
    if hooks.get("missing_repos"):
        for r in hooks["missing_repos"]:
            click.echo(f"  MISSING  {r}")

    gpg = data["sections"].get("gpg_enforcement", {})
    click.echo(
        f"GPG signing:     {gpg.get('gpg_enabled', '?')}/"
        f"{gpg.get('total_profiles', '?')} profiles have GPG key"
    )
    if gpg.get("profiles_without_gpg"):
        for name in gpg["profiles_without_gpg"]:
            click.echo(f"  NO GPG   {name}")

    sso = data["sections"].get("sso_compliance", {})
    click.echo(
        f"SSO:             configured={sso.get('sso_configured', '?')}  "
        f"enforce={sso.get('enforce_sso', '?')}  "
        f"active_session={sso.get('active_sso_session', '?')}"
    )

    audit = data["sections"].get("audit_summary", {})
    click.echo(f"Audit events:    {audit.get('total_events', 0)} total")
    for action, count in audit.get("by_action", {}).items():
        click.echo(f"  {action}: {count}")

    if not data["compliant"]:
        sys.exit(1)


@compliance.command("hooks")
def hooks() -> None:
    """Check Grit hook installation across all watched repositories."""
    from grit.enterprise.compliance import check_hook_inventory

    result = check_hook_inventory()
    status = "OK" if result["hooks_missing"] == 0 else "FAIL"
    click.echo(
        f"[{status}] {result['hooks_installed']}/{result['total_repos']} repos have hook installed"
    )
    for repo in result.get("missing_repos", []):
        click.echo(f"  MISSING: {repo}")
    if result["hooks_missing"]:
        sys.exit(1)


@compliance.command("gpg")
def gpg() -> None:
    """Check GPG signing configuration across all profiles."""
    from grit.enterprise.compliance import check_gpg_enforcement

    result = check_gpg_enforcement()
    status = "OK" if result["gpg_missing"] == 0 else "WARN"
    click.echo(
        f"[{status}] {result['gpg_enabled']}/{result['total_profiles']} profiles have GPG key"
    )
    for name in result.get("profiles_without_gpg", []):
        click.echo(f"  NO GPG: {name}")
