"""Grit exception hierarchy."""

from __future__ import annotations


class GritError(Exception):
    """Base exception for all Grit errors."""


class ProfileNotFoundError(GritError):
    """Raised when a requested profile does not exist."""

    def __init__(self, identifier: str) -> None:
        super().__init__(f"Profile not found: {identifier!r}")
        self.identifier = identifier


class ProfileExistsError(GritError):
    """Raised when creating a profile whose name already exists."""

    def __init__(self, name: str) -> None:
        super().__init__(f"A profile named {name!r} already exists")
        self.name = name


class SessionExpiredError(GritError):
    """Raised when a session has expired and cannot be used."""

    def __init__(self, repo_path: str) -> None:
        super().__init__(f"Session expired for repository: {repo_path}")
        self.repo_path = repo_path


class DaemonNotRunningError(GritError):
    """Raised when the IPC client cannot reach the daemon."""

    def __init__(self) -> None:
        super().__init__(
            "Grit daemon is not running. Start it with: grit daemon start"
        )


class DaemonAlreadyRunningError(GritError):
    """Raised when trying to start a daemon that is already running."""

    def __init__(self, pid: int) -> None:
        super().__init__(f"Grit daemon is already running (PID {pid})")
        self.pid = pid


class GitCommandError(GritError):
    """Raised when a git subprocess command fails."""

    def __init__(self, cmd: list[str], returncode: int, stderr: str = "") -> None:
        cmd_str = " ".join(str(c) for c in cmd)
        msg = f"Git command failed (exit {returncode}): {cmd_str}"
        if stderr:
            msg += f"\n{stderr.strip()}"
        super().__init__(msg)
        self.cmd = cmd
        self.returncode = returncode
        self.stderr = stderr


class StorageCorruptError(GritError):
    """Raised when a storage file cannot be parsed."""

    def __init__(self, path: str, detail: str = "") -> None:
        msg = f"Storage file is corrupt or invalid: {path}"
        if detail:
            msg += f" ({detail})"
        super().__init__(msg)
        self.path = path


class HookInstallError(GritError):
    """Raised when a git hook cannot be installed or removed."""


class IPCProtocolError(GritError):
    """Raised when an IPC message cannot be encoded or decoded."""
