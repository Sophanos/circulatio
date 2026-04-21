from __future__ import annotations

from typing import Literal, NotRequired, Required, TypedDict

from .types import Id, ISODateString


class UserAdaptationProfileRecord(TypedDict, total=False):
    id: Required[Id]
    userId: Required[Id]
    explicitPreferences: Required[dict[str, object]]
    learnedSignals: Required[dict[str, object]]
    sampleCounts: Required[dict[str, int]]
    createdAt: Required[ISODateString]
    updatedAt: Required[ISODateString]
    status: Required[Literal["active", "deleted"]]


class UserAdaptationProfileUpdate(TypedDict, total=False):
    explicitPreferences: dict[str, object]
    learnedSignals: dict[str, object]
    sampleCounts: dict[str, int]
    updatedAt: ISODateString
    status: Literal["active", "deleted"]


class AdaptationSignalEvent(TypedDict, total=False):
    eventType: Required[str]
    timestamp: Required[ISODateString]
    signals: Required[dict[str, object]]
    success: NotRequired[bool]
    sampleWeight: NotRequired[int]


class RhythmCadenceHints(TypedDict, total=False):
    maxBriefsPerDay: Required[int]
    minimumHoursBetweenBriefs: Required[int]
    dismissedTriggerCooldownHours: Required[int]
    actedOnTriggerCooldownHours: Required[int]
    quietHours: NotRequired[dict[str, str]]
    maturity: Required[Literal["default", "learning", "mature"]]
