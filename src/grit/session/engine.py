"""Session engine — the core brain that resolves, creates, and applies sessions."""

from __future__ import annotations

import logging

from grit.config.app_config import AppConfig
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
        profile_store: ProfileStore | None = None,
        session_store: SessionStore | None = None,
        app_config: AppConfig | None = None,
    ) -> None:
        self._profiles = profile_store or ProfileStore()
        self._sessions = session_store or SessionStore()
        self._config = app_config or AppConfig.load()

    # ── Resolution ────────────────────────────────────────────────────────────

    def resolve(self, repo_path: str) -> Session | None:
        """Return an active session for *repo_path*, or None if none exists.

        Resolution order:
          1. Existing (non-pinned) session cache hit
          2. Enterprise SSO (if enforce_sso)
          3. Auto-detect: .grit file > path patterns > repo name > remote patterns
          4. Pinned session (grit session pin) — only if auto-detect found nothing
          5. Default profile (grit profile set-default) — only if no pin exists
          6. None — caller (daemon IPC handler) should prompt the user
        """
        cached = self._sessions.get(repo_path)
        if cached is not None and not cached.pinned:
            cached.touch(self._config.session_ttl_seconds)
            self._sessions.set(cached)
            return cached

        # Enterprise SSO: if enforce_sso is on and user has a valid SSO session,
        # attempt to match a profile for the SSO identity before falling back to
        # path-pattern detection.
        sso_session = self._resolve_sso(repo_path)
        if sso_session is not None:
            return sso_session

        if self._config.auto_detect:
            detected = self._auto_detect(repo_path)
            if detected is not None:
                return detected

        if cached is not None and cached.pinned:
            try:
                self._profiles.get_by_id(cached.profile_id)
            except Exception:
                pass  # dangling pin (profile deleted out of band) — treat as no pin
            else:
                cached.touch(self._config.session_ttl_seconds)
                self._sessions.set(cached)
                return cached

        return self._resolve_default_profile(repo_path)

    def _resolve_sso(self, repo_path: str) -> Session | None:
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
            log.info(
                "SSO-matched profile %r for %s (user: %s)",
                profile.name,
                repo_path,
                sso.user_email,
            )
            return self.create(repo_path, profile.id)
        except Exception as exc:  # noqa: BLE001
            log.debug("SSO resolution skipped: %s", exc)
            return None

    def _auto_detect(self, repo_path: str) -> Session | None:
        from grit.session.detector import detect_profile  # lazy import

        profiles = self._profiles.get_all()
        matched = detect_profile(repo_path, profiles)
        if matched is None:
            return None
        log.info("Auto-detected profile %r for %s", matched.name, repo_path)
        return self.create(repo_path, matched.id)

    # ── Pinning ───────────────────────────────────────────────────────────────

    def pin(self, repo_path: str, profile_id: str) -> Session:
        """Create a persistent, non-expiring session pin and apply its profile."""
        session = Session(repo_path=repo_path, profile_id=profile_id, pinned=True)
        self._sessions.set(session)
        self.apply(session)
        self._audit_session_create(repo_path, profile_id)
        return session

    def unpin(self, repo_path: str) -> bool:
        """Remove a pin for *repo_path*. Returns False if none was set."""
        existing = self._sessions.get(repo_path)
        if existing is None or not existing.pinned:
            return False
        self._sessions.delete(repo_path)
        return True

    # ── Default profile ─────────────────────────────────────────────────────────

    def _resolve_default_profile(self, repo_path: str) -> Session | None:
        default = self._profiles.get_default()
        if default is None:
            return None
        log.info("Applying default profile %r for %s", default.name, repo_path)
        return self.create(repo_path, default.id)

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
