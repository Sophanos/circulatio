from __future__ import annotations

import json
from typing import Any, Protocol

from ..domain.method_state import MethodStateRoutingInput
from ..domain.normalization import (
    compact_life_context_snapshot,
    normalize_hermes_memory_context,
    normalize_session_context,
)
from ..domain.types import (
    AnalysisPacketInput,
    CirculationSummaryInput,
    LivingMythReviewInput,
    MaterialInterpretationInput,
    PracticeRecommendationInput,
    RhythmicBriefInput,
    ThresholdReviewInput,
)
from . import prompt_fragments
from .json_schema import (
    ANALYSIS_PACKET_OUTPUT_SCHEMA,
    INTERPRETATION_OUTPUT_SCHEMA,
    LIFE_CONTEXT_OUTPUT_SCHEMA,
    LIVING_MYTH_REVIEW_OUTPUT_SCHEMA,
    METHOD_STATE_ROUTING_OUTPUT_SCHEMA,
    PRACTICE_OUTPUT_SCHEMA,
    RHYTHMIC_BRIEF_OUTPUT_SCHEMA,
    THRESHOLD_REVIEW_OUTPUT_SCHEMA,
    WEEKLY_REVIEW_OUTPUT_SCHEMA,
    schema_text,
)


class PromptFragmentsProvider(Protocol):
    def interpretation_instruction_block(self) -> dict[str, str]: ...

    def weekly_review_instruction_block(self) -> dict[str, str]: ...

    def life_context_instruction_block(self) -> dict[str, object]: ...

    def practice_instruction_block(self) -> dict[str, str]: ...

    def rhythmic_brief_instruction_block(self) -> dict[str, str]: ...

    def threshold_review_instruction_block(self) -> dict[str, str]: ...

    def living_myth_instruction_block(self) -> dict[str, str]: ...

    def method_state_routing_instruction_block(self) -> dict[str, str]: ...

    def analysis_packet_instruction_block(self) -> dict[str, str]: ...


def _fragments(provider: PromptFragmentsProvider | None) -> PromptFragmentsProvider:
    return provider or prompt_fragments


def build_interpretation_messages(
    input_data: MaterialInterpretationInput,
    *,
    fragments: PromptFragmentsProvider | None = None,
) -> list[dict[str, str]]:
    active_fragments = _fragments(fragments)
    memory = normalize_hermes_memory_context(input_data.get("hermesMemoryContext"))
    payload = {
        "material": {
            "materialId": input_data.get("materialId"),
            "materialType": input_data["materialType"],
            "materialText": input_data["materialText"],
            "materialDate": input_data.get("materialDate"),
            "explicitQuestion": input_data.get("explicitQuestion"),
            "wakingTone": input_data.get("wakingTone"),
        },
        "sessionContext": normalize_session_context(input_data.get("sessionContext")),
        "lifeContextSnapshot": compact_life_context_snapshot(input_data.get("lifeContextSnapshot")),
        "methodContextSnapshot": input_data.get("methodContextSnapshot"),
        "userAssociations": list(input_data.get("userAssociations", [])),
        "culturalOrigins": list(input_data.get("culturalOrigins", [])),
        "trustedAmplificationSources": list(input_data.get("trustedAmplificationSources", [])),
        "communicationHints": input_data.get("communicationHints"),
        "interpretationHints": input_data.get("interpretationHints"),
        "practiceHints": input_data.get("practiceHints"),
        "options": dict(input_data.get("options", {})),
        "symbolicMemory": {
            "recurringSymbols": memory["recurringSymbols"][:8],
            "activeComplexCandidates": memory["activeComplexCandidates"][:5],
            "recentMaterialSummaries": memory["recentMaterialSummaries"][:5],
            "practiceOutcomes": memory["practiceOutcomes"][:5],
            "suppressedHypotheses": memory["suppressedHypotheses"][:10],
            "typologyLensSummaries": memory["typologyLensSummaries"][:5],
        },
        "instructions": active_fragments.interpretation_instruction_block(),
    }
    system = (
        "You are Circulatio's symbolic interpretation model. Produce structured JSON only. "
        "Stay tentative, avoid diagnosis, crisis counseling, or certainty claims, and never perform memory writes. "
        "Interpretive depth is allowed only within the supplied safety boundary. "
        "Return JSON matching this schema:\n"
        f"{schema_text(INTERPRETATION_OUTPUT_SCHEMA)}"
    )
    user = json.dumps(payload, indent=2, sort_keys=True, default=str)
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]



