from __future__ import annotations

from typing import Literal, NotRequired, Required, TypedDict

from .types import (
    CoachCaptureContract,
    CoachLoopKind,
    CoachMoveKind,
    Id,
    ISODateString,
    ResourceInvitationSummary,
)

ProactiveBriefType = Literal[
    "daily",
    "weekly",
    "practice_followup",
    "series_followup",
    "journey_checkin",
    "threshold_invitation",
    "chapter_invitation",
    "resource_invitation",
    "return_invitation",
    "bridge_invitation",
    "analysis_packet_invitation",
]
ProactiveBriefStatus = Literal["candidate", "shown", "dismissed", "acted_on", "deleted"]
RhythmBriefSource = Literal["manual", "scheduled", "review", "practice_followup"]


class RhythmicBriefSeed(TypedDict, total=False):
    briefType: Required[ProactiveBriefType]
    triggerKey: Required[str]
    titleHint: Required[str]
    summaryHint: Required[str]
    suggestedActionHint: NotRequired[str]
    priority: Required[int]
    relatedJourneyIds: Required[list[Id]]
    relatedExperimentIds: NotRequired[list[Id]]
    relatedMaterialIds: Required[list[Id]]
    relatedSymbolIds: Required[list[Id]]
    relatedPracticeSessionIds: Required[list[Id]]
    evidenceIds: Required[list[Id]]
    reason: Required[str]
    coachLoopKey: NotRequired[str]
    coachLoopKind: NotRequired[CoachLoopKind]
    coachMoveKind: NotRequired[CoachMoveKind]
    capture: NotRequired[CoachCaptureContract]
    resourceInvitation: NotRequired[ResourceInvitationSummary]
    relatedResourceIds: NotRequired[list[Id]]


class ProactiveBriefRecord(TypedDict, total=False):
    id: Required[Id]
    userId: Required[Id]
    briefType: Required[ProactiveBriefType]
    status: Required[ProactiveBriefStatus]
    title: Required[str]
    summary: Required[str]
    triggerKey: NotRequired[str]
    source: NotRequired[RhythmBriefSource]
    priority: NotRequired[int]
    suggestedAction: NotRequired[str]
    renderedResponse: NotRequired[str]
    relatedJourneyIds: Required[list[Id]]
    relatedExperimentIds: NotRequired[list[Id]]
    relatedMaterialIds: Required[list[Id]]
    relatedSymbolIds: Required[list[Id]]
    relatedPracticeSessionIds: Required[list[Id]]
    evidenceIds: Required[list[Id]]
    coachLoopKey: NotRequired[str]
    coachLoopKind: NotRequired[CoachLoopKind]
    coachMoveKind: NotRequired[CoachMoveKind]
    capture: NotRequired[CoachCaptureContract]
    resourceInvitation: NotRequired[ResourceInvitationSummary]
    relatedResourceIds: NotRequired[list[Id]]
    createdAt: Required[ISODateString]
    shownAt: NotRequired[ISODateString]
    actedOnAt: NotRequired[ISODateString]
    dismissedAt: NotRequired[ISODateString]
    updatedAt: NotRequired[ISODateString]
    expiresAt: NotRequired[ISODateString]
    cooldownUntil: NotRequired[ISODateString]
    deletedAt: NotRequired[ISODateString]


class ProactiveBriefUpdate(TypedDict, total=False):
    status: ProactiveBriefStatus
    title: str
    summary: str
    triggerKey: str
    source: RhythmBriefSource
    priority: int
    suggestedAction: str
    renderedResponse: str
    relatedJourneyIds: list[Id]
    relatedExperimentIds: list[Id]
    relatedMaterialIds: list[Id]
    relatedSymbolIds: list[Id]
    relatedPracticeSessionIds: list[Id]
    evidenceIds: list[Id]
    coachLoopKey: str
    coachLoopKind: CoachLoopKind
    coachMoveKind: CoachMoveKind
    capture: CoachCaptureContract
    resourceInvitation: ResourceInvitationSummary
    relatedResourceIds: list[Id]
    shownAt: ISODateString
    actedOnAt: ISODateString
    dismissedAt: ISODateString
    updatedAt: ISODateString
    expiresAt: ISODateString
    cooldownUntil: ISODateString
    deletedAt: ISODateString
