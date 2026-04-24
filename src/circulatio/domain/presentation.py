from __future__ import annotations

from typing import Literal, NotRequired, Required, TypedDict

from .types import Id, ISODateString, SafetyContext

RitualIntent = Literal[
    "weekly_integration",
    "alive_today",
    "hold_container",
    "guided_ritual",
    "breath_container",
    "meditation_container",
    "image_return",
    "active_imagination_container",
    "journey_broadcast",
    "threshold_container",
]
NarrativeMode = Literal[
    "full_guided",
    "sparse_guided",
    "breath_only",
    "meditation_only",
    "user_script",
    "hybrid",
]
PresentationSourceType = Literal[
    "material",
    "weekly_review",
    "proactive_brief",
    "journey",
    "analysis_packet",
    "threshold_review",
    "living_myth_review",
    "practice_session",
    "method_context",
    "surface_result",
]
PresentationSourceRole = Literal["primary", "supporting", "completion_anchor"]
PresentationApprovalState = Literal[
    "approved",
    "user_authored",
    "read_only_generated",
    "pending",
    "unknown",
]
PresentationPrivacyClass = Literal["private", "sensitive", "session_only"]
PresentationRenderMode = Literal["plan_only", "dry_run_manifest", "render_static"]


class PresentationSourceRef(TypedDict, total=False):
    id: NotRequired[Id]
    sourceType: Required[PresentationSourceType]
    recordId: NotRequired[Id]
    role: Required[PresentationSourceRole]
    surface: NotRequired[str]
    title: NotRequired[str]
    evidenceIds: NotRequired[list[Id]]
    approvalState: NotRequired[PresentationApprovalState]


class RequestedTextSurface(TypedDict, total=False):
    enabled: Required[bool]


class RequestedAudioSurface(TypedDict, total=False):
    enabled: Required[bool]
    voiceId: NotRequired[str]
    tone: NotRequired[Literal["neutral", "clear", "gentle", "holding", "steady"]]
    pace: NotRequired[Literal["normal", "measured", "slow"]]


class RequestedCaptionSurface(TypedDict, total=False):
    enabled: Required[bool]
    format: NotRequired[Literal["webvtt", "segments"]]


class RequestedBreathRequest(TypedDict, total=False):
    pattern: NotRequired[Literal["steadying", "lengthened_exhale", "box_breath", "orienting"]]
    techniqueName: NotRequired[str]
    cycles: NotRequired[int]
    maxDurationSeconds: NotRequired[int]


class RequestedBreathSurface(TypedDict, total=False):
    enabled: Required[bool]
    request: NotRequired[RequestedBreathRequest]


class RequestedMeditationRequest(TypedDict, total=False):
    fieldType: NotRequired[
        Literal[
            "coherence_convergence",
            "attention_anchor",
            "threshold_stillness",
            "image_afterglow",
        ]
    ]
    durationMs: NotRequired[int]
    instructionDensity: NotRequired[Literal["none", "sparse", "phase_label"]]


class RequestedMeditationSurface(TypedDict, total=False):
    enabled: Required[bool]
    request: NotRequired[RequestedMeditationRequest]


class RequestedImageSurface(TypedDict, total=False):
    enabled: Required[bool]
    styleIntent: NotRequired[
        Literal["symbolic_non_literal", "abstract", "photographic", "user_provided"]
    ]
    allowExternalGeneration: NotRequired[bool]


class RequestedCinemaSurface(TypedDict, total=False):
    enabled: Required[bool]
    allowExternalGeneration: NotRequired[bool]
    maxDurationSeconds: NotRequired[int]


class RequestedRitualSurfaces(TypedDict, total=False):
    text: NotRequired[RequestedTextSurface]
    audio: NotRequired[RequestedAudioSurface]
    captions: NotRequired[RequestedCaptionSurface]
    breath: NotRequired[RequestedBreathSurface]
    meditation: NotRequired[RequestedMeditationSurface]
    image: NotRequired[RequestedImageSurface]
    cinema: NotRequired[RequestedCinemaSurface]


class RitualMaxCost(TypedDict, total=False):
    currency: NotRequired[str]
    amount: NotRequired[float]


class RitualCachePolicy(TypedDict, total=False):
    read: NotRequired[bool]
    write: NotRequired[bool]
    cacheScope: NotRequired[Literal["user_private", "local_dev", "shared_safe"]]


