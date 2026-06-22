"""Application-wide constants."""

import sys

APP_NAME = "grit"
APP_VERSION = "0.1.0-alpha"

# IPC
if sys.platform == "win32":
    IPC_PIPE_NAME = r"\\.\pipe\grit-daemon"
    IPC_ADDRESS: object = IPC_PIPE_NAME
else:
    IPC_SOCKET_FILENAME = "grit.sock"
    IPC_ADDRESS = None  # resolved at runtime via paths.data_dir()

# Storage filenames
PROFILES_FILENAME = "profiles.json"
SESSIONS_FILENAME = "sessions.json"
WATCHED_REPOS_FILENAME = "watched_repos.json"
APP_CONFIG_FILENAME = "config.json"
LICENSE_FILENAME = "license.json"
AUDIT_LOG_FILENAME = "audit.log"
PID_FILENAME = "grit.pid"

# Git hook
GRIT_HOOK_SENTINEL = "# GRIT_HOOK_v1"

# Session defaults
DEFAULT_SESSION_TTL_SECONDS = 8 * 60 * 60  # 8 hours

# Profile limits (free tier — Phase 2)
FREE_TIER_MAX_PROFILES = 5

# Performance budgets (milliseconds) — used in benchmarks
PERF_IPC_ROUNDTRIP_MS = 50
PERF_PROFILE_SWITCH_MS = 500
PERF_POPUP_DISPLAY_MS = 200
PERF_DAEMON_STARTUP_S = 3
