from __future__ import annotations

from typing import Literal, NotRequired, Required, TypedDict

from .interpretations import ProposalDecisionRecord
from .types import (
    AnalysisPacketSection,
    Confidence,
    Id,
    ISODateString,
    LivingMythReviewResult,
    MemoryWritePlan,
    PrivacyClass,
    ThresholdReviewResult,
)

LivingMythRecordType = Literal[
    "life_chapter_snapshot",
    "mythic_question",
    "threshold_marker",
    "complex_encounter",
    "integration_contour",
    "symbolic_wellbeing_snapshot",
]
LivingMythRecordStatus = Literal["active", "user_confirmed", "released", "archived", "deleted"]
LivingMythRecordSource = Literal[
    "living_myth_review",
    "threshold_review",
    "analysis_packet",
    "user_reported",
    "interpretation_proposal",
]


class LifeChapterSnapshotDetails(TypedDict, total=False):
    chapterLabel: Required[str]
    chapterSummary: Required[str]
    governingSymbolIds: Required[list[Id]]
    governingQuestions: Required[list[str]]
    activeOppositionIds: Required[list[Id]]
    thresholdProcessIds: Required[list[Id]]
    relationalSceneIds: Required[list[Id]]
    correspondenceIds: Required[list[Id]]
    chapterTone: NotRequired[str]


class MythicQuestionDetails(TypedDict, total=False):
    questionText: Required[str]
    questionStatus: Required[Literal["active", "answered", "released"]]
    relatedChapterId: NotRequired[Id]
    lastReturnedAt: NotRequired[ISODateString]


class ThresholdMarkerDetails(TypedDict, total=False):
    markerType: Required[
        Literal["ending", "initiation", "return", "choice", "loss", "bridge", "unknown"]
    ]
    markerSummary: Required[str]
    thresholdProcessId: NotRequired[Id]


class ComplexEncounterDetails(TypedDict, total=False):
    complexCandidateId: NotRequired[Id]
    patternId: NotRequired[Id]
    encounterSummary: Required[str]
    trajectorySummary: Required[str]
    movement: Required[
        Literal["approaching", "avoiding", "dialogue", "integration_hint", "stuck", "unknown"]
    ]


class IntegrationContourDetails(TypedDict, total=False):
    contourSummary: Required[str]
    symbolicStrands: Required[list[str]]
    somaticStrands: Required[list[str]]
    relationalStrands: Required[list[str]]
    existentialStrands: Required[list[str]]
    tensionsHeld: Required[list[str]]
    assimilatedSignals: Required[list[str]]
    unassimilatedEdges: Required[list[str]]
    nextQuestions: Required[list[str]]


class SymbolicWellbeingSnapshotDetails(TypedDict, total=False):
    capacitySummary: Required[str]
    groundingCapacity: Required[Literal["steady", "strained", "unknown"]]
    symbolicLiveliness: Required[str]
    somaticContact: Required[str]
    relationalSpaciousness: Required[str]
    agencyTone: Required[str]
    supportNeeded: NotRequired[str]


class LivingMythRecordBase(TypedDict, total=False):
    id: Required[Id]
    userId: Required[Id]
    status: Required[LivingMythRecordStatus]
    source: Required[LivingMythRecordSource]
    label: Required[str]
    summary: Required[str]
    confidence: Required[Confidence]
    evidenceIds: Required[list[Id]]
    relatedMaterialIds: Required[list[Id]]
    relatedSymbolIds: Required[list[Id]]
    relatedGoalIds: Required[list[Id]]
    relatedDreamSeriesIds: Required[list[Id]]
    relatedIndividuationRecordIds: Required[list[Id]]
    privacyClass: Required[PrivacyClass]
    windowStart: NotRequired[ISODateString]
    windowEnd: NotRequired[ISODateString]
    createdAt: Required[ISODateString]
    updatedAt: Required[ISODateString]
    deletedAt: NotRequired[ISODateString]


class LifeChapterSnapshotRecord(LivingMythRecordBase):
    recordType: Literal["life_chapter_snapshot"]
    details: LifeChapterSnapshotDetails


class MythicQuestionRecord(LivingMythRecordBase):
    recordType: Literal["mythic_question"]
    details: MythicQuestionDetails


class ThresholdMarkerRecord(LivingMythRecordBase):
    recordType: Literal["threshold_marker"]
    details: ThresholdMarkerDetails


class ComplexEncounterRecord(LivingMythRecordBase):
    recordType: Literal["complex_encounter"]
    details: ComplexEncounterDetails