def build_weekly_review_messages(
    input_data: CirculationSummaryInput,
    *,
    fragments: PromptFragmentsProvider | None = None,
) -> list[dict[str, str]]:
    active_fragments = _fragments(fragments)
    payload = {
        "windowStart": input_data["windowStart"],
        "windowEnd": input_data["windowEnd"],
        "lifeContextSnapshot": compact_life_context_snapshot(input_data.get("lifeContextSnapshot")),
        "methodContextSnapshot": input_data.get("methodContextSnapshot"),
        "symbolicMemory": {
            "recurringSymbols": input_data["hermesMemoryContext"]["recurringSymbols"][:8],
            "activeComplexCandidates": input_data["hermesMemoryContext"]["activeComplexCandidates"][
                :5
            ],
            "recentMaterialSummaries": input_data["hermesMemoryContext"]["recentMaterialSummaries"][
                :8
            ],
            "practiceOutcomes": input_data["hermesMemoryContext"]["practiceOutcomes"][:5],
            "suppressedHypotheses": input_data["hermesMemoryContext"]["suppressedHypotheses"][:5],
        },
        "instructions": active_fragments.weekly_review_instruction_block(),
    }
    system = (
        "You write Circulatio weekly review summaries. Return JSON only. "
        "The narrative must remain symbolic, cautious, and grounded in the supplied memory, life-context, and method-context summaries. "
        "Do not invent raw telemetry or clinical claims. Return JSON matching this schema:\n"
        f"{schema_text(WEEKLY_REVIEW_OUTPUT_SCHEMA)}"
    )
    user = json.dumps(payload, indent=2, sort_keys=True, default=str)
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]



def build_life_context_messages(
    *,
    user_id: str,
    window_start: str,
    window_end: str,
    raw_context: dict[str, Any],
    fragments: PromptFragmentsProvider | None = None,
) -> list[dict[str, str]]:
    active_fragments = _fragments(fragments)
    payload = {
        "userId": user_id,
        "windowStart": window_start,
        "windowEnd": window_end,
        "rawContext": raw_context,
        "instructions": active_fragments.life_context_instruction_block(),
    }
    system = (
        "You compress Hermes profile context into Circulatio's LifeContextSnapshot schema. Return JSON only. "
        "Use concise summaries, preserve concrete source references when available, and never fabricate ids. "
        "Return JSON matching this schema:\n"
        f"{schema_text(LIFE_CONTEXT_OUTPUT_SCHEMA)}"
    )
    user = json.dumps(payload, indent=2, sort_keys=True, default=str)
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]



def build_practice_messages(
    input_data: PracticeRecommendationInput,
    *,
    fragments: PromptFragmentsProvider | None = None,
) -> list[dict[str, str]]:
    active_fragments = _fragments(fragments)
    memory = normalize_hermes_memory_context(input_data.get("hermesMemoryContext"))
    payload = {
        "windowStart": input_data["windowStart"],
        "windowEnd": input_data["windowEnd"],
        "trigger": input_data["trigger"],
        "sessionContext": normalize_session_context(input_data.get("sessionContext")),
        "lifeContextSnapshot": compact_life_context_snapshot(input_data.get("lifeContextSnapshot")),
        "methodContextSnapshot": input_data.get("methodContextSnapshot"),
        "safetyContext": input_data.get("safetyContext"),
        "explicitQuestion": input_data.get("explicitQuestion"),
        "practiceHints": input_data.get("practiceHints") or input_data.get("adaptationHints"),
        "options": dict(input_data.get("options", {})),
        "symbolicMemory": {
            "recurringSymbols": memory["recurringSymbols"][:8],
            "recentMaterialSummaries": memory["recentMaterialSummaries"][:5],
            "practiceOutcomes": memory["practiceOutcomes"][:5],
            "suppressedHypotheses": memory["suppressedHypotheses"][:5],
        },
        "instructions": active_fragments.practice_instruction_block(),
    }
    system = (
        "You write Circulatio practice recommendations. Return JSON only. "
        "Keep the language symbolic, relationally safe, and lightly held. "
        "The user may skip the practice without guilt. "
        "Return JSON matching this schema:\n"
        f"{schema_text(PRACTICE_OUTPUT_SCHEMA)}"
    )
    user = json.dumps(payload, indent=2, sort_keys=True, default=str)
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]



