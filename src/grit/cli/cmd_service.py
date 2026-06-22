"""CLI commands: grit service <subcommand>

Windows Service management for enterprise multi-user deployments.
Only meaningful on Windows with pywin32 installed.
"""

from __future__ import annotations

import sys

import click


def _check_windows() -> None:
    if sys.platform != "win32":
        click.echo("The 'grit service' commands are only available on Windows.", err=True)
        sys.exit(1)


@click.group("service")
def service() -> None:
    """Manage the Grit Windows NT Service (enterprise, requires elevation)."""


@service.command("install")
def install() -> None:
    """Install the Grit daemon as a Windows Service (run as Administrator)."""
    _check_windows()
    try:
        from grit.platform.windows_service import install_service, PROGRAMDATA_DIR
        install_service()
        click.echo(f"GritDaemon service installed.  Data directory: {PROGRAMDATA_DIR}")
        click.echo("Run  grit service start  to start the service.")
    except RuntimeError as exc:
        click.echo(str(exc), err=True)
        sys.exit(1)
    except Exception as exc:
        click.echo(f"Installation failed: {exc}", err=True)
        sys.exit(1)


@service.command("uninstall")
@click.confirmation_option(prompt="Remove the GritDaemon Windows Service?")
def uninstall() -> None:
    """Remove the Grit Windows Service (run as Administrator)."""
    _check_windows()
    try:
        from grit.platform.windows_service import stop_service, uninstall_service, query_service_status
        status = query_service_status()
        if status == "running":
            click.echo("Stopping service...")
            stop_service()
        uninstall_service()
        click.echo("GritDaemon service removed.")
    except RuntimeError as exc:
        click.echo(str(exc), err=True)
        sys.exit(1)
    except Exception as exc:
        click.echo(f"Uninstall failed: {exc}", err=True)
        sys.exit(1)


@service.command("start")
def start() -> None:
    """Start the GritDaemon Windows Service."""
    _check_windows()
    try:
        from grit.platform.windows_service import start_service
        start_service()
        click.echo("GritDaemon service started.")
    except RuntimeError as exc:
        click.echo(str(exc), err=True)
        sys.exit(1)
    except Exception as exc:
        click.echo(f"Start failed: {exc}", err=True)
        sys.exit(1)


@service.command("stop")
def stop() -> None:
    """Stop the GritDaemon Windows Service."""
    _check_windows()
    try:
        from grit.platform.windows_service import stop_service
        stop_service()
        click.echo("GritDaemon service stopped.")
    except RuntimeError as exc:
        click.echo(str(exc), err=True)
        sys.exit(1)
    except Exception as exc:
        click.echo(f"Stop failed: {exc}", err=True)
        sys.exit(1)


@service.command("status")
def status() -> None:
    """Show the status of the GritDaemon Windows Service."""
    _check_windows()
    from grit.platform.windows_service import query_service_status
    result = query_service_status()
    if result is None:
        click.echo("GritDaemon service: not installed")
    else:
        click.echo(f"GritDaemon service: {result}")
