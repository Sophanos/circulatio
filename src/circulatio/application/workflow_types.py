from __future__ import annotations

from typing import Literal, NotRequired, Required, TypedDict

from ..adapters.context_adapter import LifeOsWindow
from ..domain.adaptation import UserAdaptationProfileRecord
from ..domain.clarifications import (
    ClarificationAnswerRecord,
    ClarificationCaptureTarget,
    ClarificationPromptRecord,
)
from ..domain.context import ContextSnapshot
from ..domain.graph import GraphNodeType
from ..domain.interpretations import InterpretationRunRecord
from ..domain.journeys import JourneyRecord, JourneyStatus
from ..domain.living_myth import AnalysisPacketRecord, LivingMythReviewRecord
from ..domain.materials import MaterialListFilters, MaterialRecord, StoredDreamStructure
from ..domain.memory import MemoryKernelSnapshot, MemoryNamespace, MemoryRetrievalRankingProfile
from ..domain.method_state import (
    MethodStateAnchorRefs,
    MethodStateAppliedEntityRef,
    MethodStateCaptureRunRecord,
    MethodStateCaptureTargetKind,
    MethodStateResponseSource,
)
from ..domain.patterns import PatternHistoryEntry, PatternRecord
from ..domain.practices import PracticeSessionRecord
from ..domain.presentation import (
    NarrativeMode,
    PresentationPrivacyClass,
    PresentationRitualPlanResult,
    PresentationSourceRef,
    RequestedRitualSurfaces,
    RitualCompletionBodyStatePayload,
    RitualCompletionEvent,
    RitualCompletionPolicy,
    RitualIntent,
    RitualRenderPolicy,
)
from ..domain.proactive import ProactiveBriefRecord, RhythmBriefSource
from ..domain.records import DeletionMode, MaterialSource
from ..domain.reviews import DashboardSummary, WeeklyReviewRecord
from ..domain.soma import BodyActivation, BodyStateRecord
from ..domain.symbols import SymbolHistoryEntry, SymbolRecord
from ..domain.types import (
    AnalysisPacketFocus,
    AnalysisPacketResult,
    AnalyticLens,
    CirculationSummaryResult,
    FeedbackValue,
    Id,
    InterpretationOptions,
    InterpretationResult,
    LifeContextSnapshot,
    LivingMythReviewResult,
    MaterialType,
    MemoryWriteProposal,
    MethodContextSnapshot,
    PracticeOutcomeWritePayload,
    PracticePlan,
    PracticeRecommendationResult,
    PracticeTriggerSummary,
    PrivacyClass,
    RhythmicBriefResult,
    SafetyContext,
    SessionContext,
    ThreadDigest,
    ThresholdReviewResult,
    TypologyEvidenceDigest,
    UserAdaptationProfileSummary,
    UserAssociationInput,
)


class CreateMaterialInput(TypedDict, total=False):
    userId: Required[Id]
    materialType: Required[MaterialType]
    text: NotRequired[str]
    title: NotRequired[str]
    summary: NotRequired[str]
    materialDate: NotRequired[str]
    privacyClass: NotRequired[PrivacyClass]
    source: NotRequired[MaterialSource]
    tags: NotRequired[list[str]]
    dreamStructure: NotRequired[StoredDreamStructure]


class CreateAndInterpretMaterialInput(CreateMaterialInput, total=False):
    sessionContext: NotRequired[SessionContext]
    lifeContextSnapshot: NotRequired[LifeContextSnapshot]
    lifeOsWindow: NotRequired[LifeOsWindow]
    userAssociations: NotRequired[list[UserAssociationInput]]
    explicitQuestion: NotRequired[str]
    culturalOrigins: NotRequired[list[dict[str, object]]]
    safetyContext: NotRequired[SafetyContext]
    options: NotRequired[InterpretationOptions]


class MaterialWorkflowResult(TypedDict, total=False):
    material: Required[MaterialRecord]
    run: Required[InterpretationRunRecord]
    interpretation: Required[InterpretationResult]
    pendingProposals: Required[list[MemoryWriteProposal]]
    pendingClarificationPrompts: NotRequired[list[ClarificationPromptRecord]]
    contextSnapshot: NotRequired[ContextSnapshot]
    practiceSession: NotRequired[PracticeSessionRecord]
    continuity: NotRequired[ThreadAwareContinuityBundle]


class ThreadAwareContinuityBundle(TypedDict, total=False):
    generatedAt: Required[str]
    windowStart: Required[str]
    windowEnd: Required[str]
    methodContextSnapshot: NotRequired[MethodContextSnapshot]
    threadDigests: Required[list[ThreadDigest]]


