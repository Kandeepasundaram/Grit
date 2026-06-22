"""Windows NT Service wrapper for the Grit daemon.

Allows Grit to run as a Windows Service under the NETWORK SERVICE account,
with data stored in %PROGRAMDATA%\\Grit — suitable for enterprise multi-user
environments where the daemon must start before any user logs in.

Requires: pywin32 (`pip install pywin32`)

Usage (elevated prompt):
    python -m grit.platform.windows_service install
    python -m grit.platform.windows_service start
    python -m grit.platform.windows_service stop
    python -m grit.platform.windows_service remove

Or via the CLI:
    grit service install|uninstall|start|stop|status
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

SERVICE_NAME = "GritDaemon"
SERVICE_DISPLAY_NAME = "Grit Git Profile Daemon"
SERVICE_DESCRIPTION = (
    "Manages per-repository Git identities (name, email, GPG, SSH) "
    "for all users on this machine.  Required for enterprise Grit deployments."
)

# Data directory under %PROGRAMDATA% (e.g. C:\ProgramData\Grit)
PROGRAMDATA_DIR: Path = Path(os.environ.get("PROGRAMDATA", "C:\\ProgramData")) / "Grit"


# ── Service class (only importable with pywin32) ───────────────────────────────

def _build_service_class():  # type: ignore[return]
    """Factory so the pywin32 import only runs when actually needed."""
    try:
        import win32serviceutil  # type: ignore[import]
        import win32service       # type: ignore[import]
        import win32event         # type: ignore[import]
        import servicemanager     # type: ignore[import]
    except ImportError:
        return None

    class GritService(win32serviceutil.ServiceFramework):  # type: ignore[misc]
        _svc_name_ = SERVICE_NAME
        _svc_display_name_ = SERVICE_DISPLAY_NAME
        _svc_description_ = SERVICE_DESCRIPTION

        def __init__(self, args):  # type: ignore[override]
            win32serviceutil.ServiceFramework.__init__(self, args)
            self._stop_event = win32event.CreateEvent(None, 0, 0, None)
            self._running = False

        def SvcStop(self):
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            win32event.SetEvent(self._stop_event)
            self._running = False

        def SvcDoRun(self):
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STARTED,
                (self._svc_name_, ""),
            )
            self._running = True
            # Point all Grit storage at the shared %PROGRAMDATA%\Grit dir
            os.environ.setdefault("GRIT_CONFIG_DIR", str(PROGRAMDATA_DIR))
            PROGRAMDATA_DIR.mkdir(parents=True, exist_ok=True)

            import asyncio
            import threading

            loop = asyncio.new_event_loop()
            thread = threading.Thread(target=self._run_daemon, args=(loop,), daemon=True)
            thread.start()

            # Block until service stop is signalled
            win32event.WaitForSingleObject(self._stop_event, win32event.INFINITE)

            loop.call_soon_threadsafe(loop.stop)
            thread.join(timeout=10)

            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STOPPED,
                (self._svc_name_, ""),
            )

        def _run_daemon(self, loop: "asyncio.AbstractEventLoop") -> None:
            asyncio.set_event_loop(loop)
            try:
                from grit.daemon.server import run_daemon
                loop.run_until_complete(run_daemon())
            except Exception as exc:
                log.error("Daemon error in Windows Service: %s", exc, exc_info=True)

    return GritService


# ── Install / uninstall helpers ───────────────────────────────────────────────

def _require_pywin32() -> None:
    try:
        import win32serviceutil  # noqa: F401
    except ImportError:
        raise RuntimeError(
            "pywin32 is required for Windows Service management.\n"
            "Install it with: pip install pywin32"
        )


def install_service() -> None:
    """Install the Grit Windows Service (requires elevated privileges)."""
    _require_pywin32()
    import win32serviceutil  # type: ignore[import]

    cls = _build_service_class()
    if cls is None:
        raise RuntimeError("Failed to build service class — pywin32 not available.")

    # win32serviceutil.InstallService expects the module path
    win32serviceutil.InstallService(
        pythonClassString=f"{__name__}.{cls.__name__}",
        serviceName=SERVICE_NAME,
        displayName=SERVICE_DISPLAY_NAME,
        description=SERVICE_DESCRIPTION,
        startType=0x02,  # SERVICE_AUTO_START
    )
    log.info("Service %r installed.", SERVICE_NAME)


def uninstall_service() -> None:
    """Remove the Grit Windows Service (requires elevated privileges)."""
    _require_pywin32()
    import win32serviceutil  # type: ignore[import]

    win32serviceutil.RemoveService(SERVICE_NAME)
    log.info("Service %r removed.", SERVICE_NAME)


def start_service() -> None:
    """Start the installed Grit Windows Service."""
    _require_pywin32()
    import win32serviceutil  # type: ignore[import]

    win32serviceutil.StartService(SERVICE_NAME)
    log.info("Service %r started.", SERVICE_NAME)


def stop_service() -> None:
    """Stop the running Grit Windows Service."""
    _require_pywin32()
    import win32serviceutil  # type: ignore[import]

    win32serviceutil.StopService(SERVICE_NAME)
    log.info("Service %r stopped.", SERVICE_NAME)


def query_service_status() -> Optional[str]:
    """Return a human-readable status string, or None if not installed."""
    try:
        import win32serviceutil  # type: ignore[import]
        import win32service       # type: ignore[import]

        status_code = win32serviceutil.QueryServiceStatus(SERVICE_NAME)[1]
        return {
            win32service.SERVICE_STOPPED: "stopped",
            win32service.SERVICE_START_PENDING: "start_pending",
            win32service.SERVICE_STOP_PENDING: "stop_pending",
            win32service.SERVICE_RUNNING: "running",
            win32service.SERVICE_CONTINUE_PENDING: "continue_pending",
            win32service.SERVICE_PAUSE_PENDING: "pause_pending",
            win32service.SERVICE_PAUSED: "paused",
        }.get(status_code, f"unknown({status_code})")
    except Exception:
        return None


# ── __main__ entry (for pywin32 service registration) ────────────────────────

if __name__ == "__main__":
    cls = _build_service_class()
    if cls is None:
        print("pywin32 is not installed.  Cannot manage Windows Service.", file=sys.stderr)
        sys.exit(1)

    import win32serviceutil  # type: ignore[import]

    win32serviceutil.HandleCommandLine(cls)
