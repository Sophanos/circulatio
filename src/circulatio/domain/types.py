from __future__ import annotations

from typing import TYPE_CHECKING, Literal, NotRequired, Required, TypedDict

if TYPE_CHECKING:
    from .clarifications import (
        ClarificationCaptureTarget,
        ClarificationCreatedRecordRef,
        ClarificationIntentType,
        ExpectedAnswerKind,
    )
    from .method_state import (
        MethodStateAnchorRefs,
        MethodStateCaptureTargetKind,
        MethodStateResponseSource,
    )

ISODateString = str
Id = str

MaterialType = Literal[
    "dream",
    "reflection",
    "charged_event",
    "symbolic_motif",
    "practice_outcome",
]
PrivacyClass = Literal[
    "session_only",
    "approved_summary",
    "approved_raw_material",
    "sensitive",
    "user_private",
]
EvidenceType = Literal[
    "material_text_span",
    "dream_text_span",
    "user_association",
    "prior_material",
    "recurring_symbol",
    "life_event_ref",
    "life_os_state_snapshot",
    "practice_outcome",
    "cultural_reference",
    "counterevidence",
    "session_context",
    "method_state_response",
]
Confidence = Literal["low", "medium", "high"]
HypothesisType = Literal[
    "compensation",
    "complex_candidate",
    "symbol_meaning",
    "practice_need",
    "theme",
]
SafetyFlag = Literal[
    "self_harm_or_suicide",
    "harm_to_others",
    "psychosis_like_certainty",
    "mania_like_activation",
    "severe_dissociation",
    "panic_or_overwhelm",
    "intoxication",
    "minor_policy_sensitive",
    "none",
]
SymbolCategory = Literal[
    "animal",
    "element",
    "place",
    "object",
    "figure",
    "body",
    "movement",
    "color",
    "threshold",
    "unknown",
]
PracticeType = Literal[
    "grounding",
    "journaling",
    "passive_imagination",
    "brief_meditation",
    "active_imagination",
    "somatic_tracking",
    "shadow_dialogue",
    "image_dialogue",
    "body_checkin",
    "amplification_journaling",
    "none",
]
CoachSurface = Literal[
    "generic",
    "alive_today",
    "weekly_review",
    "journey_page",
    "rhythmic_brief",
    "practice_followup",
    "method_state_response",
    "analysis_packet",
]
CoachLoopKind = Literal[
    "soma",
    "goal_guidance",
    "relational_scene",
    "practice_integration",
    "journey_reentry",
    "resource_support",
]
CoachLoopStatus = Literal[
    "eligible",
    "waiting_for_user",
    "cooling_down",
    "withheld",
    "track_only",
]
CoachMoveKind = Literal[
    "ask_body_checkin",
    "ask_goal_tension",
    "ask_relational_scene",
    "ask_practice_followup",
    "offer_resource",
    "offer_practice",
    "hold_silence",
    "track_without_prompt",
    "return_to_journey",
]
CoachAnswerMode = Literal["free_text", "choice_then_free_text", "skip_only"]
CoachSkipBehavior = Literal["hold_silence", "track_only", "cooldown"]
EmbodiedResourceType = Literal[
    "audio",
    "video",
    "text",
    "breath_container",
    "voice_script",
    "interactive_card",
]
EmbodiedResourceModality = Literal[
    "grounding",
    "breath",
    "body_scan",
    "somatic_tracking",
    "journaling",
    "association",
    "movement",
]
ActivationBand = Literal["low", "moderate", "high", "overwhelming"]
PsychologicalFunction = Literal["thinking", "feeling", "sensation", "intuition"]
TypologyRole = Literal["dominant", "auxiliary", "tertiary", "inferior", "compensation_link"]
TypologySignalCategory = Literal[
    "linguistic_marker",
    "orientation_marker",
    "sensation_trigger",
    "fixation_or_overuse",
    "compensatory_marker",
    "longitudinal_pattern",
    "feedback_signal",
]


class CrisisSupportResource(TypedDict, total=False):
    label: Required[str]
    region: NotRequired[str]
    phone: NotRequired[str]
    text: NotRequired[str]
    url: NotRequired[str]
    note: NotRequired[str]


class SafetyDispositionClear(TypedDict):
    status: Literal["clear"]
    flags: list[SafetyFlag]
    depthWorkAllowed: Literal[True]
    message: NotRequired[str]


class SafetyDispositionGroundingOnly(TypedDict):
    status: Literal["grounding_only"]
    flags: list[SafetyFlag]
    depthWorkAllowed: Literal[False]
    message: str
    suggestedSupport: list[CrisisSupportResource]


class SafetyDispositionCrisisHandoff(TypedDict):
    status: Literal["crisis_handoff"]
    flags: list[SafetyFlag]
    depthWorkAllowed: Literal[False]
    message: str
    suggestedSupport: list[CrisisSupportResource]


SafetyDisposition = (
    SafetyDispositionClear | SafetyDispositionGroundingOnly | SafetyDispositionCrisisHandoff
)


class SessionContext(TypedDict):
    contextNotes: list[str]
    recentEventNotes: list[str]
    currentStateNotes: list[str]
    source: Literal["current-conversation"]


class SafetyContext(TypedDict, total=False):
    userReportedActivation: Literal["low", "moderate", "high", "overwhelming"]
    crisisSupportResources: list[CrisisSupportResource]
    userIsMinor: bool
    intoxicationReported: bool


DepthMove = Literal[
    "withhold",
    "mirror_only",
    "ask_consent",
    "soften",
    "allow",
]
DepthWorkScope = Literal[
    "shadow_work",
    "projection_language",
    "collective_amplification",
    "active_imagination",
    "somatic_correlation",
    "proactive_briefing",
    "archetypal_patterning",
    "inner_outer_correspondence",
    "living_myth_synthesis",
]
InterpretationDepthLevel = Literal[
    "grounding_only",
    "observations_only",
    "personal_amplification_needed",
    "cautious_pattern_note",
    "depth_interpretation_allowed",
]


class DepthReadinessAssessment(TypedDict, total=False):
    status: Required[Literal["grounding_only", "limited", "ready"]]
    allowedMoves: Required[dict[DepthWorkScope, DepthMove]]
    reasons: Required[list[str]]
    requiredUserAction: NotRequired[str]
    evidenceIds: Required[list[Id]]


class MethodGateResult(TypedDict, total=False):
    depthLevel: Required[InterpretationDepthLevel]
    missingPrerequisites: Required[list[str]]
    blockedMoves: Required[list[str]]
    requiredPrompts: Required[list[str]]
    responseConstraints: Required[list[str]]


class InterpretationOptions(TypedDict, total=False):
    maxHistoricalItems: int
    maxHypotheses: int
    allowCulturalAmplification: bool
    allowLifeContextLinks: bool
    proposeRawMaterialStorage: bool
    enableTypology: bool
    maxTypologyHypotheses: int


class UserAssociationInput(TypedDict, total=False):
    surfaceText: Required[str]
    association: Required[str]
    tone: NotRequired[str]


class LifeEventDateRange(TypedDict):
    start: ISODateString
    end: ISODateString


class LifeEventRefSummary(TypedDict, total=False):
    id: Required[Id]
    date: NotRequired[ISODateString]
    dateRange: NotRequired[LifeEventDateRange]
    summary: Required[str]
    intensity: NotRequired[Literal["low", "moderate", "high"]]
    symbolicAnnotation: NotRequired[str]


class MaterialSummary(TypedDict):
    id: Id
    materialType: MaterialType
    date: ISODateString
    summary: str
    symbolNames: list[str]
    themeLabels: list[str]


class InterpretationFeedbackSummary(TypedDict, total=False):
    hypothesisId: Required[Id]
    runId: Required[Id]
    feedback: Required[Literal["resonated", "rejected", "partially_refined"]]
    note: NotRequired[str]
    timestamp: Required[ISODateString]
    normalizedClaimKey: NotRequired[str]
    claimDomain: NotRequired[str]


InterpretationInteractionFeedback = Literal[
    "too_much",
    "too_vague",
    "too_abstract",
    "good_level",
    "helpful",
    "not_helpful",
]
PracticeInteractionFeedback = Literal[
    "good_fit",
    "not_for_me",
    "too_intense",
    "too_long",
    "helpful",
    "not_helpful",
]
InteractionFeedbackDomain = Literal["interpretation", "practice", "brief", "journey_page"]
InteractionFeedbackTargetType = Literal[
    "interpretation_run",
    "practice_session",
    "brief",
    "journey_page",
]


class InteractionFeedbackSummary(TypedDict, total=False):
    id: Required[Id]
    domain: Required[InteractionFeedbackDomain]
    targetType: Required[InteractionFeedbackTargetType]
    targetId: Required[Id]
    feedback: Required[str]
    locale: NotRequired[str]
    createdAt: Required[ISODateString]


class PracticeOutcomeSummary(TypedDict, total=False):
    id: Required[Id]
    practiceType: Required[PracticeType]
    target: NotRequired[str]
    outcome: Required[str]
    activationBefore: NotRequired[Literal["low", "moderate", "high"]]
    activationAfter: NotRequired[Literal["low", "moderate", "high"]]
    timestamp: Required[ISODateString]


class PracticeSessionSummary(TypedDict, total=False):
    id: Required[Id]
    practiceType: Required[PracticeType]
    target: NotRequired[str]
    status: Required[str]
    outcome: NotRequired[str]
    activationBefore: NotRequired[Literal["low", "moderate", "high"]]
    activationAfter: NotRequired[Literal["low", "moderate", "high"]]
    outcomeEvidenceIds: NotRequired[list[Id]]
    templateId: NotRequired[Id]
    modality: NotRequired[str]
    intensity: NotRequired[str]
    coachLoopKey: NotRequired[Id]
    resourceInvitationId: NotRequired[Id]
    coachLoopKind: NotRequired[CoachLoopKind]
    coachMoveKind: NotRequired[CoachMoveKind]
    relatedResourceIds: NotRequired[list[Id]]
    relatedJourneyIds: NotRequired[list[Id]]
    resourceInvitation: NotRequired[ResourceInvitationSummary]
    createdAt: Required[ISODateString]
    completedAt: NotRequired[ISODateString]
    nextFollowUpDueAt: NotRequired[ISODateString]


class ConsciousAttitudeSummary(TypedDict, total=False):
    id: Required[Id]
    stanceSummary: Required[str]
    activeValues: Required[list[str]]
    activeConflicts: Required[list[str]]
    avoidedThemes: Required[list[str]]
    confidence: Required[Confidence]
    status: Required[str]
    evidenceIds: Required[list[Id]]
    emotionalTone: NotRequired[str]
    egoPosition: NotRequired[str]


class BodyStateSummary(TypedDict, total=False):
    id: Required[Id]
    observedAt: Required[ISODateString]
    sensation: Required[str]
    bodyRegion: NotRequired[str]
    activation: NotRequired[Literal["low", "moderate", "high", "overwhelming"]]
    tone: NotRequired[str]
    linkedSymbolIds: NotRequired[list[Id]]
    linkedGoalIds: NotRequired[list[Id]]


class GoalSummary(TypedDict, total=False):
    id: Required[Id]
    label: Required[str]
    status: Required[str]
    valueTags: Required[list[str]]
    description: NotRequired[str]
    evidenceIds: NotRequired[list[Id]]


class GoalTensionSummary(TypedDict, total=False):
    id: Required[Id]
    goalIds: Required[list[Id]]
    tensionSummary: Required[str]
    polarityLabels: Required[list[str]]
    status: Required[str]
    evidenceIds: Required[list[Id]]


class PersonalAmplificationSummary(TypedDict, total=False):
    id: Required[Id]
    canonicalName: Required[str]
    surfaceText: Required[str]
    associationText: Required[str]
    feelingTone: NotRequired[str]
    bodySensations: NotRequired[list[str]]
    createdAt: Required[ISODateString]


class AmplificationPromptSummary(TypedDict, total=False):
    id: Required[Id]
    canonicalName: Required[str]
    surfaceText: Required[str]
    promptText: Required[str]
    reason: Required[str]
    status: Required[str]
    createdAt: Required[ISODateString]
    symbolMentionId: NotRequired[Id]
    symbolRefKey: NotRequired[str]


class ConsentPreferenceSummary(TypedDict, total=False):
    id: Required[Id]
    scope: Required[DepthWorkScope]
    status: Required[str]
    note: NotRequired[str]


