from __future__ import annotations
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, AliasChoices, model_validator

from ..models import FeedbackCategory, FeedbackPriority, FeedbackStatus


class FeedbackBase(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    module: str = Field(min_length=2, max_length=80)
    category: FeedbackCategory
    priority: FeedbackPriority = FeedbackPriority.MEDIA
    title: str = Field(min_length=4, max_length=180)
    description: str = Field(min_length=10, max_length=4000)
    contact: str | None = Field(default=None, max_length=180)
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        alias="metadata_json",
        validation_alias=AliasChoices("metadata", "metadata_json"),
    )
    usage_context: dict[str, Any] = Field(default_factory=dict)


class FeedbackCreate(FeedbackBase):
    pass


class FeedbackStatusUpdate(BaseModel):
    status: FeedbackStatus
    resolution_notes: str | None = Field(default=None, max_length=4000)


class FeedbackResponse(FeedbackBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    tracking_id: str
    status: FeedbackStatus = FeedbackStatus.ABIERTO
    created_at: datetime
    updated_at: datetime
    resolution_notes: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _normalize_feedback(cls, value: object) -> object:
        if hasattr(value, "metadata_json"):
            return {
                "id": getattr(value, "id", None),
                "tracking_id": getattr(value, "tracking_id", None),
                "module": getattr(value, "module", None),
                "category": getattr(value, "category", None),
                "priority": getattr(value, "priority", None),
                "status": getattr(value, "status", FeedbackStatus.ABIERTO),
                "title": getattr(value, "title", None),
                "description": getattr(value, "description", None),
                "contact": getattr(value, "contact", None),
                "metadata_json": getattr(value, "metadata_json", {}) or {},
                "usage_context": getattr(value, "usage_context", {}) or {},
                "created_at": getattr(value, "created_at", None),
                "updated_at": getattr(value, "updated_at", None),
                "resolution_notes": getattr(value, "resolution_notes", None),
            }
        return value


class FeedbackSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tracking_id: str
    title: str
    module: str
    category: FeedbackCategory
    priority: FeedbackPriority
    status: FeedbackStatus
    created_at: datetime
    updated_at: datetime


class FeedbackUsageHotspot(BaseModel):
    module: str
    interactions_last_30d: int
    open_feedback: int
    priority_score: float


class FeedbackMetrics(BaseModel):
    totals: dict[str, int] = Field(default_factory=dict)
    by_category: dict[FeedbackCategory, int] = Field(default_factory=dict)
    by_priority: dict[FeedbackPriority, int] = Field(default_factory=dict)
    by_status: dict[FeedbackStatus, int] = Field(default_factory=dict)
    hotspots: list[FeedbackUsageHotspot] = Field(default_factory=list)
    recent_feedback: list[FeedbackSummary] = Field(default_factory=list)
