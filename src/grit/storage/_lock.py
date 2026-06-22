"""Cross-platform file locking for concurrent-safe JSON storage."""

from __future__ import annotations

import os
import sys
from contextlib import contextmanager, suppress
from pathlib import Path
from typing import Generator

if sys.platform == "win32":
    import msvcrt

    @contextmanager
    def file_lock(path: Path) -> Generator[None, None, None]:
        lock_path = path.with_suffix(path.suffix + ".lock")
        try:
            with open(lock_path, "w") as fh:
                # Lock 1 byte at position 0
                msvcrt.locking(fh.fileno(), msvcrt.LK_LOCK, 1)
                try:
                    yield
                finally:
                    fh.seek(0)
                    msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
        finally:
            with suppress(OSError):
                os.unlink(lock_path)

else:
    import fcntl

    @contextmanager
    def file_lock(path: Path) -> Generator[None, None, None]:
        lock_path = path.with_suffix(path.suffix + ".lock")
        try:
            with open(lock_path, "w") as fh:
                fcntl.flock(fh, fcntl.LOCK_EX)
                try:
                    yield
                finally:
                    fcntl.flock(fh, fcntl.LOCK_UN)
        finally:
            with suppress(OSError):
                os.unlink(lock_path)
