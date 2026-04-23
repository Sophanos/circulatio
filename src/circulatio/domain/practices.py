from __future__ import annotations

from typing import Literal, NotRequired, Required, TypedDict

from .types import (
    CoachLoopKind,
    CoachMoveKind,
    Id,
    ISODateString,
    PracticeScriptStep,
    PracticeType,
    ResourceInvitationSummary,
    SafetyFlag,
)

PracticeSessionStatus = Literal["recommended", "accepted", "completed", "skipped", "deleted"]
PracticeSessionSource = Literal[
    "interpretation",
    "weekly_review",
    "alive_today",
    "manual",
    "rhythmic_brief",
    "practice_followup",
    "threshold_review",
    "living_myth_review",
    "analysis_packet",
]
PracticeLifecycleAction = Literal[
    "recommended",
    "accepted",
    "skipped",
    "completed",
    "outcome_recorded",
]


class PracticeSessionRecord(TypedDict, total=False):
    id: Required[Id]
    userId: Required[Id]
    materialId: NotRequired[Id]
    runId: NotRequired[Id]
    practiceType: Required[PracticeType]
    target: NotRequired[str]
    reason: Required[str]
    instructions: Required[list[str]]
    durationMinutes: Required[int]
    contraindicationsChecked: Required[list[SafetyFlag]]
    requiresConsent: Required[bool]
    status: Required[PracticeSessionStatus]
    outcome: NotRequired[str]
    activationBefore: NotRequired[Literal["low", "moderate", "high"]]
    activationAfter: NotRequired[Literal["low", "moderate", "high"]]
    outcomeEvidenceIds: NotRequired[list[Id]]
    source: NotRequired[PracticeSessionSource]
    templateId: NotRequired[Id]
    modality: NotRequired[str]
    intensity: NotRequired[str]
    script: NotRequired[list[PracticeScriptStep]]
    followUpPrompt: NotRequired[str]
    adaptationSignals: NotRequired[dict[str, object]]
    acceptedAt: NotRequired[ISODateString]
    skippedAt: NotRequired[ISODateString]
    skipReason: NotRequired[str]
    nextFollowUpDueAt: NotRequired[ISODateString]
    lastFollowUpBriefId: NotRequired[Id]
    followUpCount: NotRequired[int]
    relatedBriefId: NotRequired[Id]
    relatedJourneyIds: NotRequired[list[Id]]
    relatedExperimentIds: NotRequired[list[Id]]
    coachLoopKey: NotRequired[Id]
    coachLoopKind: NotRequired[CoachLoopKind]
    coachMoveKind: NotRequired[CoachMoveKind]
    resourceInvitationId: NotRequired[Id]
    resourceInvitation: NotRequired[ResourceInvitationSummary]
    relatedResourceIds: NotRequired[list[Id]]
    createdAt: Required[ISODateString]
    updatedAt: Required[ISODateString]
    deletedAt: NotRequired[ISODateString]
    completedAt: NotRequired[ISODateString]


class PracticeSessionUpdate(TypedDict, total=False):
    materialId: Id
    runId: Id
    practiceType: PracticeType
    target: str
    reason: str
    instructions: list[str]
    durationMinutes: int
    contraindicationsChecked: list[SafetyFlag]
    requiresConsent: bool
    status: PracticeSessionStatus
    outcome: str
    activationBefore: Literal["low", "moderate", "high"]
    activationAfter: Literal["low", "moderate", "high"]
    outcomeEvidenceIds: list[Id]
    source: PracticeSessionSource
    templateId: Id
    modality: str
    intensity: str
    script: list[PracticeScriptStep]
    followUpPrompt: str
    adaptationSignals: dict[str, object]
    acceptedAt: ISODateString
    skippedAt: ISODateString
    skipReason: str
    nextFollowUpDueAt: ISODateString
    lastFollowUpBriefId: Id
    followUpCount: int
    relatedBriefId: Id
    relatedJourneyIds: list[Id]
    relatedExperimentIds: list[Id]
    coachLoopKey: Id
    coachLoopKind: CoachLoopKind
    coachMoveKind: CoachMoveKind
    resourceInvitationId: Id
    resourceInvitation: ResourceInvitationSummary
    relatedResourceIds: list[Id]
    updatedAt: ISODateString
    deletedAt: ISODateString
    completedAt: ISODateString


class PracticeLifecycleDefaults(TypedDict, total=False):
    source: PracticeSessionSource
    nextFollowUpDueAt: ISODateString
    relatedBriefId: Id
    followUpCount: int
