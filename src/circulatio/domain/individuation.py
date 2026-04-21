from __future__ import annotations

from typing import Literal, NotRequired, Required, TypedDict

from .types import Confidence, Id, ISODateString, PrivacyClass

IndividuationRecordType = Literal[
    "reality_anchor_summary",
    "self_orientation_snapshot",
    "psychic_opposition",
    "emergent_third_signal",
    "bridge_moment",
    "numinous_encounter",
    "aesthetic_resonance",
    "archetypal_pattern",
    "threshold_process",
    "relational_scene",
    "projection_hypothesis",
    "inner_outer_correspondence",
]
IndividuationRecordStatus = Literal[
    "active",
    "user_confirmed",
    "disconfirmed",
    "archived",
    "deleted",
]
IndividuationRecordSource = Literal[
    "user_reported",
    "interpretation_proposal",
    "threshold_review",
    "living_myth_review",
    "analysis_packet",
    "imported",
]


class RealityAnchorSummaryDetails(TypedDict, total=False):
    anchorSummary: Required[str]
    workDailyLifeContinuity: Required[Literal["stable", "strained", "unknown"]]
    sleepBodyRegulation: Required[Literal["stable", "strained", "unknown"]]
    relationshipContact: Required[Literal["available", "thin", "unknown"]]
    reflectiveCapacity: Required[Literal["steady", "fragile", "unknown"]]
    groundingRecommendation: Required[Literal["clear_for_depth", "pace_gently", "grounding_first"]]
    reasons: Required[list[str]]


class SelfOrientationSnapshotDetails(TypedDict, total=False):
    orientationSummary: Required[str]
    emergentDirection: Required[str]
    egoRelation: Required[Literal["aligned", "conflicted", "avoidant", "curious", "unknown"]]
    movementLanguage: Required[list[str]]
    notMetaphysicalClaim: Required[Literal[True]]


class PsychicOppositionDetails(TypedDict, total=False):
    poleA: Required[str]
    poleB: Required[str]
    oppositionSummary: Required[str]
    currentHoldingPattern: Required[str]
    pressureTone: NotRequired[str]
    holdingInstruction: NotRequired[str]
    normalizedOppositionKey: Required[str]


class EmergentThirdSignalDetails(TypedDict, total=False):
    signalType: Required[
        Literal[
            "symbol",
            "attitude",
            "practice",
            "relationship_move",
            "dream_lysis",
            "body_shift",
            "unknown",
        ]
    ]
    signalSummary: Required[str]
    oppositionIds: Required[list[Id]]
    novelty: Required[Literal["new", "returning", "unclear"]]


class BridgeMomentDetails(TypedDict, total=False):
    bridgeType: Required[
        Literal[
            "dream_to_waking",
            "body_to_symbol",
            "practice_to_dream",
            "relationship_to_dream",
            "aesthetic_to_symbol",
            "unknown",
        ]
    ]
    bridgeSummary: Required[str]
    beforeAfter: NotRequired[str]


class NuminousEncounterDetails(TypedDict, total=False):
    encounterMedium: Required[
        Literal["dream", "waking_event", "body", "art", "place", "conversation", "unknown"]
    ]
    affectTone: Required[str]
    containmentNeed: Required[Literal["ordinary_reflection", "pace_gently", "grounding_first"]]
    interpretationConstraint: Required[str]


class AestheticResonanceDetails(TypedDict, total=False):
    medium: Required[str]
    objectDescription: Required[str]
    resonanceSummary: Required[str]
    feelingTone: NotRequired[str]
    bodySensations: Required[list[str]]


class ArchetypalPatternDetails(TypedDict, total=False):
    patternFamily: Required[
        Literal[
            "shadow",
            "anima_animus",
            "persona",
            "self_orientation",
            "trickster",
            "great_mother",
            "wise_old",
            "hero",
            "threshold",
            "descent_return",
            "unknown",
        ]
    ]
    resonanceSummary: Required[str]
    caveat: Required[str]
    counterevidenceIds: Required[list[Id]]
    phrasingPolicy: Required[Literal["very_tentative"]]


class ThresholdProcessDetails(TypedDict, total=False):
    thresholdName: Required[str]
    phase: Required[Literal["ending", "liminal", "reorientation", "return", "unknown"]]
    whatIsEnding: Required[str]
    notYetBegun: Required[str]
    bodyCarrying: NotRequired[str]
    groundingStatus: Required[Literal["steady", "strained", "unknown"]]
    symbolicLens: NotRequired[str]
    invitationReadiness: Required[Literal["not_now", "ask", "ready"]]
    normalizedThresholdKey: Required[str]


class RelationalSceneRole(TypedDict, total=False):
    roleLabel: Required[str]
    affectTone: NotRequired[str]
    egoStance: NotRequired[str]


class RelationalSceneDetails(TypedDict, total=False):
    sceneSummary: Required[str]
    chargedRoles: Required[list[RelationalSceneRole]]
    recurringAffect: Required[list[str]]
    recurrenceContexts: Required[list[str]]
    normalizedSceneKey: Required[str]


class ProjectionHypothesisDetails(TypedDict, total=False):
    relationalSceneId: NotRequired[Id]
    hypothesisSummary: Required[str]
    projectionPattern: Required[str]
    userTestPrompt: Required[str]
    counterevidenceIds: Required[list[Id]]
    phrasingPolicy: Required[Literal["very_tentative"]]
    consentScope: Required[Literal["projection_language"]]
    normalizedHypothesisKey: Required[str]


