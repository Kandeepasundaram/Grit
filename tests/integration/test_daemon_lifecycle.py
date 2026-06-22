"""Integration tests: daemon start → IPC ping → stop → PID cleanup."""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

import pytest

from grit.daemon import pid as pid_mod
from grit.ipc.client import ping


@pytest.mark.integration
@pytest.mark.slow
def test_daemon_starts_and_responds(tmp_config_dir: Path) -> None:
    """Start the daemon, verify it responds to pings, then stop it cleanly."""
    proc = subprocess.Popen(
        [sys.executable, "-m", "grit.daemon.server"],
        env={**__import__("os").environ, "GRIT_CONFIG_DIR": str(tmp_config_dir)},
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        # Wait up to 5 seconds for the daemon to become ready
        deadline = time.time() + 5
        ready = False
        while time.time() < deadline:
            if ping():
                ready = True
                break
            time.sleep(0.1)
        assert ready, "Daemon did not respond to ping within 5 seconds"

        # Verify PID file was written
        stored_pid = pid_mod.read()
        assert stored_pid is not None
        assert pid_mod.is_running(stored_pid)
    finally:
        proc.terminate()
        proc.wait(timeout=10)

    # After termination, PID file should be gone
    time.sleep(0.5)
    assert not pid_mod.is_running(proc.pid)
