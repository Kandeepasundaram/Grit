"""PID file management for the Grit daemon."""

from __future__ import annotations

import contextlib
import os

import psutil

from grit.config.paths import pid_file


def write(pid: int | None = None) -> None:
    """Write the current (or given) PID to the PID file."""
    path = pid_file()
    path.write_text(str(pid or os.getpid()), encoding="utf-8")


def read() -> int | None:
    """Return the PID stored in the PID file, or None if it doesn't exist."""
    path = pid_file()
    if not path.exists():
        return None
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except (ValueError, OSError):
        return None


def clear() -> None:
    """Remove the PID file."""
    path = pid_file()
    with contextlib.suppress(FileNotFoundError):
        path.unlink()


def is_running(pid: int | None = None) -> bool:
    """Return True if *pid* (or the PID in the PID file) belongs to a live process."""
    target = pid if pid is not None else read()
    if target is None:
        return False
    try:
        proc = psutil.Process(target)
        # On POSIX a zombie process still has a PID; check its status
        return proc.status() != psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess:
        return False


def get_running_pid() -> int | None:
    """Return the daemon PID if it is currently running, else None."""
    pid = read()
    if pid and is_running(pid):
        return pid
    return None
