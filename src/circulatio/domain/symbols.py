from __future__ import annotations

from typing import Literal, NotRequired, Required, TypedDict

from .records import RecordStatus
from .types import Id, ISODateString, PersonalAssociationSummary, SymbolCategory, ValencePoint

SymbolHistoryEventType = Literal[
    "mentioned",
    "created",
    "association_added",
    "valence_shift",
    "recurrence_incremented",
    "revised",
    "deleted",
    "restored",
]


class SymbolRecord(TypedDict, total=False):
    id: Required[Id]
    userId: Required[Id]
    canonicalName: Required[str]
    aliases: Required[list[str]]
    category: Required[SymbolCategory]
    recurrenceCount: Required[int]
    firstSeen: NotRequired[ISODateString]
    lastSeen: NotRequired[ISODateString]
    valenceHistory: Required[list[ValencePoint]]
    personalAssociations: Required[list[PersonalAssociationSummary]]
    linkedMaterialIds: Required[list[Id]]
    linkedLifeEventRefs: Required[list[Id]]
    status: Required[RecordStatus]
    createdAt: Required[ISODateString]
    updatedAt: Required[ISODateString]
    deletedAt: NotRequired[ISODateString]


class SymbolHistoryEntry(TypedDict, total=False):
    id: Required[Id]
    userId: Required[Id]
    symbolId: Required[Id]
    eventType: Required[SymbolHistoryEventType]
    materialId: NotRequired[Id]
    runId: NotRequired[Id]
    proposalId: NotRequired[Id]
    evidenceIds: Required[list[Id]]
    previousValue: NotRequired[dict[str, object]]
    newValue: NotRequired[dict[str, object]]
    note: NotRequired[str]
    createdAt: Required[ISODateString]


class SymbolUpdate(TypedDict, total=False):
    canonicalName: str
    aliases: list[str]
    category: SymbolCategory
    recurrenceCount: int
    lastSeen: ISODateString
    valenceHistory: list[ValencePoint]
    personalAssociations: list[PersonalAssociationSummary]
    linkedMaterialIds: list[Id]
    linkedLifeEventRefs: list[Id]
    status: RecordStatus
    updatedAt: ISODateString
    deletedAt: ISODateString
