"""Application configuration — persisted to config.json."""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Optional

from grit.config.paths import app_config_file
from grit.constants import DEFAULT_SESSION_TTL_SECONDS
from grit.exceptions import StorageCorruptError


@dataclass
class AppConfig:
    session_ttl_seconds: int = DEFAULT_SESSION_TTL_SECONDS
    auto_detect: bool = True
    notifications_enabled: bool = True
    auto_install_hooks: bool = True
    # Phase 2: cloud sync
    cloud_sync_enabled: bool = False
    cloud_sync_interval_seconds: int = 300

    @classmethod
    def load(cls) -> "AppConfig":
        path = app_config_file()
        if not path.exists():
            return cls()
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            raise StorageCorruptError(str(path), str(exc)) from exc
        # Only keep known fields; ignore unknown keys from newer versions
        known = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        filtered = {k: v for k, v in raw.items() if k in known}
        return cls(**filtered)

    def save(self) -> None:
        path = app_config_file()
        tmp = path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(asdict(self), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        tmp.replace(path)
