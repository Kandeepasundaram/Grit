"""OS credential store integration and GitHub browser-based OAuth login.

Manages per-profile HTTPS credentials (e.g. GitHub PATs obtained via OAuth)
in the platform's native secure storage so git operations authenticate as the
right account.  Credential secrets never touch Grit's own JSON files.

Platform targets:
  Windows : Windows Credential Manager via pywin32 (pip install grit[windows])
             Target name follows GCM convention: gh:<host>:<username>
  macOS   : Keychain via `security` CLI (built-in, no extra deps)
  Linux   : keyring package (pip install grit[linux-keyring])
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
import webbrowser
from typing import Optional
import urllib.parse
import urllib.request

from grit.exceptions import GritError

log = logging.getLogger(__name__)

# GitHub OAuth App client ID for Grit.  Override with GRIT_GITHUB_CLIENT_ID.
# Device flow uses only the client_id (no client secret needed).
_GITHUB_CLIENT_ID = os.environ.get("GRIT_GITHUB_CLIENT_ID", "Ov23liZXsJoXhR2fumDt")

_DEVICE_AUTH_URL = "https://github.com/login/device/code"
_TOKEN_URL = "https://github.com/login/oauth/access_token"
_SCOPES = "repo read:user"
_POLL_TIMEOUT = 300  # seconds


# ── OS credential store ───────────────────────────────────────────────────────

def _gcm_target(host: str, username: str) -> str:
    """Return the Windows Credential Manager target that GCM uses for a GitHub account."""
    return f"gh:{host}:{username}"


def store_credential(host: str, username: str, token: str) -> None:
    """Store *token* in the OS credential store for *username*@*host*."""
    if sys.platform == "win32":
        _win_store(host, username, token)
    elif sys.platform == "darwin":
        _mac_store(host, username, token)
    else:
        _linux_store(host, username, token)


def delete_credential(host: str, username: str) -> None:
    """Remove the stored credential for *username*@*host*.  No-op if absent."""
    if sys.platform == "win32":
        _win_delete(host, username)
    elif sys.platform == "darwin":
        _mac_delete(host, username)
    else:
        _linux_delete(host, username)


def has_credential(host: str, username: str) -> bool:
    """Return True if a credential is stored for *username*@*host*."""
    if sys.platform == "win32":
        return _win_has(host, username)
    elif sys.platform == "darwin":
        return _mac_has(host, username)
    else:
        return _linux_has(host, username)


# ── Windows implementation ────────────────────────────────────────────────────

def _win_store(host: str, username: str, token: str) -> None:
    try:
        import win32cred  # type: ignore[import]
    except ImportError:
        raise GritError(
            "pywin32 is required for Windows credential storage.\n"
            "Install it with:  pip install grit[windows]"
        )
    target = _gcm_target(host, username)
    credential = {
        "Type": win32cred.CRED_TYPE_GENERIC,
        "TargetName": target,
        "UserName": username,
        "CredentialBlob": token,
        "Persist": win32cred.CRED_PERSIST_LOCAL_MACHINE,
        "Comment": f"Grit credential for {username}@{host}",
    }
    win32cred.CredWrite(credential, 0)
    log.debug("Stored credential in WCM: %s", target)


def _win_delete(host: str, username: str) -> None:
    try:
        import win32cred  # type: ignore[import]
    except ImportError:
        return
    target = _gcm_target(host, username)
    try:
        win32cred.CredDelete(target, win32cred.CRED_TYPE_GENERIC, 0)
        log.debug("Deleted credential from WCM: %s", target)
    except Exception:
        pass  # not found — that's fine


def _win_has(host: str, username: str) -> bool:
    try:
        import win32cred  # type: ignore[import]
    except ImportError:
        return False
    target = _gcm_target(host, username)
    try:
        win32cred.CredRead(target, win32cred.CRED_TYPE_GENERIC, 0)
        return True
    except Exception:
        return False


# ── macOS implementation ──────────────────────────────────────────────────────

def _mac_store(host: str, username: str, token: str) -> None:
    import subprocess
    # Delete first to avoid "already exists" error
    _mac_delete(host, username)
    result = subprocess.run(
        ["security", "add-internet-password",
         "-a", username, "-s", host, "-w", token,
         "-l", f"git:https://{host}", "-U"],
        capture_output=True,
    )
    if result.returncode != 0:
        raise GritError(f"Keychain write failed: {result.stderr.decode().strip()}")
    log.debug("Stored credential in Keychain: %s@%s", username, host)


def _mac_delete(host: str, username: str) -> None:
    import subprocess
    subprocess.run(
        ["security", "delete-internet-password", "-a", username, "-s", host],
        capture_output=True,
    )


def _mac_has(host: str, username: str) -> bool:
    import subprocess
    result = subprocess.run(
        ["security", "find-internet-password", "-a", username, "-s", host],
        capture_output=True,
    )
    return result.returncode == 0


# ── Linux implementation ──────────────────────────────────────────────────────

def _linux_store(host: str, username: str, token: str) -> None:
    try:
        import keyring  # type: ignore[import]
    except ImportError:
        raise GritError(
            "keyring is required for Linux credential storage.\n"
            "Install it with:  pip install grit[linux-keyring]"
        )
    keyring.set_password(f"git:https://{host}", username, token)
    log.debug("Stored credential in keyring: %s@%s", username, host)


def _linux_delete(host: str, username: str) -> None:
    try:
        import keyring  # type: ignore[import]
        keyring.delete_password(f"git:https://{host}", username)
    except Exception:
        pass


def _linux_has(host: str, username: str) -> bool:
    try:
        import keyring  # type: ignore[import]
        return keyring.get_password(f"git:https://{host}", username) is not None
    except Exception:
        return False


# ── GitHub device flow ────────────────────────────────────────────────────────

def github_browser_login(username_hint: Optional[str] = None) -> str:
    """Authenticate with GitHub via device flow, opening a browser automatically.

    Returns the OAuth access token on success.
    Raises GritError on auth failure or timeout.
    """
    # Step 1: request device + user codes
    payload = urllib.parse.urlencode({
        "client_id": _GITHUB_CLIENT_ID,
        "scope": _SCOPES,
    }).encode()
    req = urllib.request.Request(
        _DEVICE_AUTH_URL,
        data=payload,
        headers={"Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
    except Exception as exc:
        raise GritError(f"Failed to start GitHub device flow: {exc}") from exc

    if "error" in data:
        raise GritError(f"GitHub device flow error: {data['error']}: {data.get('error_description', '')}")

    device_code = data["device_code"]
    user_code = data["user_code"]
    verification_uri = data["verification_uri"]
    # GitHub returns verification_uri_complete with the code pre-filled
    verification_uri_complete = data.get("verification_uri_complete", verification_uri)
    interval = int(data.get("interval", 5))

    # Step 2: open browser with the code pre-filled
    print(f"\n  Your verification code: {user_code}")
    print(f"  Opening: {verification_uri}\n")
    webbrowser.open(verification_uri_complete)

    # Step 3: poll until approved
    print("  Waiting for browser authorization", end="", flush=True)
    deadline = time.monotonic() + _POLL_TIMEOUT
    while time.monotonic() < deadline:
        time.sleep(interval)
        print(".", end="", flush=True)

        poll_payload = urllib.parse.urlencode({
            "client_id": _GITHUB_CLIENT_ID,
            "device_code": device_code,
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        }).encode()
        poll_req = urllib.request.Request(
            _TOKEN_URL,
            data=poll_payload,
            headers={"Accept": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(poll_req, timeout=15) as resp:
                result = json.loads(resp.read())
        except Exception as exc:
            log.debug("Poll request failed: %s", exc)
            continue

        error = result.get("error")
        if error == "authorization_pending":
            continue
        if error == "slow_down":
            interval += 5
            continue
        if error == "expired_token":
            raise GritError("\nDevice code expired. Please try again.")
        if error == "access_denied":
            raise GritError("\nAuthorization was denied.")
        if error:
            raise GritError(f"\nUnexpected OAuth error: {error}")

        token = result.get("access_token")
        if token:
            print(" done.")
            return token

    raise GritError(
        "\nTimed out waiting for authorization. "
        f"Please visit {verification_uri} and enter code {user_code} manually."
    )