def build_rhythmic_brief_messages(
    input_data: RhythmicBriefInput,
    *,
    fragments: PromptFragmentsProvider | None = None,
) -> list[dict[str, str]]:
    active_fragments = _fragments(fragments)
    memory = normalize_hermes_memory_context(input_data.get("hermesMemoryContext"))
    payload = {
        "windowStart": input_data["windowStart"],
        "windowEnd": input_data["windowEnd"],
        "source": input_data["source"],
        "seed": input_data["seed"],
        "lifeContextSnapshot": compact_life_context_snapshot(input_data.get("lifeContextSnapshot")),
        "methodContextSnapshot": input_data.get("methodContextSnapshot"),
        "adaptationProfile": input_data.get("adaptationProfile"),
        "safetyContext": input_data.get("safetyContext"),
        "symbolicMemory": {
            "recurringSymbols": memory["recurringSymbols"][:5],
            "recentMaterialSummaries": memory["recentMaterialSummaries"][:5],
            "practiceOutcomes": memory["practiceOutcomes"][:5],
        },
        "instructions": active_fragments.rhythmic_brief_instruction_block(),
    }
    system = (
        "You write short Circulatio rhythmic briefs. Return JSON only. "
        "The brief should feel like a gentle pattern surfacing, not a demand or notification. "
        "Return JSON matching this schema:\n"
        f"{schema_text(RHYTHMIC_BRIEF_OUTPUT_SCHEMA)}"
    )
    user = json.dumps(payload, indent=2, sort_keys=True, default=str)
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]



def build_threshold_review_messages(
    input_data: ThresholdReviewInput,
    *,
    fragments: PromptFragmentsProvider | None = None,
) -> list[dict[str, str]]:
    active_fragments = _fragments(fragments)
    memory = normalize_hermes_memory_context(input_data.get("hermesMemoryContext"))
    payload = {
        "windowStart": input_data["windowStart"],
        "windowEnd": input_data["windowEnd"],
        "explicitQuestion": input_data.get("explicitQuestion"),
        "lifeContextSnapshot": compact_life_context_snapshot(input_data.get("lifeContextSnapshot")),
        "methodContextSnapshot": input_data.get("methodContextSnapshot"),
        "safetyContext": input_data.get("safetyContext"),
        "targetThresholdProcess": input_data.get("targetThresholdProcess"),
        "relatedRealityAnchors": list(input_data.get("relatedRealityAnchors", [])),
        "relatedBodyStates": list(input_data.get("relatedBodyStates", [])),
        "relatedDreamSeries": list(input_data.get("relatedDreamSeries", [])),
        "relatedRelationalScenes": list(input_data.get("relatedRelationalScenes", [])),
        "symbolicMemory": {
            "recurringSymbols": memory["recurringSymbols"][:6],
            "recentMaterialSummaries": memory["recentMaterialSummaries"][:6],
            "practiceOutcomes": memory["practiceOutcomes"][:4],
        },
        "instructions": active_fragments.threshold_review_instruction_block(),
    }
    system = (
        "You write Circulatio threshold reviews. Return JSON only. "
        "Hold threshold processes lightly, avoid doctrine or fixed-stage claims, and keep symbolic language paced by grounding. "
        "Return JSON matching this schema:\n"
        f"{schema_text(THRESHOLD_REVIEW_OUTPUT_SCHEMA)}"
    )
    user = json.dumps(payload, indent=2, sort_keys=True, default=str)
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]



def build_living_myth_review_messages(
    input_data: LivingMythReviewInput,
    *,
    fragments: PromptFragmentsProvider | None = None,
) -> list[dict[str, str]]:
    active_fragments = _fragments(fragments)
    memory = normalize_hermes_memory_context(input_data.get("hermesMemoryContext"))
    payload = {
        "windowStart": input_data["windowStart"],
        "windowEnd": input_data["windowEnd"],
        "explicitQuestion": input_data.get("explicitQuestion"),
        "lifeContextSnapshot": compact_life_context_snapshot(input_data.get("lifeContextSnapshot")),
        "methodContextSnapshot": input_data.get("methodContextSnapshot"),
        "safetyContext": input_data.get("safetyContext"),
        "recentMaterialSummaries": list(input_data.get("recentMaterialSummaries", [])),
        "symbolicMemory": {
            "recurringSymbols": memory["recurringSymbols"][:8],
            "activeComplexCandidates": memory["activeComplexCandidates"][:5],
            "recentMaterialSummaries": memory["recentMaterialSummaries"][:8],
            "practiceOutcomes": memory["practiceOutcomes"][:5],
            "suppressedHypotheses": memory["suppressedHypotheses"][:6],
        },
        "instructions": active_fragments.living_myth_instruction_block(),
    }
    system = (
        "You write Circulatio living myth reviews. Return JSON only. "
        "Treat life chapters, mythic questions, and integration contours as qualitative, user-owned, and lightly held. "
        "Return JSON matching this schema:\n"
        f"{schema_text(LIVING_MYTH_REVIEW_OUTPUT_SCHEMA)}"
    )
    user = json.dumps(payload, indent=2, sort_keys=True, default=str)
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]



