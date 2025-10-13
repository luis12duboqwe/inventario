"""Servicios para gestionar las actualizaciones de Softmobile."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from packaging.version import InvalidVersion, Version
from pydantic import ValidationError

from ..config import settings
from ..schemas import ReleaseInfo, UpdateStatus


def _read_feed(path: str | Path | None = None) -> dict[str, object]:
    file_path = Path(path or settings.update_feed_path)
    if not file_path.exists():
        return {"releases": []}
    data = json.loads(file_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return {"releases": []}
    return data


def _parse_releases(raw_releases: Iterable[object]) -> list[ReleaseInfo]:
    releases: list[ReleaseInfo] = []
    for item in raw_releases:
        if not isinstance(item, dict):
            continue
        try:
            release = ReleaseInfo.model_validate(item)
        except ValidationError:
            continue
        releases.append(release)
    releases.sort(key=_release_sort_key, reverse=True)
    return releases


def _release_sort_key(release: ReleaseInfo) -> Version:
    try:
        return Version(release.version)
    except InvalidVersion:
        return Version("0")


def get_release_history(*, limit: int | None = None, path: str | Path | None = None) -> list[ReleaseInfo]:
    feed = _read_feed(path)
    releases = _parse_releases(feed.get("releases", []))
    if limit is None:
        return releases
    return releases[:limit]


def get_update_status(*, path: str | Path | None = None) -> UpdateStatus:
    releases = get_release_history(path=path)
    latest_release = releases[0] if releases else None

    latest_version = latest_release.version if latest_release else None
    is_update_available = False

    if latest_release is not None and latest_version is not None:
        try:
            is_update_available = Version(latest_version) > Version(settings.version)
        except InvalidVersion:
            is_update_available = latest_version != settings.version

    return UpdateStatus(
        current_version=settings.version,
        latest_version=latest_version,
        is_update_available=is_update_available,
        latest_release=latest_release,
    )

