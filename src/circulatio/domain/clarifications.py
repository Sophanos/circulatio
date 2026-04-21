from __future__ import annotations

from typing import Literal, NotRequired, Required, TypedDict

from .types import Id, ISODateString, PrivacyClass

ClarificationIntentType = Literal[
    "personal_association",
    "body_signal",
    "conscious_stance",
    "goal_pressure",
    "reality_anchor",
    "threshold_orientation",
    "relational_scene",
    "consent_check",
    "interpretation_preference",
    "safety_pacing",
    "typology_feedback",
    "other",
]

ClarificationCaptureTarget = Literal[
    "answer_only",
    "body_state",
    "conscious_attitude",
    "goal",
    "goal_tension",
    "personal_amplification",
    "reality_anchors",
    "threshold_process",
    "relational_scene",
    "inner_outer_correspondence",
    "numinous_encounter",
    "aesthetic_resonance",
    "consent_preference",
    "interpretation_preference",
    "typology_feedback",
]

ExpectedAnswerKind = Literal[
    "free_text",
    "yes_no",
    "single_choice",
    "multi_choice",
    "body_state",
    "scale",
    "structured_payload",
]

ClarificationPromptStatus = Literal[
    "pending",
    "answered",
    "answered_unrouted",
    "skipped",
    "expired",
    "deleted",
]

ClarificationRoutingStatus = Literal[
    "routing_pending",
    "routed",
    "unrouted",
    "needs_review",
    "skipped",
    "rejected",
]


class ClarificationCreatedRecordRef(TypedDict):
    recordType: str
    id: Id


class ClarificationPromptRecord(TypedDict, total=False):
    id: Required[Id]
    userId: Required[Id]
    materialId: NotRequired[Id]
    runId: NotRequired[Id]
    questionText: Required[str]
    questionKey: NotRequired[str]
    intent: Required[ClarificationIntentType]
    captureTarget: Required[ClarificationCaptureTarget]
    expectedAnswerKind: Required[ExpectedAnswerKind]
    answerSlots: NotRequired[dict[str, object]]
    routingHints: NotRequired[dict[str, object]]
    supportingRefs: NotRequired[list[str]]
    evidenceIds: NotRequired[list[Id]]
    status: Required[ClarificationPromptStatus]
    privacyClass: Required[PrivacyClass]
    createdAt: Required[ISODateString]
    updatedAt: Required[ISODateString]
    answeredAt: NotRequired[ISODateString]
    answerRecordId: NotRequired[Id]
    deletedAt: NotRequired[ISODateString]


class ClarificationPromptUpdate(TypedDict, total=False):
    questionText: str
    questionKey: str
    intent: ClarificationIntentType
    captureTarget: ClarificationCaptureTarget
    expectedAnswerKind: ExpectedAnswerKind
    answerSlots: dict[str, object]
    routingHints: dict[str, object]
    supportingRefs: list[str]
    evidenceIds: list[Id]
    status: ClarificationPromptStatus
    privacyClass: PrivacyClass
    updatedAt: ISODateString
    answeredAt: ISODateString
    answerRecordId: Id
    deletedAt: ISODateString


class ClarificationAnswerRecord(TypedDict, total=False):
    id: Required[Id]
    userId: Required[Id]
    promptId: NotRequired[Id]
    materialId: NotRequired[Id]
    runId: NotRequired[Id]
    answerText: Required[str]
    answerPayload: NotRequired[dict[str, object]]
    captureTarget: Required[ClarificationCaptureTarget]
    routingStatus: Required[ClarificationRoutingStatus]
    createdRecordRefs: Required[list[ClarificationCreatedRecordRef]]
    validationErrors: NotRequired[list[str]]
    privacyClass: Required[PrivacyClass]
    createdAt: Required[ISODateString]
    updatedAt: Required[ISODateString]
    deletedAt: NotRequired[ISODateString]


class ClarificationAnswerUpdate(TypedDict, total=False):
    answerText: str
    answerPayload: dict[str, object]
    captureTarget: ClarificationCaptureTarget
    routingStatus: ClarificationRoutingStatus
    createdRecordRefs: list[ClarificationCreatedRecordRef]
    validationErrors: list[str]
    privacyClass: PrivacyClass
    updatedAt: ISODateString
    deletedAt: ISODateString


__all__ = [
    "ClarificationAnswerRecord",
    "ClarificationAnswerUpdate",
    "ClarificationCaptureTarget",
    "ClarificationCreatedRecordRef",
    "ClarificationIntentType",
    "ClarificationPromptRecord",
    "ClarificationPromptStatus",
    "ClarificationPromptUpdate",
    "ClarificationRoutingStatus",
    "ExpectedAnswerKind",
]
