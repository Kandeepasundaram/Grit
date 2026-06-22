"""Windows autostart support — registry Run key."""

from __future__ import annotations

import contextlib
import sys

from grit.platform.base import PlatformBase

_REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_REG_VALUE = "GritDaemon"


class WindowsPlatform(PlatformBase):
    def install_autostart(self) -> None:
        if sys.platform != "win32":
            raise RuntimeError("winreg not available — are you running on Windows?")
        import winreg

        cmd = f'"{sys.executable}" -m grit.daemon.server'
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, _REG_KEY, 0, winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(key, _REG_VALUE, 0, winreg.REG_SZ, cmd)
        winreg.CloseKey(key)

    def uninstall_autostart(self) -> None:
        if sys.platform != "win32":
            return
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, _REG_KEY, 0, winreg.KEY_SET_VALUE
        )
        with contextlib.suppress(FileNotFoundError):
            winreg.DeleteValue(key, _REG_VALUE)
        winreg.CloseKey(key)

    def is_autostart_installed(self) -> bool:
        if sys.platform != "win32":
            return False
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
