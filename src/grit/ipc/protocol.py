"""IPC message protocol between daemon and clients.

Messages are newline-delimited JSON objects:
    {"type": "<msg_type>", "payload": {...}}        ← request
    {"status": "ok"|"error", "payload": {...}}      ← response

All encode/decode operations go through this module so the framing is
defined in exactly one place.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Literal, Optional

from grit.exceptions import IPCProtocolError

# ── Message types ─────────────────────────────────────────────────────────────

MessageType = Literal[
    "pre-commit",
    "get-session",
    "set-session",
    "delete-session",
    "list-sessions",
    "list-profiles",
    "switch-profile",
    "daemon-status",
    "ping",
]

ResponseStatus = Literal["ok", "error"]

# ── Framing ───────────────────────────────────────────────────────────────────

_ENCODING = "utf-8"
_DELIMITER = b"\n"


def encode_request(msg_type: str, payload: Optional[Dict[str, Any]] = None) -> bytes:
    """Serialise a request dict to bytes (JSON + newline)."""
    try:
        return (
            json.dumps({"type": msg_type, "payload": payload or {}}, ensure_ascii=False)
            + "\n"
        ).encode(_ENCODING)
    except (TypeError, ValueError) as exc:
        raise IPCProtocolError(f"Cannot encode request: {exc}") from exc


def encode_response(
    status: str, payload: Optional[Dict[str, Any]] = None, error: Optional[str] = None
) -> bytes:
    """Serialise a response dict to bytes (JSON + newline)."""
    msg: Dict[str, Any] = {"status": status, "payload": payload or {}}
    if error:
        msg["error"] = error
    try:
        return (json.dumps(msg, ensure_ascii=False) + "\n").encode(_ENCODING)
    except (TypeError, ValueError) as exc:
        raise IPCProtocolError(f"Cannot encode response: {exc}") from exc


def decode(data: bytes) -> Dict[str, Any]:
    """Deserialise one newline-delimited JSON message from bytes."""
    try:
        return json.loads(data.rstrip(_DELIMITER).decode(_ENCODING))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise IPCProtocolError(f"Cannot decode message: {exc}") from exc


# ── Convenience constructors ──────────────────────────────────────────────────

def ok(payload: Optional[Dict[str, Any]] = None) -> bytes:
    return encode_response("ok", payload)


def error(message: str) -> bytes:
    return encode_response("error", error=message)
