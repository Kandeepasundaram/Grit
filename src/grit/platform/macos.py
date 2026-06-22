"""macOS autostart support — LaunchAgent plist."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from grit.platform.base import PlatformBase

_PLIST_LABEL = "com.grit.daemon"

_PLIST_TEMPLATE = """\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{label}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python}</string>
        <string>-m</string>
        <string>grit.daemon.server</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>{log_dir}/gritd.log</string>
    <key>StandardErrorPath</key>
    <string>{log_dir}/gritd.err</string>
</dict>
</plist>
"""


class MacOSPlatform(PlatformBase):
    @property
    def _plist_path(self) -> Path:
        return (
            Path.home()
            / "Library"
            / "LaunchAgents"
            / f"{_PLIST_LABEL}.plist"
        )

    def _log_dir(self) -> str:
        from grit.config.paths import log_dir
        return str(log_dir())

    def install_autostart(self) -> None:
        self._plist_path.parent.mkdir(parents=True, exist_ok=True)
        self._plist_path.write_text(
            _PLIST_TEMPLATE.format(
                label=_PLIST_LABEL,
                python=sys.executable,
                log_dir=self._log_dir(),
            ),
            encoding="utf-8",
        )
        subprocess.run(
            ["launchctl", "load", str(self._plist_path)], check=False
        )

    def uninstall_autostart(self) -> None:
        if self._plist_path.exists():
            subprocess.run(
                ["launchctl", "unload", str(self._plist_path)], check=False
            )
            self._plist_path.unlink()

    def is_autostart_installed(self) -> bool:
        return self._plist_path.exists()