class SurfaceContextBundle(TypedDict, total=False):
    preparedPayload: Required[dict[str, object]]
    continuity: Required[ThreadAwareContinuityBundle]
    methodContextSnapshot: NotRequired[MethodContextSnapshot]
    threadDigests: Required[list[ThreadDigest]]
    typologyEvidenceDigest: NotRequired[TypologyEvidenceDigest]
    dashboard: NotRequired[DashboardSummary]
    memorySnapshot: NotRequired[MemoryKernelSnapshot]
    recentPractices: NotRequired[list[PracticeSessionRecord]]
    journeys: NotRequired[list[JourneyRecord]]
    existingBriefs: NotRequired[list[ProactiveBriefRecord]]
    profile: NotRequired[UserAdaptationProfileRecord | None]
    adaptationSummary: NotRequired[UserAdaptationProfileSummary]
    weeklyReviews: NotRequired[list[WeeklyReviewRecord]]


IntakeContextVisibility = Literal["host_only"]
IntakeContextStatus = Literal["complete", "partial"]
IntakeContextSourceKind = Literal["material", "dashboard", "method_context", "policy"]
IntakeContextItemKind = Literal[
    "stored_material",
    "recent_material",
    "recurring_symbol",
    "active_pattern",
    "thread_digest",
    "recent_body_state",
    "active_dream_series",
    "recent_dream_dynamic",
    "longitudinal_signal",
    "active_journey",
    "method_state",
    "clarification_state",
    "reality_anchor",
    "threshold_process",
    "relational_scene",
    "living_myth_context",
]
IntakeMentionRecommendation = Literal[
    "acknowledge_only",
    "context_available_hold_first",
    "grounding_first_hold_context",
    "ask_one_clarification_only_if_user_invites",
]
IntakeFollowupQuestionStyle = Literal[
    "none",
    "single_gentle_question",
    "grounding_orienting",
    "clarify_before_depth",
    "user_choice",
]


class IntakeAnchorMaterial(TypedDict, total=False):
    id: Required[Id]
    materialType: Required[MaterialType]
    materialDate: Required[str]
    title: NotRequired[str]
    summary: NotRequired[str]
    textPreview: NotRequired[str]
    tags: Required[list[str]]


class IntakeContextItem(TypedDict, total=False):
    key: Required[str]
    kind: Required[IntakeContextItemKind]
    label: Required[str]
    sourceKind: Required[IntakeContextSourceKind]
    criteria: Required[list[str]]
    entityRefs: Required[dict[str, list[Id]]]
    evidenceIds: Required[list[Id]]
    summary: NotRequired[str]
    caution: NotRequired[str]


class IntakeHostGuidance(TypedDict):
    holdFirst: bool
    allowAutoInterpretation: bool
    maxQuestions: int
    mentionRecommendation: IntakeMentionRecommendation
    followupQuestionStyle: IntakeFollowupQuestionStyle
    reasons: list[str]


class IntakeContextSourceCounts(TypedDict):
    recentMaterialCount: int
    recurringSymbolCount: int
    activePatternCount: int
    activeJourneyCount: int
    longitudinalSignalCount: int
    threadDigestCount: int
    intakeItemCount: int
    pendingProposalCount: int


class IntakeContextPacket(TypedDict):
    packetId: Id
    visibility: IntakeContextVisibility
    status: IntakeContextStatus
    source: str
    generatedAt: str
    userId: Id
    materialId: Id
    materialType: MaterialType
    windowStart: str
    windowEnd: str
    anchorMaterial: IntakeAnchorMaterial
    hostGuidance: IntakeHostGuidance
    items: list[IntakeContextItem]
    entityRefs: dict[str, list[Id]]
    sourceCounts: IntakeContextSourceCounts
    warnings: list[str]


class StoreMaterialWithIntakeContextResult(TypedDict, total=False):
    material: Required[MaterialRecord]
    intakeContext: Required[IntakeContextPacket]
    continuity: NotRequired[ThreadAwareContinuityBundle]


class ApproveProposalsInput(TypedDict, total=False):
    userId: Required[Id]
    runId: Required[Id]
    proposalIds: Required[list[Id]]
    integrationNote: NotRequired[str]


class RejectProposalsInput(TypedDict, total=False):
    userId: Required[Id]
    runId: Required[Id]
    proposalIds: Required[list[Id]]
    reason: NotRequired[str]


