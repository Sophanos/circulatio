from __future__ import annotations

from typing import Literal, NotRequired, Required, TypedDict

from .types import Confidence, Id, ISODateString

PatternType = Literal["theme", "complex_candidate", "compensation", "symbol_cluster"]
PatternStatus = Literal[
    "observed_signal",
    "candidate",
    "active",
    "recurring",
    "integrating",
    "dormant",
    "disconfirmed",
    "deleted",
]
PatternHistoryEventType = Literal[
    "created",
    "evidence_added",
    "counterevidence_added",
    "status_changed",
    "formulation_revised",
    "linked_symbol_added",
    "linked_material_added",
    "disconfirmed",
    "deleted",
    "restored",
]


class PatternRecord(TypedDict, total=False):
    id: Required[Id]
    userId: Required[Id]
    patternType: Required[PatternType]
    label: Required[str]
    formulation: Required[str]
    status: Required[PatternStatus]
    activationIntensity: NotRequired[float]
    confidence: Required[Confidence]
    evidenceIds: Required[list[Id]]
    counterevidenceIds: Required[list[Id]]
    linkedSymbols: Required[list[str]]
    linkedSymbolIds: NotRequired[list[Id]]
    linkedMaterialIds: Required[list[Id]]
    linkedLifeEventRefs: Required[list[Id]]
    createdAt: Required[ISODateString]
    updatedAt: Required[ISODateString]
    deletedAt: NotRequired[ISODateString]
    lastSeen: NotRequired[ISODateString]


class PatternHistoryEntry(TypedDict, total=False):
    id: Required[Id]
    userId: Required[Id]
    patternId: Required[Id]
    eventType: Required[PatternHistoryEventType]
    materialId: NotRequired[Id]
    runId: NotRequired[Id]
    proposalId: NotRequired[Id]
    evidenceIds: Required[list[Id]]
    previousValue: NotRequired[dict[str, object]]
    newValue: NotRequired[dict[str, object]]
    note: NotRequired[str]
    createdAt: Required[ISODateString]


class PatternUpdate(TypedDict, total=False):
    label: str
    formulation: str
    status: PatternStatus
    activationIntensity: float
    confidence: Confidence
    evidenceIds: list[Id]
    counterevidenceIds: list[Id]
    linkedSymbols: list[str]
    linkedSymbolIds: list[Id]
    linkedMaterialIds: list[Id]
    linkedLifeEventRefs: list[Id]
    updatedAt: ISODateString
    deletedAt: ISODateString
    lastSeen: ISODateString
