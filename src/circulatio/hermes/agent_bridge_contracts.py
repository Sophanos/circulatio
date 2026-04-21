from __future__ import annotations

from typing import Literal, NotRequired, Required, TypedDict

from ..domain.types import Id

BridgeStatus = Literal[
    "ok",
    "blocked",
    "validation_error",
    "not_found",
    "conflict",
    "retryable_error",
    "error",
]

BridgeOperation = Literal[
    "circulatio.material.store",
    "circulatio.material.get",
    "circulatio.material.list",
    "circulatio.body.store",
    "circulatio.material.interpret",
    "circulatio.review.threshold",
    "circulatio.review.living_myth",
    "circulatio.packet.analysis",
    "circulatio.practice.generate",
    "circulatio.practice.respond",
    "circulatio.feedback.interpretation",
    "circulatio.feedback.practice",
    "circulatio.briefs.generate",
    "circulatio.briefs.respond",
    "circulatio.method_state.respond",
    "circulatio.proposals.approve",
    "circulatio.proposals.reject",
    "circulatio.proposals.list_pending",
    "circulatio.review.proposals.approve",
    "circulatio.review.proposals.reject",
    "circulatio.review.proposals.list_pending",
    "circulatio.hypotheses.reject",
    "circulatio.entity.revise",
    "circulatio.entity.delete",
    "circulatio.graph.query",
    "circulatio.memory.kernel",
    "circulatio.dashboard.summary",
    "circulatio.discovery",
    "circulatio.summary.alive_today",
    "circulatio.journey.page",
    "circulatio.journeys.create",
    "circulatio.journeys.list",
    "circulatio.journeys.get",
    "circulatio.journeys.update",
    "circulatio.journeys.set_status",
    "circulatio.review.weekly",
    "circulatio.witness.state",
    "circulatio.conscious_attitude.capture",
    "circulatio.individuation.reality_anchors.capture",
    "circulatio.individuation.threshold_process.upsert",
    "circulatio.individuation.relational_scene.capture",
    "circulatio.individuation.inner_outer_correspondence.capture",
    "circulatio.individuation.numinous_encounter.capture",
    "circulatio.individuation.aesthetic_resonance.capture",
    "circulatio.consent.set",
    "circulatio.amplification.answer",
    "circulatio.goals.upsert",
    "circulatio.goal_tensions.upsert",
    "circulatio.culture.frame.set",
    "circulatio.symbols.list",
    "circulatio.symbols.get",
    "circulatio.symbols.history",
]


class HermesSourceContext(TypedDict, total=False):
    platform: Required[str]
    sessionId: NotRequired[str | None]
    messageId: NotRequired[str | None]
    profile: NotRequired[str | None]
    rawCommand: NotRequired[str | None]


class BridgeRequestEnvelope(TypedDict):
    requestId: Id
    idempotencyKey: str
    userId: Id
    source: HermesSourceContext
    operation: BridgeOperation
    payload: dict[str, object]


class BridgeError(TypedDict, total=False):
    code: Required[str]
    message: Required[str]
    retryable: Required[bool]
    details: NotRequired[dict[str, object]]


class BridgePendingProposal(TypedDict, total=False):
    alias: Required[str]
    id: Required[Id]
    action: Required[str]
    entityType: Required[str]
    reason: Required[str]
    evidenceIds: Required[list[Id]]
    payload: NotRequired[dict[str, object]]
    sourceKind: NotRequired[str]
    sourceId: NotRequired[Id]


class BridgeResponseEnvelope(TypedDict):
    requestId: Id
    idempotencyKey: str
    replayed: bool
    status: BridgeStatus
    message: str
    result: dict[str, object]
    pendingProposals: list[BridgePendingProposal]
    affectedEntityIds: list[Id]
    errors: list[BridgeError]