class RejectHypothesesInput(TypedDict, total=False):
    userId: Required[Id]
    runId: Required[Id]
    feedbackByHypothesisId: Required[dict[Id, FeedbackValue]]


class ReviseEntityInput(TypedDict, total=False):
    userId: Required[Id]
    entityType: Required[GraphNodeType]
    entityId: Required[Id]
    revisionNote: Required[str]
    replacement: NotRequired[dict[str, object]]


class DeleteEntityInput(TypedDict, total=False):
    userId: Required[Id]
    entityType: Required[GraphNodeType]
    entityId: Required[Id]
    mode: NotRequired[DeletionMode]
    reason: NotRequired[str]


class SymbolHistoryResult(TypedDict):
    symbol: SymbolRecord
    history: list[SymbolHistoryEntry]
    linkedMaterials: list[MaterialRecord]


class PatternHistoryResult(TypedDict):
    pattern: PatternRecord
    history: list[PatternHistoryEntry]
    linkedMaterials: list[MaterialRecord]


class RecordPracticeOutcomeInput(TypedDict, total=False):
    userId: Required[Id]
    practiceSessionId: NotRequired[Id]
    materialId: NotRequired[Id]
    outcome: Required[PracticeOutcomeWritePayload]


class ProcessMethodStateResponseInput(TypedDict, total=False):
    userId: Required[Id]
    idempotencyKey: Required[str]
    source: Required[MethodStateResponseSource]
    responseText: Required[str]
    observedAt: NotRequired[str]
    anchorRefs: NotRequired[MethodStateAnchorRefs]
    expectedTargets: NotRequired[list[MethodStateCaptureTargetKind]]
    privacyClass: NotRequired[PrivacyClass]
    sessionContext: NotRequired[SessionContext]
    lifeContextSnapshot: NotRequired[LifeContextSnapshot]
    safetyContext: NotRequired[SafetyContext]
    options: NotRequired[InterpretationOptions]


class MethodStateWorkflowResult(TypedDict, total=False):
    captureRun: Required[MethodStateCaptureRunRecord]
    responseMaterial: Required[MaterialRecord]
    evidence: Required[list[dict[str, object]]]
    appliedEntityRefs: Required[list[MethodStateAppliedEntityRef]]
    pendingProposals: Required[list[MemoryWriteProposal]]
    followUpPrompts: Required[list[str]]
    withheldCandidates: Required[list[dict[str, object]]]
    warnings: Required[list[str]]
    continuity: NotRequired[ThreadAwareContinuityBundle]


class AnswerClarificationInput(TypedDict, total=False):
    userId: Required[Id]
    promptId: NotRequired[Id]
    materialId: NotRequired[Id]
    runId: NotRequired[Id]
    answerText: Required[str]
    answerPayload: NotRequired[dict[str, object]]
    captureTargetOverride: NotRequired[ClarificationCaptureTarget]
    privacyClass: NotRequired[PrivacyClass]
    skip: NotRequired[bool]


class AnswerClarificationResult(TypedDict, total=False):
    prompt: NotRequired[ClarificationPromptRecord]
    answer: Required[ClarificationAnswerRecord]
    createdRecordRefs: Required[list[dict[str, str]]]
    routedRecord: NotRequired[dict[str, object]]
    routingStatus: Required[str]


class GeneratePracticeInput(TypedDict, total=False):
    userId: Required[Id]
    windowStart: NotRequired[str]
    windowEnd: NotRequired[str]
    trigger: NotRequired[PracticeTriggerSummary]
    sessionContext: NotRequired[SessionContext]
    explicitQuestion: NotRequired[str]
    safetyContext: NotRequired[SafetyContext]
    options: NotRequired[InterpretationOptions]
    persist: NotRequired[bool]


class PracticeWorkflowResult(TypedDict, total=False):
    practiceSession: NotRequired[PracticeSessionRecord]
    practiceRecommendation: Required[PracticePlan]
    userFacingResponse: Required[str]
    contextSnapshot: NotRequired[ContextSnapshot]
    llmResult: NotRequired[PracticeRecommendationResult]
    continuity: NotRequired[ThreadAwareContinuityBundle]


class PracticeMutationResult(TypedDict):
    practiceSession: PracticeSessionRecord
    continuity: ThreadAwareContinuityBundle


class RespondPracticeInput(TypedDict, total=False):
    userId: Required[Id]
    practiceSessionId: Required[Id]
    action: Required[str]
    note: NotRequired[str]
    activationBefore: NotRequired[str]


