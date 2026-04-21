from __future__ import annotations

from typing import Literal, NotRequired, Required, TypedDict

from .types import Id, ISODateString

GoalStatus = Literal[
    "active",
    "challenged",
    "avoided",
    "integrating",
    "completed",
    "deleted",
]
GoalTensionStatus = Literal["candidate", "active", "integrating", "resolved", "deleted"]


class GoalRecord(TypedDict, total=False):
    id: Required[Id]
    userId: Required[Id]
    label: Required[str]
    description: NotRequired[str]
    status: Required[GoalStatus]
    valueTags: Required[list[str]]
    linkedMaterialIds: Required[list[Id]]
    linkedSymbolIds: Required[list[Id]]
    evidenceIds: NotRequired[list[Id]]
    createdAt: Required[ISODateString]
    updatedAt: Required[ISODateString]
    deletedAt: NotRequired[ISODateString]


class GoalUpdate(TypedDict, total=False):
    label: str
    description: str
    status: GoalStatus
    valueTags: list[str]
    linkedMaterialIds: list[Id]
    linkedSymbolIds: list[Id]
    evidenceIds: list[Id]
    updatedAt: ISODateString
    deletedAt: ISODateString


class GoalTensionRecord(TypedDict, total=False):
    id: Required[Id]
    userId: Required[Id]
    goalIds: Required[list[Id]]
    tensionSummary: Required[str]
    polarityLabels: Required[list[str]]
    evidenceIds: Required[list[Id]]
    status: Required[GoalTensionStatus]
    createdAt: Required[ISODateString]
    updatedAt: Required[ISODateString]
    deletedAt: NotRequired[ISODateString]


class GoalTensionUpdate(TypedDict, total=False):
    goalIds: list[Id]
    tensionSummary: str
    polarityLabels: list[str]
    evidenceIds: list[Id]
    status: GoalTensionStatus
    updatedAt: ISODateString
    deletedAt: ISODateString