def build_method_state_routing_messages(
    input_data: MethodStateRoutingInput,
    *,
    fragments: PromptFragmentsProvider | None = None,
) -> list[dict[str, str]]:
    active_fragments = _fragments(fragments)
    payload = {
        "responseText": input_data["responseText"],
        "source": input_data["source"],
        "anchorRefs": dict(input_data.get("anchorRefs", {})),
        "expectedTargets": list(input_data.get("expectedTargets", [])),
        "clarificationIntent": input_data.get("clarificationIntent"),
        "methodContextSnapshot": input_data.get("methodContextSnapshot"),
        "lifeContextSnapshot": compact_life_context_snapshot(input_data.get("lifeContextSnapshot")),
        "symbolicMemory": normalize_hermes_memory_context(input_data.get("hermesMemoryContext")),
        "safetyContext": input_data.get("safetyContext"),
        "consentPreferences": list(input_data.get("consentPreferences", [])),
        "recentPromptOrRunSummary": input_data.get("recentPromptOrRunSummary"),
        "options": dict(input_data.get("options", {})),
        "instructions": active_fragments.method_state_routing_instruction_block(),
    }
    system = (
        "You route Circulatio follow-up responses into typed method-state capture candidates. Return JSON only. "
        "Do not generate user-facing witness prose, do not infer deterministic symbolism, and do not write memory. "
        "Return JSON matching this schema:\n"
        f"{schema_text(METHOD_STATE_ROUTING_OUTPUT_SCHEMA)}"
    )
    user = json.dumps(payload, indent=2, sort_keys=True, default=str)
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]



def build_analysis_packet_messages(
    input_data: AnalysisPacketInput,
    *,
    fragments: PromptFragmentsProvider | None = None,
) -> list[dict[str, str]]:
    active_fragments = _fragments(fragments)
    memory = normalize_hermes_memory_context(input_data.get("hermesMemoryContext"))
    payload = {
        "windowStart": input_data["windowStart"],
        "windowEnd": input_data["windowEnd"],
        "packetFocus": input_data.get("packetFocus"),
        "explicitQuestion": input_data.get("explicitQuestion"),
        "lifeContextSnapshot": compact_life_context_snapshot(input_data.get("lifeContextSnapshot")),
        "methodContextSnapshot": input_data.get("methodContextSnapshot"),
        "safetyContext": input_data.get("safetyContext"),
        "currentDreamSeries": list(input_data.get("currentDreamSeries", [])),
        "activeThresholdProcesses": list(input_data.get("activeThresholdProcesses", [])),
        "bodyEchoes": list(input_data.get("bodyEchoes", [])),
        "relationalScenes": list(input_data.get("relationalScenes", [])),
        "projectionHypotheses": list(input_data.get("projectionHypotheses", [])),
        "innerOuterCorrespondences": list(input_data.get("innerOuterCorrespondences", [])),
        "activeMythicQuestions": list(input_data.get("activeMythicQuestions", [])),
        "userCorrectionsAndRejectedClaims": list(
            input_data.get("userCorrectionsAndRejectedClaims", [])
        ),
        "recentPracticeOutcomes": list(input_data.get("recentPracticeOutcomes", [])),
        "evidence": list(input_data.get("evidence", [])),
        "symbolicMemory": {
            "recurringSymbols": memory["recurringSymbols"][:8],
            "recentMaterialSummaries": memory["recentMaterialSummaries"][:8],
        },
        "instructions": active_fragments.analysis_packet_instruction_block(),
    }
    system = (
        "You write bounded Circulatio analysis packets. Return JSON only. "
        "Keep the packet evidence-grounded, concise, and useful for reflection or analysis rather than exhaustive. "
        "Return JSON matching this schema:\n"
        f"{schema_text(ANALYSIS_PACKET_OUTPUT_SCHEMA)}"
    )
    user = json.dumps(payload, indent=2, sort_keys=True, default=str)
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]