class CreateBodyStateInput(TypedDict, total=False):
    userId: Required[Id]
    sensation: Required[str]
    observedAt: NotRequired[str]
    bodyRegion: NotRequired[str]
    activation: NotRequired[BodyActivation]
    tone: NotRequired[str]
    temporalContext: NotRequired[str]
    linkedGoalIds: NotRequired[list[Id]]
    linkedMaterialIds: NotRequired[list[Id]]
    evidenceIds: NotRequired[list[Id]]
    privacyClass: NotRequired[PrivacyClass]
    noteText: NotRequired[str]


class StoreBodyStateResult(TypedDict, total=False):
    bodyState: Required[BodyStateRecord]
    noteMaterial: NotRequired[MaterialRecord]


class ListMaterialsInput(TypedDict, total=False):
    userId: Required[Id]
    filters: NotRequired[MaterialListFilters]


class AliveTodayResult(TypedDict, total=False):
    summary: Required[CirculationSummaryResult]
    continuity: NotRequired[ThreadAwareContinuityBundle]


class GenerateDiscoveryInput(TypedDict, total=False):
    userId: Required[Id]
    windowStart: NotRequired[str]
    windowEnd: NotRequired[str]
    explicitQuestion: NotRequired[str]
    analyticLens: NotRequired[AnalyticLens]
    textQuery: NotRequired[str]
    rootNodeIds: NotRequired[list[Id]]
    memoryNamespaces: NotRequired[list[MemoryNamespace]]
    rankingProfile: NotRequired[MemoryRetrievalRankingProfile]
    maxItems: NotRequired[int]


DiscoverySectionKey = Literal[
    "recurring",
    "dream_body_event_links",
    "ripe_to_revisit",
    "conscious_attitude",
    "body_states",
    "method_state",
    "function_dynamics",
    "journey_threads",
    "held_for_now",
]


class DiscoveryDigestItem(TypedDict, total=False):
    label: Required[str]
    summary: NotRequired[str]
    criteria: Required[list[str]]
    sourceKinds: Required[list[str]]
    entityRefs: Required[dict[str, list[Id]]]
    evidenceIds: Required[list[Id]]


class DiscoverySection(TypedDict, total=False):
    key: Required[DiscoverySectionKey]
    title: Required[str]
    summary: Required[str]
    items: Required[list[DiscoveryDigestItem]]


class DiscoverySourceCounts(TypedDict):
    recentMaterialCount: int
    recurringSymbolCount: int
    activePatternCount: int
    pendingProposalCount: int
    memoryItemCount: int
    threadDigestCount: int
    graphNodeCount: int
    graphEdgeCount: int


class DiscoveryResult(TypedDict, total=False):
    discoveryId: Required[Id]
    userId: Required[Id]
    generatedAt: Required[str]
    windowStart: Required[str]
    windowEnd: Required[str]
    explicitQuestion: NotRequired[str]
    sections: Required[list[DiscoverySection]]
    sourceCounts: Required[DiscoverySourceCounts]
    fallbackText: Required[str]
    warnings: Required[list[str]]
    continuity: NotRequired[ThreadAwareContinuityBundle]


JourneyLifecycleStatus = Literal["active", "paused", "completed", "archived"]


class CreateJourneyInput(TypedDict, total=False):
    userId: Required[Id]
    label: Required[str]
    currentQuestion: NotRequired[str]
    relatedMaterialIds: NotRequired[list[Id]]
    relatedSymbolIds: NotRequired[list[Id]]
    relatedPatternIds: NotRequired[list[Id]]
    relatedDreamSeriesIds: NotRequired[list[Id]]
    relatedGoalIds: NotRequired[list[Id]]
    nextReviewDueAt: NotRequired[str]
    status: NotRequired[JourneyLifecycleStatus]


class ListJourneysInput(TypedDict, total=False):
    userId: Required[Id]
    statuses: NotRequired[list[JourneyStatus]]
    includeDeleted: NotRequired[bool]
    limit: NotRequired[int]


class GetJourneyInput(TypedDict, total=False):
    userId: Required[Id]
    journeyId: NotRequired[Id]
    journeyLabel: NotRequired[str]
    includeDeleted: NotRequired[bool]


