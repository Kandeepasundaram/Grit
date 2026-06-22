"""Linux autostart support — XDG autostart + systemd user unit."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from grit.platform.base import PlatformBase

_DESKTOP_ENTRY = """\
[Desktop Entry]
Type=Application
Name=Grit Daemon
Comment=Session-based Git profile manager
Exec={exec_path}
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
"""

_SYSTEMD_UNIT = """\
[Unit]
Description=Grit Git Profile Manager Daemon
After=network.target

[Service]
Type=simple
ExecStart={exec_path}
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=default.target
"""


class LinuxPlatform(PlatformBase):
    @property
    def _exec_path(self) -> str:
        return sys.executable + " -m grit.daemon.server"

    @property
    def _desktop_path(self) -> Path:
        return Path.home() / ".config" / "autostart" / "grit.desktop"

    @property
    def _systemd_path(self) -> Path:
        return Path.home() / ".config" / "systemd" / "user" / "grit.service"

    def install_autostart(self) -> None:
        # Prefer systemd if available
        if self._systemd_available():
            self._install_systemd()
        else:
            self._install_xdg()

    def uninstall_autostart(self) -> None:
        if self._systemd_path.exists():
            self._uninstall_systemd()
        if self._desktop_path.exists():
            self._desktop_path.unlink()

    def is_autostart_installed(self) -> bool:
        return self._desktop_path.exists() or self._systemd_path.exists()

    def _systemd_available(self) -> bool:
        try:
            result = subprocess.run(
                ["systemctl", "--user", "is-system-running"],
                capture_output=True, check=False,
            )
            return result.returncode in (0, 1)  # 0=running, 1=degraded
        except FileNotFoundError:
            return False

    def _install_xdg(self) -> None:
        self._desktop_path.parent.mkdir(parents=True, exist_ok=True)
        self._desktop_path.write_text(
            _DESKTOP_ENTRY.format(exec_path=self._exec_path), encoding="utf-8"
        )

    def _install_systemd(self) -> None:
        self._systemd_path.parent.mkdir(parents=True, exist_ok=True)
        self._systemd_path.write_text(
            _SYSTEMD_UNIT.format(exec_path=self._exec_path), encoding="utf-8"
        )
        subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)
        subprocess.run(["systemctl", "--user", "enable", "grit.service"], check=False)

    def _uninstall_systemd(self) -> None:
        subprocess.run(["systemctl", "--user", "disable", "grit.service"], check=False)
        self._systemd_path.unlink(missing_ok=True)