class DreamSeriesSummary(TypedDict, total=False):
    id: Required[Id]
    label: Required[str]
    status: Required[str]
    progressionSummary: NotRequired[str]
    egoTrajectory: NotRequired[str]
    compensationTrajectory: NotRequired[str]
    confidence: Required[Confidence]
    materialIds: Required[list[Id]]
    recentMemberships: NotRequired[list[DreamSeriesMembershipSummary]]
    lastSeen: NotRequired[ISODateString]
    symbolIds: NotRequired[list[Id]]
    motifKeys: NotRequired[list[str]]
    settingKeys: NotRequired[list[str]]
    figureKeys: NotRequired[list[str]]


class DreamSeriesMembershipSummary(TypedDict, total=False):
    id: Required[Id]
    seriesId: Required[Id]
    materialId: Required[Id]
    sequenceIndex: NotRequired[int]
    matchScore: Required[float]
    matchingFeatures: Required[list[str]]
    narrativeRole: Required[str]
    egoStance: NotRequired[str]
    lysisSummary: NotRequired[str]
    status: Required[str]
    createdAt: Required[ISODateString]


class DreamSeriesSuggestion(TypedDict, total=False):
    seriesId: NotRequired[Id]
    label: Required[str]
    matchScore: Required[float]
    matchingFeatures: Required[list[str]]
    narrativeRole: Required[str]
    confidence: Required[Confidence]
    ambiguityNote: NotRequired[str]
    evidenceIds: Required[list[Id]]
    egoStance: NotRequired[str]
    lysisSummary: NotRequired[str]
    progressionSummary: NotRequired[str]
    compensationTrajectory: NotRequired[str]


class UserAdaptationProfileSummary(TypedDict, total=False):
    id: Required[Id]
    explicitPreferences: Required[dict[str, object]]
    learnedSignals: Required[dict[str, object]]
    sampleCounts: Required[dict[str, int]]


CommunicationTone = Literal["gentle", "direct", "spacious"]
CommunicationQuestioningStyle = Literal["soma_first", "image_first", "feeling_first", "reflective"]
CommunicationSymbolicDensity = Literal["sparse", "moderate", "dense"]
InterpretationDepthPreference = Literal[
    "brief_pattern_notes",
    "cautious_amplification",
    "deep_amplification",
]
InterpretationModalityBias = Literal["body", "image", "emotion", "narrative", "cultural"]
AdaptationPreferenceScope = Literal["communication", "interpretation", "practice", "rhythm"]
RuntimeHintSource = Literal["default", "learned", "explicit", "mixed"]


class CommunicationPreferenceSettings(TypedDict, total=False):
    tone: NotRequired[CommunicationTone]
    questioningStyle: NotRequired[CommunicationQuestioningStyle]
    symbolicDensity: NotRequired[CommunicationSymbolicDensity]


class InterpretationPreferenceSettings(TypedDict, total=False):
    depthPreference: NotRequired[InterpretationDepthPreference]
    modalityBias: NotRequired[InterpretationModalityBias]


class PracticePreferenceSettings(TypedDict, total=False):
    preferredModalities: NotRequired[list[str]]
    avoidedModalities: NotRequired[list[str]]
    maxDurationMinutes: NotRequired[int]


class RhythmPreferenceSettings(TypedDict, total=False):
    maxBriefsPerDay: NotRequired[int]
    minimumHoursBetweenBriefs: NotRequired[int]
    dismissedTriggerCooldownHours: NotRequired[int]
    actedOnTriggerCooldownHours: NotRequired[int]
    quietHours: NotRequired[dict[str, str]]


class CommunicationHints(TypedDict, total=False):
    tone: Required[CommunicationTone]
    questioningStyle: Required[CommunicationQuestioningStyle]
    symbolicDensity: Required[CommunicationSymbolicDensity]
    source: Required[RuntimeHintSource]


class InterpretationHints(TypedDict, total=False):
    depthPreference: Required[InterpretationDepthPreference]
    modalityBias: Required[InterpretationModalityBias]
    source: Required[RuntimeHintSource]


class PracticeHints(TypedDict, total=False):
    preferredModalities: NotRequired[list[str]]
    avoidedModalities: NotRequired[list[str]]
    maxDurationMinutes: NotRequired[int]
    recentSkips: NotRequired[list[str]]
    recentCompletions: NotRequired[list[str]]
    notes: NotRequired[list[str]]
    maturity: Required[Literal["default", "learning", "mature"]]
    source: Required[RuntimeHintSource]


class JourneySummary(TypedDict, total=False):
    id: Required[Id]
    label: Required[str]
    status: Required[str]
    currentQuestion: NotRequired[str]
    relatedMaterialIds: Required[list[Id]]
    relatedSymbolIds: Required[list[Id]]
    relatedPatternIds: Required[list[Id]]
    relatedDreamSeriesIds: Required[list[Id]]
    relatedGoalIds: Required[list[Id]]
    relatedBodyStateIds: NotRequired[list[Id]]


JourneyFamilyKind = Literal[
    "embodied_recurrence",
    "symbol_body_life_pressure",
    "thought_loop_typology_restraint",
    "relational_scene_recurrence",
    "practice_reentry",
    "cross_family",
]


class JourneyFollowthroughSummary(TypedDict, total=False):
    journeyId: Required[Id]
    family: Required[JourneyFamilyKind]
    readiness: Required[Literal["quiet", "available", "ready"]]
    recommendedSurface: Required[CoachSurface | Literal["none"]]
    recommendedMoveKind: NotRequired[CoachMoveKind]
    bodyFirst: Required[bool]
    priority: Required[int]
    reasons: Required[list[str]]
    blockedEscalations: Required[list[str]]
    relatedExperimentIds: Required[list[Id]]
    currentExperimentStatus: NotRequired[
        Literal["active", "quiet", "completed", "released", "archived", "deleted"]
    ]
    relatedPracticeSessionIds: Required[list[Id]]
    relatedBodyStateIds: Required[list[Id]]
    relatedGoalTensionIds: Required[list[Id]]
    lastTouchedAt: Required[ISODateString]
    lastBriefedAt: NotRequired[ISODateString]
    cooldownUntil: NotRequired[ISODateString]


LongitudinalSignalType = Literal[
    "symbol_body_cooccurrence",
    "symbol_goal_cooccurrence",
    "body_goal_cooccurrence",
    "dream_series_shift",
    "culture_symbol_lens",
    "relational_scene_recurrence",
    "practice_feedback_pattern",
    "dream_ego_stance_shift",
    "compensation_pattern",
    "goal_tension_recurrence",
    "typology_feedback_signal",
]


class LongitudinalSignalSummary(TypedDict, total=False):
    id: Required[Id]
    signalType: Required[LongitudinalSignalType]
    summary: Required[str]
    sourceEntityIds: Required[list[Id]]
    materialIds: Required[list[Id]]
    count: Required[int]
    lastSeen: Required[ISODateString]
    strength: Required[Literal["weak", "moderate", "strong"]]


ThreadDigestKind = Literal[
    "journey",
    "dream_series",
    "threshold_process",
    "relational_scene",
    "goal_tension",
    "practice_loop",
    "longitudinal_signal",
    "coach_loop",
]
ThreadSurfaceReadinessLevel = Literal["quiet", "available", "ready"]


class ThreadSurfaceReadiness(TypedDict, total=False):
    intakeContext: NotRequired[ThreadSurfaceReadinessLevel]
    discovery: NotRequired[ThreadSurfaceReadinessLevel]
    aliveToday: NotRequired[ThreadSurfaceReadinessLevel]
    weeklyReview: NotRequired[ThreadSurfaceReadinessLevel]
    journeyPage: NotRequired[ThreadSurfaceReadinessLevel]
    rhythmicBrief: NotRequired[ThreadSurfaceReadinessLevel]
    thresholdReview: NotRequired[ThreadSurfaceReadinessLevel]
    livingMythReview: NotRequired[ThreadSurfaceReadinessLevel]
    analysisPacket: NotRequired[ThreadSurfaceReadinessLevel]
    methodStateResponse: NotRequired[ThreadSurfaceReadinessLevel]
    practice: NotRequired[ThreadSurfaceReadinessLevel]


class ThreadDigest(TypedDict, total=False):
    threadKey: Required[str]
    kind: Required[ThreadDigestKind]
    status: Required[str]
    summary: Required[str]
    entityRefs: Required[dict[str, list[Id]]]
    evidenceIds: Required[list[Id]]
    journeyIds: Required[list[Id]]
    sourceRecordRefs: Required[list[MethodStateSourceRef]]
    lastTouchedAt: Required[ISODateString]
    surfaceReadiness: Required[ThreadSurfaceReadiness]


AmplificationSourceKind = Literal[
    "symbol_reference",
    "depth_psychology_archive",
    "primary_text",
    "scholarly_reference",
    "other",
]


class AmplificationSourceSummary(TypedDict, total=False):
    label: Required[str]
    url: Required[str]
    kind: Required[AmplificationSourceKind]
    language: NotRequired[str]
    notes: NotRequired[str]


class CulturalFrameSummary(TypedDict, total=False):
    id: Required[Id]
    label: Required[str]
    type: NotRequired[str]
    status: Required[str]
    allowedUses: NotRequired[list[str]]
    avoidUses: NotRequired[list[str]]
    notes: NotRequired[str]


class CollectiveAmplificationSummary(TypedDict, total=False):
    id: Required[Id]
    symbolId: NotRequired[Id]
    canonicalName: Required[str]
    culturalFrameId: NotRequired[Id]
    lensLabel: NotRequired[str]
    amplificationText: Required[str]
    status: Required[str]
    createdAt: Required[ISODateString]


class RealityAnchorSummary(TypedDict, total=False):
    id: Required[Id]
    label: Required[str]
    summary: Required[str]
    confidence: Required[Confidence]
    evidenceIds: Required[list[Id]]
    anchorSummary: Required[str]
    workDailyLifeContinuity: Required[Literal["stable", "strained", "unknown"]]
    sleepBodyRegulation: Required[Literal["stable", "strained", "unknown"]]
    relationshipContact: Required[Literal["available", "thin", "unknown"]]
    reflectiveCapacity: Required[Literal["steady", "fragile", "unknown"]]
    groundingRecommendation: Required[Literal["clear_for_depth", "pace_gently", "grounding_first"]]
    reasons: Required[list[str]]
    status: Required[str]
    updatedAt: Required[ISODateString]


class SelfOrientationSummary(TypedDict, total=False):
    id: Required[Id]
    label: Required[str]
    summary: Required[str]
    confidence: Required[Confidence]
    evidenceIds: Required[list[Id]]
    orientationSummary: Required[str]
    emergentDirection: Required[str]
    egoRelation: Required[Literal["aligned", "conflicted", "avoidant", "curious", "unknown"]]
    movementLanguage: Required[list[str]]
    notMetaphysicalClaim: Required[Literal[True]]
    status: Required[str]
    updatedAt: Required[ISODateString]


class PsychicOppositionSummary(TypedDict, total=False):
    id: Required[Id]
    label: Required[str]
    summary: Required[str]
    confidence: Required[Confidence]
    evidenceIds: Required[list[Id]]
    poleA: Required[str]
    poleB: Required[str]
    oppositionSummary: Required[str]
    currentHoldingPattern: Required[str]
    pressureTone: NotRequired[str]
    holdingInstruction: NotRequired[str]
    normalizedOppositionKey: Required[str]
    status: Required[str]
    updatedAt: Required[ISODateString]


class EmergentThirdSignalSummary(TypedDict, total=False):
    id: Required[Id]
    label: Required[str]
    summary: Required[str]
    confidence: Required[Confidence]
    evidenceIds: Required[list[Id]]
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
    status: Required[str]
    updatedAt: Required[ISODateString]


class BridgeMomentSummary(TypedDict, total=False):
    id: Required[Id]
    label: Required[str]
    summary: Required[str]
    confidence: Required[Confidence]
    evidenceIds: Required[list[Id]]
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
    status: Required[str]
    updatedAt: Required[ISODateString]


class ThresholdProcessSummary(TypedDict, total=False):
    id: Required[Id]
    label: Required[str]
    summary: Required[str]
    confidence: Required[Confidence]
    evidenceIds: Required[list[Id]]
    thresholdName: Required[str]
    phase: Required[Literal["ending", "liminal", "reorientation", "return", "unknown"]]
    whatIsEnding: Required[str]
    notYetBegun: Required[str]
    bodyCarrying: NotRequired[str]
    groundingStatus: Required[Literal["steady", "strained", "unknown"]]
    symbolicLens: NotRequired[str]
    invitationReadiness: Required[Literal["not_now", "ask", "ready"]]
    normalizedThresholdKey: Required[str]
    status: Required[str]
    updatedAt: Required[ISODateString]


