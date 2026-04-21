from __future__ import annotations

from typing import Literal, NotRequired, Required, TypedDict

from .types import Confidence, Id, ISODateString

DreamSeriesStatus = Literal[
    "candidate",
    "active",
    "dormant",
    "integrating",
    "closed",
    "deleted",
]
DreamSeriesMembershipStatus = Literal["candidate", "confirmed", "rejected", "deleted"]
DreamSeriesNarrativeRole = Literal[
    "seed",
    "continuation",
    "turning_point",
    "regression",
    "resolution_candidate",
]


class DreamSeriesRecord(TypedDict, total=False):
    id: Required[Id]
    userId: Required[Id]
    label: Required[str]
    status: Required[DreamSeriesStatus]
    seedMaterialId: Required[Id]
    materialIds: Required[list[Id]]
    symbolIds: Required[list[Id]]
    motifKeys: Required[list[str]]
    settingKeys: Required[list[str]]
    figureKeys: Required[list[str]]
    progressionSummary: NotRequired[str]
    egoTrajectory: NotRequired[str]
    compensationTrajectory: NotRequired[str]
    confidence: Required[Confidence]
    evidenceIds: Required[list[Id]]
    createdAt: Required[ISODateString]
    updatedAt: Required[ISODateString]
    lastSeen: NotRequired[ISODateString]
    deletedAt: NotRequired[ISODateString]


class DreamSeriesUpdate(TypedDict, total=False):
    label: str
    status: DreamSeriesStatus
    materialIds: list[Id]
    symbolIds: list[Id]
    motifKeys: list[str]
    settingKeys: list[str]
    figureKeys: list[str]
    progressionSummary: str
    egoTrajectory: str
    compensationTrajectory: str
    confidence: Confidence
    evidenceIds: list[Id]
    updatedAt: ISODateString
    lastSeen: ISODateString
    deletedAt: ISODateString


class DreamSeriesMembershipRecord(TypedDict, total=False):
    id: Required[Id]
    userId: Required[Id]
    seriesId: Required[Id]
    materialId: Required[Id]
    sequenceIndex: Required[int]
    matchScore: Required[float]
    matchingFeatures: Required[list[str]]
    narrativeRole: Required[DreamSeriesNarrativeRole]
    egoStance: NotRequired[str]
    lysisSummary: NotRequired[str]
    evidenceIds: Required[list[Id]]
    status: Required[DreamSeriesMembershipStatus]
    createdAt: Required[ISODateString]
    updatedAt: Required[ISODateString]
    deletedAt: NotRequired[ISODateString]


class DreamSeriesMembershipUpdate(TypedDict, total=False):
    sequenceIndex: int
    matchScore: float
    matchingFeatures: list[str]
    narrativeRole: DreamSeriesNarrativeRole
    egoStance: str
    lysisSummary: str
    evidenceIds: list[Id]
    status: DreamSeriesMembershipStatus
    updatedAt: ISODateString
    deletedAt: ISODateString
