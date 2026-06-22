"""Shared pytest fixtures for the Grit test suite.

Key fixture: ``tmp_config_dir`` — sets GRIT_CONFIG_DIR to a temp path so that
every storage operation in tests is automatically redirected without any mocking.
Simply requesting this fixture (or any fixture that depends on it) is enough;
no test needs to import from grit.config.paths directly.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Generator

import pytest


@pytest.fixture()
def tmp_config_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect all Grit I/O to a temporary directory.

    Sets GRIT_CONFIG_DIR so that grit.config.paths returns paths inside
    ``tmp_path``.  The directory is created fresh for each test.
    """
    config_root = tmp_path / "grit"
    config_root.mkdir()
    monkeypatch.setenv("GRIT_CONFIG_DIR", str(config_root))
    return config_root


@pytest.fixture()
def git_repo(tmp_path: Path) -> Path:
    """Create a minimal, initialised git repository in a temp directory."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", str(repo)], check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@grit.test"],
        cwd=str(repo), check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Grit Test"],
        cwd=str(repo), check=True, capture_output=True,
    )
    return repo