class RelationalSceneRoleSummary(TypedDict, total=False):
    roleLabel: Required[str]
    affectTone: NotRequired[str]
    egoStance: NotRequired[str]


class RelationalSceneSummary(TypedDict, total=False):
    id: Required[Id]
    label: Required[str]
    summary: Required[str]
    confidence: Required[Confidence]
    evidenceIds: Required[list[Id]]
    sceneSummary: Required[str]
    chargedRoles: Required[list[RelationalSceneRoleSummary]]
    recurringAffect: Required[list[str]]
    recurrenceContexts: Required[list[str]]
    normalizedSceneKey: Required[str]
    status: Required[str]
    updatedAt: Required[ISODateString]


class ProjectionHypothesisSummary(TypedDict, total=False):
    id: Required[Id]
    label: Required[str]
    summary: Required[str]
    confidence: Required[Literal["low", "medium"]]
    evidenceIds: Required[list[Id]]
    relationalSceneId: NotRequired[Id]
    hypothesisSummary: Required[str]
    projectionPattern: Required[str]
    userTestPrompt: Required[str]
    counterevidenceIds: Required[list[Id]]
    phrasingPolicy: Required[Literal["very_tentative"]]
    consentScope: Required[Literal["projection_language"]]
    normalizedHypothesisKey: Required[str]
    status: Required[str]
    updatedAt: Required[ISODateString]


class InnerOuterCorrespondenceSummary(TypedDict, total=False):
    id: Required[Id]
    label: Required[str]
    summary: Required[str]
    confidence: Required[Literal["low", "medium"]]
    evidenceIds: Required[list[Id]]
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
    status: Required[str]
    updatedAt: Required[ISODateString]


class NuminousEncounterSummary(TypedDict, total=False):
    id: Required[Id]
    label: Required[str]
    summary: Required[str]
    confidence: Required[Confidence]
    evidenceIds: Required[list[Id]]
    encounterMedium: Required[
        Literal["dream", "waking_event", "body", "art", "place", "conversation", "unknown"]
    ]
    affectTone: Required[str]
    containmentNeed: Required[Literal["ordinary_reflection", "pace_gently", "grounding_first"]]
    interpretationConstraint: Required[str]
    status: Required[str]
    updatedAt: Required[ISODateString]


class AestheticResonanceSummary(TypedDict, total=False):
    id: Required[Id]
    label: Required[str]
    summary: Required[str]
    confidence: Required[Confidence]
    evidenceIds: Required[list[Id]]
    medium: Required[str]
    objectDescription: Required[str]
    resonanceSummary: Required[str]
    feelingTone: NotRequired[str]
    bodySensations: Required[list[str]]
    status: Required[str]
    updatedAt: Required[ISODateString]


class ArchetypalPatternSummary(TypedDict, total=False):
    id: Required[Id]
    label: Required[str]
    summary: Required[str]
    confidence: Required[Literal["low", "medium"]]
    evidenceIds: Required[list[Id]]
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
    status: Required[str]
    updatedAt: Required[ISODateString]


class LifeChapterSnapshotSummary(TypedDict, total=False):
    id: Required[Id]
    label: Required[str]
    summary: Required[str]
    confidence: Required[Confidence]
    evidenceIds: Required[list[Id]]
    chapterLabel: Required[str]
    chapterSummary: Required[str]
    governingSymbolIds: Required[list[Id]]
    governingQuestions: Required[list[str]]
    activeOppositionIds: Required[list[Id]]
    thresholdProcessIds: Required[list[Id]]
    relationalSceneIds: Required[list[Id]]
    correspondenceIds: Required[list[Id]]
    chapterTone: NotRequired[str]
    status: Required[str]
    updatedAt: Required[ISODateString]


class MythicQuestionSummary(TypedDict, total=False):
    id: Required[Id]
    label: Required[str]
    summary: Required[str]
    confidence: Required[Confidence]
    evidenceIds: Required[list[Id]]
    questionText: Required[str]
    questionStatus: Required[Literal["active", "answered", "released"]]
    relatedChapterId: NotRequired[Id]
    lastReturnedAt: NotRequired[ISODateString]
    status: Required[str]
    updatedAt: Required[ISODateString]


class ThresholdMarkerSummary(TypedDict, total=False):
    id: Required[Id]
    label: Required[str]
    summary: Required[str]
    confidence: Required[Confidence]
    evidenceIds: Required[list[Id]]
    markerType: Required[
        Literal["ending", "initiation", "return", "choice", "loss", "bridge", "unknown"]
    ]
    markerSummary: Required[str]
    thresholdProcessId: NotRequired[Id]
    status: Required[str]
    updatedAt: Required[ISODateString]


class ComplexEncounterSummary(TypedDict, total=False):
    id: Required[Id]
    label: Required[str]
    summary: Required[str]
    confidence: Required[Confidence]
    evidenceIds: Required[list[Id]]
    complexCandidateId: NotRequired[Id]
    patternId: NotRequired[Id]
    encounterSummary: Required[str]
    trajectorySummary: Required[str]
    movement: Required[
        Literal["approaching", "avoiding", "dialogue", "integration_hint", "stuck", "unknown"]
    ]
    status: Required[str]
    updatedAt: Required[ISODateString]


class IntegrationContourSummary(TypedDict, total=False):
    id: Required[Id]
    label: Required[str]
    summary: Required[str]
    confidence: Required[Confidence]
    evidenceIds: Required[list[Id]]
    contourSummary: Required[str]
    symbolicStrands: Required[list[str]]
    somaticStrands: Required[list[str]]
    relationalStrands: Required[list[str]]
    existentialStrands: Required[list[str]]
    tensionsHeld: Required[list[str]]
    assimilatedSignals: Required[list[str]]
    unassimilatedEdges: Required[list[str]]
    nextQuestions: Required[list[str]]
    status: Required[str]
    updatedAt: Required[ISODateString]


class SymbolicWellbeingSnapshotSummary(TypedDict, total=False):
    id: Required[Id]
    label: Required[str]
    summary: Required[str]
    confidence: Required[Confidence]
    evidenceIds: Required[list[Id]]
    capacitySummary: Required[str]
    groundingCapacity: Required[Literal["steady", "strained", "unknown"]]
    symbolicLiveliness: Required[str]
    somaticContact: Required[str]
    relationalSpaciousness: Required[str]
    agencyTone: Required[str]
    supportNeeded: NotRequired[str]
    status: Required[str]
    updatedAt: Required[ISODateString]


class IndividuationContextSummary(TypedDict, total=False):
    realityAnchors: NotRequired[RealityAnchorSummary]
    selfOrientation: NotRequired[SelfOrientationSummary]
    activeOppositions: NotRequired[list[PsychicOppositionSummary]]
    emergentThirdSignals: NotRequired[list[EmergentThirdSignalSummary]]
    bridgeMoments: NotRequired[list[BridgeMomentSummary]]
    thresholdProcesses: NotRequired[list[ThresholdProcessSummary]]
    relationalScenes: NotRequired[list[RelationalSceneSummary]]
    projectionHypotheses: NotRequired[list[ProjectionHypothesisSummary]]
    innerOuterCorrespondences: NotRequired[list[InnerOuterCorrespondenceSummary]]
    numinousEncounters: NotRequired[list[NuminousEncounterSummary]]
    aestheticResonances: NotRequired[list[AestheticResonanceSummary]]
    archetypalPatterns: NotRequired[list[ArchetypalPatternSummary]]


class LivingMythContextSummary(TypedDict, total=False):
    currentLifeChapter: NotRequired[LifeChapterSnapshotSummary]
    activeMythicQuestions: NotRequired[list[MythicQuestionSummary]]
    recentThresholdMarkers: NotRequired[list[ThresholdMarkerSummary]]
    complexEncounters: NotRequired[list[ComplexEncounterSummary]]
    latestIntegrationContour: NotRequired[IntegrationContourSummary]
    latestSymbolicWellbeing: NotRequired[SymbolicWellbeingSnapshotSummary]


class CulturalOriginSummary(TypedDict, total=False):
    id: Required[Id]
    label: Required[str]
    type: NotRequired[
        Literal["family", "ethnic", "regional", "religious", "spiritual", "literary", "chosen"]
    ]
    relevance: NotRequired[Literal["low", "medium", "high"]]
    allowedUses: NotRequired[list[str]]
    avoidUses: NotRequired[list[str]]
    notes: NotRequired[str]


class SuppressedHypothesisSummary(TypedDict, total=False):
    id: Required[Id]
    normalizedClaimKey: Required[str]
    reason: Required[
        Literal["user_rejected", "user_refined", "counterevidence", "expired", "unsafe"]
    ]
    note: NotRequired[str]
    timestamp: Required[ISODateString]


class ValencePoint(TypedDict, total=False):
    date: Required[ISODateString]
    tone: Required[str]
    sourceId: NotRequired[Id]


class PersonalAssociationSummary(TypedDict, total=False):
    id: Required[Id]
    symbolName: Required[str]
    association: Required[str]
    source: Required[Literal["user_confirmed", "session_input"]]
    date: Required[ISODateString]


class PersonalSymbolSummary(TypedDict, total=False):
    id: Required[Id]
    canonicalName: Required[str]
    aliases: NotRequired[list[str]]
    category: Required[SymbolCategory]
    recurrenceCount: NotRequired[int]
    firstSeen: NotRequired[ISODateString]
    lastSeen: NotRequired[ISODateString]
    valenceHistory: NotRequired[list[ValencePoint]]
    personalAssociations: NotRequired[list[PersonalAssociationSummary]]
    linkedMaterialIds: NotRequired[list[Id]]
    linkedLifeEventRefs: NotRequired[list[Id]]


class ComplexCandidateSummary(TypedDict):
    id: Id
    label: str
    formulation: str
    status: Literal[
        "observed_signal",
        "candidate",
        "active",
        "recurring",
        "integrating",
        "dormant",
        "disconfirmed",
    ]
    activationIntensity: float
    confidence: Confidence
    evidenceIds: list[Id]
    counterevidenceIds: list[Id]
    linkedSymbols: list[str]
    linkedLifeEventRefs: list[Id]
    lastUpdated: ISODateString


class TypologyLensSummary(TypedDict):
    id: Id
    role: TypologyRole
    function: PsychologicalFunction
    claim: str
    confidence: Literal["low", "medium"]
    status: Literal["candidate", "user_refined", "disconfirmed"]
    evidenceIds: list[Id]
    counterevidenceIds: list[Id]
    linkedMaterialIds: list[Id]
    userTestPrompt: str
    lastUpdated: ISODateString


class HermesMemoryContext(TypedDict):
    recurringSymbols: list[PersonalSymbolSummary]
    activeComplexCandidates: list[ComplexCandidateSummary]
    recentMaterialSummaries: list[MaterialSummary]
    recentInterpretationFeedback: list[InterpretationFeedbackSummary]
    practiceOutcomes: list[PracticeOutcomeSummary]
    culturalOriginPreferences: list[CulturalOriginSummary]
    suppressedHypotheses: list[SuppressedHypothesisSummary]
    typologyLensSummaries: list[TypologyLensSummary]
    recentTypologySignals: list[str]


class LifeContextSnapshot(TypedDict, total=False):
    windowStart: Required[ISODateString]
    windowEnd: Required[ISODateString]
    lifeEventRefs: NotRequired[list[LifeEventRefSummary]]
    activeGoals: NotRequired[list[GoalSummary]]
    goalTensions: NotRequired[list[GoalTensionSummary]]
    moodSummary: NotRequired[str]
    energySummary: NotRequired[str]
    focusSummary: NotRequired[str]
    mentalStateSummary: NotRequired[str]
    habitSummary: NotRequired[str]
    notableChanges: NotRequired[list[str]]
    source: Required[
        Literal[
            "circulatio-backend",
            "circulatio-life-os",
            "hermes-life-os",
            "manual-session-context",
            "seed-demo",
        ]
    ]


class DreamDynamicsObservation(TypedDict, total=False):
    id: Required[Id]
    source: Required[Literal["user_reported", "clarifying_answer", "interpretation_input"]]
    observedAt: Required[ISODateString]
    egoStance: Required[str]
    actionSummary: Required[str]
    affectBefore: NotRequired[str]
    affectAfter: NotRequired[str]
    bodySensations: NotRequired[list[str]]
    lysisSummary: NotRequired[str]
    relationalStance: NotRequired[str]
    evidenceIds: Required[list[Id]]
    createdAt: Required[ISODateString]


class DreamDynamicsSummary(TypedDict, total=False):
    materialId: Required[Id]
    observedAt: Required[ISODateString]
    egoStance: Required[str]
    actionSummary: Required[str]
    lysisSummary: NotRequired[str]
    evidenceIds: Required[list[Id]]


