"""Subscription tier enforcement via locally-verified JWT license.

The license.json file is a JWT signed with the server's RSA private key.
The client verifies it using the bundled public key — no internet contact
required for verification.

Tier limits (enforced client-side):
  free:       max 5 profiles, no cloud sync, no team profiles
  pro:        unlimited profiles, cloud sync, team profiles
  enterprise: all pro features + SSO, audit logs, on-premise

Grace period: 30 days offline before enforcement kicks in after license expiry.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal

from grit.config.paths import license_file
from grit.constants import FREE_TIER_MAX_PROFILES

log = logging.getLogger(__name__)

Tier = Literal["free", "pro", "enterprise"]

_GRACE_PERIOD_DAYS = 30
_PUBLIC_KEY_PATH = Path(__file__).parent.parent / "cloud" / "license_public.pem"


@dataclass
class License:
    user_id: str
    email: str
    tier: Tier
    profile_limit: int  # -1 = unlimited
    expires_at: str     # ISO-8601
    issued_at: str
    # The raw JWT, kept for refresh purposes
    raw_token: str = ""

    @property
    def is_expired(self) -> bool:
        try:
            expiry = datetime.fromisoformat(self.expires_at)
            return datetime.now(timezone.utc) >= expiry
        except ValueError:
            return True

    @property
    def is_in_grace_period(self) -> bool:
        """Return True if license is expired but within the 30-day grace window."""
        if not self.is_expired:
            return False
        try:
            expiry = datetime.fromisoformat(self.expires_at)
            grace_end = expiry + timedelta(days=_GRACE_PERIOD_DAYS)
            return datetime.now(timezone.utc) < grace_end
        except ValueError:
            return False

    @property
    def is_valid(self) -> bool:
        """Active or within grace period."""
        return not self.is_expired or self.is_in_grace_period

    def allows_profile_count(self, count: int) -> bool:
        if self.profile_limit == -1:
            return True
        return count <= self.profile_limit

    def allows_cloud_sync(self) -> bool:
        return self.tier in ("pro", "enterprise")

    def allows_team_profiles(self) -> bool:
        return self.tier in ("pro", "enterprise")

    def allows_sso(self) -> bool:
        return self.tier == "enterprise"

    def allows_audit_log(self) -> bool:
        return self.tier == "enterprise"


# ── Free tier fallback ────────────────────────────────────────────────────────

_FREE_LICENSE = License(
    user_id="",
    email="",
    tier="free",
    profile_limit=FREE_TIER_MAX_PROFILES,
    expires_at="9999-12-31T23:59:59+00:00",
    issued_at="2026-01-01T00:00:00+00:00",
)


# ── JWT verification ──────────────────────────────────────────────────────────

def _verify_jwt(token: str) -> dict[str, Any] | None:
    """Verify a JWT using the bundled RSA public key. Returns claims or None."""
    try:
        import base64

        from cryptography.hazmat.primitives.asymmetric.padding import PKCS1v15
        from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
        from cryptography.hazmat.primitives.hashes import SHA256
        from cryptography.hazmat.primitives.serialization import load_pem_public_key
    except ImportError:
        log.warning(
            "cryptography library not installed; license verification skipped. "
            "Install it with: pip install cryptography"
        )
        return None

    try:
        public_key_pem = _PUBLIC_KEY_PATH.read_bytes()
        if b"PLACEHOLDER" in public_key_pem:
            log.debug("Placeholder public key — skipping JWT verification")
            return None

        # Split JWT into header.payload.signature
        parts = token.split(".")
        if len(parts) != 3:
            return None

        def _b64decode(s: str) -> bytes:
            pad = 4 - len(s) % 4
            return base64.urlsafe_b64decode(s + "=" * pad)

        header_payload = f"{parts[0]}.{parts[1]}".encode()
        signature = _b64decode(parts[2])
        claims_bytes = _b64decode(parts[1])

        pub_key = load_pem_public_key(public_key_pem)
        if not isinstance(pub_key, RSAPublicKey):
            log.warning("License public key is not an RSA key; skipping verification")
            return None
        pub_key.verify(signature, header_payload, PKCS1v15(), SHA256())
        claims: dict[str, Any] = json.loads(claims_bytes)
        return claims
    except Exception as exc:
        log.warning("License JWT verification failed: %s", exc)
        return None


# ── Storage ───────────────────────────────────────────────────────────────────

def _load_raw() -> dict[str, Any] | None:
    path = license_file()
    if not path.exists():
        return None
    try:
        raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        return raw
    except (json.JSONDecodeError, OSError):
        return None


def _save_raw(data: dict[str, Any]) -> None:
    path = license_file()
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


# ── Public API ────────────────────────────────────────────────────────────────

def load_license() -> License:
    """Load and verify the stored license. Returns free-tier if absent/invalid."""
    raw = _load_raw()
    if raw is None:
        return _FREE_LICENSE

    token = raw.get("token", "")
    claims = _verify_jwt(token)

    if claims is None:
        # Verification failed — never trust unverified stored claims.
        log.warning("License JWT verification failed; reverting to free tier")
        return _FREE_LICENSE

    tier = claims.get("tier", "free")
    if tier not in ("free", "pro", "enterprise"):
        tier = "free"

    raw_limit = claims.get("profile_limit", FREE_TIER_MAX_PROFILES)
    profile_limit = raw_limit if isinstance(raw_limit, int) else FREE_TIER_MAX_PROFILES

    return License(
        user_id=claims.get("user_id", ""),
        email=claims.get("email", ""),
        tier=tier,
        profile_limit=profile_limit,
        expires_at=claims.get("expires_at", "9999-12-31T23:59:59+00:00"),
        issued_at=claims.get("issued_at", ""),
        raw_token=token,
    )


def save_license(token: str, claims: dict[str, Any]) -> None:
    """Persist a new license JWT with its claims."""
    _save_raw({"token": token, "claims": claims})
    log.info(
        "License saved: tier=%s, expires=%s",
        claims.get("tier"),
        claims.get("expires_at"),
    )


def clear_license() -> None:
    """Remove the stored license (reverts to free tier)."""
    path = license_file()
    path.unlink(missing_ok=True)


def enforce_profile_limit(current_count: int) -> None:
    """Raise ValueError if adding another profile would exceed the tier limit."""
    lic = load_license()
    if not lic.is_valid:
        # Grace period expired — enforce free tier
        lic = _FREE_LICENSE
    if not lic.allows_profile_count(current_count + 1):
        raise ValueError(
            f"Free tier is limited to {lic.profile_limit} profiles. "
            "Grit Pro (coming soon) removes this limit — "
            "pre-register at kandeepasundaram+GRIT@gmail.com"
        )


def pro_is_installed() -> bool:
    """Return True if the grit-pro package is installed alongside grit."""
    try:
        import grit_pro  # noqa: F401
        return True
    except ImportError:
        return False


def warn_profile_limit(current_count: int) -> None:
    """Print a warning when one slot away from the free tier profile limit."""
    import click
    lic = load_license()
    if lic.tier != "free" or lic.profile_limit == -1:
        return
    remaining = lic.profile_limit - current_count
    if remaining == 1:
        click.echo(
            f"\nNote: 1 profile slot remaining on the free tier (limit: {lic.profile_limit}). "
            "Grit Pro is coming soon — pre-register: kandeepasundaram+GRIT@gmail.com",
            err=True,
        )


def require_pro_installed(feature: str) -> None:
    """Exit with a friendly message if grit-pro is not installed.

    Call this at the top of any command that needs pro functionality before
    attempting any imports from grit.cloud or grit.enterprise.
    """
    import sys

    import click
    if not pro_is_installed():
        click.echo(
            f"\n'{feature}' is a Grit Pro feature — coming soon.\n\n"
            "  Pre-register to be notified when Grit Pro launches:\n"
            "    kandeepasundaram+GRIT@gmail.com\n",
            err=True,
        )
        sys.exit(1)


def require_pro(feature_name: str) -> None:
    """Raise ValueError if the current tier doesn't include *feature_name*."""
    lic = load_license()
    if not lic.is_valid:
        lic = _FREE_LICENSE

    allowed = {
        "cloud_sync": lic.allows_cloud_sync(),
        "team_profiles": lic.allows_team_profiles(),
        "sso": lic.allows_sso(),
        "audit_log": lic.allows_audit_log(),
    }
    if not allowed.get(feature_name, False):
        raise ValueError(
            f"{feature_name!r} requires Grit Pro or Enterprise (coming soon). "
            "Pre-register at kandeepasundaram+GRIT@gmail.com"
        )
