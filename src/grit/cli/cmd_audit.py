"""CLI commands: grit audit <subcommand>

Enterprise audit log viewer and exporter.
"""

from __future__ import annotations

import json
import sys

import click


@click.group("audit")
def audit() -> None:
    """View and export the enterprise audit log."""


@audit.command("show")
@click.option("--since", default=None, metavar="ISO_DATETIME",
              help="Only show entries at or after this ISO timestamp (e.g. 2025-01-01T00:00:00Z).")
@click.option("--action", default=None, metavar="ACTION",
              help="Filter by action type: profile_switch, session_create, git_config_write.")
@click.option("--limit", type=int, default=50, show_default=True,
              help="Maximum number of entries to display.")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON array.")
def show(since: str, action: str, limit: int, as_json: bool) -> None:
    """Display recent audit log entries."""
    from grit.config.subscription import require_pro_installed
    require_pro_installed("audit log")
    from grit.enterprise.audit import export_entries

    entries = export_entries(since=since)

    if action:
        entries = [e for e in entries if e.get("action") == action]

    entries = entries[-limit:]  # most recent N

    if as_json:
        click.echo(json.dumps(entries, indent=2))
        return

    if not entries:
        click.echo("No audit log entries found.")
        return

    for entry in entries:
        ts = entry.get("timestamp", "?")
        act = entry.get("action", "?")
        repo = entry.get("repo_path", "")
        profile = entry.get("profile_name", entry.get("profile_id", ""))
        key = entry.get("key", "")

        if act == "profile_switch":
            click.echo(f"{ts}  profile_switch  {profile!r}  →  {repo}")
        elif act == "session_create":
            click.echo(f"{ts}  session_create  profile={profile or entry.get('profile_id', '?')}  repo={repo}")
        elif act == "git_config_write":
            click.echo(f"{ts}  git_config_write  {key}  →  {repo}")
        else:
            click.echo(f"{ts}  {act}  {json.dumps({k: v for k, v in entry.items() if k not in ('timestamp', 'action')})}")


@audit.command("export")
@click.option("--since", default=None, metavar="ISO_DATETIME",
              help="Only export entries at or after this ISO timestamp.")
@click.option("--format", "fmt", type=click.Choice(["json", "csv", "jsonl"]), default="jsonl",
              show_default=True)
@click.option("--output", "-o", default=None, metavar="FILE",
              help="Write to FILE instead of stdout.")
def export(since: str, fmt: str, output: str) -> None:
    """Export audit log entries to JSON, JSONL, or CSV."""
    from grit.config.subscription import require_pro_installed
    require_pro_installed("audit log")
    import csv
    import io
    from grit.enterprise.audit import export_entries

    entries = export_entries(since=since)

    if fmt == "jsonl":
        lines = "\n".join(json.dumps(e, ensure_ascii=False) for e in entries)
        text = lines + ("\n" if lines else "")
    elif fmt == "json":
        text = json.dumps(entries, indent=2, ensure_ascii=False) + "\n"
    else:  # csv
        buf = io.StringIO()
        fieldnames = ["timestamp", "action", "repo_path", "profile_id", "profile_name", "key"]
        writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore",
                                lineterminator="\n")
        writer.writeheader()
        writer.writerows(entries)
        text = buf.getvalue()

    if output:
        try:
            with open(output, "w", encoding="utf-8") as fh:
                fh.write(text)
            click.echo(f"Exported {len(entries)} entries to {output}")
        except OSError as exc:
            click.echo(f"Error writing {output}: {exc}", err=True)
            sys.exit(1)
    else:
        click.echo(text, nl=False)


@audit.command("clear")
@click.confirmation_option(prompt="This will permanently delete all audit log entries. Continue?")
def clear() -> None:
    """Delete the audit log file (irreversible)."""
    from grit.config.subscription import require_pro_installed
    require_pro_installed("audit log")
    from grit.config.paths import audit_log_file

    path = audit_log_file()
    if path.exists():
        path.unlink()
        click.echo("Audit log cleared.")
    else:
        click.echo("No audit log found.")