class ClarificationIntent(TypedDict, total=False):
    refKey: Required[str]
    questionText: Required[str]
    expectedTargets: Required[list[MethodStateCaptureTargetKind]]
    anchorRefs: Required[dict[str, object]]
    consentScopes: Required[list[str]]
    storagePolicy: Required[
        Literal[
            "direct_if_explicit",
            "candidate_then_review",
            "proposal_required",
            "no_storage_without_confirmation",
        ]
    ]
    expiresAt: Required[ISODateString]


class MethodStateSourceRef(TypedDict, total=False):
    recordType: Required[str]
    recordId: Required[Id]
    summary: NotRequired[str]


class GroundingSummary(TypedDict, total=False):
    recommendation: Required[Literal["clear_for_depth", "pace_gently", "grounding_first"]]
    activationPattern: Required[
        Literal["low", "moderate", "high", "overwhelming", "mixed", "unknown"]
    ]
    supportSignals: Required[list[str]]
    strainSignals: Required[list[str]]
    sourceRecordRefs: Required[list[MethodStateSourceRef]]
    evidenceIds: Required[list[Id]]
    confidence: Required[Confidence]
    updatedAt: Required[ISODateString]


class ContainmentSummary(TypedDict, total=False):
    status: Required[Literal["steady", "strained", "thin", "unknown"]]
    supportSignals: Required[list[str]]
    strainSignals: Required[list[str]]
    sourceRecordRefs: Required[list[MethodStateSourceRef]]
    evidenceIds: Required[list[Id]]
    confidence: Required[Confidence]
    updatedAt: Required[ISODateString]


class EgoCapacitySummary(TypedDict, total=False):
    reflectiveCapacity: Required[Literal["steady", "fragile", "unknown"]]
    agencyTone: Required[Literal["available", "strained", "collapsed", "unknown"]]
    symbolicContact: Required[Literal["available", "too_intense", "thin", "unknown"]]
    confidence: Required[Confidence]
    reasons: Required[list[str]]
    sourceRecordRefs: Required[list[MethodStateSourceRef]]
    evidenceIds: Required[list[Id]]
    updatedAt: Required[ISODateString]


class EgoRelationTrajectorySummary(TypedDict, total=False):
    currentRelation: Required[Literal["aligned", "curious", "conflicted", "avoidant", "unknown"]]
    agencyTrend: Required[Literal["expanding", "contracting", "mixed", "unknown"]]
    movementLanguage: Required[list[str]]
    recentEgoStances: Required[list[str]]
    confidence: Required[Confidence]
    sourceRecordRefs: Required[list[MethodStateSourceRef]]
    evidenceIds: Required[list[Id]]
    updatedAt: Required[ISODateString]


class RelationalFieldSummary(TypedDict, total=False):
    relationshipContact: Required[Literal["available", "thin", "isolated", "unknown"]]
    spaciousness: Required[Literal["spacious", "constricted", "mixed", "unknown"]]
    isolationRisk: Required[Literal["low", "moderate", "high", "unknown"]]
    dependencyPressure: Required[Literal["low", "moderate", "high", "unknown"]]
    supportDirection: Required[
        Literal["increase_contact", "protect_space", "hold_contact_lightly", "stabilize_field"]
    ]
    recurringAffect: Required[list[str]]
    activeSceneIds: Required[list[Id]]
    projectionLanguageAllowed: Required[bool]
    reasons: Required[list[str]]
    sourceRecordRefs: Required[list[MethodStateSourceRef]]
    evidenceIds: Required[list[Id]]
    confidence: Required[Confidence]
    updatedAt: Required[ISODateString]


class CompensationTendencySummary(TypedDict, total=False):
    status: Required[Literal["insufficient_evidence", "signals_only", "hypothesis_available"]]
    consciousPole: NotRequired[str]
    compensatingPole: NotRequired[str]
    patternSummary: Required[str]
    confidence: Required[Literal["low", "medium"]]
    evidenceIds: Required[list[Id]]
    sourceRecordRefs: Required[list[MethodStateSourceRef]]
    counterevidenceIds: Required[list[Id]]
    userTestPrompt: Required[str]
    normalizedClaimKey: Required[str]
    approvalRequired: Required[Literal[True]]
    updatedAt: Required[ISODateString]


class QuestioningPreferenceSummary(TypedDict, total=False):
    preferredQuestionStyles: Required[
        list[
            Literal[
                "body_first",
                "image_first",
                "relational_first",
                "choice_based",
                "open_association",
            ]
        ]
    ]
    avoidedQuestionStyles: Required[list[str]]
    preferredCaptureTargets: Required[list[ClarificationCaptureTarget]]
    maxQuestionsPerTurn: Required[int]
    depthPacing: Required[Literal["direct", "gentle", "one_step", "unknown"]]
    answerFrictionSignals: Required[list[str]]
    confidence: Required[Confidence]
    source: Required[Literal["adaptation_profile"]]
    updatedAt: Required[ISODateString]


class ActiveGoalTensionSummary(TypedDict, total=False):
    goalTensionId: Required[Id]
    linkedGoalIds: Required[list[Id]]
    summary: Required[str]
    polarityLabels: Required[list[str]]
    balancingDirection: Required[str]
    evidenceIds: Required[list[Id]]
    updatedAt: Required[ISODateString]


class PracticeLoopSummary(TypedDict, total=False):
    preferredModalities: Required[list[str]]
    avoidedModalities: Required[list[str]]
    recentCompletedTypes: Required[list[str]]
    recentSkippedTypes: Required[list[str]]
    recentOutcomeTrend: Required[Literal["settling", "activating", "mixed", "unknown"]]
    recommendedIntensity: Required[Literal["low", "moderate", "unknown"]]
    maxDurationMinutes: NotRequired[int]
    reasons: Required[list[str]]
    source: Required[Literal["adaptation_profile", "practice_outcomes", "mixed"]]
    updatedAt: Required[ISODateString]


class TypologyMethodStateSummary(TypedDict, total=False):
    status: Required[Literal["insufficient_evidence", "signals_only", "candidate_available"]]
    activeLensIds: Required[list[Id]]
    feedbackSignalCount: Required[int]
    activeFunctions: Required[list[PsychologicalFunction]]
    foregroundFunctions: NotRequired[list[PsychologicalFunction]]
    compensatoryFunctions: NotRequired[list[PsychologicalFunction]]
    backgroundFunctions: NotRequired[list[PsychologicalFunction]]
    supportingEvidenceIds: NotRequired[list[Id]]
    counterevidenceIds: NotRequired[list[Id]]
    ambiguityNotes: NotRequired[list[str]]
    evidencedLensCount: NotRequired[int]
    promptBias: Required[
        Literal["body_first", "image_first", "relational_first", "reflection_first", "neutral"]
    ]
    practiceBias: Required[
        Literal[
            "sensation_grounding",
            "image_tracking",
            "value_discernment",
            "pattern_noting",
            "neutral",
        ]
    ]
    balancingFunction: NotRequired[PsychologicalFunction]
    caution: NotRequired[str]
    confidence: Required[Literal["low", "medium"]]
    updatedAt: Required[ISODateString]


class MethodStateSummary(TypedDict, total=False):
    grounding: NotRequired[GroundingSummary]
    containment: NotRequired[ContainmentSummary]
    egoCapacity: NotRequired[EgoCapacitySummary]
    egoRelationTrajectory: NotRequired[EgoRelationTrajectorySummary]
    relationalField: NotRequired[RelationalFieldSummary]
    compensationTendencies: NotRequired[list[CompensationTendencySummary]]
    questioningPreference: NotRequired[QuestioningPreferenceSummary]
    activeGoalTension: NotRequired[ActiveGoalTensionSummary]
    practiceLoop: NotRequired[PracticeLoopSummary]
    typologyMethodState: NotRequired[TypologyMethodStateSummary]
    generatedAt: Required[ISODateString]


class WitnessStateSummary(TypedDict, total=False):
    stance: Required[Literal["grounding_first", "paced_contact", "symbolic_contact"]]
    tone: Required[Literal["grounded", "gentle", "direct", "spacious"]]
    startingMove: Required[str]
    maxQuestionsPerTurn: Required[int]
    preferredQuestionStyles: Required[list[str]]
    avoidedQuestionStyles: Required[list[str]]
    preferredClarificationTargets: Required[list[ClarificationCaptureTarget]]
    blockedMoves: Required[list[str]]
    witnessVoice: NotRequired[str]
    avoidPhrasingPatterns: Required[list[str]]
    activeGoalFrame: NotRequired[str]
    practiceFrame: NotRequired[str]
    typologyFrame: NotRequired[str]
    recentLocale: NotRequired[str]
    reasons: Required[list[str]]
    updatedAt: Required[ISODateString]


class CoachPromptFrame(TypedDict, total=False):
    stance: Required[str]
    askAbout: Required[str]
    avoid: Required[list[str]]
    choices: NotRequired[list[str]]
    focus: NotRequired[str]


class CoachCaptureContract(TypedDict, total=False):
    source: Required[MethodStateResponseSource]
    anchorRefs: Required[MethodStateAnchorRefs]
    expectedTargets: Required[list[MethodStateCaptureTargetKind]]
    maxQuestions: Required[int]
    answerMode: Required[CoachAnswerMode]
    skipBehavior: Required[CoachSkipBehavior]


class EmbodiedResourceSummary(TypedDict, total=False):
    id: Required[Id]
    title: Required[str]
    provider: Required[str]
    url: Required[str]
    resourceType: Required[EmbodiedResourceType]
    durationMinutes: NotRequired[int]
    modality: Required[EmbodiedResourceModality]
    activationBand: Required[ActivationBand]
    contraindications: Required[list[str]]
    tags: Required[list[str]]
    followUpQuestion: NotRequired[str]
    curationSource: Required[str]
    reviewedAt: Required[ISODateString]
    sourceRecordRefs: NotRequired[list[MethodStateSourceRef]]
    evidenceIds: NotRequired[list[Id]]


class ResourceInvitationSummary(TypedDict, total=False):
    id: Required[Id]
    resource: Required[EmbodiedResourceSummary]
    triggerLoopKey: Required[str]
    reason: Required[str]
    activationRationale: Required[str]
    capture: Required[CoachCaptureContract]
    presentationPolicy: Required[dict[str, object]]
    createdAt: Required[ISODateString]
    expiresAt: NotRequired[ISODateString]


class CoachLoopSummary(TypedDict, total=False):
    loopKey: Required[str]
    kind: Required[CoachLoopKind]
    status: Required[CoachLoopStatus]
    priority: Required[int]
    titleHint: Required[str]
    summaryHint: Required[str]
    promptFrame: Required[CoachPromptFrame]
    moveKind: Required[CoachMoveKind]
    capture: Required[CoachCaptureContract]
    relatedMaterialIds: Required[list[Id]]
    relatedGoalIds: Required[list[Id]]
    relatedJourneyIds: Required[list[Id]]
    relatedExperimentIds: NotRequired[list[Id]]
    relatedPracticeSessionIds: Required[list[Id]]
    relatedSymbolIds: Required[list[Id]]
    relatedBodyStateIds: Required[list[Id]]
    relatedRelationalSceneIds: Required[list[Id]]
    relatedResourceIds: NotRequired[list[Id]]
    evidenceIds: Required[list[Id]]
    sourceRecordRefs: Required[list[MethodStateSourceRef]]
    blockedMoves: Required[list[str]]
    consentScopes: Required[list[str]]
    cooldownUntil: NotRequired[ISODateString]
    reasons: Required[list[str]]
    resourceInvitation: NotRequired[ResourceInvitationSummary]


class CoachMoveContract(TypedDict, total=False):
    moveId: Required[Id]
    loopKey: Required[str]
    kind: Required[CoachMoveKind]
    titleHint: Required[str]
    summaryHint: Required[str]
    promptFrame: Required[CoachPromptFrame]
    capture: Required[CoachCaptureContract]
    blockedMoves: Required[list[str]]
    reasons: Required[list[str]]
    relatedExperimentIds: NotRequired[list[Id]]
    relatedResourceIds: NotRequired[list[Id]]
    resourceInvitation: NotRequired[ResourceInvitationSummary]


class CoachWithheldMoveSummary(TypedDict, total=False):
    loopKey: Required[str]
    kind: Required[CoachLoopKind]
    moveKind: Required[CoachMoveKind]
    reason: Required[str]
    blockedMoves: Required[list[str]]
    consentScopes: Required[list[str]]


