"""Windows autostart support — registry Run key."""

from __future__ import annotations

import sys
from pathlib import Path

from grit.platform.base import PlatformBase

_REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_REG_VALUE = "GritDaemon"


class WindowsPlatform(PlatformBase):
    def install_autostart(self) -> None:
        try:
            import winreg
            cmd = f'"{sys.executable}" -m grit.daemon.server'
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, _REG_KEY, 0, winreg.KEY_SET_VALUE
            )
            winreg.SetValueEx(key, _REG_VALUE, 0, winreg.REG_SZ, cmd)
            winreg.CloseKey(key)
        except ImportError:
            raise RuntimeError("winreg not available — are you running on Windows?")

    def uninstall_autostart(self) -> None:
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, _REG_KEY, 0, winreg.KEY_SET_VALUE
            )
            try:
                winreg.DeleteValue(key, _REG_VALUE)
            except FileNotFoundError:
                pass
            winreg.CloseKey(key)
        except ImportError:
            pass

    def is_autostart_installed(self) -> bool:
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, _REG_KEY, 0, winreg.KEY_READ
            )
            try:
                winreg.QueryValueEx(key, _REG_VALUE)
                winreg.CloseKey(key)
                return True
            except FileNotFoundError:
                winreg.CloseKey(key)
                return False
        except ImportError:
            return False
