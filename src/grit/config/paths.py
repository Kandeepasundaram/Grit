"""Canonical path resolution for all Grit data files.

Every module that needs to read or write Grit data should import from here.
Tests override paths by setting the GRIT_CONFIG_DIR environment variable,
which redirects *all* I/O to a temporary directory without any mocking.
"""

import os
from pathlib import Path

import platformdirs


def _base_dir() -> Path:
    """Return the root config/data directory, honouring GRIT_CONFIG_DIR for tests."""
    override = os.environ.get("GRIT_CONFIG_DIR")
    if override:
        return Path(override)
    return Path(platformdirs.user_config_dir("grit", ensure_exists=False))


def _data_dir() -> Path:
    override = os.environ.get("GRIT_CONFIG_DIR")
    if override:
        return Path(override) / "data"
    return Path(platformdirs.user_data_dir("grit", ensure_exists=False))


def _log_dir() -> Path:
    override = os.environ.get("GRIT_CONFIG_DIR")
    if override:
        return Path(override) / "logs"
    return Path(platformdirs.user_log_dir("grit", ensure_exists=False))


def config_dir() -> Path:
    """~/.config/grit  (or platform equivalent, or GRIT_CONFIG_DIR)."""
    p = _base_dir()
    p.mkdir(parents=True, exist_ok=True)
    return p


def data_dir() -> Path:
    """~/.local/share/grit  (or platform equivalent, or GRIT_CONFIG_DIR/data)."""
    p = _data_dir()
    p.mkdir(parents=True, exist_ok=True)
    return p


def log_dir() -> Path:
    """~/.local/share/grit/logs  (or platform equivalent, or GRIT_CONFIG_DIR/logs)."""
    p = _log_dir()
    p.mkdir(parents=True, exist_ok=True)
    return p


# ── Concrete file paths ──────────────────────────────────────────────────────

def profiles_file() -> Path:
    return config_dir() / "profiles.json"


def sessions_file() -> Path:
    return data_dir() / "sessions.json"


def watched_repos_file() -> Path:
    return data_dir() / "watched_repos.json"


def app_config_file() -> Path:
    return config_dir() / "config.json"


def pid_file() -> Path:
    return data_dir() / "grit.pid"


def ipc_socket_path() -> Path:
    """Unix domain socket path (macOS/Linux only)."""
    return data_dir() / "grit.sock"


def ipc_port_file() -> Path:
    """Windows: file that stores the TCP port the daemon is listening on."""
    return data_dir() / "grit.port"


def audit_log_file() -> Path:
    return data_dir() / "audit.log"


def license_file() -> Path:
    return config_dir() / "license.json"