class CoachGlobalConstraints(TypedDict, total=False):
    depthLevel: Required[Literal["grounding_only", "gentle", "standard"]]
    blockedMoves: Required[list[str]]
    maxQuestionsPerTurn: Required[int]
    doNotAskReasons: Required[list[str]]


class CoachStateSummary(TypedDict, total=False):
    generatedAt: Required[ISODateString]
    surface: Required[CoachSurface]
    runtimePolicyVersion: Required[str]
    witness: Required[WitnessStateSummary]
    activeLoops: Required[list[CoachLoopSummary]]
    selectedMove: NotRequired[CoachMoveContract]
    withheldMoves: Required[list[CoachWithheldMoveSummary]]
    globalConstraints: Required[CoachGlobalConstraints]
    cooldownKeys: Required[list[str]]
    sourceRecordRefs: Required[list[MethodStateSourceRef]]
    evidenceIds: Required[list[Id]]
    reasons: Required[list[str]]


class ClarificationPlan(TypedDict, total=False):
    questionText: Required[str]
    questionKey: NotRequired[str]
    intent: Required[ClarificationIntentType]
    captureTarget: Required[ClarificationCaptureTarget]
    expectedAnswerKind: Required[ExpectedAnswerKind]
    answerSlots: NotRequired[dict[str, object]]
    routingHints: NotRequired[dict[str, object]]
    supportingRefs: NotRequired[list[str]]
    anchorRefs: NotRequired[dict[str, object]]
    consentScopes: NotRequired[list[str]]


class ClarificationPromptSummary(TypedDict, total=False):
    id: Required[Id]
    materialId: NotRequired[Id]
    runId: NotRequired[Id]
    questionText: Required[str]
    questionKey: NotRequired[str]
    intent: Required[ClarificationIntentType]
    captureTarget: Required[ClarificationCaptureTarget]
    expectedAnswerKind: Required[ExpectedAnswerKind]
    status: Required[str]
    supportingRefs: NotRequired[list[str]]
    createdAt: Required[ISODateString]
    updatedAt: Required[ISODateString]


class ClarificationAnswerSummary(TypedDict, total=False):
    id: Required[Id]
    promptId: NotRequired[Id]
    materialId: NotRequired[Id]
    runId: NotRequired[Id]
    captureTarget: Required[ClarificationCaptureTarget]
    routingStatus: Required[str]
    createdRecordRefs: Required[list[ClarificationCreatedRecordRef]]
    validationErrors: NotRequired[list[str]]
    createdAt: Required[ISODateString]
    updatedAt: Required[ISODateString]


class ClarificationStateSummary(TypedDict, total=False):
    pendingPrompts: Required[list[ClarificationPromptSummary]]
    recentlyAnswered: Required[list[ClarificationAnswerSummary]]
    recentlyUnrouted: Required[list[ClarificationAnswerSummary]]
    avoidRepeatQuestionKeys: Required[list[str]]


class MethodContextSnapshot(TypedDict, total=False):
    windowStart: Required[ISODateString]
    windowEnd: Required[ISODateString]
    consciousAttitude: NotRequired[ConsciousAttitudeSummary]
    recentBodyStates: NotRequired[list[BodyStateSummary]]
    activeGoals: NotRequired[list[GoalSummary]]
    goalTensions: NotRequired[list[GoalTensionSummary]]
    personalAmplifications: NotRequired[list[PersonalAmplificationSummary]]
    consentPreferences: NotRequired[list[ConsentPreferenceSummary]]
    pendingAmplificationPrompts: NotRequired[list[AmplificationPromptSummary]]
    activeDreamSeries: NotRequired[list[DreamSeriesSummary]]
    activeCulturalFrames: NotRequired[list[CulturalFrameSummary]]
    collectiveAmplifications: NotRequired[list[CollectiveAmplificationSummary]]
    longitudinalSignals: NotRequired[list[LongitudinalSignalSummary]]
    adaptationProfile: NotRequired[UserAdaptationProfileSummary]
    activeJourneys: NotRequired[list[JourneySummary]]
    activeJourneyExperiments: NotRequired[list["JourneyExperimentSummary"]]
    recentPracticeSessions: NotRequired[list[PracticeSessionSummary]]
    recentDreamDynamics: NotRequired[list[DreamDynamicsSummary]]
    methodState: NotRequired[MethodStateSummary]
    clarificationState: NotRequired[ClarificationStateSummary]
    individuationContext: NotRequired[IndividuationContextSummary]
    livingMythContext: NotRequired[LivingMythContextSummary]
    witnessState: NotRequired[WitnessStateSummary]
    coachState: NotRequired[CoachStateSummary]
    source: Required[Literal["circulatio-backend"]]


class MaterialInterpretationInput(TypedDict, total=False):
    userId: Required[Id]
    materialId: NotRequired[Id]
    materialType: Required[MaterialType]
    materialText: Required[str]
    materialDate: NotRequired[ISODateString]
    sessionContext: NotRequired[SessionContext]
    wakingTone: NotRequired[str]
    userAssociations: NotRequired[list[UserAssociationInput]]
    explicitQuestion: NotRequired[str]
    culturalOrigins: NotRequired[list[CulturalOriginSummary]]
    lifeContextSnapshot: NotRequired[LifeContextSnapshot]
    methodContextSnapshot: NotRequired[MethodContextSnapshot]
    hermesMemoryContext: NotRequired[HermesMemoryContext]
    trustedAmplificationSources: NotRequired[list[AmplificationSourceSummary]]
    communicationHints: NotRequired[CommunicationHints]
    interpretationHints: NotRequired[InterpretationHints]
    practiceHints: NotRequired[PracticeHints]
    safetyContext: NotRequired[SafetyContext]
    options: NotRequired[InterpretationOptions]


PracticeTriggerType = Literal[
    "manual",
    "interpretation",
    "weekly_review",
    "alive_today",
    "practice_followup",
    "rhythmic_brief",
    "threshold_review",
    "living_myth_review",
    "analysis_packet",
]


class PracticeTriggerSummary(TypedDict, total=False):
    triggerType: Required[PracticeTriggerType]
    materialId: NotRequired[Id]
    runId: NotRequired[Id]
    reviewId: NotRequired[Id]
    briefId: NotRequired[Id]
    practiceSessionId: NotRequired[Id]
    journeyId: NotRequired[Id]
    reason: NotRequired[str]


PracticeAdaptationHints = PracticeHints


class PracticeRecommendationInput(TypedDict, total=False):
    userId: Required[Id]
    windowStart: Required[ISODateString]
    windowEnd: Required[ISODateString]
    trigger: Required[PracticeTriggerSummary]
    sessionContext: NotRequired[SessionContext]
    lifeContextSnapshot: NotRequired[LifeContextSnapshot]
    methodContextSnapshot: NotRequired[MethodContextSnapshot]
    threadDigests: NotRequired[list[ThreadDigest]]
    hermesMemoryContext: Required[HermesMemoryContext]
    safetyContext: NotRequired[SafetyContext]
    explicitQuestion: NotRequired[str]
    practiceHints: NotRequired[PracticeHints]
    adaptationHints: NotRequired[PracticeHints]
    options: NotRequired[InterpretationOptions]


class EvidenceItem(TypedDict):
    id: Id
    type: EvidenceType
    sourceId: Id
    quoteOrSummary: str
    timestamp: ISODateString
    privacyClass: PrivacyClass
    reliability: Literal["low", "medium", "high"]


class Observation(TypedDict):
    id: Id
    kind: Literal[
        "image",
        "figure",
        "tone",
        "structure",
        "recurrence",
        "life_context_link",
        "practice_outcome",
        "motif",
    ]
    statement: str
    evidenceIds: list[Id]


class Hypothesis(TypedDict):
    id: Id
    claim: str
    hypothesisType: HypothesisType
    confidence: Confidence
    evidenceIds: list[Id]
    counterevidenceIds: list[Id]
    userTestPrompt: str
    phrasingPolicy: Literal["tentative", "very_tentative"]
    normalizedClaimKey: str


class SymbolSpan(TypedDict):
    start: int
    end: int


class SymbolMention(TypedDict, total=False):
    id: Required[Id]
    symbolId: NotRequired[Id]
    surfaceText: Required[str]
    canonicalName: Required[str]
    category: Required[SymbolCategory]
    textSpan: Required[SymbolSpan]
    tone: NotRequired[str]
    salience: Required[float]
    evidenceId: Required[Id]


class FigureMention(TypedDict):
    id: Id
    surfaceText: str
    label: str
    role: Literal["family", "authority", "child", "stranger", "elder", "shadow_like", "unknown"]
    textSpan: SymbolSpan
    salience: float
    evidenceId: Id


class MotifMention(TypedDict):
    id: Id
    canonicalName: str
    surfaceText: str
    motifType: Literal[
        "threshold",
        "descent",
        "containment",
        "flooding",
        "pursuit",
        "authority_pressure",
        "body_sensation",
    ]
    textSpan: SymbolSpan
    salience: float
    evidenceId: Id


class MaterialStructure(TypedDict, total=False):
    entryMode: Required[MaterialType]
    stance: Required[str]
    keyTurn: NotRequired[str]
    closingImageOrTheme: NotRequired[str]


class DreamStructure(TypedDict, total=False):
    exposition: NotRequired[str]
    peripetia: NotRequired[str]
    lysis: NotRequired[str]
    finalImage: NotRequired[str]
    relationshipPattern: NotRequired[str]
    setting: NotRequired[str]
    keyImages: NotRequired[list[str]]
    egoStance: NotRequired[str]
    lysisQuality: NotRequired[str]
    seriesFeatureKeys: NotRequired[list[str]]
    agencyScore: Required[float]


class CompensationAssessment(TypedDict):
    claim: str
    confidence: Confidence
    evidenceIds: list[Id]
    userTestPrompt: str


class PracticeScriptStep(TypedDict, total=False):
    instruction: Required[str]
    pauseSeconds: NotRequired[int]
    safetyNote: NotRequired[str]


class PracticePlan(TypedDict, total=False):
    id: Required[Id]
    type: Required[PracticeType]
    target: NotRequired[str]
    targetedTensionId: NotRequired[Id]
    targetedBodyStateId: NotRequired[Id]
    targetedRelationalSceneId: NotRequired[Id]
    reason: Required[str]
    contraindicationsChecked: Required[list[SafetyFlag]]
    durationMinutes: Required[int]
    instructions: Required[list[str]]
    requiresConsent: Required[bool]
    templateId: NotRequired[Id]
    modality: NotRequired[Literal["writing", "somatic", "imaginal", "breath", "dialogue"]]
    intensity: NotRequired[Literal["low", "moderate"]]
    script: NotRequired[list[PracticeScriptStep]]
    followUpPrompt: NotRequired[str]
    adaptationNotes: NotRequired[list[str]]
    coachLoopKey: NotRequired[str]
    coachLoopKind: NotRequired[CoachLoopKind]
    coachMoveKind: NotRequired[CoachMoveKind]
    resourceInvitationId: NotRequired[Id]
    resourceInvitation: NotRequired[ResourceInvitationSummary]
    relatedResourceIds: NotRequired[list[Id]]
    relatedJourneyIds: NotRequired[list[Id]]
    relatedExperimentIds: NotRequired[list[Id]]


class JourneyExperimentSummary(TypedDict, total=False):
    id: Required[Id]
    journeyId: Required[Id]
    title: Required[str]
    summary: Required[str]
    status: Required[
        Literal["active", "quiet", "completed", "released", "archived", "deleted"]
    ]
    bodyFirst: Required[bool]
    preferredMoveKind: NotRequired[CoachMoveKind]
    currentQuestion: NotRequired[str]
    suggestedActionText: NotRequired[str]
    relatedPracticeSessionIds: Required[list[Id]]
    relatedSymbolIds: Required[list[Id]]
    relatedGoalTensionIds: Required[list[Id]]
    relatedBodyStateIds: Required[list[Id]]
    relatedResourceIds: Required[list[Id]]
    nextCheckInDueAt: NotRequired[ISODateString]
    cooldownUntil: NotRequired[ISODateString]
    updatedAt: Required[ISODateString]


class PersonalSymbolWritePayload(TypedDict, total=False):
    canonicalName: Required[str]
    aliases: NotRequired[list[str]]
    category: Required[SymbolCategory]
    association: NotRequired[str]
    tone: NotRequired[str]
    sourceMaterialId: NotRequired[Id]
    linkedLifeEventRefs: NotRequired[list[Id]]


class ComplexCandidateWritePayload(TypedDict):
    label: str
    formulation: str
    linkedSymbols: list[str]
    linkedLifeEventRefs: list[Id]
    confidence: Confidence


