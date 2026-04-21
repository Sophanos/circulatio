from __future__ import annotations

from typing import NotRequired, Required, TypedDict

from .types import Id, InteractionFeedbackDomain, InteractionFeedbackTargetType, ISODateString


class InteractionFeedbackRecord(TypedDict, total=False):
    id: Required[Id]
    userId: Required[Id]
    domain: Required[InteractionFeedbackDomain]
    targetType: Required[InteractionFeedbackTargetType]
    targetId: Required[Id]
    feedback: Required[str]
    note: NotRequired[str]
    locale: NotRequired[str]
    createdAt: Required[ISODateString]
