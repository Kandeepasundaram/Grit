"""Synchronous IPC client — used by the CLI and git hooks to talk to the daemon."""

from __future__ import annotations

import socket
import sys
from typing import Any

from grit.config.paths import ipc_socket_path
from grit.exceptions import DaemonNotRunningError, IPCProtocolError
from grit.ipc import protocol

_RECV_SIZE = 65536
_MAX_MSG_BYTES = 1024 * 1024  # 1 MB — guard against unbounded reads


def _connect() -> socket.socket:
    if sys.platform == "win32":
        return _connect_windows()
    else:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        socket_path = str(ipc_socket_path())
        try:
            sock.connect(socket_path)
        except (FileNotFoundError, ConnectionRefusedError, OSError) as err:
            raise DaemonNotRunningError() from err
        return sock


def _connect_windows() -> socket.socket:
    from grit.config.paths import ipc_port_file
    port_file = ipc_port_file()
    if not port_file.exists():
        raise DaemonNotRunningError()
    try:
        port = int(port_file.read_text().strip())
    except (ValueError, OSError) as err:
        raise DaemonNotRunningError() from err
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect(("127.0.0.1", port))
    except (ConnectionRefusedError, OSError) as err:
        raise DaemonNotRunningError() from err
    return sock


def send_request(
    msg_type: str, payload: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Send one request to the daemon and return the decoded response.

    Raises:
        DaemonNotRunningError: if the daemon socket is not reachable.
        IPCProtocolError: if the response cannot be decoded.
    """
    sock = _connect()
    try:
        sock.sendall(protocol.encode_request(msg_type, payload))
        data = b""
        while True:
            chunk = sock.recv(_RECV_SIZE)
            if not chunk:
                break
            data += chunk
            if len(data) > _MAX_MSG_BYTES:
                raise IPCProtocolError("IPC response exceeded maximum allowed size")
            if b"\n" in chunk:
                break
    finally:
        sock.close()
    return protocol.decode(data)


def ping() -> bool:
    """Return True if the daemon is reachable."""
    try:
        resp = send_request("ping")
        return resp.get("status") == "ok"
    except DaemonNotRunningError:
        return False