class UpdateJourneyInput(TypedDict, total=False):
    userId: Required[Id]
    journeyId: NotRequired[Id]
    journeyLabel: NotRequired[str]
    label: NotRequired[str]
    currentQuestion: NotRequired[str]
    addRelatedMaterialIds: NotRequired[list[Id]]
    removeRelatedMaterialIds: NotRequired[list[Id]]
    addRelatedSymbolIds: NotRequired[list[Id]]
    removeRelatedSymbolIds: NotRequired[list[Id]]
    addRelatedPatternIds: NotRequired[list[Id]]
    removeRelatedPatternIds: NotRequired[list[Id]]
    addRelatedDreamSeriesIds: NotRequired[list[Id]]
    removeRelatedDreamSeriesIds: NotRequired[list[Id]]
    addRelatedGoalIds: NotRequired[list[Id]]
    removeRelatedGoalIds: NotRequired[list[Id]]
    nextReviewDueAt: NotRequired[str]


class SetJourneyStatusInput(TypedDict, total=False):
    userId: Required[Id]
    journeyId: NotRequired[Id]
    journeyLabel: NotRequired[str]
    status: Required[JourneyLifecycleStatus]


class GenerateJourneyPageInput(TypedDict, total=False):
    userId: Required[Id]
    windowStart: NotRequired[str]
    windowEnd: NotRequired[str]
    explicitQuestion: NotRequired[str]
    maxInvitations: NotRequired[int]
    includeAnalysisPacket: NotRequired[bool]


JourneyPageActionKind = Literal["tool", "command", "entity"]
JourneyPageWriteIntent = Literal["read", "write"]


class JourneyPageAction(TypedDict, total=False):
    label: Required[str]
    kind: Required[JourneyPageActionKind]
    operation: NotRequired[str]
    command: NotRequired[str]
    payload: NotRequired[dict[str, object]]
    entityType: NotRequired[str]
    entityId: NotRequired[Id]
    writeIntent: Required[JourneyPageWriteIntent]
    requiresExplicitUserAction: Required[bool]


JourneyPageSection = Literal[
    "alive_today",
    "weekly_reflection",
    "rhythmic_invitations",
    "practice_container",
    "analysis_packet",
]


class JourneyPageCard(TypedDict, total=False):
    id: Required[Id]
    section: Required[JourneyPageSection]
    title: Required[str]
    body: Required[str]
    status: NotRequired[str]
    entityRefs: NotRequired[dict[str, list[Id]]]
    actions: Required[list[JourneyPageAction]]
    payload: NotRequired[dict[str, object]]


class JourneyAliveTodaySurface(TypedDict, total=False):
    summaryId: Required[Id]
    title: Required[str]
    response: Required[str]
    activeThemes: Required[list[str]]
    recurringSymbolIds: Required[list[Id]]


JourneyWeeklySurfaceKind = Literal[
    "latest_review",
    "review_due",
    "review_invitation_active",
    "quiet",
]


class JourneyWeeklySurface(TypedDict, total=False):
    kind: Required[JourneyWeeklySurfaceKind]
    title: Required[str]
    summary: Required[str]
    reviewId: NotRequired[Id]
    briefId: NotRequired[Id]
    windowStart: Required[str]
    windowEnd: Required[str]
    actions: Required[list[JourneyPageAction]]


JourneyInvitationKind = Literal["active_brief", "due_seed_preview"]


class JourneyInvitationPreview(TypedDict, total=False):
    kind: Required[JourneyInvitationKind]
    title: Required[str]
    summary: Required[str]
    briefType: Required[str]
    briefId: NotRequired[Id]
    triggerKey: NotRequired[str]
    status: NotRequired[str]
    suggestedAction: NotRequired[str]
    relatedJourneyIds: Required[list[Id]]
    relatedMaterialIds: Required[list[Id]]
    relatedSymbolIds: Required[list[Id]]
    relatedPracticeSessionIds: Required[list[Id]]
    actions: Required[list[JourneyPageAction]]


JourneyPracticeContainerKind = Literal[
    "practice_follow_up",
    "recommended_session",
    "suggested_container",
    "quiet",
]


class JourneyPracticeContainer(TypedDict, total=False):
    kind: Required[JourneyPracticeContainerKind]
    title: Required[str]
    summary: Required[str]
    practiceSessionId: NotRequired[Id]
    status: NotRequired[str]
    practiceRecommendation: NotRequired[PracticePlan]
    actions: Required[list[JourneyPageAction]]


class JourneyAnalysisPacketItem(TypedDict, total=False):
    label: Required[str]
    summary: NotRequired[str]
    entityType: NotRequired[str]
    entityId: NotRequired[Id]
    source: Required[str]


JourneyAnalysisSectionType = Literal[
    "symbol_field",
    "life_context",
    "method_context",
    "journey_threads",
    "practice_context",
]


