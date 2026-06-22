"""Session engine — the core brain that resolves, creates, and applies sessions."""

from __future__ import annotations

import logging
from typing import Optional

from grit.config.app_config import AppConfig
from grit.models.profile import Profile
from grit.models.session import Session
from grit.storage.profile_store import ProfileStore
from grit.storage.session_store import SessionStore

log = logging.getLogger(__name__)


class SessionEngine:
    """Orchestrates session lifecycle for a single daemon instance.

    The engine is the single point of contact for all session-related IPC
    handlers.  It holds references to the stores and lazily imports the
    detector and git.config to avoid circular imports.
    """

    def __init__(
        self,
        profile_store: Optional[ProfileStore] = None,
        session_store: Optional[SessionStore] = None,
        app_config: Optional[AppConfig] = None,
    ) -> None:
        self._profiles = profile_store or ProfileStore()
        self._sessions = session_store or SessionStore()
        self._config = app_config or AppConfig.load()

    # ── Resolution ────────────────────────────────────────────────────────────

    def resolve(self, repo_path: str) -> Optional[Session]:
        """Return an active session for *repo_path*, or None if none exists.

        Checks the session cache first; if a session is found and not expired
        it is returned.  If auto-detect is enabled and no session exists,
        attempts path-pattern matching.  Returns None if no match — the caller
        (daemon IPC handler) should prompt the user to pick a profile.
        """
        session = self._sessions.get(repo_path)
        if session is not None:
            session.touch(self._config.session_ttl_seconds)
            self._sessions.set(session)
            return session

        # Enterprise SSO: if enforce_sso is on and user has a valid SSO session,
        # attempt to match a profile for the SSO identity before falling back to
        # path-pattern detection.
        sso_session = self._resolve_sso(repo_path)
        if sso_session is not None:
            return sso_session

        if self._config.auto_detect:
            return self._auto_detect(repo_path)

        return None

    def _resolve_sso(self, repo_path: str) -> Optional[Session]:
        """Return a session matched via enterprise SSO, or None.

        Only runs when enterprise SSO is configured and enforce_sso=True.
        """
        try:
            from grit.enterprise.sso import (
                load_enterprise_config,
                load_sso_session,
                resolve_profile_for_sso,
            )
        except ImportError:
            return None

        try:
            cfg = load_enterprise_config()
            if not cfg.is_configured() or not cfg.enforce_sso:
                return None
            sso = load_sso_session()
            if sso is None or sso.is_expired():
                return None
            profiles = self._profiles.get_all()
            profile = resolve_profile_for_sso(sso, profiles)
            if profile is None:
                return None
            log.info("SSO-matched profile %r for %s (user: %s)", profile.name, repo_path, sso.user_email)
            return self.create(repo_path, profile.id)
        except Exception as exc:  # noqa: BLE001
            log.debug("SSO resolution skipped: %s", exc)
            return None

    def _auto_detect(self, repo_path: str) -> Optional[Session]:
        from grit.session.detector import detect_profile  # lazy import

        profiles = self._profiles.get_all()
        matched = detect_profile(repo_path, profiles)
        if matched is None:
            return None
        log.info("Auto-detected profile %r for %s", matched.name, repo_path)
        return self.create(repo_path, matched.id)

    # ── Creation ──────────────────────────────────────────────────────────────

    def create(self, repo_path: str, profile_id: str) -> Session:
        """Create and persist a new session, then apply the profile to git config."""
        session = Session(
            repo_path=repo_path,
            profile_id=profile_id,
            # expires_at default is set by the Session dataclass
        )
        self._sessions.set(session)
        self.apply(session)
        self._audit_session_create(repo_path, profile_id)
        return session

    def _audit_session_create(self, repo_path: str, profile_id: str) -> None:
        try:
            from grit.enterprise.audit import log_session_create
            log_session_create(repo_path, profile_id)
        except Exception:  # noqa: BLE001
            pass

    # ── Application ───────────────────────────────────────────────────────────

    def apply(self, session: Session) -> None:
        """Write the session's profile into the repository's local git config."""
        from grit.git import config as git_config  # lazy import

        try:
            profile = self._profiles.get_by_id(session.profile_id)
        except Exception as exc:
            log.error("Cannot apply session — profile %r not found: %s", session.profile_id, exc)
            return

        git_config.apply_profile(session.repo_path, profile)
        log.info("Applied profile %r to %s", profile.name, session.repo_path)
        try:
            from grit.enterprise.audit import log_profile_switch
            log_profile_switch(session.repo_path, profile.id, profile.name)
        except Exception:  # noqa: BLE001
            pass

    # ── Invalidation ──────────────────────────────────────────────────────────

    def invalidate(self, repo_path: str) -> None:
        """Remove the session for *repo_path*."""
        self._sessions.delete(repo_path)
        log.info("Invalidated session for %s", repo_path)

    def invalidate_all(self) -> None:
        """Remove all sessions."""
        self._sessions.invalidate_all()

    # ── Startup ───────────────────────────────────────────────────────────────

    def startup_purge(self) -> int:
        """Purge expired sessions on daemon start. Returns count removed."""
        return self._sessions.purge_expired()
