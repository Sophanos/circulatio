from __future__ import annotations

from typing import Literal, NotRequired, Required, TypedDict

from .records import DecisionStatus
from .types import (
    Id,
    InterpretationOptions,
    InterpretationResult,
    ISODateString,
    MaterialType,
    SafetyDisposition,
)

InterpretationRunStatus = Literal["completed", "blocked_by_safety", "failed", "superseded"]


class ProposalDecisionRecord(TypedDict, total=False):
    proposalId: Required[Id]
    action: Required[str]
    entityType: Required[str]
    status: Required[DecisionStatus]
    decidedAt: NotRequired[ISODateString]
    integrationRecordId: NotRequired[Id]
    reason: NotRequired[str]


class InterpretationRunRecord(TypedDict, total=False):
    id: Required[Id]
    userId: Required[Id]
    materialId: Required[Id]
    materialType: Required[MaterialType]
    createdAt: Required[ISODateString]
    status: Required[InterpretationRunStatus]
    inputSnapshotId: NotRequired[Id]
    options: Required[InterpretationOptions]
    safetyDisposition: Required[SafetyDisposition]
    result: Required[InterpretationResult]
    evidenceIds: Required[list[Id]]
    hypothesisIds: Required[list[Id]]
    proposalDecisions: Required[list[ProposalDecisionRecord]]
    practiceRecommendationId: NotRequired[Id]


class InterpretationRunUpdate(TypedDict, total=False):
    status: InterpretationRunStatus
    inputSnapshotId: Id
    options: InterpretationOptions
    safetyDisposition: SafetyDisposition
    result: InterpretationResult
    evidenceIds: list[Id]
    hypothesisIds: list[Id]
    proposalDecisions: list[ProposalDecisionRecord]
    practiceRecommendationId: Id
