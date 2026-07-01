"""Unit tests for ProfileStore."""

from __future__ import annotations

from pathlib import Path

import pytest

from grit.exceptions import ProfileExistsError, ProfileNotFoundError, StorageCorruptError
from grit.models.profile import Profile
from grit.storage.profile_store import ProfileStore


@pytest.fixture()
def store(tmp_config_dir: Path) -> ProfileStore:
    return ProfileStore()


def _make_profile(name: str = "Work", email: str = "work@co.com") -> Profile:
    return Profile(name=name, email=email)


class TestAdd:
    def test_add_and_retrieve(self, store: ProfileStore) -> None:
        p = _make_profile()
        store.add(p)
        result = store.get_by_id(p.id)
        assert result.name == "Work"
        assert result.email == "work@co.com"

    def test_duplicate_name_raises(self, store: ProfileStore) -> None:
        store.add(_make_profile("Work"))
        with pytest.raises(ProfileExistsError):
            store.add(_make_profile("Work", email="other@co.com"))

    def test_multiple_profiles(self, store: ProfileStore) -> None:
        store.add(_make_profile("Work"))
        store.add(_make_profile("Personal", "me@gmail.com"))
        assert store.count() == 2


class TestGetByName:
    def test_found(self, store: ProfileStore) -> None:
        p = _make_profile("Work")
        store.add(p)
        assert store.get_by_name("Work").id == p.id

    def test_not_found(self, store: ProfileStore) -> None:
        with pytest.raises(ProfileNotFoundError):
            store.get_by_name("NonExistent")


class TestUpdate:
    def test_update_email(self, store: ProfileStore) -> None:
        p = _make_profile()
        store.add(p)
        p.email = "new@co.com"
        store.update(p)
        assert store.get_by_id(p.id).email == "new@co.com"

    def test_update_nonexistent_raises(self, store: ProfileStore) -> None:
        p = _make_profile()
        with pytest.raises(ProfileNotFoundError):
            store.update(p)


class TestDelete:
    def test_delete(self, store: ProfileStore) -> None:
        p = _make_profile()
        store.add(p)
        store.delete(p.id)
        assert store.count() == 0

    def test_delete_nonexistent_raises(self, store: ProfileStore) -> None:
        with pytest.raises(ProfileNotFoundError):
            store.delete("nonexistent-id")


class TestDefaultProfile:
    def test_set_default(self, store: ProfileStore) -> None:
        p = store.add(_make_profile("Work"))
        store.set_default(p.id)
        result = store.get_default()
        assert result is not None
        assert result.id == p.id

    def test_set_default_clears_previous(self, store: ProfileStore) -> None:
        p1 = store.add(_make_profile("Work"))
        p2 = store.add(_make_profile("Personal", "me@gmail.com"))
        store.set_default(p1.id)
        store.set_default(p2.id)
        assert store.get_by_id(p1.id).is_default is False
        assert store.get_by_id(p2.id).is_default is True

    def test_set_default_nonexistent_raises(self, store: ProfileStore) -> None:
        with pytest.raises(ProfileNotFoundError):
            store.set_default("nonexistent-id")

    def test_clear_default(self, store: ProfileStore) -> None:
        p = store.add(_make_profile("Work"))
        store.set_default(p.id)
        store.clear_default()
        assert store.get_default() is None

    def test_get_default_none_when_unset(self, store: ProfileStore) -> None:
        store.add(_make_profile("Work"))
        assert store.get_default() is None


class TestCorruptFile:
    def test_corrupt_json_raises_storage_error(self, tmp_config_dir: Path) -> None:
        profiles_path = tmp_config_dir / "profiles.json"
        profiles_path.write_text("not valid json", encoding="utf-8")
        store = ProfileStore()
        with pytest.raises(StorageCorruptError):
            store.get_all()

    def test_wrong_type_raises_storage_error(self, tmp_config_dir: Path) -> None:
        profiles_path = tmp_config_dir / "profiles.json"
        profiles_path.write_text('{"not": "a list"}', encoding="utf-8")
        store = ProfileStore()
        with pytest.raises(StorageCorruptError):
            store.get_all()
