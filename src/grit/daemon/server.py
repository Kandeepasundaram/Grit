"""Grit daemon entry point (gritd).

Starts the asyncio event loop, registers IPC handlers, launches the
filesystem watchdog, and manages the PID file lifecycle.
"""

from __future__ import annotations

import asyncio
import logging
import signal
import sys
from typing import Any

from grit.config.app_config import AppConfig
from grit.daemon import pid as pid_mod
from grit.exceptions import DaemonAlreadyRunningError
from grit.ipc import server as ipc_server
from grit.ipc.server import register
from grit.session.engine import SessionEngine
from grit.storage.profile_store import ProfileStore
from grit.storage.session_store import SessionStore

log = logging.getLogger(__name__)

# Module-level engine — set up in main() before the loop starts
_engine: SessionEngine


# ── IPC Handlers ─────────────────────────────────────────────────────────────

def _safe_repo_path(raw: str) -> str:
    """Resolve and validate a repo_path from an IPC payload."""
    from pathlib import Path
    if not raw:
        raise ValueError("repo_path is required")
    resolved = str(Path(raw).resolve())
    if not Path(resolved).is_dir():
        raise ValueError(f"Not a valid directory: {raw!r}")
    return resolved


@register("ping")
async def handle_ping(payload: dict[str, Any]) -> dict[str, Any]:
    return {"pong": True}


@register("daemon-status")
async def handle_status(payload: dict[str, Any]) -> dict[str, Any]:
    import os

    from grit import __version__
    sessions = SessionStore().get_all()
    profiles = ProfileStore().get_all()
    return {
        "version": __version__,
        "pid": os.getpid(),
        "active_sessions": len(sessions),
        "profile_count": len(profiles),
    }


@register("get-session")
async def handle_get_session(payload: dict[str, Any]) -> dict[str, Any]:
    repo_path = _safe_repo_path(payload.get("repo_path", ""))
    session = _engine.resolve(repo_path)
    if session is None:
        return {"session": None}
    return {"session": session.to_dict()}


@register("set-session")
async def handle_set_session(payload: dict[str, Any]) -> dict[str, Any]:
    repo_path = _safe_repo_path(payload.get("repo_path", ""))
    profile_id: str = payload["profile_id"]
    session = _engine.create(repo_path, profile_id)
    return {"session": session.to_dict()}


@register("delete-session")
async def handle_delete_session(payload: dict[str, Any]) -> dict[str, Any]:
    repo_path = _safe_repo_path(payload.get("repo_path", ""))
    _engine.invalidate(repo_path)
    return {}


@register("list-sessions")
async def handle_list_sessions(payload: dict[str, Any]) -> dict[str, Any]:
    sessions = SessionStore().get_all()
    return {"sessions": [s.to_dict() for s in sessions]}


@register("list-profiles")
async def handle_list_profiles(payload: dict[str, Any]) -> dict[str, Any]:
    profiles = ProfileStore().get_all()
    return {"profiles": [p.to_dict() for p in profiles]}


@register("switch-profile")
async def handle_switch_profile(payload: dict[str, Any]) -> dict[str, Any]:
    repo_path = _safe_repo_path(payload.get("repo_path", ""))
    profile_id: str = payload["profile_id"]
    _engine.invalidate(repo_path)
    session = _engine.create(repo_path, profile_id)
    return {"session": session.to_dict()}


@register("pre-commit")
async def handle_pre_commit(payload: dict[str, Any]) -> dict[str, Any]:
    """Called by the git pre-commit hook via the CLI bridge."""
    repo_path = _safe_repo_path(payload.get("repo_path", ""))
    session = _engine.resolve(repo_path)
    if session is None:
        # Signal that the hook should prompt the user (UI layer handles this)
        return {"session": None, "needs_profile": True}
    return {"session": session.to_dict(), "needs_profile": False}


# ── Daemon lifecycle ──────────────────────────────────────────────────────────

def _setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )


async def _run(stop_event: asyncio.Event, verbose: bool = False) -> None:
    global _engine
    config = AppConfig.load()
    _engine = SessionEngine(app_config=config)
    purged = _engine.startup_purge()
    if purged:
        log.info("Purged %d expired session(s) on startup", purged)

    # Start IPC server concurrently with the watchdog
    from grit.daemon.watchdog import start_watchdog
    await asyncio.gather(
        ipc_server.start_server(stop_event),
        start_watchdog(stop_event),
    )


def main() -> None:
    """Entry point for the `gritd` command."""
    import argparse

    parser = argparse.ArgumentParser(prog="gritd", description="Grit daemon")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    _setup_logging(args.verbose)

    # Guard against double-start
    running_pid = pid_mod.get_running_pid()
    if running_pid:
        raise DaemonAlreadyRunningError(running_pid)

    pid_mod.write()
    log.info("Grit daemon starting (PID %d)", pid_mod.read())

    loop = asyncio.new_event_loop()
    stop_event = asyncio.Event()

    def _on_signal() -> None:
        log.info("Received shutdown signal")
        loop.call_soon_threadsafe(stop_event.set)

    if sys.platform != "win32":
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, _on_signal)
    else:
        signal.signal(signal.SIGTERM, lambda *_: _on_signal())
        signal.signal(signal.SIGINT, lambda *_: _on_signal())

    try:
        loop.run_until_complete(_run(stop_event, verbose=args.verbose))
    finally:
        pid_mod.clear()
        loop.close()
        log.info("Grit daemon stopped")


if __name__ == "__main__":
    main()
