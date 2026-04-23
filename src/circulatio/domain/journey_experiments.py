from __future__ import annotations

from typing import Literal, NotRequired, Required, TypedDict

from .types import CoachMoveKind, Id, ISODateString

JourneyExperimentStatus = Literal[
    "active",
    "quiet",
    "completed",
    "released",
    "archived",
    "deleted",
]

JourneyExperimentSource = Literal[
    "manual",
    "journey_page",
    "alive_today",
    "rhythmic_brief",
    "practice_followup",
    "weekly_review",
]


class JourneyExperimentRecord(TypedDict, total=False):
    id: Required[Id]
    userId: Required[Id]
    journeyId: Required[Id]
    title: Required[str]
    summary: Required[str]
    status: Required[JourneyExperimentStatus]
    source: Required[JourneyExperimentSource]
    bodyFirst: Required[bool]
    preferredMoveKind: NotRequired[CoachMoveKind]
    currentQuestion: NotRequired[str]
    suggestedActionText: NotRequired[str]
    originBriefId: NotRequired[Id]
    relatedPracticeSessionIds: Required[list[Id]]
    relatedBriefIds: Required[list[Id]]
    relatedSymbolIds: Required[list[Id]]
    relatedGoalTensionIds: Required[list[Id]]
    relatedBodyStateIds: Required[list[Id]]
    relatedResourceIds: Required[list[Id]]
    nextCheckInDueAt: NotRequired[ISODateString]
    cooldownUntil: NotRequired[ISODateString]
    createdAt: Required[ISODateString]
    updatedAt: Required[ISODateString]
    completedAt: NotRequired[ISODateString]
    releasedAt: NotRequired[ISODateString]
    archivedAt: NotRequired[ISODateString]
    deletedAt: NotRequired[ISODateString]


class JourneyExperimentUpdate(TypedDict, total=False):
    title: str
    summary: str
    status: JourneyExperimentStatus
    source: JourneyExperimentSource
    bodyFirst: bool
    preferredMoveKind: CoachMoveKind
    currentQuestion: str
    suggestedActionText: str
    originBriefId: Id
    relatedPracticeSessionIds: list[Id]
    relatedBriefIds: list[Id]
    relatedSymbolIds: list[Id]
    relatedGoalTensionIds: list[Id]
    relatedBodyStateIds: list[Id]
    relatedResourceIds: list[Id]
    nextCheckInDueAt: ISODateString
    cooldownUntil: ISODateString
    updatedAt: ISODateString
    completedAt: ISODateString
    releasedAt: ISODateString
    archivedAt: ISODateString
    deletedAt: ISODateString
