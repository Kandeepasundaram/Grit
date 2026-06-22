"""Unit tests for session/detector.py."""

from __future__ import annotations

from pathlib import Path

import pytest

from grit.models.profile import Profile
from grit.session.detector import detect_profile, _matches_path_pattern, _matches_remote_pattern


def _make_profile(
    name: str = "Work",
    email: str = "w@co.com",
    path_patterns: list = None,
    remote_patterns: list = None,
) -> Profile:
    return Profile(
        name=name,
        email=email,
        path_patterns=path_patterns or [],
        remote_patterns=remote_patterns or [],
    )


class TestPathPatternMatching:
    def test_simple_wildcard(self) -> None:
        # ~/work/* should match ~/work/myproject
        home = str(Path.home())
        assert _matches_path_pattern(f"{home}/work/myproject", "~/work/*")

    def test_no_match(self) -> None:
        home = str(Path.home())
        assert not _matches_path_pattern(f"{home}/personal/myproject", "~/work/*")

    def test_nested_wildcard(self) -> None:
        home = str(Path.home())
        assert _matches_path_pattern(f"{home}/clients/acme/website", "~/clients/acme/*")

    def test_invalid_pattern_returns_false(self) -> None:
        assert not _matches_path_pattern("/some/repo", "")


class TestRemotePatternMatching:
    def test_https_url(self) -> None:
        assert _matches_remote_pattern(
            "https://github.com/myorg/myrepo", "github.com/myorg/*"
        )

    def test_ssh_url(self) -> None:
        assert _matches_remote_pattern(
            "git@github.com:myorg/myrepo.git", "github.com/myorg/*"
        )

    def test_no_match(self) -> None:
        assert not _matches_remote_pattern(
            "https://github.com/otherorg/myrepo", "github.com/myorg/*"
        )

    def test_none_url_returns_false(self) -> None:
        assert not _matches_remote_pattern(None, "github.com/myorg/*")


class TestDetectProfile:
    def test_no_profiles_returns_none(self, tmp_path: Path) -> None:
        assert detect_profile(str(tmp_path), []) is None

    def test_path_pattern_match(self, tmp_path: Path) -> None:
        home = str(Path.home())
        # Use tmp_path as a stand-in path; supply an exact path pattern match
        profile = _make_profile(path_patterns=[str(tmp_path) + "/*"])
        sub = tmp_path / "subrepo"
        sub.mkdir()
        result = detect_profile(str(sub), [profile])
        assert result is not None
        assert result.name == "Work"

    def test_grit_file_takes_priority(self, tmp_path: Path) -> None:
        # Create a .grit file in the repo
        (tmp_path / ".grit").write_text('profile = "Personal"\n', encoding="utf-8")
        work = _make_profile("Work", path_patterns=[str(tmp_path)])
        personal = _make_profile("Personal", email="me@gmail.com")
        result = detect_profile(str(tmp_path), [work, personal])
        assert result is not None
        assert result.name == "Personal"

    def test_no_match_returns_none(self, tmp_path: Path) -> None:
        profile = _make_profile(path_patterns=["~/totally/different/*"])
        result = detect_profile(str(tmp_path), [profile])
        assert result is None

    def test_first_matching_profile_returned(self, tmp_path: Path) -> None:
        p1 = _make_profile("First", path_patterns=[str(tmp_path) + "*"])
        p2 = _make_profile("Second", email="s@co.com", path_patterns=[str(tmp_path) + "*"])
        result = detect_profile(str(tmp_path), [p1, p2])
        assert result is not None
        assert result.name == "First"
