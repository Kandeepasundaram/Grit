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
    from pathlib import Path

    repo_path = _safe_repo_path(payload.get("repo_path", ""))
    session = _engine.resolve(repo_path)

    if session is None:
        # No session — show the profile picker so the user can choose one now.
        loop = asyncio.get_event_loop()
        profiles = ProfileStore().get_all()
        repo_name = Path(repo_path).name
        from grit.ui.popup import show_profile_picker
        profile_id = await loop.run_in_executor(
            None, show_profile_picker, repo_name, profiles
        )
        if profile_id is None:
            return {"session": None, "needs_profile": True}
        session = _engine.create(repo_path, profile_id)
        return {"session": session.to_dict(), "needs_profile": False}

    # Re-apply on every commit so git config stays in sync even if edited manually.
    _engine.apply(session)
    return {"session": session.to_dict(), "needs_profile": False}


# ── Daemon lifecycle ──────────────────────────────────────────────────────────

def _setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )


async def _run(stop_event: asyncio.Event) -> None:
    global _engine
    config = AppConfig.load()
    _engine = SessionEngine(app_config=config)
    purged = _engine.startup_purge()
    if purged:
        log.info("Purged %d expired session(s) on startup", purged)

    from grit.daemon.watchdog import start_watchdog
    await asyncio.gather(
        ipc_server.start_server(stop_event),
        start_watchdog(stop_event),
    )


def main() -> None:
    """Entry point for the `gritd` command."""
    import argparse
    import threading

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
    asyncio_stop = asyncio.Event()
    tray_stop = threading.Event()

    def _on_signal(*_: object) -> None:
        log.info("Received shutdown signal")
        loop.call_soon_threadsafe(asyncio_stop.set)

    from grit.ui.tray import run_tray

    if sys.platform == "win32":
        # Win32 message loop must be on the main thread; asyncio runs in a thread.
        # proc.terminate() on Windows uses TerminateProcess (not SIGTERM), so the
        # signal handler is only needed for interactive Ctrl-C.
        signal.signal(signal.SIGINT, _on_signal)

        def _run_asyncio_win() -> None:
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(_run(asyncio_stop))
            finally:
                pid_mod.clear()
                loop.close()
                tray_stop.set()
                log.info("Grit daemon stopped")

        asyncio_thread = threading.Thread(target=_run_asyncio_win, daemon=True, name="grit-asyncio")
        asyncio_thread.start()
        run_tray(tray_stop)
        loop.call_soon_threadsafe(asyncio_stop.set)
        asyncio_thread.join(timeout=10)

    else:
        # POSIX (macOS/Linux): asyncio on main thread so loop.add_signal_handler()
        # fires reliably on SIGTERM even while the event loop is in a C wait call.
        # Tray runs in a daemon thread (best-effort; skipped on headless systems).
        asyncio.set_event_loop(loop)
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, _on_signal)

        tray_thread = threading.Thread(
            target=run_tray, args=(tray_stop,), daemon=True, name="grit-tray"
        )
        tray_thread.start()

        try:
            loop.run_until_complete(_run(asyncio_stop))
        finally:
            pid_mod.clear()
            loop.close()
            tray_stop.set()
            tray_thread.join(timeout=5)
            log.info("Grit daemon stopped")


if __name__ == "__main__":
    main()
