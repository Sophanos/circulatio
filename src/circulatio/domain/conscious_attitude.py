from __future__ import annotations

from typing import Literal, NotRequired, Required, TypedDict

from .records import DeletionMode
from .types import Confidence, Id, ISODateString, PrivacyClass

ConsciousAttitudeSnapshotStatus = Literal[
    "candidate",
    "user_confirmed",
    "superseded",
    "deleted",
    "active",
]
ConsciousAttitudeSource = Literal[
    "manual_checkin",
    "reflection",
    "goal_checkin",
    "weekly_review",
    "interpretation_input",
    "system_candidate",
    "user_reported",
]


class ConsciousAttitudeSnapshotRecord(TypedDict, total=False):
    id: Required[Id]
    userId: Required[Id]
    source: Required[ConsciousAttitudeSource]
    status: Required[ConsciousAttitudeSnapshotStatus]
    windowStart: NotRequired[ISODateString]
    windowEnd: NotRequired[ISODateString]
    stanceSummary: Required[str]
    activeValues: Required[list[str]]
    activeConflicts: Required[list[str]]
    avoidedThemes: Required[list[str]]
    emotionalTone: NotRequired[str]
    egoPosition: NotRequired[str]
    confidence: Required[Confidence]
    evidenceIds: Required[list[Id]]
    relatedMaterialIds: Required[list[Id]]
    relatedGoalIds: Required[list[Id]]
    privacyClass: Required[PrivacyClass]
    createdAt: Required[ISODateString]
    updatedAt: Required[ISODateString]
    deletedAt: NotRequired[ISODateString]


class ConsciousAttitudeSnapshotUpdate(TypedDict, total=False):
    source: ConsciousAttitudeSource
    status: ConsciousAttitudeSnapshotStatus
    windowStart: ISODateString
    windowEnd: ISODateString
    stanceSummary: str
    activeValues: list[str]
    activeConflicts: list[str]
    avoidedThemes: list[str]
    emotionalTone: str
    egoPosition: str
    confidence: Confidence
    evidenceIds: list[Id]
    relatedMaterialIds: list[Id]
    relatedGoalIds: list[Id]
    privacyClass: PrivacyClass
    updatedAt: ISODateString
    deletedAt: ISODateString


class ConsciousAttitudeSnapshotFilters(TypedDict, total=False):
    windowStart: ISODateString
    windowEnd: ISODateString
    statuses: list[ConsciousAttitudeSnapshotStatus]
    limit: int


__all__ = [
    "ConsciousAttitudeSnapshotFilters",
    "ConsciousAttitudeSnapshotRecord",
    "ConsciousAttitudeSnapshotStatus",
    "ConsciousAttitudeSnapshotUpdate",
    "ConsciousAttitudeSource",
    "DeletionMode",
]