class JourneyAnalysisPacketSection(TypedDict, total=False):
    sectionType: Required[JourneyAnalysisSectionType]
    title: Required[str]
    items: Required[list[JourneyAnalysisPacketItem]]


class JourneyFutureSeams(TypedDict, total=False):
    thresholdPacket: NotRequired[dict[str, object]]
    relationalFieldPacket: NotRequired[dict[str, object]]
    correspondencePacket: NotRequired[dict[str, object]]
    livingMythPacket: NotRequired[dict[str, object]]


class JourneyAnalysisPacketPreview(TypedDict, total=False):
    status: Required[Literal["preview"]]
    bounded: Required[bool]
    windowStart: Required[str]
    windowEnd: Required[str]
    sections: Required[list[JourneyAnalysisPacketSection]]
    futureSeams: NotRequired[JourneyFutureSeams]


class JourneyPageResult(TypedDict, total=False):
    pageId: Required[Id]
    userId: Required[Id]
    title: Required[str]
    generatedAt: Required[str]
    windowStart: Required[str]
    windowEnd: Required[str]
    cards: Required[list[JourneyPageCard]]
    aliveToday: Required[JourneyAliveTodaySurface]
    weeklySurface: Required[JourneyWeeklySurface]
    rhythmicInvitations: Required[list[JourneyInvitationPreview]]
    practiceContainer: Required[JourneyPracticeContainer]
    analysisPacket: NotRequired[JourneyAnalysisPacketPreview]
    fallbackText: Required[str]
    warnings: Required[list[str]]
    continuity: NotRequired[ThreadAwareContinuityBundle]


class PlanRitualInput(TypedDict, total=False):
    userId: Required[Id]
    windowStart: NotRequired[str]
    windowEnd: NotRequired[str]
    ritualIntent: NotRequired[RitualIntent]
    narrativeMode: NotRequired[NarrativeMode]
    explicitQuestion: NotRequired[str]
    sourceRefs: NotRequired[list[PresentationSourceRef]]
    requestedSurfaces: NotRequired[RequestedRitualSurfaces]
    renderPolicy: NotRequired[RitualRenderPolicy]
    completionPolicy: NotRequired[RitualCompletionPolicy]
    privacyClass: NotRequired[PresentationPrivacyClass]
    locale: NotRequired[str]
    safetyContext: NotRequired[SafetyContext]


class PlanRitualWorkflowResult(PresentationRitualPlanResult, total=False):
    continuity: NotRequired[ThreadAwareContinuityBundle]


class GenerateRhythmicBriefsInput(TypedDict, total=False):
    userId: Required[Id]
    windowStart: NotRequired[str]
    windowEnd: NotRequired[str]
    source: NotRequired[RhythmBriefSource]
    briefTypes: NotRequired[list[str]]
    limit: NotRequired[int]
    safetyContext: NotRequired[SafetyContext]


class RhythmicBriefWorkflowResult(TypedDict, total=False):
    briefs: Required[list[ProactiveBriefRecord]]
    skippedReasons: NotRequired[list[str]]
    continuity: NotRequired[ThreadAwareContinuityBundle]


class RespondRhythmicBriefInput(TypedDict, total=False):
    userId: Required[Id]
    briefId: Required[Id]
    action: Required[str]
    note: NotRequired[str]
    llmResult: NotRequired[RhythmicBriefResult]


class AnswerAmplificationPromptInput(TypedDict, total=False):
    userId: Required[Id]
    promptId: NotRequired[Id]
    materialId: NotRequired[Id]
    runId: NotRequired[Id]
    symbolId: NotRequired[Id]
    canonicalName: Required[str]
    surfaceText: Required[str]
    associationText: Required[str]
    feelingTone: NotRequired[str]
    bodySensations: NotRequired[list[str]]
    memoryRefs: NotRequired[list[Id]]
    evidenceIds: NotRequired[list[Id]]
    privacyClass: NotRequired[PrivacyClass]


class CaptureConsciousAttitudeInput(TypedDict, total=False):
    userId: Required[Id]
    windowStart: Required[str]
    windowEnd: Required[str]
    stanceSummary: Required[str]
    activeValues: NotRequired[list[str]]
    activeConflicts: NotRequired[list[str]]
    avoidedThemes: NotRequired[list[str]]
    emotionalTone: NotRequired[str]
    egoPosition: NotRequired[str]
    confidence: NotRequired[str]
    relatedMaterialIds: NotRequired[list[Id]]
    relatedGoalIds: NotRequired[list[Id]]
    evidenceIds: NotRequired[list[Id]]
    source: NotRequired[str]
    status: NotRequired[str]
    privacyClass: NotRequired[PrivacyClass]


