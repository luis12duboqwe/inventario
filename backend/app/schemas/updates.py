from __future__ import annotations
from datetime import date
from pydantic import BaseModel, Field


class ReleaseInfo(BaseModel):
    version: str
    release_date: date
    notes: str
    download_url: str | None = None


class UpdateStatus(BaseModel):
    current_version: str
    latest_version: str | None
    is_update_available: bool
    latest_release: ReleaseInfo | None
