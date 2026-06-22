"""CLI commands: grit daemon <subcommand>"""

from __future__ import annotations

import json
import subprocess
import sys

import click

from grit.daemon import pid as pid_mod
from grit.exceptions import DaemonNotRunningError


@click.group()
def daemon() -> None:
    """Control the Grit background daemon."""


@daemon.command("start")
@click.option("--foreground", "-f", is_flag=True, help="Run in foreground (don't daemonise).")
@click.option("--verbose", "-v", is_flag=True)
def start(foreground: bool, verbose: bool) -> None:
    """Start the Grit daemon."""
    running = pid_mod.get_running_pid()
    if running:
        click.echo(f"Daemon already running (PID {running}).")
        return

    cmd = [sys.executable, "-m", "grit.daemon.server"]
    if verbose:
        cmd.append("--verbose")

    if foreground:
        import os
        os.execv(sys.executable, cmd)  # replace current process
    else:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        click.echo(f"Daemon started (PID {proc.pid}).")


@daemon.command("stop")
def stop() -> None:
    """Stop the running daemon."""
    import os
    import signal as sig_mod
    running = pid_mod.get_running_pid()
    if not running:
        click.echo("Daemon is not running.")
        return
    try:
        os.kill(running, sig_mod.SIGTERM)
        click.echo(f"Sent SIGTERM to daemon (PID {running}).")
    except OSError as exc:
        click.echo(f"Could not stop daemon: {exc}", err=True)
        sys.exit(1)


@daemon.command("status")
@click.option("--json", "as_json", is_flag=True)
def status(as_json: bool) -> None:
    """Show daemon status."""
    from grit.ipc.client import send_request
    running = pid_mod.get_running_pid()
    if not running:
        if as_json:
            click.echo(json.dumps({"running": False}))
        else:
            click.echo("Daemon is not running.")
        sys.exit(2)
    try:
        resp = send_request("daemon-status")
        info = resp.get("payload", {})
    except DaemonNotRunningError:
        info = {}

    if as_json:
        click.echo(json.dumps({"running": True, **info}))
        return
    click.echo(f"Daemon running (PID {running})")
    if info:
        click.echo(f"  Version:         {info.get('version', '?')}")
        click.echo(f"  Active sessions: {info.get('active_sessions', '?')}")
        click.echo(f"  Profiles:        {info.get('profile_count', '?')}")


@daemon.command("restart")
@click.pass_context
def restart(ctx: click.Context) -> None:
    """Restart the daemon (stop then start)."""
    import time
    ctx.invoke(stop)
    # SIGTERM is asynchronous — wait until the process is actually gone
    for _ in range(50):  # up to 5 seconds
        time.sleep(0.1)
        if not pid_mod.get_running_pid():
            break
    else:
        click.echo("Timed out waiting for daemon to stop.", err=True)
        sys.exit(1)
    ctx.invoke(start)