class RitualDeliveryPolicy(TypedDict, total=False):
    target: NotRequired[Literal["hermes_chat", "frontend_url", "file_manifest"]]
    expiresAt: NotRequired[ISODateString]


class RitualSourceDataPolicy(TypedDict, total=False):
    allowRawMaterialTextInPlan: NotRequired[bool]
    allowRawMaterialTextToProviders: NotRequired[bool]
    providerPromptPolicy: NotRequired[
        Literal["derived_user_facing_only", "sanitized_visual_only", "none"]
    ]


class RitualRenderPolicy(TypedDict, total=False):
    mode: NotRequired[PresentationRenderMode]
    defaultDurationSeconds: NotRequired[int]
    maxDurationSeconds: NotRequired[int]
    externalProvidersAllowed: NotRequired[bool]
    providerAllowlist: NotRequired[list[str]]
    videoAllowed: NotRequired[bool]
    maxCost: NotRequired[RitualMaxCost]
    cachePolicy: NotRequired[RitualCachePolicy]
    delivery: NotRequired[RitualDeliveryPolicy]
    sourceDataPolicy: NotRequired[RitualSourceDataPolicy]


class RitualCompletionPolicy(TypedDict, total=False):
    captureReflection: NotRequired[bool]
    capturePracticeFeedback: NotRequired[bool]
    reflectionPrompt: NotRequired[str]
    returnMode: NotRequired[
        Literal["hermes_chat", "frontend_callback", "local_completion_file"]
    ]


class VoiceScriptSegment(TypedDict, total=False):
    id: Required[str]
    role: Required[
        Literal[
            "opening",
            "source_reflection",
            "breath_instruction",
            "meditation_instruction",
            "closing",
            "silence",
        ]
    ]
    text: Required[str]
    pace: Required[str]
    tone: Required[str]
    pauseAfterMs: Required[int]
    sourceRefIds: Required[list[Id]]
    safetyNote: NotRequired[str]


class VoiceScriptSilenceMarker(TypedDict):
    afterSegmentId: str
    durationMs: int
    purpose: str


class VoiceScript(TypedDict, total=False):
    segments: Required[list[VoiceScriptSegment]]
    silenceMarkers: Required[list[VoiceScriptSilenceMarker]]
    contraindications: Required[list[str]]


class PresentationDurationSpec(TypedDict):
    targetSeconds: int
    minSeconds: int
    maxSeconds: int


class PresentationTextSpec(TypedDict):
    summary: str
    body: str


class PresentationSpeechMarkupPlan(TypedDict):
    format: Literal["structured_intent"]
    ssmlAllowed: bool
    pausePolicy: str


class PresentationBreathSpec(TypedDict, total=False):
    enabled: Required[bool]
    pattern: Required[str]
    inhaleSeconds: Required[int]
    holdSeconds: Required[int]
    exhaleSeconds: Required[int]
    restSeconds: Required[int]
    cycles: Required[int]
    visualForm: Required[str]
    syncMarkers: Required[list[dict[str, object]]]


class PresentationMeditationSpec(TypedDict, total=False):
    enabled: Required[bool]
    fieldType: Required[str]
    durationMs: Required[int]
    sourceRefs: Required[list[Id]]
    macroProgressPolicy: Required[str]
    microMotion: Required[str]
    instructionDensity: Required[str]
    safetyBoundary: Required[str]
    syncMarkers: Required[list[dict[str, object]]]


class VisualPromptSurfacePlan(TypedDict, total=False):
    enabled: Required[bool]
    prompt: NotRequired[str]
    negativePrompt: NotRequired[str]
    privacyNotes: Required[list[str]]
    sourceRefIds: Required[list[Id]]


class VisualCinemaPlan(TypedDict, total=False):
    enabled: Required[bool]
    storyboard: Required[list[dict[str, object]]]
    maxDurationSeconds: Required[int]


class VisualPromptPlan(TypedDict):
    image: VisualPromptSurfacePlan
    cinema: VisualCinemaPlan


class RitualInteractionSpec(TypedDict):
    finishPrompt: str
    captureReactionTime: bool
    captureBodyResponse: bool
    maxPrompts: int


class PresentationDeliveryPolicy(TypedDict, total=False):
    renderMode: Required[PresentationRenderMode]
    frontendRoute: Required[str]
    expiresAt: NotRequired[ISODateString]


