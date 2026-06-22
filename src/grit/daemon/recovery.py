"""Crash detection and state integrity helpers.

Actual process supervision is handled by the platform's native mechanism
(launchd KeepAlive, systemd Restart=on-failure, Windows service).  This
module provides helpers for detecting stale state after a crash and ensuring
data integrity.
"""

from __future__ import annotations

import logging

from grit.daemon import pid as pid_mod

log = logging.getLogger(__name__)


def detect_stale_state() -> bool:
    """Return True if there is a PID file with a dead process (crash indicator)."""
    stored_pid = pid_mod.read()
    if stored_pid is None:
        return False
    return not pid_mod.is_running(stored_pid)


def clean_stale_state() -> None:
    """Remove PID file and socket left by a crashed daemon."""
    if detect_stale_state():
        log.warning("Detected stale daemon state — cleaning up")
        pid_mod.clear()
        # Remove stale socket file
        try:
            import sys
            if sys.platform != "win32":
                from grit.config.paths import ipc_socket_path
                sock = ipc_socket_path()
                if sock.exists():
                    sock.unlink()
                    log.info("Removed stale IPC socket: %s", sock)
        except Exception as exc:
            log.debug("Could not remove stale socket: %s", exc)