class InnerOuterCorrespondenceDetails(TypedDict, total=False):
    correspondenceSummary: Required[str]
    innerRefs: Required[list[Id]]
    outerRefs: Required[list[Id]]
    symbolIds: Required[list[Id]]
    timeWindowStart: NotRequired[ISODateString]
    timeWindowEnd: NotRequired[ISODateString]
    userCharge: Required[Literal["explicitly_charged", "implicitly_charged", "unclear"]]
    caveat: Required[str]
    causalityPolicy: Required[Literal["no_causal_claim"]]
    normalizedCorrespondenceKey: Required[str]


class IndividuationRecordBase(TypedDict, total=False):
    id: Required[Id]
    userId: Required[Id]
    status: Required[IndividuationRecordStatus]
    source: Required[IndividuationRecordSource]
    label: Required[str]
    summary: Required[str]
    confidence: Required[Confidence]
    evidenceIds: Required[list[Id]]
    relatedMaterialIds: Required[list[Id]]
    relatedSymbolIds: Required[list[Id]]
    relatedGoalIds: Required[list[Id]]
    relatedDreamSeriesIds: Required[list[Id]]
    relatedJourneyIds: Required[list[Id]]
    relatedPracticeSessionIds: Required[list[Id]]
    privacyClass: Required[PrivacyClass]
    createdAt: Required[ISODateString]
    updatedAt: Required[ISODateString]
    deletedAt: NotRequired[ISODateString]
    windowStart: NotRequired[ISODateString]
    windowEnd: NotRequired[ISODateString]


class RealityAnchorSummaryRecord(IndividuationRecordBase):
    recordType: Literal["reality_anchor_summary"]
    details: RealityAnchorSummaryDetails


class SelfOrientationSnapshotRecord(IndividuationRecordBase):
    recordType: Literal["self_orientation_snapshot"]
    details: SelfOrientationSnapshotDetails


class PsychicOppositionRecord(IndividuationRecordBase):
    recordType: Literal["psychic_opposition"]
    details: PsychicOppositionDetails


class EmergentThirdSignalRecord(IndividuationRecordBase):
    recordType: Literal["emergent_third_signal"]
    details: EmergentThirdSignalDetails


class BridgeMomentRecord(IndividuationRecordBase):
    recordType: Literal["bridge_moment"]
    details: BridgeMomentDetails


class NuminousEncounterRecord(IndividuationRecordBase):
    recordType: Literal["numinous_encounter"]
    details: NuminousEncounterDetails


class AestheticResonanceRecord(IndividuationRecordBase):
    recordType: Literal["aesthetic_resonance"]
    details: AestheticResonanceDetails


class ArchetypalPatternRecord(IndividuationRecordBase):
    recordType: Literal["archetypal_pattern"]
    details: ArchetypalPatternDetails


class ThresholdProcessRecord(IndividuationRecordBase):
    recordType: Literal["threshold_process"]
    details: ThresholdProcessDetails


class RelationalSceneRecord(IndividuationRecordBase):
    recordType: Literal["relational_scene"]
    details: RelationalSceneDetails


class ProjectionHypothesisRecord(IndividuationRecordBase):
    recordType: Literal["projection_hypothesis"]
    details: ProjectionHypothesisDetails


class InnerOuterCorrespondenceRecord(IndividuationRecordBase):
    recordType: Literal["inner_outer_correspondence"]
    details: InnerOuterCorrespondenceDetails


IndividuationRecord = (
    RealityAnchorSummaryRecord
    | SelfOrientationSnapshotRecord
    | PsychicOppositionRecord
    | EmergentThirdSignalRecord
    | BridgeMomentRecord
    | NuminousEncounterRecord
    | AestheticResonanceRecord
    | ArchetypalPatternRecord
    | ThresholdProcessRecord
    | RelationalSceneRecord
    | ProjectionHypothesisRecord
    | InnerOuterCorrespondenceRecord
)


class IndividuationRecordUpdate(TypedDict, total=False):
    status: IndividuationRecordStatus
    source: IndividuationRecordSource
    label: str
    summary: str
    confidence: Confidence
    evidenceIds: list[Id]
    relatedMaterialIds: list[Id]
    relatedSymbolIds: list[Id]
    relatedGoalIds: list[Id]
    relatedDreamSeriesIds: list[Id]
    relatedJourneyIds: list[Id]
    relatedPracticeSessionIds: list[Id]
    privacyClass: PrivacyClass
    windowStart: ISODateString
    windowEnd: ISODateString
    details: object
    updatedAt: ISODateString
    deletedAt: ISODateString


__all__ = [
    "AestheticResonanceDetails",
    "AestheticResonanceRecord",
    "ArchetypalPatternDetails",
    "ArchetypalPatternRecord",
    "BridgeMomentDetails",
    "BridgeMomentRecord",
    "EmergentThirdSignalDetails",
    "EmergentThirdSignalRecord",
    "IndividuationRecord",
    "IndividuationRecordSource",
    "IndividuationRecordStatus",
    "IndividuationRecordType",
    "IndividuationRecordUpdate",
    "InnerOuterCorrespondenceDetails",
    "InnerOuterCorrespondenceRecord",
    "NuminousEncounterDetails",
    "NuminousEncounterRecord",
    "ProjectionHypothesisDetails",
    "ProjectionHypothesisRecord",
    "PsychicOppositionDetails",
    "PsychicOppositionRecord",
    "RealityAnchorSummaryDetails",
    "RealityAnchorSummaryRecord",
    "RelationalSceneDetails",
    "RelationalSceneRecord",
    "SelfOrientationSnapshotDetails",
    "SelfOrientationSnapshotRecord",
    "ThresholdProcessDetails",
    "ThresholdProcessRecord",
]