class PresentationSafetyBoundary(TypedDict, total=False):
    depthWorkAllowed: Required[bool]
    blockedSurfaces: Required[list[str]]
    groundingInstruction: Required[str]
    providerRestrictions: Required[list[str]]


class PresentationProvenance(TypedDict, total=False):
    evidenceIds: Required[list[Id]]
    contextSnapshotIds: Required[list[Id]]
    threadKeys: Required[list[str]]
    generatedFromSurface: Required[str]


class PresentationRitualPlan(TypedDict, total=False):
    id: Required[Id]
    schemaVersion: Required[str]
    userId: Required[Id]
    title: Required[str]
    ritualIntent: Required[RitualIntent]
    narrativeMode: Required[NarrativeMode]
    sourceType: Required[str]
    sourceRefs: Required[list[PresentationSourceRef]]
    generatedAt: Required[ISODateString]
    windowStart: Required[ISODateString]
    windowEnd: Required[ISODateString]
    privacyClass: Required[PresentationPrivacyClass]
    locale: Required[str]
    duration: Required[PresentationDurationSpec]
    text: Required[PresentationTextSpec]
    voiceScript: Required[VoiceScript]
    speechMarkupPlan: Required[PresentationSpeechMarkupPlan]
    breath: Required[PresentationBreathSpec]
    meditation: Required[PresentationMeditationSpec]
    visualPromptPlan: Required[VisualPromptPlan]
    interactionSpec: Required[RitualInteractionSpec]
    deliveryPolicy: Required[PresentationDeliveryPolicy]
    safetyBoundary: Required[PresentationSafetyBoundary]
    provenance: Required[PresentationProvenance]
    stableHash: Required[str]


class PresentationCostComponent(TypedDict):
    surface: str
    providerKind: str
    estimated: float
    cacheKey: str


class PresentationCostEstimate(TypedDict):
    currency: str
    totalEstimated: float
    components: list[PresentationCostComponent]
    budgetExceeded: bool


class PresentationRenderRequest(TypedDict):
    planId: Id
    rendererVersion: str
    allowedSurfaces: list[str]
    artifactCacheKey: str
    dryRunAvailable: bool


class PresentationRitualPlanResult(TypedDict, total=False):
    plan: Required[PresentationRitualPlan]
    costEstimate: Required[PresentationCostEstimate]
    renderRequest: Required[PresentationRenderRequest]
    warnings: Required[list[str]]
    continuity: NotRequired[dict[str, object]]


class PresentationSourceDigest(TypedDict, total=False):
    sourceType: Required[str]
    title: Required[str]
    summary: Required[str]
    activeThemes: Required[list[str]]
    recurringSymbols: Required[list[str]]
    practiceSummary: NotRequired[str]
    evidenceIds: Required[list[Id]]
    contextSnapshotIds: Required[list[Id]]
    threadKeys: Required[list[str]]


class PresentationRitualPlanningInput(TypedDict, total=False):
    userId: Required[Id]
    generatedAt: Required[ISODateString]
    windowStart: Required[ISODateString]
    windowEnd: Required[ISODateString]
    ritualIntent: Required[RitualIntent]
    narrativeMode: Required[NarrativeMode]
    sourceType: Required[str]
    sourceRefs: Required[list[PresentationSourceRef]]
    sourceDigest: Required[PresentationSourceDigest]
    requestedSurfaces: Required[RequestedRitualSurfaces]
    renderPolicy: Required[RitualRenderPolicy]
    completionPolicy: Required[RitualCompletionPolicy]
    privacyClass: Required[PresentationPrivacyClass]
    locale: Required[str]
    safetyContext: NotRequired[SafetyContext]


__all__ = [
    "NarrativeMode",
    "PresentationApprovalState",
    "PresentationBreathSpec",
    "PresentationCostEstimate",
    "PresentationPrivacyClass",
    "PresentationRenderRequest",
    "PresentationRitualPlan",
    "PresentationRitualPlanResult",
    "PresentationRitualPlanningInput",
    "PresentationSourceDigest",
    "PresentationSourceRef",
    "PresentationSourceRole",
    "PresentationSourceType",
    "RequestedRitualSurfaces",
    "RitualCompletionPolicy",
    "RitualIntent",
    "RitualRenderPolicy",
]
