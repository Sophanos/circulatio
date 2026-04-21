from __future__ import annotations

from typing import Literal, NotRequired, Required, TypedDict

from .types import (
    ComplexCandidateSummary,
    CulturalOriginSummary,
    EvidenceItem,
    Id,
    ISODateString,
    MaterialSummary,
    PersonalSymbolSummary,
    PracticeOutcomeSummary,
    PrivacyClass,
    TypologyLensSummary,
)

GraphNodeType = Literal[
    "MaterialEntry",
    "DreamEntry",
    "ReflectionEntry",
    "ChargedEventNote",
    "ContextSnapshot",
    "SymbolMention",
    "MotifMention",
    "PersonalSymbol",
    "DreamFigure",
    "Theme",
    "ComplexCandidate",
    "CulturalOrigin",
    "CulturalAmplification",
    "InterpretationRun",
    "PracticePlan",
    "PracticeSession",
    "IntegrationNote",
    "LifeEventRef",
    "StateSnapshotRef",
    "HabitRef",
    "TypologySignal",
    "TypologyHypothesis",
    "TypologyLens",
    "WeeklyReview",
    "EvidenceItem",
    "BodyState",
    "Goal",
    "GoalTension",
    "ConsciousAttitude",
    "DreamSeries",
    "DreamSeriesMembership",
    "PersonalAmplification",
    "AmplificationPrompt",
    "CollectiveAmplification",
    "CulturalFrame",
    "ConsentPreference",
    "AdaptationProfile",
    "Journey",
    "ProactiveBrief",
    "RealityAnchorSummary",
    "SelfOrientationSnapshot",
    "PsychicOpposition",
    "EmergentThirdSignal",
    "BridgeMoment",
    "NuminousEncounter",
    "AestheticResonance",
    "ArchetypalPattern",
    "ThresholdProcess",
    "RelationalScene",
    "ProjectionHypothesis",
    "InnerOuterCorrespondence",
    "LifeChapterSnapshot",
    "MythicQuestion",
    "ThresholdMarker",
    "ComplexEncounter",
    "IntegrationContour",
    "SymbolicWellbeingSnapshot",
    "LivingMythReview",
    "AnalysisPacket",
]

GraphEdgeType = Literal[
    "MENTIONS",
    "INSTANCE_OF",
    "FEATURES",
    "MAY_EXPRESS",
    "LINKED_TO",
    "CONTEXTUALIZED_BY",
    "SUPPORTED_BY",
    "CONTRADICTED_BY",
    "AMPLIFIED_BY",
    "DRAWS_FROM",
    "USED_EVIDENCE",
    "TARGETED",
    "CONFIRMS_OR_REJECTS",
    "SUMMARIZES",
    "ASSOCIATED_WITH",
    "TRIGGERS",
    "CORRELATES_WITH",
    "COMPENSATES_FOR",
    "BELONGS_TO_SERIES",
    "HAS_AMPLIFICATION",
    "REQUESTS_AMPLIFICATION",
    "EMERGED_FROM",
    "HAS_BODY_STATE",
    "HAS_CONSCIOUS_ATTITUDE",
    "RELATES_TO_GOAL",
    "TENSIONS_WITH",
    "PRECEDED_BY_PRACTICE",
    "FOLLOWED_BY",
    "RESPONDED_TO",
    "WITHHELD_BY_POLICY",
    "HOLDS_OPPOSITION",
    "EMERGES_FROM",
    "MARKS_THRESHOLD",
    "REPEATS_AS_SCENE",
    "MAY_PROJECT",
    "CORRESPONDS_WITH",
    "ORIENTS_TOWARD",
    "BELONGS_TO_CHAPTER",
    "TRACKS_COMPLEX",
    "CONTAINED_IN_PACKET",
]

GraphTraversalDirection = Literal["outbound", "inbound", "both"]

DEFAULT_GRAPH_NODE_TYPES: tuple[GraphNodeType, ...] = (
    "MaterialEntry",
    "DreamEntry",
    "ReflectionEntry",
    "ChargedEventNote",
    "ContextSnapshot",
    "PersonalSymbol",
    "DreamFigure",
    "MotifMention",
    "Theme",
    "ComplexCandidate",
    "InterpretationRun",
    "PracticeSession",
    "IntegrationNote",
    "LifeEventRef",
    "StateSnapshotRef",
    "TypologyLens",
    "TypologyHypothesis",
    "WeeklyReview",
    "EvidenceItem",
    "BodyState",
    "Goal",
    "GoalTension",
    "ConsciousAttitude",
    "DreamSeries",
    "DreamSeriesMembership",
    "PersonalAmplification",
    "AmplificationPrompt",
    "CollectiveAmplification",
    "CulturalFrame",
    "ConsentPreference",
    "AdaptationProfile",
    "Journey",
    "ProactiveBrief",
    "RealityAnchorSummary",
    "SelfOrientationSnapshot",
    "PsychicOpposition",
    "EmergentThirdSignal",
    "BridgeMoment",
    "NuminousEncounter",
    "AestheticResonance",
    "ArchetypalPattern",
    "ThresholdProcess",
    "RelationalScene",
    "ProjectionHypothesis",
    "InnerOuterCorrespondence",
    "LifeChapterSnapshot",
    "MythicQuestion",
    "ThresholdMarker",
    "ComplexEncounter",
    "IntegrationContour",
    "SymbolicWellbeingSnapshot",
    "LivingMythReview",
    "AnalysisPacket",
)

