from __future__ import annotations

from typing import Literal, NotRequired, Required, TypedDict

from .records import RecordStatus
from .types import Id, ISODateString, PrivacyClass

BodyActivation = Literal["low", "moderate", "high", "overwhelming"]


class BodyStateRecord(TypedDict, total=False):
    id: Required[Id]
    userId: Required[Id]
    materialId: NotRequired[Id]
    runId: NotRequired[Id]
    source: Required[
        Literal["manual_body_note", "practice_outcome", "interpretation_input", "import"]
    ]
    observedAt: Required[ISODateString]
    bodyRegion: NotRequired[str]
    sensation: Required[str]
    activation: NotRequired[BodyActivation]
    tone: NotRequired[str]
    temporalContext: NotRequired[str]
    linkedMaterialIds: Required[list[Id]]
    linkedSymbolIds: Required[list[Id]]
    linkedGoalIds: Required[list[Id]]
    evidenceIds: Required[list[Id]]
    privacyClass: Required[PrivacyClass]
    status: Required[RecordStatus]
    createdAt: Required[ISODateString]
    updatedAt: Required[ISODateString]
    deletedAt: NotRequired[ISODateString]


class BodyStateUpdate(TypedDict, total=False):
    observedAt: ISODateString
    bodyRegion: str
    sensation: str
    activation: BodyActivation
    tone: str
    temporalContext: str
    linkedMaterialIds: list[Id]
    linkedSymbolIds: list[Id]
    linkedGoalIds: list[Id]
    evidenceIds: list[Id]
    privacyClass: PrivacyClass
    status: RecordStatus
    updatedAt: ISODateString
    deletedAt: ISODateString