class SetConsentPreferenceInput(TypedDict, total=False):
    userId: Required[Id]
    scope: Required[str]
    status: Required[str]
    note: NotRequired[str]
    source: NotRequired[str]


class SetCulturalFrameInput(TypedDict, total=False):
    userId: Required[Id]
    culturalFrameId: NotRequired[Id]
    label: Required[str]
    type: NotRequired[str]
    allowedUses: NotRequired[list[str]]
    avoidUses: NotRequired[list[str]]
    notes: NotRequired[str]
    status: NotRequired[str]


class UpsertGoalInput(TypedDict, total=False):
    userId: Required[Id]
    goalId: NotRequired[Id]
    label: Required[str]
    description: NotRequired[str]
    status: NotRequired[str]
    valueTags: NotRequired[list[str]]
    linkedMaterialIds: NotRequired[list[Id]]
    linkedSymbolIds: NotRequired[list[Id]]
    evidenceIds: NotRequired[list[Id]]


class UpsertGoalTensionInput(TypedDict, total=False):
    userId: Required[Id]
    tensionId: NotRequired[Id]
    goalIds: Required[list[Id]]
    tensionSummary: Required[str]
    polarityLabels: NotRequired[list[str]]
    evidenceIds: NotRequired[list[Id]]
    status: NotRequired[str]


class CaptureRealityAnchorsInput(TypedDict, total=False):
    userId: Required[Id]
    label: NotRequired[str]
    summary: Required[str]
    anchorSummary: Required[str]
    workDailyLifeContinuity: Required[str]
    sleepBodyRegulation: Required[str]
    relationshipContact: Required[str]
    reflectiveCapacity: Required[str]
    groundingRecommendation: Required[str]
    reasons: NotRequired[list[str]]
    relatedMaterialIds: NotRequired[list[Id]]
    relatedSymbolIds: NotRequired[list[Id]]
    relatedGoalIds: NotRequired[list[Id]]
    relatedJourneyIds: NotRequired[list[Id]]
    privacyClass: NotRequired[PrivacyClass]


class UpsertThresholdProcessInput(TypedDict, total=False):
    userId: Required[Id]
    thresholdId: NotRequired[Id]
    label: NotRequired[str]
    summary: Required[str]
    thresholdName: Required[str]
    phase: Required[str]
    whatIsEnding: Required[str]
    notYetBegun: Required[str]
    bodyCarrying: NotRequired[str]
    groundingStatus: Required[str]
    symbolicLens: NotRequired[str]
    invitationReadiness: Required[str]
    normalizedThresholdKey: Required[str]
    relatedMaterialIds: NotRequired[list[Id]]
    relatedSymbolIds: NotRequired[list[Id]]
    relatedGoalIds: NotRequired[list[Id]]
    relatedDreamSeriesIds: NotRequired[list[Id]]
    relatedJourneyIds: NotRequired[list[Id]]
    privacyClass: NotRequired[PrivacyClass]


class RecordRelationalSceneInput(TypedDict, total=False):
    userId: Required[Id]
    sceneId: NotRequired[Id]
    label: NotRequired[str]
    summary: Required[str]
    sceneSummary: Required[str]
    chargedRoles: NotRequired[list[dict[str, object]]]
    recurringAffect: NotRequired[list[str]]
    recurrenceContexts: NotRequired[list[str]]
    normalizedSceneKey: Required[str]
    relatedMaterialIds: NotRequired[list[Id]]
    relatedGoalIds: NotRequired[list[Id]]
    relatedJourneyIds: NotRequired[list[Id]]
    evidenceIds: NotRequired[list[Id]]
    privacyClass: NotRequired[PrivacyClass]


class RecordInnerOuterCorrespondenceInput(TypedDict, total=False):
    userId: Required[Id]
    correspondenceId: NotRequired[Id]
    label: NotRequired[str]
    summary: Required[str]
    correspondenceSummary: Required[str]
    innerRefs: NotRequired[list[Id]]
    outerRefs: NotRequired[list[Id]]
    symbolIds: NotRequired[list[Id]]
    relatedJourneyIds: NotRequired[list[Id]]
    userCharge: Required[str]
    caveat: Required[str]
    normalizedCorrespondenceKey: Required[str]
    evidenceIds: NotRequired[list[Id]]
    privacyClass: NotRequired[PrivacyClass]