DEFAULT_GRAPH_EDGE_TYPES: tuple[GraphEdgeType, ...] = (
    "MENTIONS",
    "INSTANCE_OF",
    "FEATURES",
    "MAY_EXPRESS",
    "LINKED_TO",
    "CONTEXTUALIZED_BY",
    "SUPPORTED_BY",
    "CONTRADICTED_BY",
    "AMPLIFIED_BY",
    "DRAWS_FROM",
    "USED_EVIDENCE",
    "TARGETED",
    "CONFIRMS_OR_REJECTS",
    "SUMMARIZES",
    "ASSOCIATED_WITH",
    "TRIGGERS",
    "CORRELATES_WITH",
    "COMPENSATES_FOR",
    "BELONGS_TO_SERIES",
    "HAS_AMPLIFICATION",
    "REQUESTS_AMPLIFICATION",
    "EMERGED_FROM",
    "HAS_BODY_STATE",
    "HAS_CONSCIOUS_ATTITUDE",
    "RELATES_TO_GOAL",
    "TENSIONS_WITH",
    "PRECEDED_BY_PRACTICE",
    "FOLLOWED_BY",
    "RESPONDED_TO",
    "WITHHELD_BY_POLICY",
    "HOLDS_OPPOSITION",
    "EMERGES_FROM",
    "MARKS_THRESHOLD",
    "REPEATS_AS_SCENE",
    "MAY_PROJECT",
    "CORRESPONDS_WITH",
    "ORIENTS_TOWARD",
    "BELONGS_TO_CHAPTER",
    "TRACKS_COMPLEX",
    "CONTAINED_IN_PACKET",
)


class GraphNodeBase(TypedDict):
    id: Id
    userId: Id
    type: GraphNodeType
    createdAt: ISODateString
    updatedAt: ISODateString
    privacyClass: PrivacyClass


class GraphEdge(TypedDict):
    id: Id
    userId: Id
    type: GraphEdgeType
    fromNodeId: Id
    toNodeId: Id
    evidenceIds: list[Id]
    createdAt: ISODateString


class SymbolicMemorySnapshot(TypedDict):
    personalSymbols: list[PersonalSymbolSummary]
    complexCandidates: list[ComplexCandidateSummary]
    materialSummaries: list[MaterialSummary]
    evidence: list[EvidenceItem]
    practiceOutcomes: list[PracticeOutcomeSummary]
    culturalOrigins: list[CulturalOriginSummary]
    typologyLenses: list[TypologyLensSummary]


class GraphQuery(TypedDict, total=False):
    rootNodeIds: list[Id]
    nodeTypes: list[GraphNodeType]
    edgeTypes: list[GraphEdgeType]
    maxDepth: int
    direction: GraphTraversalDirection
    includeEvidence: bool
    limit: int


class GraphNodeProjection(TypedDict, total=False):
    id: Required[Id]
    userId: Required[Id]
    type: Required[GraphNodeType]
    sourceId: Required[Id]
    label: Required[str]
    summary: NotRequired[str]
    privacyClass: Required[PrivacyClass]
    createdAt: Required[ISODateString]
    updatedAt: Required[ISODateString]
    metadata: NotRequired[dict[str, object]]


class GraphEdgeProjection(TypedDict):
    id: Id
    userId: Id
    type: GraphEdgeType
    fromNodeId: Id
    toNodeId: Id
    evidenceIds: list[Id]
    createdAt: ISODateString


class GraphQueryAllowlist(TypedDict):
    nodeTypes: list[GraphNodeType]
    edgeTypes: list[GraphEdgeType]
    maxDepth: int
    maxLimit: int


class GraphQueryResult(TypedDict):
    userId: Id
    nodes: list[GraphNodeProjection]
    edges: list[GraphEdgeProjection]
    allowlist: GraphQueryAllowlist
    warnings: list[str]


DEFAULT_GRAPH_QUERY_ALLOWLIST: GraphQueryAllowlist = {
    "nodeTypes": list(DEFAULT_GRAPH_NODE_TYPES),
    "edgeTypes": list(DEFAULT_GRAPH_EDGE_TYPES),
    "maxDepth": 2,
    "maxLimit": 100,
}


class DeleteGraphEntityRequest(TypedDict):
    userId: Id
    entityId: Id
    entityType: GraphNodeType
    reason: Literal["user_requested", "incorrect", "privacy", "other"]


class ReviseGraphEntityRequest(TypedDict, total=False):
    userId: Id
    entityId: Id
    entityType: GraphNodeType
    revisionNote: str
    replacementSummary: str


class SuppressHypothesisRequest(TypedDict, total=False):
    userId: Id
    hypothesisId: Id
    normalizedClaimKey: str
    reason: Literal["user_rejected", "user_refined", "counterevidence", "expired", "unsafe"]
    note: str