class PracticeOutcomeWritePayload(TypedDict, total=False):
    practiceType: Required[PracticeType]
    target: NotRequired[str]
    outcome: Required[str]
    activationBefore: NotRequired[Literal["low", "moderate", "high"]]
    activationAfter: NotRequired[Literal["low", "moderate", "high"]]
    outcomeEvidenceIds: NotRequired[list[Id]]


class MaterialSummaryWritePayload(TypedDict, total=False):
    materialType: Required[MaterialType]
    date: Required[ISODateString]
    summary: Required[str]
    symbolNames: Required[list[str]]
    themeLabels: Required[list[str]]
    privacyClass: NotRequired[PrivacyClass]
    rawText: NotRequired[str]


class TypologyLensWritePayload(TypedDict):
    role: TypologyRole
    function: PsychologicalFunction
    claim: str
    confidence: Literal["low", "medium"]
    status: Literal["candidate", "user_refined", "disconfirmed"]
    evidenceIds: list[Id]
    userTestPrompt: str


class ConsciousAttitudeWritePayload(TypedDict, total=False):
    stanceSummary: Required[str]
    activeValues: Required[list[str]]
    activeConflicts: Required[list[str]]
    avoidedThemes: Required[list[str]]
    emotionalTone: NotRequired[str]
    egoPosition: NotRequired[str]
    confidence: Required[Confidence]
    relatedMaterialIds: NotRequired[list[Id]]
    relatedGoalIds: NotRequired[list[Id]]


class PersonalAmplificationWritePayload(TypedDict, total=False):
    canonicalName: Required[str]
    surfaceText: Required[str]
    associationText: Required[str]
    feelingTone: NotRequired[str]
    bodySensations: NotRequired[list[str]]
    memoryRefs: NotRequired[list[Id]]
    promptId: NotRequired[Id]
    symbolId: NotRequired[Id]


class AmplificationPromptWritePayload(TypedDict, total=False):
    canonicalName: Required[str]
    surfaceText: Required[str]
    promptText: Required[str]
    reason: Required[str]
    symbolId: NotRequired[Id]
    symbolMentionId: NotRequired[Id]


class BodyStateWritePayload(TypedDict, total=False):
    observedAt: Required[ISODateString]
    sensation: Required[str]
    bodyRegion: NotRequired[str]
    activation: NotRequired[Literal["low", "moderate", "high", "overwhelming"]]
    tone: NotRequired[str]
    temporalContext: NotRequired[str]
    linkedSymbolIds: NotRequired[list[Id]]
    linkedGoalIds: NotRequired[list[Id]]


class GoalTensionWritePayload(TypedDict, total=False):
    goalIds: Required[list[Id]]
    tensionSummary: Required[str]
    polarityLabels: Required[list[str]]
    evidenceIds: NotRequired[list[Id]]
    status: NotRequired[str]


class DreamSeriesLinkWritePayload(TypedDict, total=False):
    seriesId: NotRequired[Id]
    label: Required[str]
    materialIds: Required[list[Id]]
    symbolIds: NotRequired[list[Id]]
    motifKeys: NotRequired[list[str]]
    settingKeys: NotRequired[list[str]]
    figureKeys: NotRequired[list[str]]
    progressionSummary: NotRequired[str]
    egoTrajectory: NotRequired[str]
    compensationTrajectory: NotRequired[str]
    confidence: Required[Confidence]
    matchScore: NotRequired[float]
    matchingFeatures: NotRequired[list[str]]
    narrativeRole: NotRequired[str]
    egoStance: NotRequired[str]
    lysisSummary: NotRequired[str]
    evidenceIds: NotRequired[list[Id]]


class CollectiveAmplificationWritePayload(TypedDict, total=False):
    culturalFrameId: NotRequired[Id]
    canonicalName: Required[str]
    lensLabel: NotRequired[str]
    amplificationText: Required[str]
    reference: NotRequired[str]
    fitReason: NotRequired[str]
    caveat: NotRequired[str]
    confidence: NotRequired[Confidence]
    symbolId: NotRequired[Id]


class RealityAnchorSummaryWritePayload(TypedDict, total=False):
    anchorSummary: Required[str]
    workDailyLifeContinuity: Required[Literal["stable", "strained", "unknown"]]
    sleepBodyRegulation: Required[Literal["stable", "strained", "unknown"]]
    relationshipContact: Required[Literal["available", "thin", "unknown"]]
    reflectiveCapacity: Required[Literal["steady", "fragile", "unknown"]]
    groundingRecommendation: Required[Literal["clear_for_depth", "pace_gently", "grounding_first"]]
    reasons: Required[list[str]]
    relatedMaterialIds: NotRequired[list[Id]]
    relatedSymbolIds: NotRequired[list[Id]]
    relatedGoalIds: NotRequired[list[Id]]


class SelfOrientationWritePayload(TypedDict, total=False):
    orientationSummary: Required[str]
    emergentDirection: Required[str]
    egoRelation: Required[Literal["aligned", "conflicted", "avoidant", "curious", "unknown"]]
    movementLanguage: Required[list[str]]
    relatedMaterialIds: NotRequired[list[Id]]
    relatedSymbolIds: NotRequired[list[Id]]
    relatedGoalIds: NotRequired[list[Id]]


class PsychicOppositionWritePayload(TypedDict, total=False):
    poleA: Required[str]
    poleB: Required[str]
    oppositionSummary: Required[str]
    currentHoldingPattern: Required[str]
    pressureTone: NotRequired[str]
    holdingInstruction: NotRequired[str]
    normalizedOppositionKey: Required[str]
    relatedMaterialIds: NotRequired[list[Id]]
    relatedGoalIds: NotRequired[list[Id]]


class EmergentThirdSignalWritePayload(TypedDict, total=False):
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
    oppositionIds: NotRequired[list[Id]]
    novelty: Required[Literal["new", "returning", "unclear"]]
    relatedMaterialIds: NotRequired[list[Id]]
    relatedSymbolIds: NotRequired[list[Id]]
    relatedPracticeSessionIds: NotRequired[list[Id]]


class BridgeMomentWritePayload(TypedDict, total=False):
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
    relatedMaterialIds: NotRequired[list[Id]]
    relatedSymbolIds: NotRequired[list[Id]]
    relatedPracticeSessionIds: NotRequired[list[Id]]


class NuminousEncounterWritePayload(TypedDict, total=False):
    encounterMedium: Required[
        Literal["dream", "waking_event", "body", "art", "place", "conversation", "unknown"]
    ]
    affectTone: Required[str]
    containmentNeed: Required[Literal["ordinary_reflection", "pace_gently", "grounding_first"]]
    interpretationConstraint: Required[str]
    relatedMaterialIds: NotRequired[list[Id]]
    relatedSymbolIds: NotRequired[list[Id]]


class AestheticResonanceWritePayload(TypedDict, total=False):
    medium: Required[str]
    objectDescription: Required[str]
    resonanceSummary: Required[str]
    feelingTone: NotRequired[str]
    bodySensations: NotRequired[list[str]]
    relatedMaterialIds: NotRequired[list[Id]]
    relatedSymbolIds: NotRequired[list[Id]]


class ArchetypalPatternWritePayload(TypedDict, total=False):
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
    relatedMaterialIds: NotRequired[list[Id]]
    relatedSymbolIds: NotRequired[list[Id]]


class ThresholdProcessWritePayload(TypedDict, total=False):
    thresholdName: Required[str]
    phase: Required[Literal["ending", "liminal", "reorientation", "return", "unknown"]]
    whatIsEnding: Required[str]
    notYetBegun: Required[str]
    bodyCarrying: NotRequired[str]
    groundingStatus: Required[Literal["steady", "strained", "unknown"]]
    symbolicLens: NotRequired[str]
    invitationReadiness: Required[Literal["not_now", "ask", "ready"]]
    normalizedThresholdKey: Required[str]
    relatedMaterialIds: NotRequired[list[Id]]
    relatedSymbolIds: NotRequired[list[Id]]
    relatedGoalIds: NotRequired[list[Id]]
    relatedDreamSeriesIds: NotRequired[list[Id]]


class RelationalSceneWritePayload(TypedDict, total=False):
    sceneSummary: Required[str]
    chargedRoles: Required[list[dict[str, object]]]
    recurringAffect: Required[list[str]]
    recurrenceContexts: Required[list[str]]
    normalizedSceneKey: Required[str]
    relatedMaterialIds: NotRequired[list[Id]]
    relatedGoalIds: NotRequired[list[Id]]


class ProjectionHypothesisWritePayload(TypedDict, total=False):
    relationalSceneId: NotRequired[Id]
    hypothesisSummary: Required[str]
    projectionPattern: Required[str]
    userTestPrompt: Required[str]
    counterevidenceIds: Required[list[Id]]
    normalizedHypothesisKey: Required[str]
    relatedMaterialIds: NotRequired[list[Id]]


class InnerOuterCorrespondenceWritePayload(TypedDict, total=False):
    correspondenceSummary: Required[str]
    innerRefs: Required[list[Id]]
    outerRefs: Required[list[Id]]
    symbolIds: Required[list[Id]]
    timeWindowStart: NotRequired[ISODateString]
    timeWindowEnd: NotRequired[ISODateString]
    userCharge: Required[Literal["explicitly_charged", "implicitly_charged", "unclear"]]
    caveat: Required[str]
    normalizedCorrespondenceKey: Required[str]
    relatedMaterialIds: NotRequired[list[Id]]


class LifeChapterSnapshotWritePayload(TypedDict, total=False):
    chapterLabel: Required[str]
    chapterSummary: Required[str]
    governingSymbolIds: Required[list[Id]]
    governingQuestions: Required[list[str]]
    activeOppositionIds: Required[list[Id]]
    thresholdProcessIds: Required[list[Id]]
    relationalSceneIds: Required[list[Id]]
    correspondenceIds: Required[list[Id]]
    chapterTone: NotRequired[str]
    relatedMaterialIds: NotRequired[list[Id]]


class MythicQuestionWritePayload(TypedDict, total=False):
    questionText: Required[str]
    questionStatus: Required[Literal["active", "answered", "released"]]
    relatedChapterId: NotRequired[Id]
    lastReturnedAt: NotRequired[ISODateString]


class ThresholdMarkerWritePayload(TypedDict, total=False):
    markerType: Required[
        Literal["ending", "initiation", "return", "choice", "loss", "bridge", "unknown"]
    ]
    markerSummary: Required[str]
    thresholdProcessId: NotRequired[Id]
    relatedMaterialIds: NotRequired[list[Id]]


class ComplexEncounterWritePayload(TypedDict, total=False):
    complexCandidateId: NotRequired[Id]
    patternId: NotRequired[Id]
    encounterSummary: Required[str]
    trajectorySummary: Required[str]
    movement: Required[
        Literal["approaching", "avoiding", "dialogue", "integration_hint", "stuck", "unknown"]
    ]
    relatedMaterialIds: NotRequired[list[Id]]
    relatedIndividuationRecordIds: NotRequired[list[Id]]


class IntegrationContourWritePayload(TypedDict, total=False):
    contourSummary: Required[str]
    symbolicStrands: Required[list[str]]
    somaticStrands: Required[list[str]]
    relationalStrands: Required[list[str]]
    existentialStrands: Required[list[str]]
    tensionsHeld: Required[list[str]]
    assimilatedSignals: Required[list[str]]
    unassimilatedEdges: Required[list[str]]
    nextQuestions: Required[list[str]]
    relatedMaterialIds: NotRequired[list[Id]]
    relatedIndividuationRecordIds: NotRequired[list[Id]]


class SymbolicWellbeingSnapshotWritePayload(TypedDict, total=False):
    capacitySummary: Required[str]
    groundingCapacity: Required[Literal["steady", "strained", "unknown"]]
    symbolicLiveliness: Required[str]
    somaticContact: Required[str]
    relationalSpaciousness: Required[str]
    agencyTone: Required[str]
    supportNeeded: NotRequired[str]
    relatedMaterialIds: NotRequired[list[Id]]
    relatedIndividuationRecordIds: NotRequired[list[Id]]


class MemoryWriteProposalBase(TypedDict):
    id: Id
    evidenceIds: list[Id]
    reason: str
    requiresUserApproval: Literal[True]
    status: Literal["pending_user_approval"]


class MemoryWriteProposalPersonalSymbol(MemoryWriteProposalBase):
    action: Literal["upsert_personal_symbol"]
    entityType: Literal["PersonalSymbol"]
    payload: PersonalSymbolWritePayload


class MemoryWriteProposalComplex(MemoryWriteProposalBase):
    action: Literal["upsert_complex_candidate"]
    entityType: Literal["ComplexCandidate"]
    payload: ComplexCandidateWritePayload