class RecordNuminousEncounterInput(TypedDict, total=False):
    userId: Required[Id]
    label: NotRequired[str]
    summary: Required[str]
    encounterMedium: Required[str]
    affectTone: Required[str]
    containmentNeed: Required[str]
    interpretationConstraint: Required[str]
    relatedMaterialIds: NotRequired[list[Id]]
    relatedSymbolIds: NotRequired[list[Id]]
    relatedJourneyIds: NotRequired[list[Id]]
    evidenceIds: NotRequired[list[Id]]
    privacyClass: NotRequired[PrivacyClass]


class RecordAestheticResonanceInput(TypedDict, total=False):
    userId: Required[Id]
    label: NotRequired[str]
    summary: Required[str]
    medium: Required[str]
    objectDescription: Required[str]
    resonanceSummary: Required[str]
    feelingTone: NotRequired[str]
    bodySensations: NotRequired[list[str]]
    relatedMaterialIds: NotRequired[list[Id]]
    relatedSymbolIds: NotRequired[list[Id]]
    relatedJourneyIds: NotRequired[list[Id]]
    evidenceIds: NotRequired[list[Id]]
    privacyClass: NotRequired[PrivacyClass]


class GenerateThresholdReviewInput(TypedDict, total=False):
    userId: Required[Id]
    windowStart: NotRequired[str]
    windowEnd: NotRequired[str]
    thresholdProcessId: NotRequired[Id]
    explicitQuestion: NotRequired[str]
    safetyContext: NotRequired[SafetyContext]
    persist: NotRequired[bool]


class ThresholdReviewWorkflowResult(TypedDict, total=False):
    review: NotRequired[LivingMythReviewRecord]
    result: Required[ThresholdReviewResult]
    pendingProposals: Required[list[MemoryWriteProposal]]
    practiceSession: NotRequired[PracticeSessionRecord]
    continuity: NotRequired[ThreadAwareContinuityBundle]


class GenerateLivingMythReviewInput(TypedDict, total=False):
    userId: Required[Id]
    windowStart: NotRequired[str]
    windowEnd: NotRequired[str]
    explicitQuestion: NotRequired[str]
    safetyContext: NotRequired[SafetyContext]
    persist: NotRequired[bool]


class LivingMythReviewWorkflowResult(TypedDict, total=False):
    review: NotRequired[LivingMythReviewRecord]
    result: Required[LivingMythReviewResult]
    pendingProposals: Required[list[MemoryWriteProposal]]
    practiceSession: NotRequired[PracticeSessionRecord]
    continuity: NotRequired[ThreadAwareContinuityBundle]


class GenerateAnalysisPacketInput(TypedDict, total=False):
    userId: Required[Id]
    windowStart: NotRequired[str]
    windowEnd: NotRequired[str]
    packetFocus: NotRequired[AnalysisPacketFocus]
    analyticLens: NotRequired[AnalyticLens]
    explicitQuestion: NotRequired[str]
    safetyContext: NotRequired[SafetyContext]
    persist: NotRequired[bool]


class AnalysisPacketWorkflowResult(TypedDict, total=False):
    packet: NotRequired[AnalysisPacketRecord]
    result: Required[AnalysisPacketResult]
    continuity: NotRequired[ThreadAwareContinuityBundle]


class ApproveLivingMythReviewProposalsInput(TypedDict, total=False):
    userId: Required[Id]
    reviewId: Required[Id]
    proposalIds: Required[list[Id]]


class RejectLivingMythReviewProposalsInput(TypedDict, total=False):
    userId: Required[Id]
    reviewId: Required[Id]
    proposalIds: Required[list[Id]]
    reason: NotRequired[str]


class RecordRitualCompletionBodyStateInput(RitualCompletionBodyStatePayload, total=False):
    pass


class RecordRitualCompletionInput(TypedDict, total=False):
    userId: Required[Id]
    artifactId: Required[str]
    manifestVersion: Required[str]
    idempotencyKey: Required[str]
    completedAt: Required[str]
    playbackState: Required[str]
    planId: NotRequired[Id]
    sourceRefs: NotRequired[list[PresentationSourceRef]]
    durationMs: NotRequired[int]
    completedSections: NotRequired[list[str]]
    reflectionText: NotRequired[str]
    practiceFeedback: NotRequired[dict[str, object]]
    bodyState: NotRequired[RecordRitualCompletionBodyStateInput]
    clientMetadata: NotRequired[dict[str, object]]


class RecordRitualCompletionResult(TypedDict, total=False):
    event: Required[RitualCompletionEvent]
    replayed: Required[bool]
