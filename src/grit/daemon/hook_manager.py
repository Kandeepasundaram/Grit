"""Hook manager — tracks which repos have Grit hooks installed."""

from __future__ import annotations

import json
import logging

from grit.config.paths import watched_repos_file
from grit.storage._lock import file_lock

log = logging.getLogger(__name__)


class HookManager:
    """Maintains the watched_repos.json registry and installs hooks."""

    def __init__(self) -> None:
        self._path = watched_repos_file()

    def _load(self) -> list[str]:
        if not self._path.exists():
            return []
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError):
            return []

    def _save(self, repos: list[str]) -> None:
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(repos, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self._path)

    def watched_repos(self) -> list[str]:
        with file_lock(self._path):
            return list(self._load())

    def register_and_install(self, repo_path: str) -> bool:
        """Register *repo_path* and install the pre-commit hook.

        Returns True if the hook was newly installed, False if already present.
        """
        from grit.git.hook import install, is_installed

        with file_lock(self._path):
            repos = self._load()
            if repo_path not in repos:
                repos.append(repo_path)
                self._save(repos)

        if not is_installed(repo_path):
            install(repo_path)
            log.info("Installed hook in %s", repo_path)
            return True
        return False

    def unregister(self, repo_path: str) -> None:
        from grit.git.hook import uninstall

        with file_lock(self._path):
            repos = self._load()
            repos = [r for r in repos if r != repo_path]
            self._save(repos)
        try:
            uninstall(repo_path)
        except Exception as exc:
            log.warning("Could not uninstall hook from %s: %s", repo_path, exc)
