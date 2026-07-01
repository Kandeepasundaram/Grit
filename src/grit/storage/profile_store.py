"""CRUD storage for Profile objects backed by profiles.json."""

from __future__ import annotations

import json
from typing import Any

from grit.config.paths import profiles_file
from grit.exceptions import ProfileExistsError, ProfileNotFoundError, StorageCorruptError
from grit.models.profile import Profile
from grit.storage._lock import file_lock


class ProfileStore:
    """Thread-safe CRUD store for profiles.

    All mutating methods write atomically (tmp → replace) so a crash mid-write
    cannot corrupt the stored data.
    """

    def __init__(self) -> None:
        self._path = profiles_file()

    # ── Private helpers ───────────────────────────────────────────────────────

    def _load_raw(self) -> list[dict[str, Any]]:
        if not self._path.exists():
            return []
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            raise StorageCorruptError(str(self._path), str(exc)) from exc
        if not isinstance(data, list):
            raise StorageCorruptError(str(self._path), "expected a JSON array")
        return data

    def _save_raw(self, profiles: list[Profile]) -> None:
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps([p.to_dict() for p in profiles], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        tmp.replace(self._path)

    # ── Public API ────────────────────────────────────────────────────────────

    def get_all(self) -> list[Profile]:
        """Return all profiles, ordered as stored."""
        with file_lock(self._path):
            return [Profile.from_dict(d) for d in self._load_raw()]

    def get_by_id(self, profile_id: str) -> Profile:
        for p in self.get_all():
            if p.id == profile_id:
                return p
        raise ProfileNotFoundError(profile_id)

    def get_by_name(self, name: str) -> Profile:
        for p in self.get_all():
            if p.name == name:
                return p
        raise ProfileNotFoundError(name)

    def add(self, profile: Profile) -> Profile:
        """Persist a new profile. Raises ProfileExistsError if name already taken.

        Raises ValueError if the current subscription tier's profile limit would
        be exceeded (free tier: max 5 profiles).
        """
        with file_lock(self._path):
            profiles = [Profile.from_dict(d) for d in self._load_raw()]
            if any(p.name == profile.name for p in profiles):
                raise ProfileExistsError(profile.name)
            # Tier enforcement — import lazily to avoid circular imports at startup
            try:
                from grit.config.subscription import enforce_profile_limit
                enforce_profile_limit(len(profiles))
            except ImportError:
                pass  # subscription module not yet available (tests / early installs)
            profiles.append(profile)
            self._save_raw(profiles)
        return profile

    def update(self, profile: Profile) -> Profile:
        """Replace an existing profile by id. Raises ProfileNotFoundError if missing."""
        with file_lock(self._path):
            profiles = [Profile.from_dict(d) for d in self._load_raw()]
            for i, p in enumerate(profiles):
                if p.id == profile.id:
                    profile.touch()
                    profiles[i] = profile
                    self._save_raw(profiles)
                    return profile
        raise ProfileNotFoundError(profile.id)

    def delete(self, profile_id: str) -> None:
        """Remove profile by id. Raises ProfileNotFoundError if not present."""
        with file_lock(self._path):
            profiles = [Profile.from_dict(d) for d in self._load_raw()]
            new_profiles = [p for p in profiles if p.id != profile_id]
            if len(new_profiles) == len(profiles):
                raise ProfileNotFoundError(profile_id)
            self._save_raw(new_profiles)

    def count(self) -> int:
        return len(self.get_all())

    def set_default(self, profile_id: str) -> Profile:
        """Mark a profile as the fallback default, clearing any other default.

        Raises ProfileNotFoundError if profile_id doesn't exist.
        """
        with file_lock(self._path):
            profiles = [Profile.from_dict(d) for d in self._load_raw()]
            target: Profile | None = None
            for p in profiles:
                if p.id == profile_id:
                    p.is_default = True
                    target = p
                else:
                    p.is_default = False
            if target is None:
                raise ProfileNotFoundError(profile_id)
            self._save_raw(profiles)
            return target

    def clear_default(self) -> None:
        """Clear the default flag on every profile, if any is set."""
        with file_lock(self._path):
            profiles = [Profile.from_dict(d) for d in self._load_raw()]
            for p in profiles:
                p.is_default = False
            self._save_raw(profiles)

    def get_default(self) -> Profile | None:
        """Return the profile flagged as default, or None."""
        for p in self.get_all():
            if p.is_default:
                return p
        return None
