"""Cross-platform desktop notifications."""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)


def notify(title: str, message: str, timeout: int = 5) -> None:
    """Show a desktop notification if notifications are enabled in config."""
    from grit.config.app_config import AppConfig
    if not AppConfig.load().notifications_enabled:
        return
    try:
        import plyer.notification
        plyer.notification.notify(
            title=title,
            message=message,
            app_name="Grit",
            timeout=timeout,
        )
    except Exception as exc:
        log.debug("Notification failed: %s", exc)


def notify_profile_applied(profile_name: str, repo_name: str) -> None:
    notify("Grit — Profile Applied", f"{profile_name!r} active for {repo_name}")


def notify_session_expiring(profile_name: str, minutes_remaining: int) -> None:
    notify("Grit — Session Expiring", f"{profile_name!r} expires in {minutes_remaining} min")
