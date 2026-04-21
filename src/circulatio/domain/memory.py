from __future__ import annotations

from typing import Literal, NotRequired, Required, TypedDict

from .types import Id, ISODateString, PrivacyClass

MemoryNamespace = Literal[
    "materials",
    "context_snapshots",
    "interpretation_runs",
    "evidence",
    "personal_symbols",
    "patterns",
    "typology_lenses",
    "practice_sessions",
    "weekly_reviews",
    "integrations",
    "suppressed_hypotheses",
    "conscious_attitudes",
    "body_states",
    "goals",
    "goal_tensions",
    "dream_series",
    "personal_amplifications",
    "amplification_prompts",
    "collective_amplifications",
    "cultural_frames",
    "consent_preferences",
    "adaptation_profiles",
    "journeys",
    "proactive_briefs",
    "individuation_records",
    "living_myth_records",
    "living_myth_reviews",
    "analysis_packets",
]

MEMORY_NAMESPACE_ALLOWLIST: tuple[MemoryNamespace, ...] = (
    "materials",
    "context_snapshots",
    "interpretation_runs",
    "evidence",
    "personal_symbols",
    "patterns",
    "typology_lenses",
    "practice_sessions",
    "weekly_reviews",
    "integrations",
    "suppressed_hypotheses",
    "conscious_attitudes",
    "body_states",
    "goals",
    "goal_tensions",
    "dream_series",
    "personal_amplifications",
    "amplification_prompts",
    "collective_amplifications",
    "cultural_frames",
    "consent_preferences",
    "adaptation_profiles",
    "journeys",
    "proactive_briefs",
    "individuation_records",
    "living_myth_records",
    "living_myth_reviews",
    "analysis_packets",
)

MemoryRetrievalRankingProfile = Literal[
    "default",
    "recency",
    "recurrence",
    "importance",
]


class MemoryKernelProvenance(TypedDict, total=False):
    sourceNamespace: Required[MemoryNamespace]
    sourceId: Required[Id]
    materialId: NotRequired[Id]
    runId: NotRequired[Id]
    evidenceIds: Required[list[Id]]
    createdAt: NotRequired[ISODateString]
    observedAt: NotRequired[ISODateString]


class MemoryImportance(TypedDict, total=False):
    score: Required[float]
    reasons: Required[list[str]]
    recurrenceCount: NotRequired[int]
    userConfirmed: NotRequired[bool]
    lastSeen: NotRequired[ISODateString]


class MemoryKernelItem(TypedDict, total=False):
    id: Required[Id]
    userId: Required[Id]
    namespace: Required[MemoryNamespace]
    entityId: Required[Id]
    entityType: Required[str]
    label: Required[str]
    summary: Required[str]
    keywords: Required[list[str]]
    symbolicFingerprint: NotRequired[list[str]]
    embedding: NotRequired[list[float]]
    provenance: Required[MemoryKernelProvenance]
    importance: Required[MemoryImportance]
    privacyClass: Required[PrivacyClass]
    createdAt: Required[ISODateString]
    updatedAt: Required[ISODateString]


class MemoryRetrievalQuery(TypedDict, total=False):
    namespaces: list[MemoryNamespace]
    relatedEntityIds: list[Id]
    windowStart: ISODateString
    windowEnd: ISODateString
    privacyClasses: list[PrivacyClass]
    textQuery: str
    rankingProfile: MemoryRetrievalRankingProfile
    limit: int


class MemoryKernelSnapshot(TypedDict, total=False):
    userId: Required[Id]
    query: NotRequired[MemoryRetrievalQuery]
    items: Required[list[MemoryKernelItem]]
    generatedAt: Required[ISODateString]
    rankingNotes: Required[list[str]]
