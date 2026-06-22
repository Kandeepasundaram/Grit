"""License JWT generation and validation (server-side)."""

from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from app.config import settings
from app.models.user import Subscription, User


def _load_private_key():
    """Load RSA private key for signing license JWTs."""
    from cryptography.hazmat.primitives.serialization import load_pem_private_key
    pem = Path(settings.license_private_key_path).read_bytes()
    return load_pem_private_key(pem, password=None)


def _build_claims(user: User, subscription: Optional[Subscription]) -> dict:
    tier = "free"
    profile_limit = settings.free_profile_limit
    expires_at = (datetime.now(timezone.utc) + timedelta(days=settings.license_expire_days)).isoformat()

    if subscription and subscription.expires_at:
        if datetime.now(timezone.utc) < subscription.expires_at.replace(tzinfo=timezone.utc):
            tier = subscription.tier
            profile_limit = subscription.profile_limit

    return {
        "user_id": user.id,
        "email": user.email,
        "tier": tier,
        "profile_limit": profile_limit,
        "expires_at": expires_at,
        "issued_at": datetime.now(timezone.utc).isoformat(),
    }


def issue_license_jwt(user: User, subscription: Optional[Subscription]) -> tuple[str, dict]:
    """Return (signed_jwt, claims_dict) for the given user and subscription."""
    import base64

    claims = _build_claims(user, subscription)
    header = {"alg": "RS256", "typ": "JWT"}

    def _b64url(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

    h = _b64url(json.dumps(header, separators=(",", ":")).encode())
    p = _b64url(json.dumps(claims, separators=(",", ":")).encode())
    signing_input = f"{h}.{p}".encode()

    from cryptography.hazmat.primitives.asymmetric.padding import PKCS1v15
    from cryptography.hazmat.primitives.hashes import SHA256

    private_key = _load_private_key()
    signature = private_key.sign(signing_input, PKCS1v15(), SHA256())  # type: ignore[arg-type]
    sig = _b64url(signature)

    return f"{h}.{p}.{sig}", claims
