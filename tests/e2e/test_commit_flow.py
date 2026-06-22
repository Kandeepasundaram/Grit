"""End-to-end: full commit flow with daemon, hook, session, and git config."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from grit.ipc.client import ping, send_request
from grit.models.profile import Profile
from grit.storage.profile_store import ProfileStore


@pytest.mark.e2e
@pytest.mark.slow
def test_full_commit_applies_profile(tmp_config_dir: Path, git_repo: Path) -> None:
    """
    1. Create a Work profile
    2. Start the daemon
    3. Set a session for the temp repo
    4. Make a commit
    5. Verify git log shows the Work email
    """
    # Step 1: Create profile
    profile = Profile(name="Work", email="work@e2e.test")
    ProfileStore().add(profile)

    # Step 2: Start daemon
    env = {**os.environ, "GRIT_CONFIG_DIR": str(tmp_config_dir)}
    proc = subprocess.Popen(
        [sys.executable, "-m", "grit.daemon.server"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        deadline = time.time() + 5
        while time.time() < deadline:
            if ping():
                break
            time.sleep(0.1)
        else:
            pytest.fail("Daemon did not start in time")

        # Step 3: Set session for the repo
        resp = send_request("switch-profile", {
            "repo_path": str(git_repo),
            "profile_id": profile.id,
        })
        assert resp.get("status") == "ok"

        # Step 4: Make a commit
        (git_repo / "README.md").write_text("hello\n")
        subprocess.run(["git", "add", "."], cwd=str(git_repo), check=True)
        subprocess.run(
            ["git", "commit", "-m", "E2E test commit"],
            cwd=str(git_repo),
            check=True,
            capture_output=True,
        )

        # Step 5: Verify author email in git log
        result = subprocess.run(
            ["git", "log", "--format=%ae", "-1"],
            cwd=str(git_repo),
            capture_output=True,
            text=True,
            check=True,
        )
        assert result.stdout.strip() == "work@e2e.test", (
            f"Expected work@e2e.test but got {result.stdout.strip()!r}"
        )
    finally:
        proc.terminate()
        proc.wait(timeout=10)
