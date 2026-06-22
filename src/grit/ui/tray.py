"""System tray icon and menu.

Runs in a dedicated thread alongside the daemon's asyncio event loop.
Cross-thread communication uses queue.Queue.
"""

from __future__ import annotations

import logging
import queue
import sys
import threading
from typing import Optional

log = logging.getLogger(__name__)

# Colour palette for profile icons (12 distinct colours, cycled by profile index)
_PALETTE = [
    (0x26, 0x8b, 0xd2),  # blue
    (0x2a, 0xa1, 0x98),  # teal
    (0x85, 0x99, 0x00),  # green
    (0xb5, 0x89, 0x00),  # yellow
    (0xcb, 0x4b, 0x16),  # orange
    (0xdc, 0x32, 0x2f),  # red
    (0xd3, 0x36, 0x82),  # magenta
    (0x6c, 0x71, 0xc4),  # violet
    (0x07, 0x36, 0x42),  # dark teal
    (0x58, 0x6e, 0x75),  # grey
    (0x83, 0x94, 0x96),  # light grey
    (0x00, 0x2b, 0x36),  # dark blue
]


def _profile_colour(profile_id: str) -> tuple:
    return _PALETTE[int(profile_id[:4], 16) % len(_PALETTE)]


def _make_icon_image(colour: tuple, size: int = 22):
    """Return a Pillow Image for the tray icon with a filled circle."""
    try:
        from PIL import Image, ImageDraw  # type: ignore[import]
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        margin = 2
        draw.ellipse(
            [margin, margin, size - margin, size - margin],
            fill=colour + (255,),
        )
        return img
    except ImportError:
        return None


def _build_menu(profiles, current_profile_id: Optional[str]):
    """Build a pystray Menu from the current profile list."""
    try:
        import pystray  # type: ignore[import]
    except ImportError:
        return None

    items = []
    for p in profiles:
        checked = p.id == current_profile_id

        def _switch(profile_id=p.id):
            from grit.ipc.client import send_request
            import os
            from grit.git.repo import find_repo_root
            repo = find_repo_root(os.getcwd())
            if repo:
                try:
                    send_request("switch-profile", {"repo_path": repo, "profile_id": profile_id})
                except Exception as exc:
                    log.warning("Profile switch failed: %s", exc)

        label = f"✓ {p.name}  ({p.email})" if checked else f"  {p.name}  ({p.email})"
        items.append(pystray.MenuItem(label, _switch, checked=checked))

    items.append(pystray.Menu.SEPARATOR)
    items.append(pystray.MenuItem("Quit", lambda icon, item: icon.stop()))
    return pystray.Menu(*items)


def run_tray(stop_event: threading.Event) -> None:
    """Run the system tray icon.  Blocks until stop_event is set."""
    try:
        import pystray  # type: ignore[import]
    except ImportError:
        log.warning("pystray not available; system tray disabled")
        stop_event.wait()
        return

    from grit.storage.profile_store import ProfileStore
    from grit.storage.session_store import SessionStore

    def _get_current_profile_id() -> Optional[str]:
        import os
        from grit.git.repo import find_repo_root
        repo = find_repo_root(os.getcwd())
        if not repo:
            return None
        session = SessionStore().get(repo)
        return session.profile_id if session else None

    profiles = ProfileStore().get_all()
    current_pid = _get_current_profile_id()
    colour = _profile_colour(current_pid) if current_pid else (0x26, 0x8b, 0xd2)
    image = _make_icon_image(colour)

    if image is None:
        log.warning("Pillow not available; tray icon will be blank")
        image = None  # pystray handles None gracefully on some platforms

    icon = pystray.Icon(
        "grit",
        image,
        "Grit",
        menu=_build_menu(profiles, current_pid),
    )

    def _setup(icon):
        icon.visible = True

    def _stop_check():
        while not stop_event.is_set():
            stop_event.wait(timeout=5)
            # Refresh menu with latest profiles/session
            try:
                updated_profiles = ProfileStore().get_all()
                updated_pid = _get_current_profile_id()
                icon.menu = _build_menu(updated_profiles, updated_pid)
                if updated_pid:
                    new_colour = _profile_colour(updated_pid)
                    new_img = _make_icon_image(new_colour)
                    if new_img:
                        icon.icon = new_img
            except Exception as exc:
                log.debug("Tray refresh error: %s", exc)
        icon.stop()

    t = threading.Thread(target=_stop_check, daemon=True)
    t.start()
    icon.run(_setup)
