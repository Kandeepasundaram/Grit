"""CLI commands: grit config <subcommand>"""

from __future__ import annotations

import json
import sys
from dataclasses import fields as dc_fields

import click

from grit.config.app_config import AppConfig


@click.group("config")
def config() -> None:
    """Get or set Grit application configuration."""


@config.command("get")
@click.argument("key")
@click.option("--json", "as_json", is_flag=True)
def get(key: str, as_json: bool) -> None:
    """Get a configuration value."""
    cfg = AppConfig.load()
    if not hasattr(cfg, key):
        click.echo(f"Unknown config key: {key!r}", err=True)
        sys.exit(1)
    value = getattr(cfg, key)
    if as_json:
        click.echo(json.dumps({key: value}))
    else:
        click.echo(f"{key} = {value}")


@config.command("set")
@click.argument("key")
@click.argument("value")
def set_config(key: str, value: str) -> None:
    """Set a configuration value."""
    cfg = AppConfig.load()
    if not hasattr(cfg, key):
        click.echo(f"Unknown config key: {key!r}", err=True)
        sys.exit(1)
    # Coerce value to the field's type
    field_type = type(getattr(cfg, key))
    try:
        if field_type is bool:
            coerced = value.lower() in ("true", "1", "yes")
        else:
            coerced = field_type(value)
    except (ValueError, TypeError) as exc:
        click.echo(f"Invalid value for {key!r}: {exc}", err=True)
        sys.exit(1)
    setattr(cfg, key, coerced)
    cfg.save()
    click.echo(f"Set {key} = {coerced}")


@config.command("reset")
@click.option("--force", is_flag=True, help="Skip confirmation.")
def reset(force: bool) -> None:
    """Reset all configuration to defaults."""
    if not force:
        click.confirm("Reset all configuration to defaults?", abort=True)
    AppConfig().save()
    click.echo("Configuration reset to defaults.")


@config.command("list")
@click.option("--json", "as_json", is_flag=True)
def list_config(as_json: bool) -> None:
    """Show all configuration values."""
    cfg = AppConfig.load()
    from dataclasses import asdict
    data = asdict(cfg)
    if as_json:
        click.echo(json.dumps(data, indent=2))
        return
    for k, v in data.items():
        click.echo(f"  {k} = {v}")