class MemoryWriteProposalPractice(MemoryWriteProposalBase):
    action: Literal["record_practice_outcome"]
    entityType: Literal["PracticeOutcome"]
    payload: PracticeOutcomeWritePayload


class MemoryWriteProposalMaterial(MemoryWriteProposalBase):
    action: Literal["store_material_summary"]
    entityType: Literal["MaterialEntry"]
    payload: MaterialSummaryWritePayload


class MemoryWriteProposalTypology(MemoryWriteProposalBase):
    action: Literal["store_typology_lens"]
    entityType: Literal["TypologyLens"]
    payload: TypologyLensWritePayload


class MemoryWriteProposalConsciousAttitude(MemoryWriteProposalBase):
    action: Literal["create_conscious_attitude_snapshot"]
    entityType: Literal["ConsciousAttitude"]
    payload: ConsciousAttitudeWritePayload


class MemoryWriteProposalPersonalAmplification(MemoryWriteProposalBase):
    action: Literal["record_personal_amplification"]
    entityType: Literal["PersonalAmplification"]
    payload: PersonalAmplificationWritePayload


class MemoryWriteProposalAmplificationPrompt(MemoryWriteProposalBase):
    action: Literal["create_amplification_prompt"]
    entityType: Literal["AmplificationPrompt"]
    payload: AmplificationPromptWritePayload


class MemoryWriteProposalBodyState(MemoryWriteProposalBase):
    action: Literal["record_body_state"]
    entityType: Literal["BodyState"]
    payload: BodyStateWritePayload


class MemoryWriteProposalGoalTension(MemoryWriteProposalBase):
    action: Literal["upsert_goal_tension"]
    entityType: Literal["GoalTension"]
    payload: GoalTensionWritePayload


class MemoryWriteProposalDreamSeries(MemoryWriteProposalBase):
    action: Literal[
        "create_dream_series",
        "link_material_to_dream_series",
        "update_dream_series_progression",
    ]
    entityType: Literal["DreamSeries"]
    payload: DreamSeriesLinkWritePayload


class MemoryWriteProposalCollectiveAmplification(MemoryWriteProposalBase):
    action: Literal["create_collective_amplification"]
    entityType: Literal["CollectiveAmplification"]
    payload: CollectiveAmplificationWritePayload


class MemoryWriteProposalRealityAnchorSummary(MemoryWriteProposalBase):
    action: Literal["create_reality_anchor_summary"]
    entityType: Literal["RealityAnchorSummary"]
    payload: RealityAnchorSummaryWritePayload


class MemoryWriteProposalSelfOrientation(MemoryWriteProposalBase):
    action: Literal["create_self_orientation_snapshot"]
    entityType: Literal["SelfOrientationSnapshot"]
    payload: SelfOrientationWritePayload


class MemoryWriteProposalPsychicOpposition(MemoryWriteProposalBase):
    action: Literal["upsert_psychic_opposition"]
    entityType: Literal["PsychicOpposition"]
    payload: PsychicOppositionWritePayload


class MemoryWriteProposalEmergentThirdSignal(MemoryWriteProposalBase):
    action: Literal["create_emergent_third_signal"]
    entityType: Literal["EmergentThirdSignal"]
    payload: EmergentThirdSignalWritePayload


class MemoryWriteProposalBridgeMoment(MemoryWriteProposalBase):
    action: Literal["create_bridge_moment"]
    entityType: Literal["BridgeMoment"]
    payload: BridgeMomentWritePayload


class MemoryWriteProposalNuminousEncounter(MemoryWriteProposalBase):
    action: Literal["create_numinous_encounter"]
    entityType: Literal["NuminousEncounter"]
    payload: NuminousEncounterWritePayload


class MemoryWriteProposalAestheticResonance(MemoryWriteProposalBase):
    action: Literal["create_aesthetic_resonance"]
    entityType: Literal["AestheticResonance"]
    payload: AestheticResonanceWritePayload


class MemoryWriteProposalArchetypalPattern(MemoryWriteProposalBase):
    action: Literal["upsert_archetypal_pattern"]
    entityType: Literal["ArchetypalPattern"]
    payload: ArchetypalPatternWritePayload


class MemoryWriteProposalThresholdProcess(MemoryWriteProposalBase):
    action: Literal["upsert_threshold_process"]
    entityType: Literal["ThresholdProcess"]
    payload: ThresholdProcessWritePayload


class MemoryWriteProposalRelationalScene(MemoryWriteProposalBase):
    action: Literal["upsert_relational_scene"]
    entityType: Literal["RelationalScene"]
    payload: RelationalSceneWritePayload


class MemoryWriteProposalProjectionHypothesis(MemoryWriteProposalBase):
    action: Literal["upsert_projection_hypothesis"]
    entityType: Literal["ProjectionHypothesis"]
    payload: ProjectionHypothesisWritePayload


class MemoryWriteProposalInnerOuterCorrespondence(MemoryWriteProposalBase):
    action: Literal["upsert_inner_outer_correspondence"]
    entityType: Literal["InnerOuterCorrespondence"]
    payload: InnerOuterCorrespondenceWritePayload


class MemoryWriteProposalLifeChapterSnapshot(MemoryWriteProposalBase):
    action: Literal["create_life_chapter_snapshot"]
    entityType: Literal["LifeChapterSnapshot"]
    payload: LifeChapterSnapshotWritePayload


class MemoryWriteProposalMythicQuestion(MemoryWriteProposalBase):
    action: Literal["upsert_mythic_question"]
    entityType: Literal["MythicQuestion"]
    payload: MythicQuestionWritePayload


class MemoryWriteProposalThresholdMarker(MemoryWriteProposalBase):
    action: Literal["create_threshold_marker"]
    entityType: Literal["ThresholdMarker"]
    payload: ThresholdMarkerWritePayload


class MemoryWriteProposalComplexEncounter(MemoryWriteProposalBase):
    action: Literal["upsert_complex_encounter"]
    entityType: Literal["ComplexEncounter"]
    payload: ComplexEncounterWritePayload


class MemoryWriteProposalIntegrationContour(MemoryWriteProposalBase):
    action: Literal["create_integration_contour"]
    entityType: Literal["IntegrationContour"]
    payload: IntegrationContourWritePayload


class MemoryWriteProposalSymbolicWellbeingSnapshot(MemoryWriteProposalBase):
    action: Literal["create_symbolic_wellbeing_snapshot"]
    entityType: Literal["SymbolicWellbeingSnapshot"]
    payload: SymbolicWellbeingSnapshotWritePayload


MemoryWriteProposal = (
    MemoryWriteProposalPersonalSymbol
    | MemoryWriteProposalComplex
    | MemoryWriteProposalPractice
    | MemoryWriteProposalMaterial
    | MemoryWriteProposalTypology
    | MemoryWriteProposalConsciousAttitude
    | MemoryWriteProposalPersonalAmplification
    | MemoryWriteProposalAmplificationPrompt
    | MemoryWriteProposalBodyState
    | MemoryWriteProposalGoalTension
    | MemoryWriteProposalDreamSeries
    | MemoryWriteProposalCollectiveAmplification
    | MemoryWriteProposalRealityAnchorSummary
    | MemoryWriteProposalSelfOrientation
    | MemoryWriteProposalPsychicOpposition
    | MemoryWriteProposalEmergentThirdSignal
    | MemoryWriteProposalBridgeMoment
    | MemoryWriteProposalNuminousEncounter
    | MemoryWriteProposalAestheticResonance
    | MemoryWriteProposalArchetypalPattern
    | MemoryWriteProposalThresholdProcess
    | MemoryWriteProposalRelationalScene
    | MemoryWriteProposalProjectionHypothesis
    | MemoryWriteProposalInnerOuterCorrespondence
    | MemoryWriteProposalLifeChapterSnapshot
    | MemoryWriteProposalMythicQuestion
    | MemoryWriteProposalThresholdMarker
    | MemoryWriteProposalComplexEncounter
    | MemoryWriteProposalIntegrationContour
    | MemoryWriteProposalSymbolicWellbeingSnapshot
)


class MemoryWritePlan(TypedDict):
    runId: Id
    proposals: list[MemoryWriteProposal]
    evidenceItems: list[EvidenceItem]


class CulturalAmplificationResult(TypedDict):
    symbolName: str
    originId: Id
    reference: str
    fitReason: str
    caveat: str
    confidence: Confidence
    evidenceIds: list[Id]


class LifeContextLink(TypedDict, total=False):
    lifeEventRefId: NotRequired[Id]
    stateSnapshotField: NotRequired[
        Literal[
            "moodSummary", "energySummary", "focusSummary", "mentalStateSummary", "habitSummary"
        ]
    ]
    summary: Required[str]
    evidenceId: Required[Id]


class TypologySignal(TypedDict):
    id: Id
    category: TypologySignalCategory
    function: PsychologicalFunction
    orientation: Literal[
        "conscious_adaptation", "support", "compensatory_pressure", "overuse", "unknown"
    ]
    statement: str
    strength: Literal["weak", "moderate"]
    evidenceIds: list[Id]


class TypologyHypothesis(TypedDict):
    id: Id
    claim: str
    role: TypologyRole
    function: PsychologicalFunction
    confidence: Literal["low", "medium"]
    evidenceIds: list[Id]
    counterevidenceIds: list[Id]
    userTestPrompt: str
    phrasingPolicy: Literal["very_tentative"]
    normalizedClaimKey: str


class TypologyRoleEvidenceBucket(TypedDict, total=False):
    functions: Required[list[PsychologicalFunction]]
    lensIds: Required[list[Id]]
    evidenceIds: Required[list[Id]]
    linkedMaterialIds: Required[list[Id]]


class TypologyEvidenceDigest(TypedDict, total=False):
    status: Required[Literal["insufficient_evidence", "signals_only", "hypotheses_available"]]
    lensSummaries: Required[list[TypologyLensSummary]]
    foreground: Required[TypologyRoleEvidenceBucket]
    compensation: Required[TypologyRoleEvidenceBucket]
    background: Required[TypologyRoleEvidenceBucket]
    supportingRefs: Required[list[Id]]
    counterevidenceIds: Required[list[Id]]
    bodyStateIds: Required[list[Id]]
    relationalSceneIds: Required[list[Id]]
    practiceOutcomeIds: Required[list[Id]]
    ambiguityNotes: Required[list[str]]
    evidencedLensCount: Required[int]
    feedbackSignalCount: Required[int]
    updatedAt: Required[ISODateString]


class PacketFunctionDynamicsSummary(TypedDict, total=False):
    status: Required[Literal["insufficient_evidence", "signals_only", "readable"]]
    summary: Required[str]
    foregroundFunctions: Required[list[PsychologicalFunction]]
    compensatoryFunctions: Required[list[PsychologicalFunction]]
    backgroundFunctions: Required[list[PsychologicalFunction]]
    ambiguityNotes: Required[list[str]]
    supportingRefs: Required[list[Id]]


class TypologyAssessment(TypedDict, total=False):
    status: Required[
        Literal["skipped", "insufficient_evidence", "signals_only", "hypotheses_available"]
    ]
    typologySignals: Required[list[TypologySignal]]
    typologyHypotheses: Required[list[TypologyHypothesis]]
    possibleDominantFunction: NotRequired[PsychologicalFunction]
    possibleAuxiliaryFunction: NotRequired[PsychologicalFunction]
    possibleInferiorFunction: NotRequired[PsychologicalFunction]
    compensationLink: NotRequired[str]
    userTestPrompt: NotRequired[str]


class LlmInterpretationHealth(TypedDict, total=False):
    status: Required[Literal["structured", "fallback", "opened"]]
    reason: Required[str]
    source: Required[Literal["llm", "fallback"]]
    diagnosticReason: NotRequired[str]
    symbolMentions: Required[int]
    figureMentions: Required[int]
    motifMentions: Required[int]
    observations: Required[int]
    hypotheses: Required[int]
    proposalCandidates: Required[int]


class DepthEngineHealth(TypedDict, total=False):
    status: Required[Literal["structured", "fallback", "opened"]]
    reason: Required[str]
    source: Required[Literal["llm", "depth_engine", "fallback"]]
    diagnosticReason: NotRequired[str]


