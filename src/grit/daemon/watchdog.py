"""Filesystem watchdog — monitors .git directories for new commit activity.

When a .git/COMMIT_EDITMSG write is detected in a repo that Grit doesn't
know about yet, the hook_manager is called to register it and install the
pre-commit hook.  This provides a fallback for repos that weren't set up
via `grit session set`.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

log = logging.getLogger(__name__)


async def start_watchdog(stop_event: asyncio.Event) -> None:
    """Start the watchdog observer and run until *stop_event* is set.

    Uses the ``watchdog`` library for OS-native filesystem notifications.
    Falls back to a no-op if watchdog is not importable (shouldn't happen
    in a correctly installed environment).
    """
    try:
        from watchdog.events import FileSystemEventHandler
        from watchdog.observers import Observer
    except ImportError:
        log.warning("watchdog library not available; filesystem monitoring disabled")
        await stop_event.wait()
        return

    from grit.daemon.hook_manager import HookManager
    hook_manager = HookManager()

    class _CommitHandler(FileSystemEventHandler):
        def __init__(self) -> None:
            self._seen: set[str] = set()

        def _on_commit_editmsg(self, path: str) -> None:
            # path looks like /some/repo/.git/COMMIT_EDITMSG
            git_dir = Path(path).parent
            repo_root = str(git_dir.parent.resolve())
            if repo_root not in self._seen:
                self._seen.add(repo_root)
                log.info("Detected new repo: %s", repo_root)
                try:
                    hook_manager.register_and_install(repo_root)
                except Exception as exc:
                    log.warning("Could not install hook in %s: %s", repo_root, exc)

        def on_created(self, event: object) -> None:
            if hasattr(event, "src_path") and "COMMIT_EDITMSG" in str(event.src_path):
                self._on_commit_editmsg(str(event.src_path))

        def on_modified(self, event: object) -> None:
            if hasattr(event, "src_path") and "COMMIT_EDITMSG" in str(event.src_path):
                self._on_commit_editmsg(str(event.src_path))

    handler = _CommitHandler()
    observer = Observer()

    # Watch the user's home directory tree for .git activity.
    # We watch non-recursively at the home level then rely on the handler
    # filtering by filename, because recursive watching of $HOME can be
    # expensive on large trees.  A smarter approach (watching only registered
    # git roots) is implemented in Phase 1D.
    home = str(Path.home())
    observer.schedule(handler, home, recursive=True)
    observer.start()
    log.info("Watchdog started, monitoring %s", home)

    try:
        await stop_event.wait()
    finally:
        observer.stop()
        observer.join()
        log.info("Watchdog stopped")
