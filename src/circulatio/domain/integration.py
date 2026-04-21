from __future__ import annotations

from typing import Literal, NotRequired, Required, TypedDict

from .types import FeedbackValue, Id, ISODateString

IntegrationAction = Literal[
    "approved_proposals",
    "rejected_proposals",
    "rejected_hypotheses",
    "refined_hypotheses",
    "revision",
    "deletion",
    "practice_outcome",
    "practice_feedback",
]


class IntegrationRecord(TypedDict, total=False):
    id: Required[Id]
    userId: Required[Id]
    runId: NotRequired[Id]
    materialId: NotRequired[Id]
    action: Required[IntegrationAction]
    approvedProposalIds: Required[list[Id]]
    rejectedProposalIds: Required[list[Id]]
    suppressedHypothesisIds: Required[list[Id]]
    feedbackByHypothesisId: NotRequired[dict[Id, FeedbackValue]]
    affectedEntityIds: Required[list[Id]]
    note: NotRequired[str]
    createdAt: Required[ISODateString]
