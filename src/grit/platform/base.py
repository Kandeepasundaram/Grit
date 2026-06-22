"""Abstract base class for platform-specific operations."""

from __future__ import annotations

from abc import ABC, abstractmethod


class PlatformBase(ABC):
    """Interface for platform-specific daemon lifecycle operations."""

    @abstractmethod
    def install_autostart(self) -> None:
        """Register the daemon to start on system/user login."""

    @abstractmethod
    def uninstall_autostart(self) -> None:
        """Remove the daemon from autostart."""

    @abstractmethod
    def is_autostart_installed(self) -> bool:
        """Return True if autostart is configured."""


def get_platform() -> PlatformBase:
    """Return the correct PlatformBase implementation for the current OS."""
    import sys
    if sys.platform == "darwin":
        from grit.platform.macos import MacOSPlatform
        return MacOSPlatform()
    elif sys.platform == "win32":
        from grit.platform.windows import WindowsPlatform
        return WindowsPlatform()
    else:
        from grit.platform.linux import LinuxPlatform
        return LinuxPlatform()
