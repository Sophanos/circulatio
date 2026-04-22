from __future__ import annotations

from typing import Literal, NotRequired, Required, TypedDict

from .interpretations import ProposalDecisionRecord
from .types import Id, ISODateString, MemoryWritePlan, ThreadDigest

MethodStateResponseSource = Literal[
    "clarifying_answer",
    "freeform_followup",
    "body_note",
    "amplification_answer",
    "relational_scene",
    "dream_dynamics",
    "goal_feedback",
    "practice_feedback",
    "consent_update",
]

MethodStateCaptureTargetKind = Literal[
    "body_state",
    "personal_amplification",
    "reality_anchors",
    "conscious_attitude",
    "goal",
    "goal_tension",
    "practice_outcome",
    "practice_preference",
    "relational_scene",
    "dream_dynamics",
    "threshold_process",
    "numinous_encounter",
    "aesthetic_resonance",
    "inner_outer_correspondence",
    "projection_hypothesis",
    "typology_lens",
    "living_myth_question",
    "consent_preference",
]

MethodStateCaptureApplication = Literal[
    "direct_write",
    "candidate_write",
    "approval_proposal",
    "needs_clarification",
    "withheld",
    "ignore",
]

MethodStateCaptureRunStatus = Literal[
    "processing",
    "completed",
    "no_capture",
    "failed",
    "deleted",
]


class MethodStateAnchorRefs(TypedDict, total=False):
    materialId: NotRequired[Id]
    runId: NotRequired[Id]
    promptId: NotRequired[Id]
    clarificationRefKey: NotRequired[str]
    practiceSessionId: NotRequired[Id]
    briefId: NotRequired[Id]
    reviewId: NotRequired[Id]
    goalId: NotRequired[Id]
    journeyId: NotRequired[Id]
    coachLoopKey: NotRequired[str]
    coachMoveId: NotRequired[Id]
    resourceInvitationId: NotRequired[Id]


class MethodStateEvidenceSpan(TypedDict, total=False):
    refKey: Required[str]
    quote: NotRequired[str]
    summary: NotRequired[str]
    targetKinds: Required[list[MethodStateCaptureTargetKind]]


class MethodStateCaptureCandidate(TypedDict, total=False):
    targetKind: Required[MethodStateCaptureTargetKind]
    application: Required[MethodStateCaptureApplication]
    confidence: Required[Literal["low", "medium", "high"]]
    payload: Required[dict[str, object]]
    supportingEvidenceRefs: Required[list[str]]
    consentScopes: Required[list[str]]
    reason: Required[str]


class MethodStateAppliedEntityRef(TypedDict):
    entityType: str
    entityId: Id


class MethodStateRoutingInput(TypedDict, total=False):
    userId: Required[Id]
    responseText: Required[str]
    source: Required[MethodStateResponseSource]
    anchorRefs: Required[MethodStateAnchorRefs]
    expectedTargets: Required[list[MethodStateCaptureTargetKind]]
    clarificationIntent: NotRequired[dict[str, object]]
    methodContextSnapshot: NotRequired[dict[str, object]]
    threadDigests: NotRequired[list[ThreadDigest]]
    lifeContextSnapshot: NotRequired[dict[str, object]]
    hermesMemoryContext: NotRequired[dict[str, object]]
    safetyContext: NotRequired[dict[str, object]]
    consentPreferences: Required[list[dict[str, object]]]
    recentPromptOrRunSummary: NotRequired[str]
    options: NotRequired[dict[str, object]]


class MethodStateCaptureRunRecord(TypedDict, total=False):
    id: Required[Id]
    userId: Required[Id]
    idempotencyKey: Required[str]
    source: Required[MethodStateResponseSource]
    status: Required[MethodStateCaptureRunStatus]
    anchorRefs: Required[MethodStateAnchorRefs]
    responseMaterialId: Required[Id]
    evidenceIds: Required[list[Id]]
    expectedTargets: Required[list[MethodStateCaptureTargetKind]]
    extractionResult: Required[dict[str, object]]
    appliedEntityRefs: Required[list[MethodStateAppliedEntityRef]]
    memoryWritePlan: Required[MemoryWritePlan]
    proposalDecisions: Required[list[ProposalDecisionRecord]]
    failure: NotRequired[dict[str, object]]
    createdAt: Required[ISODateString]
    updatedAt: Required[ISODateString]
    deletedAt: NotRequired[ISODateString]


class MethodStateCaptureRunUpdate(TypedDict, total=False):
    status: MethodStateCaptureRunStatus
    anchorRefs: MethodStateAnchorRefs
    responseMaterialId: Id
    evidenceIds: list[Id]
    expectedTargets: list[MethodStateCaptureTargetKind]
    extractionResult: dict[str, object]
    appliedEntityRefs: list[MethodStateAppliedEntityRef]
    memoryWritePlan: MemoryWritePlan
    proposalDecisions: list[ProposalDecisionRecord]
    failure: dict[str, object]
    updatedAt: ISODateString
    deletedAt: ISODateString


class MethodStateCaptureResult(TypedDict, total=False):
    captureRun: Required[MethodStateCaptureRunRecord]
    responseMaterialId: Required[Id]
    evidenceIds: Required[list[Id]]
    appliedEntityRefs: Required[list[MethodStateAppliedEntityRef]]
    pendingProposalIds: Required[list[Id]]
    followUpPrompts: Required[list[str]]
    withheldCandidates: Required[list[dict[str, object]]]
    warnings: Required[list[str]]


__all__ = [
    "MethodStateAnchorRefs",
    "MethodStateAppliedEntityRef",
    "MethodStateCaptureApplication",
    "MethodStateCaptureCandidate",
    "MethodStateCaptureResult",
    "MethodStateCaptureRunRecord",
    "MethodStateCaptureRunStatus",
    "MethodStateCaptureRunUpdate",
    "MethodStateCaptureTargetKind",
    "MethodStateEvidenceSpan",
    "MethodStateResponseSource",
    "MethodStateRoutingInput",
]