class IntegrationContourRecord(LivingMythRecordBase):
    recordType: Literal["integration_contour"]
    details: IntegrationContourDetails


class SymbolicWellbeingSnapshotRecord(LivingMythRecordBase):
    recordType: Literal["symbolic_wellbeing_snapshot"]
    details: SymbolicWellbeingSnapshotDetails


LivingMythRecord = (
    LifeChapterSnapshotRecord
    | MythicQuestionRecord
    | ThresholdMarkerRecord
    | ComplexEncounterRecord
    | IntegrationContourRecord
    | SymbolicWellbeingSnapshotRecord
)


class LivingMythRecordUpdate(TypedDict, total=False):
    status: LivingMythRecordStatus
    source: LivingMythRecordSource
    label: str
    summary: str
    confidence: Confidence
    evidenceIds: list[Id]
    relatedMaterialIds: list[Id]
    relatedSymbolIds: list[Id]
    relatedGoalIds: list[Id]
    relatedDreamSeriesIds: list[Id]
    relatedIndividuationRecordIds: list[Id]
    privacyClass: PrivacyClass
    windowStart: ISODateString
    windowEnd: ISODateString
    details: object
    updatedAt: ISODateString
    deletedAt: ISODateString


class LivingMythReviewRecord(TypedDict, total=False):
    id: Required[Id]
    userId: Required[Id]
    reviewType: Required[Literal["threshold_review", "living_myth_review"]]
    status: Required[Literal["generated", "withheld", "archived", "deleted"]]
    windowStart: Required[ISODateString]
    windowEnd: Required[ISODateString]
    explicitQuestion: NotRequired[str]
    materialIds: Required[list[Id]]
    contextSnapshotIds: Required[list[Id]]
    evidenceIds: Required[list[Id]]
    result: Required[ThresholdReviewResult | LivingMythReviewResult]
    memoryWritePlan: NotRequired[MemoryWritePlan]
    proposalDecisions: Required[list[ProposalDecisionRecord]]
    practiceSuggestionId: NotRequired[Id]
    createdAt: Required[ISODateString]
    updatedAt: Required[ISODateString]
    deletedAt: NotRequired[ISODateString]


class LivingMythReviewUpdate(TypedDict, total=False):
    status: Literal["generated", "withheld", "archived", "deleted"]
    explicitQuestion: str
    materialIds: list[Id]
    contextSnapshotIds: list[Id]
    evidenceIds: list[Id]
    result: ThresholdReviewResult | LivingMythReviewResult
    memoryWritePlan: MemoryWritePlan
    proposalDecisions: list[ProposalDecisionRecord]
    practiceSuggestionId: Id
    updatedAt: ISODateString
    deletedAt: ISODateString


class AnalysisPacketRecordRef(TypedDict):
    recordType: str
    recordId: Id


class AnalysisPacketRecord(TypedDict, total=False):
    id: Required[Id]
    userId: Required[Id]
    status: Required[Literal["generated", "archived", "deleted"]]
    windowStart: Required[ISODateString]
    windowEnd: Required[ISODateString]
    packetTitle: Required[str]
    sections: Required[list[AnalysisPacketSection]]
    includedMaterialIds: Required[list[Id]]
    includedRecordRefs: Required[list[AnalysisPacketRecordRef]]
    evidenceIds: Required[list[Id]]
    source: Required[Literal["llm", "bounded_fallback"]]
    privacyClass: Required[PrivacyClass]
    userFacingResponse: Required[str]
    createdAt: Required[ISODateString]
    updatedAt: Required[ISODateString]
    deletedAt: NotRequired[ISODateString]


__all__ = [
    "AnalysisPacketRecord",
    "AnalysisPacketRecordRef",
    "ComplexEncounterDetails",
    "ComplexEncounterRecord",
    "IntegrationContourDetails",
    "IntegrationContourRecord",
    "LifeChapterSnapshotDetails",
    "LifeChapterSnapshotRecord",
    "LivingMythRecord",
    "LivingMythRecordSource",
    "LivingMythRecordStatus",
    "LivingMythRecordType",
    "LivingMythRecordUpdate",
    "LivingMythReviewRecord",
    "LivingMythReviewUpdate",
    "MythicQuestionDetails",
    "MythicQuestionRecord",
    "SymbolicWellbeingSnapshotDetails",
    "SymbolicWellbeingSnapshotRecord",
    "ThresholdMarkerDetails",
    "ThresholdMarkerRecord",
]
