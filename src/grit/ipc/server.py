"""Asyncio IPC server — runs inside the daemon, dispatches incoming requests."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import sys
from typing import Any, Callable, Coroutine, Dict

from grit.ipc import protocol

log = logging.getLogger(__name__)

# Handler type: async function that receives a payload dict and returns a dict
Handler = Callable[[Dict[str, Any]], Coroutine[Any, Any, Dict[str, Any]]]

_handlers: dict[str, Handler] = {}


def register(msg_type: str) -> Callable[[Handler], Handler]:
    """Decorator to register a coroutine as the handler for *msg_type*."""
    def decorator(fn: Handler) -> Handler:
        _handlers[msg_type] = fn
        return fn
    return decorator


async def _handle_connection(
    reader: asyncio.StreamReader, writer: asyncio.StreamWriter
) -> None:
    try:
        data = await reader.readline()
        if not data:
            return
        try:
            msg = protocol.decode(data)
        except Exception as exc:
            writer.write(protocol.error(f"Bad request: {exc}"))
            await writer.drain()
            return

        msg_type = msg.get("type", "")
        payload: dict[str, Any] = msg.get("payload", {})

        handler = _handlers.get(msg_type)
        if handler is None:
            writer.write(protocol.error(f"Unknown message type: {msg_type!r}"))
            await writer.drain()
            return

        try:
            result = await handler(payload)
            writer.write(protocol.ok(result))
        except Exception:
            log.exception("Handler %r raised an error", msg_type)
            writer.write(protocol.error("internal error"))
        await writer.drain()
    finally:
        writer.close()
        with contextlib.suppress(Exception):
            await writer.wait_closed()


async def start_server(stop_event: asyncio.Event) -> None:
    """Start the IPC server and serve until *stop_event* is set.

    On macOS/Linux: Unix domain socket.
    On Windows: loopback TCP socket on a random port (port written to grit.port).
    """
    if sys.platform == "win32":
        await _start_server_windows(stop_event)
    else:
        await _start_server_unix(stop_event)


async def _start_server_unix(stop_event: asyncio.Event) -> None:
    import os

    from grit.config.paths import ipc_socket_path
    socket_path = ipc_socket_path()
    if socket_path.exists():
        socket_path.unlink()

    server = await asyncio.start_unix_server(
        _handle_connection, path=str(socket_path)
    )
    os.chmod(str(socket_path), 0o600)  # only the owner may connect
    log.info("IPC server listening on %s", socket_path)
    async with server:
        await stop_event.wait()
    log.info("IPC server stopped")
    if socket_path.exists():
        socket_path.unlink()


async def _start_server_windows(stop_event: asyncio.Event) -> None:
    from grit.config.paths import ipc_port_file
    port_file = ipc_port_file()

    # Bind to loopback on a random free port
    server = await asyncio.start_server(
        _handle_connection, host="127.0.0.1", port=0
    )
    port = server.sockets[0].getsockname()[1]
    port_file.write_text(str(port))
    log.info("IPC server listening on 127.0.0.1:%d (Windows TCP)", port)

    async with server:
        await stop_event.wait()

    log.info("IPC server stopped")
    if port_file.exists():
        port_file.unlink()
