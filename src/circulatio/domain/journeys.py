from __future__ import annotations

from typing import Literal, NotRequired, Required, TypedDict

from .types import Id, ISODateString

JourneyStatus = Literal["active", "paused", "completed", "archived", "deleted"]


class JourneyRecord(TypedDict, total=False):
    id: Required[Id]
    userId: Required[Id]
    label: Required[str]
    status: Required[JourneyStatus]
    relatedMaterialIds: Required[list[Id]]
    relatedSymbolIds: Required[list[Id]]
    relatedPatternIds: Required[list[Id]]
    relatedDreamSeriesIds: Required[list[Id]]
    relatedGoalIds: Required[list[Id]]
    relatedBodyStateIds: Required[list[Id]]
    currentQuestion: NotRequired[str]
    lastBriefedAt: NotRequired[ISODateString]
    nextReviewDueAt: NotRequired[ISODateString]
    createdAt: Required[ISODateString]
    updatedAt: Required[ISODateString]
    deletedAt: NotRequired[ISODateString]


class JourneyUpdate(TypedDict, total=False):
    label: str
    status: JourneyStatus
    relatedMaterialIds: list[Id]
    relatedSymbolIds: list[Id]
    relatedPatternIds: list[Id]
    relatedDreamSeriesIds: list[Id]
    relatedGoalIds: list[Id]
    relatedBodyStateIds: list[Id]
    currentQuestion: str
    lastBriefedAt: ISODateString
    nextReviewDueAt: ISODateString
    updatedAt: ISODateString
    deletedAt: ISODateString
