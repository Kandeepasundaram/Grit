"""Unit tests for IPC protocol encode/decode."""

from __future__ import annotations

import pytest

from grit.exceptions import IPCProtocolError
from grit.ipc import protocol


class TestEncodeRequest:
    def test_basic_encode(self) -> None:
        data = protocol.encode_request("ping")
        assert data.endswith(b"\n")
        decoded = protocol.decode(data)
        assert decoded["type"] == "ping"
        assert decoded["payload"] == {}

    def test_with_payload(self) -> None:
        data = protocol.encode_request("get-session", {"repo_path": "/tmp/repo"})
        decoded = protocol.decode(data)
        assert decoded["payload"]["repo_path"] == "/tmp/repo"


class TestEncodeResponse:
    def test_ok_response(self) -> None:
        data = protocol.ok({"result": 42})
        decoded = protocol.decode(data)
        assert decoded["status"] == "ok"
        assert decoded["payload"]["result"] == 42

    def test_error_response(self) -> None:
        data = protocol.error("something went wrong")
        decoded = protocol.decode(data)
        assert decoded["status"] == "error"
        assert "something went wrong" in decoded["error"]


class TestDecode:
    def test_invalid_json_raises(self) -> None:
        with pytest.raises(IPCProtocolError):
            protocol.decode(b"not json\n")

    def test_empty_bytes_raises(self) -> None:
        with pytest.raises(IPCProtocolError):
            protocol.decode(b"\n")

    def test_strips_newline(self) -> None:
        data = b'{"type": "ping", "payload": {}}\n'
        decoded = protocol.decode(data)
        assert decoded["type"] == "ping"

    def test_roundtrip(self) -> None:
        original = {"type": "set-session", "payload": {"repo_path": "/a/b", "profile_id": "xyz"}}
        import json
        encoded = (json.dumps(original, ensure_ascii=False) + "\n").encode()
        decoded = protocol.decode(encoded)
        assert decoded == original
