from __future__ import annotations

from typing import NotRequired, Required, TypedDict

from .records import MaterialSource, RecordStatus, RevisionReason
from .types import Id, ISODateString, MaterialType, PrivacyClass


class DreamFigureRecord(TypedDict, total=False):
    name: Required[str]
    role: NotRequired[str]
    userReaction: NotRequired[str]
    inferredComplex: NotRequired[str]


class DreamEgoDynamics(TypedDict, total=False):
    stance: Required[str]
    interactionStyle: NotRequired[str]


class StoredDreamStructure(TypedDict, total=False):
    exposition: NotRequired[str]
    peripetia: NotRequired[str]
    lysis: NotRequired[str]
    figures: NotRequired[list[DreamFigureRecord]]
    egoDynamics: NotRequired[DreamEgoDynamics]
    setting: NotRequired[str]
    keyImages: NotRequired[list[str]]
    egoStance: NotRequired[str]
    lysisQuality: NotRequired[str]
    seriesFeatureKeys: NotRequired[list[str]]


class MaterialRecord(TypedDict, total=False):
    id: Required[Id]
    userId: Required[Id]
    materialType: Required[MaterialType]
    title: NotRequired[str]
    text: NotRequired[str]
    summary: NotRequired[str]
    materialDate: Required[ISODateString]
    createdAt: Required[ISODateString]
    updatedAt: Required[ISODateString]
    deletedAt: NotRequired[ISODateString]
    status: Required[RecordStatus]
    privacyClass: Required[PrivacyClass]
    source: Required[MaterialSource]
    currentRevisionId: NotRequired[Id]
    latestInterpretationRunId: NotRequired[Id]
    linkedContextSnapshotIds: NotRequired[list[Id]]
    linkedPracticeSessionIds: NotRequired[list[Id]]
    tags: NotRequired[list[str]]
    dreamStructure: NotRequired[StoredDreamStructure]


class MaterialRevision(TypedDict, total=False):
    id: Required[Id]
    userId: Required[Id]
    materialId: Required[Id]
    revisionNumber: Required[int]
    previousText: NotRequired[str]
    newText: NotRequired[str]
    previousSummary: NotRequired[str]
    newSummary: NotRequired[str]
    reason: Required[RevisionReason]
    note: NotRequired[str]
    createdAt: Required[ISODateString]


class MaterialListFilters(TypedDict, total=False):
    materialTypes: list[MaterialType]
    statuses: list[RecordStatus]
    tags: list[str]
    includeDeleted: bool
    limit: int


class MaterialUpdate(TypedDict, total=False):
    title: str
    text: str
    summary: str
    materialDate: ISODateString
    updatedAt: ISODateString
    deletedAt: ISODateString
    status: RecordStatus
    privacyClass: PrivacyClass
    currentRevisionId: Id
    latestInterpretationRunId: Id
    linkedContextSnapshotIds: list[Id]
    linkedPracticeSessionIds: list[Id]
    tags: list[str]
    dreamStructure: StoredDreamStructure
