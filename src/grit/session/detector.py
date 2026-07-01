"""Profile auto-detection from repository context.

Detection priority (highest to lowest):
  1. .grit file in repo root  (``profile = "Work"``)
  2. path_patterns glob match on repo path
  3. repo_name_patterns glob match on the repo directory's basename
  4. remote_patterns match on the origin remote URL
  5. → None (caller should prompt the user)
"""

from __future__ import annotations

import re
from pathlib import Path, PurePosixPath

from grit.models.profile import Profile

# ── .grit file ────────────────────────────────────────────────────────────────

def _read_grit_file(repo_path: str) -> str | None:
    """Return the profile name from a .grit file, or None if absent/invalid."""
    grit_file = Path(repo_path) / ".grit"
    if not grit_file.exists():
        return None
    for line in grit_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("profile"):
            parts = line.split("=", 1)
            if len(parts) == 2:
                return parts[1].strip().strip('"').strip("'")
    return None


# ── Path pattern matching ──────────────────────────────────────────────────────

def _matches_path_pattern(repo_path: str, pattern: str) -> bool:
    """Return True if *repo_path* matches the glob *pattern*.

    Supports ``~`` expansion and ``*`` / ``**`` wildcards via pathlib.
    """
    try:
        expanded = str(Path(pattern).expanduser())
        # Use PurePosixPath.match for cross-platform glob matching
        # Convert to forward slashes for consistent matching
        repo_norm = repo_path.replace("\\", "/")
        expanded_norm = expanded.replace("\\", "/")
        return PurePosixPath(repo_norm).match(expanded_norm)
    except Exception:
        return False


# ── Repo-name matching ─────────────────────────────────────────────────────────

def _matches_repo_name_pattern(repo_path: str, pattern: str) -> bool:
    """Return True if the repo directory's basename matches the glob *pattern*.

    Matches on the folder name alone (e.g. ``acme-backend``), independent of
    where the repo lives on disk or what remote it has.
    """
    try:
        name = Path(repo_path).name
        return PurePosixPath(name).match(pattern)
    except Exception:
        return False


# ── Remote URL matching ───────────────────────────────────────────────────────

def _matches_remote_pattern(remote_url: str | None, pattern: str) -> bool:
    """Return True if *remote_url* matches the glob *pattern*.

    Pattern examples: ``github.com/myorg/*``, ``gitlab.com/me/*``
    """
    if not remote_url:
        return False
    # Normalise SSH URLs (git@github.com:org/repo.git → github.com/org/repo)
    url = remote_url.strip()
    url = re.sub(r"^git@([^:]+):", r"\1/", url)
    url = re.sub(r"\.git$", "", url)
    url = re.sub(r"^https?://", "", url)
    try:
        return PurePosixPath(url).match(pattern)
    except Exception:
        return False


# ── Public API ────────────────────────────────────────────────────────────────

def detect_profile(repo_path: str, profiles: list[Profile]) -> Profile | None:
    """Return the best-matching profile for *repo_path*, or None.

    Profiles are checked in list order; the first match within each priority
    tier is returned.
    """
    # Priority 1: .grit file
    grit_profile_name = _read_grit_file(repo_path)
    if grit_profile_name:
        for p in profiles:
            if p.name == grit_profile_name:
                return p

    # Priority 2: path patterns
    for p in profiles:
        for pattern in p.path_patterns:
            if _matches_path_pattern(repo_path, pattern):
                return p

    # Priority 3: repo name patterns
    for p in profiles:
        for pattern in p.repo_name_patterns:
            if _matches_repo_name_pattern(repo_path, pattern):
                return p

    # Priority 4: remote URL patterns
    try:
        from grit.git.repo import get_remote_url
        remote_url = get_remote_url(repo_path)
    except Exception:
        remote_url = None

    for p in profiles:
        for pattern in p.remote_patterns:
            if _matches_remote_pattern(remote_url, pattern):
                return p

    return None
