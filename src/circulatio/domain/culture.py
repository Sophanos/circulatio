from __future__ import annotations

from typing import Literal, NotRequired, Required, TypedDict

from .types import Confidence, Id, ISODateString

CulturalFrameType = Literal["alchemical", "mythic", "religious", "literary", "family", "chosen"]
CulturalFrameStatus = Literal["enabled", "disabled", "deleted"]
CollectiveAmplificationStatus = Literal[
    "candidate",
    "offered",
    "user_resonated",
    "user_rejected",
    "deleted",
]


class CulturalFrameRecord(TypedDict, total=False):
    id: Required[Id]
    userId: Required[Id]
    label: Required[str]
    frameType: Required[CulturalFrameType]
    status: Required[CulturalFrameStatus]
    allowedUses: Required[list[str]]
    avoidUses: Required[list[str]]
    notes: NotRequired[str]
    createdAt: Required[ISODateString]
    updatedAt: Required[ISODateString]


class CulturalFrameUpdate(TypedDict, total=False):
    label: str
    frameType: CulturalFrameType
    status: CulturalFrameStatus
    allowedUses: list[str]
    avoidUses: list[str]
    notes: str
    updatedAt: ISODateString


class CollectiveAmplificationRecord(TypedDict, total=False):
    id: Required[Id]
    userId: Required[Id]
    materialId: NotRequired[Id]
    runId: NotRequired[Id]
    symbolId: NotRequired[Id]
    culturalFrameId: NotRequired[Id]
    reference: Required[str]
    fitReason: Required[str]
    caveat: Required[str]
    confidence: Required[Confidence]
    evidenceIds: Required[list[Id]]
    status: Required[CollectiveAmplificationStatus]
    createdAt: Required[ISODateString]
    updatedAt: Required[ISODateString]
    deletedAt: NotRequired[ISODateString]


class CollectiveAmplificationUpdate(TypedDict, total=False):
    culturalFrameId: Id
    reference: str
    fitReason: str
    caveat: str
    confidence: Confidence
    evidenceIds: list[Id]
    status: CollectiveAmplificationStatus
    updatedAt: ISODateString
    deletedAt: ISODateString
