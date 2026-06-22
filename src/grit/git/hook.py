"""Git hook installation and removal."""

from __future__ import annotations

import os
import stat
from pathlib import Path
from typing import Optional

from grit.constants import GRIT_HOOK_SENTINEL
from grit.exceptions import HookInstallError

# The hook script injected into .git/hooks/pre-commit
_HOOK_BLOCK = """\
{sentinel}
grit hook pre-commit --repo "$(git rev-parse --show-toplevel)"
GRIT_EXIT=$?
if [ $GRIT_EXIT -ne 0 ]; then
  exit $GRIT_EXIT
fi
""".format(sentinel=GRIT_HOOK_SENTINEL)

_SHEBANG = "#!/usr/bin/env sh\n"


def _hook_path(repo_path: str) -> Path:
    return Path(repo_path) / ".git" / "hooks" / "pre-commit"


def is_installed(repo_path: str) -> bool:
    """Return True if Grit's hook block is present in the pre-commit hook."""
    hp = _hook_path(repo_path)
    if not hp.exists():
        return False
    return GRIT_HOOK_SENTINEL in hp.read_text(encoding="utf-8", errors="replace")


def install(repo_path: str) -> None:
    """Install Grit's pre-commit hook into *repo_path*.

    If a pre-commit hook already exists and does not contain Grit's block,
    the block is appended after the existing content.  Existing hooks are
    never overwritten.
    """
    hooks_dir = Path(repo_path) / ".git" / "hooks"
    if not hooks_dir.exists():
        raise HookInstallError(f"No .git/hooks directory found in {repo_path!r}")

    hp = _hook_path(repo_path)
    if is_installed(repo_path):
        return  # already installed

    if hp.exists():
        existing = hp.read_text(encoding="utf-8")
        new_content = existing.rstrip("\n") + "\n\n" + _HOOK_BLOCK
    else:
        new_content = _SHEBANG + "\n" + _HOOK_BLOCK

    hp.write_text(new_content, encoding="utf-8")
    # Make executable (no-op on Windows but harmless)
    current_mode = hp.stat().st_mode
    hp.chmod(current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def uninstall(repo_path: str) -> None:
    """Remove Grit's block from the pre-commit hook.

    If the hook only contains Grit's block (possibly with just a shebang),
    the entire file is removed.  Otherwise only the block is stripped.
    """
    hp = _hook_path(repo_path)
    if not hp.exists():
        return
    if not is_installed(repo_path):
        return

    content = hp.read_text(encoding="utf-8")
    # Remove the Grit block (from sentinel to the blank line after it)
    lines = content.splitlines(keepends=True)
    new_lines = []
    skip = False
    for line in lines:
        if GRIT_HOOK_SENTINEL in line:
            skip = True
        if skip:
            # Stop skipping after the blank line that follows the block
            if line.strip() == "" and GRIT_HOOK_SENTINEL not in line:
                skip = False
            continue
        new_lines.append(line)

    remaining = "".join(new_lines).strip()
    if not remaining or remaining == _SHEBANG.strip():
        hp.unlink()
    else:
        hp.write_text("".join(new_lines), encoding="utf-8")