class IndividuationAssessment(TypedDict, total=False):
    realityAnchors: NotRequired[RealityAnchorSummary]
    selfOrientation: NotRequired[SelfOrientationSummary]
    oppositions: Required[list[PsychicOppositionSummary]]
    emergentThirdSignals: Required[list[EmergentThirdSignalSummary]]
    thresholdProcesses: Required[list[ThresholdProcessSummary]]
    relationalScenes: Required[list[RelationalSceneSummary]]
    projectionHypotheses: Required[list[ProjectionHypothesisSummary]]
    innerOuterCorrespondences: Required[list[InnerOuterCorrespondenceSummary]]
    numinousEncounters: Required[list[NuminousEncounterSummary]]
    aestheticResonances: Required[list[AestheticResonanceSummary]]
    archetypalPatterns: Required[list[ArchetypalPatternSummary]]
    bridgeMoments: Required[list[BridgeMomentSummary]]
    withheldReasons: Required[list[str]]


class InterpretationResult(TypedDict, total=False):
    runId: Required[Id]
    materialId: Required[Id]
    safetyDisposition: Required[SafetyDisposition]
    observations: Required[list[Observation]]
    evidence: Required[list[EvidenceItem]]
    materialStructure: NotRequired[MaterialStructure]
    dreamStructure: NotRequired[DreamStructure]
    symbolMentions: Required[list[SymbolMention]]
    figureMentions: Required[list[FigureMention]]
    motifMentions: Required[list[MotifMention]]
    personalSymbolUpdates: Required[list[PersonalSymbolWritePayload]]
    culturalAmplifications: Required[list[CulturalAmplificationResult]]
    hypotheses: Required[list[Hypothesis]]
    compensationAssessment: NotRequired[CompensationAssessment]
    complexCandidateUpdates: Required[list[ComplexCandidateWritePayload]]
    lifeContextLinks: Required[list[LifeContextLink]]
    typologyAssessment: NotRequired[TypologyAssessment]
    practiceRecommendation: Required[PracticePlan]
    clarifyingQuestion: NotRequired[str]
    clarificationPlan: NotRequired[ClarificationPlan]
    clarificationIntent: NotRequired[ClarificationIntent]
    memoryWritePlan: Required[MemoryWritePlan]
    userFacingResponse: Required[str]
    llmInterpretationHealth: NotRequired[LlmInterpretationHealth]
    methodGate: NotRequired[MethodGateResult]
    depthReadiness: NotRequired[DepthReadinessAssessment]
    individuationAssessment: NotRequired[IndividuationAssessment]
    amplificationPrompts: NotRequired[list[AmplificationPromptSummary]]
    dreamSeriesSuggestions: NotRequired[list[DreamSeriesSuggestion]]
    depthEngineHealth: NotRequired[DepthEngineHealth]


class FeedbackValue(TypedDict, total=False):
    feedback: Required[Literal["resonated", "rejected", "partially_refined"]]
    note: NotRequired[str]
    refinedClaim: NotRequired[str]
    normalizedClaimKey: NotRequired[str]
    claimDomain: NotRequired[str]


class RecordIntegrationInput(TypedDict, total=False):
    userId: Required[Id]
    runId: Required[Id]
    memoryWritePlan: Required[MemoryWritePlan]
    approvedProposalIds: NotRequired[list[Id]]
    rejectedProposalIds: NotRequired[list[Id]]
    feedbackByHypothesisId: NotRequired[dict[Id, FeedbackValue]]
    integrationNote: NotRequired[str]


class RecordIntegrationResult(TypedDict, total=False):
    appliedProposalIds: Required[list[Id]]
    suppressedHypothesisIds: Required[list[Id]]
    integrationNoteId: NotRequired[Id]


class CirculationSummaryInput(TypedDict, total=False):
    userId: Required[Id]
    windowStart: Required[ISODateString]
    windowEnd: Required[ISODateString]
    hermesMemoryContext: Required[HermesMemoryContext]
    lifeContextSnapshot: NotRequired[LifeContextSnapshot]
    methodContextSnapshot: NotRequired[MethodContextSnapshot]
    threadDigests: NotRequired[list[ThreadDigest]]
    explicitQuestion: NotRequired[str]


AnalysisPacketFocus = Literal[
    "analysis",
    "journaling",
    "therapy_session",
    "threshold",
    "dream_series",
]
AnalyticLens = Literal["generic", "typology_function_dynamics"]


class ThresholdReviewInput(TypedDict, total=False):
    userId: Required[Id]
    windowStart: Required[ISODateString]
    windowEnd: Required[ISODateString]
    hermesMemoryContext: Required[HermesMemoryContext]
    lifeContextSnapshot: NotRequired[LifeContextSnapshot]
    methodContextSnapshot: NotRequired[MethodContextSnapshot]
    threadDigests: NotRequired[list[ThreadDigest]]
    activeGoalTension: NotRequired[ActiveGoalTensionSummary]
    practiceLoop: NotRequired[PracticeLoopSummary]
    latestSymbolicWellbeing: NotRequired[SymbolicWellbeingSnapshotSummary]
    activeJourneys: NotRequired[list[JourneySummary]]
    witnessState: NotRequired[WitnessStateSummary]
    explicitQuestion: NotRequired[str]
    safetyContext: NotRequired[SafetyContext]
    targetThresholdProcess: NotRequired[ThresholdProcessSummary]
    relatedRealityAnchors: NotRequired[list[RealityAnchorSummary]]
    relatedBodyStates: NotRequired[list[BodyStateSummary]]
    relatedDreamSeries: NotRequired[list[DreamSeriesSummary]]
    relatedRelationalScenes: NotRequired[list[RelationalSceneSummary]]
    evidence: NotRequired[list[EvidenceItem]]


class ThresholdReviewResult(TypedDict, total=False):
    userFacingResponse: Required[str]
    thresholdProcesses: Required[list[ThresholdProcessSummary]]
    realityAnchors: NotRequired[list[RealityAnchorSummary]]
    practiceRecommendation: NotRequired[PracticePlan]
    memoryWritePlan: NotRequired[MemoryWritePlan]
    llmHealth: NotRequired[DepthEngineHealth]
    withheld: NotRequired[bool]
    withheldReason: NotRequired[str]
    withheldReasons: NotRequired[list[str]]


class LivingMythReviewInput(TypedDict, total=False):
    userId: Required[Id]
    windowStart: Required[ISODateString]
    windowEnd: Required[ISODateString]
    hermesMemoryContext: Required[HermesMemoryContext]
    lifeContextSnapshot: NotRequired[LifeContextSnapshot]
    methodContextSnapshot: NotRequired[MethodContextSnapshot]
    threadDigests: NotRequired[list[ThreadDigest]]
    activeGoalTension: NotRequired[ActiveGoalTensionSummary]
    practiceLoop: NotRequired[PracticeLoopSummary]
    latestSymbolicWellbeing: NotRequired[SymbolicWellbeingSnapshotSummary]
    activeJourneys: NotRequired[list[JourneySummary]]
    witnessState: NotRequired[WitnessStateSummary]
    explicitQuestion: NotRequired[str]
    safetyContext: NotRequired[SafetyContext]
    recentMaterialSummaries: NotRequired[list[MaterialSummary]]
    evidence: NotRequired[list[EvidenceItem]]


class LivingMythReviewResult(TypedDict, total=False):
    userFacingResponse: Required[str]
    lifeChapter: NotRequired[LifeChapterSnapshotSummary]
    mythicQuestions: Required[list[MythicQuestionSummary]]
    thresholdMarkers: Required[list[ThresholdMarkerSummary]]
    complexEncounters: Required[list[ComplexEncounterSummary]]
    integrationContour: NotRequired[IntegrationContourSummary]
    symbolicWellbeing: NotRequired[SymbolicWellbeingSnapshotSummary]
    practiceRecommendation: NotRequired[PracticePlan]
    memoryWritePlan: NotRequired[MemoryWritePlan]
    llmHealth: NotRequired[DepthEngineHealth]
    withheld: NotRequired[bool]
    withheldReason: NotRequired[str]
    withheldReasons: NotRequired[list[str]]


class AnalysisPacketRecordRef(TypedDict):
    recordType: str
    recordId: Id


class AnalysisPacketItem(TypedDict, total=False):
    label: Required[str]
    summary: Required[str]
    evidenceIds: Required[list[Id]]
    relatedRecordRefs: Required[list[AnalysisPacketRecordRef]]


class AnalysisPacketSection(TypedDict, total=False):
    title: Required[str]
    purpose: Required[str]
    items: Required[list[AnalysisPacketItem]]


class AnalysisPacketInput(TypedDict, total=False):
    userId: Required[Id]
    windowStart: Required[ISODateString]
    windowEnd: Required[ISODateString]
    hermesMemoryContext: Required[HermesMemoryContext]
    lifeContextSnapshot: NotRequired[LifeContextSnapshot]
    methodContextSnapshot: NotRequired[MethodContextSnapshot]
    threadDigests: NotRequired[list[ThreadDigest]]
    activeGoalTension: NotRequired[ActiveGoalTensionSummary]
    practiceLoop: NotRequired[PracticeLoopSummary]
    latestSymbolicWellbeing: NotRequired[SymbolicWellbeingSnapshotSummary]
    activeJourneys: NotRequired[list[JourneySummary]]
    witnessState: NotRequired[WitnessStateSummary]
    explicitQuestion: NotRequired[str]
    safetyContext: NotRequired[SafetyContext]
    packetFocus: NotRequired[AnalysisPacketFocus]
    analyticLens: NotRequired[AnalyticLens]
    typologyEvidenceDigest: NotRequired[TypologyEvidenceDigest]
    currentDreamSeries: NotRequired[list[DreamSeriesSummary]]
    activeThresholdProcesses: NotRequired[list[ThresholdProcessSummary]]
    bodyEchoes: NotRequired[list[BodyStateSummary]]
    relationalScenes: NotRequired[list[RelationalSceneSummary]]
    projectionHypotheses: NotRequired[list[ProjectionHypothesisSummary]]
    innerOuterCorrespondences: NotRequired[list[InnerOuterCorrespondenceSummary]]
    activeMythicQuestions: NotRequired[list[MythicQuestionSummary]]
    userCorrectionsAndRejectedClaims: NotRequired[list[InterpretationFeedbackSummary]]
    recentPracticeOutcomes: NotRequired[list[PracticeOutcomeSummary]]
    evidence: NotRequired[list[EvidenceItem]]


class AnalysisPacketResult(TypedDict, total=False):
    packetTitle: Required[str]
    sections: Required[list[AnalysisPacketSection]]
    includedMaterialIds: Required[list[Id]]
    includedRecordRefs: Required[list[AnalysisPacketRecordRef]]
    evidenceIds: Required[list[Id]]
    source: Required[Literal["llm", "bounded_fallback"]]
    userFacingResponse: Required[str]
    functionDynamics: NotRequired[PacketFunctionDynamicsSummary]
    llmHealth: NotRequired[DepthEngineHealth]
    withheld: NotRequired[bool]
    withheldReason: NotRequired[str]


class PracticeRecommendationResult(TypedDict, total=False):
    practiceRecommendation: Required[PracticePlan]
    userFacingResponse: Required[str]
    llmHealth: NotRequired[DepthEngineHealth]
    resourceInvitation: NotRequired[ResourceInvitationSummary]


class RhythmicBriefInput(TypedDict, total=False):
    userId: Required[Id]
    windowStart: Required[ISODateString]
    windowEnd: Required[ISODateString]
    source: Required[str]
    seed: Required[dict[str, object]]
    lifeContextSnapshot: NotRequired[LifeContextSnapshot]
    methodContextSnapshot: NotRequired[MethodContextSnapshot]
    threadDigests: NotRequired[list[ThreadDigest]]
    hermesMemoryContext: Required[HermesMemoryContext]
    adaptationProfile: NotRequired[UserAdaptationProfileSummary]
    safetyContext: NotRequired[SafetyContext]


class RhythmicBriefResult(TypedDict, total=False):
    title: Required[str]
    summary: Required[str]
    suggestedAction: NotRequired[str]
    userFacingResponse: Required[str]
    resourceInvitation: NotRequired[ResourceInvitationSummary]
    llmHealth: NotRequired[DepthEngineHealth]
    withheld: NotRequired[bool]
    withheldReason: NotRequired[str]


class CirculationSummaryResult(TypedDict):
    summaryId: Id
    windowStart: ISODateString
    windowEnd: ISODateString
    recurringSymbols: list[PersonalSymbolSummary]
    activeThemes: list[str]
    activeComplexCandidates: list[ComplexCandidateSummary]
    notableLifeContextLinks: list[LifeContextLink]
    practiceSuggestion: PracticePlan
    userFacingResponse: str
    selectedCoachLoopKey: NotRequired[str]
    coachMoveKind: NotRequired[CoachMoveKind]
    followUpQuestion: NotRequired[str]
    suggestedAction: NotRequired[str]
    resourceInvitation: NotRequired[ResourceInvitationSummary]
    withheldReason: NotRequired[str]
