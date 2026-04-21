from __future__ import annotations

import json
from typing import Any

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
from .json_schema import (
    ANALYSIS_PACKET_OUTPUT_SCHEMA,
    INTERPRETATION_OUTPUT_SCHEMA,
    LIFE_CONTEXT_OUTPUT_SCHEMA,
    LIVING_MYTH_REVIEW_OUTPUT_SCHEMA,
    PRACTICE_OUTPUT_SCHEMA,
    RHYTHMIC_BRIEF_OUTPUT_SCHEMA,
    THRESHOLD_REVIEW_OUTPUT_SCHEMA,
    WEEKLY_REVIEW_OUTPUT_SCHEMA,
    schema_text,
)


def build_interpretation_messages(input_data: MaterialInterpretationInput) -> list[dict[str, str]]:
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
        "options": dict(input_data.get("options", {})),
        "symbolicMemory": {
            "recurringSymbols": memory["recurringSymbols"][:8],
            "activeComplexCandidates": memory["activeComplexCandidates"][:5],
            "recentMaterialSummaries": memory["recentMaterialSummaries"][:5],
            "recentInterpretationFeedback": memory["recentInterpretationFeedback"][:5],
            "practiceOutcomes": memory["practiceOutcomes"][:5],
            "suppressedHypotheses": memory["suppressedHypotheses"][:10],
            "typologyLensSummaries": memory["typologyLensSummaries"][:5],
        },
        "instructions": {
            "approvalBoundary": "Do not assume any proposal is already approved.",
            "evidencePolicy": "Use only material text, compact life context, method context, session context, and approved symbolic memory supplied here.",
            "style": "Tentative, symbolic, non-diagnostic, and explicit about uncertainty. Keep userFacingResponse short and collaborative — usually one brief paragraph or one direct question.",
            "methodPolicy": "Use the provided method context to derive readiness, method gating, amplification prompts, dream-series suggestions, and practice structure inside the JSON response. Prefer LLM judgment over local heuristics, but stay within safety and evidence boundaries.",
            "responsePolicy": "When the user wants to go deeper, the userFacingResponse should invite associative work rather than explain symbolism. Keep it short, plain, and grounded in lived feeling. Prefer one real question and at most one brief reflection. Use everyday relational or bodily language the user can actually feel. Do not use unexplained Jungian jargon like anima, Great Mother, or archetype.",
            "actionDynamicsPolicy": "Action and relational dynamics come before or alongside symbolic decoding. In dreams, what the ego DOES (running, hiding, approaching, freezing, speaking) is often more revealing than what appears. In waking reflections, what the person did or felt pulled to do matters more than what the place or object 'means.' Always ask about the felt sense during the action, the body state, and the relational stance before offering symbolic labels. If the user ran from something, ask what running felt like and what standing still might have felt like. Do not reduce action to symbols (e.g., 'running means avoiding the unconscious'). Keep the action alive as a lived, bodily choice.",
            "refKeyPolicy": "Every symbol/figure/motif/lifeContext link must have a stable refKey that observations, hypotheses, proposalCandidates, and any evidence-backed dream-series suggestions reference via supportingRefs.",
            "schemaContract": "Do not return narrative-only JSON. If userFacingResponse is non-empty, also populate grounded interpretive fields. If the material is too thin, keep interpretive arrays empty and use clarifyingQuestion instead of polished interpretation. A clarifyingQuestion with empty interpretive arrays is a valid first-pass response.",
            "witnessMethod": "Personal amplification comes before collective amplification. Dream-series suggestions are suggestions, not facts. Soma, goal, culture, and series continuity should be phrased as tentative co-occurrence unless the supplied context already confirms them.",
            "consentPolicy": "Only suggest collective amplification or deeper imaginal work when the supplied consent and method context allow it. If a move is blocked, withhold it or ask consent instead of smuggling it into practice.",
            "proposalPolicy": "Produce fewer approval-gated proposals with clear supporting refs. Never use raw symbol-dictionary meanings or deterministic-sounding claims.",
            "individuationPolicy": "Treat relational scenes before projection claims, hold inner-outer correspondence non-causally, keep Self-orientation phenomenological, and keep archetypal language very tentative. If prerequisites or consent are missing, return empty individuation arrays instead of forcing symbolic depth.",
        },
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


def build_weekly_review_messages(input_data: CirculationSummaryInput) -> list[dict[str, str]]:
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
        "instructions": {
            "style": "Keep longitudinal observations neutral, symbolic, and bounded by the supplied summaries.",
            "signalPolicy": "Treat longitudinal signals as co-occurrence material, not proof or causality.",
        },
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
) -> list[dict[str, str]]:
    payload = {
        "userId": user_id,
        "windowStart": window_start,
        "windowEnd": window_end,
        "rawContext": raw_context,
        "instructions": {
            "goal": "Summarize only the individuation-relevant context Hermes already stores.",
            "sourcePolicy": "Use bounded summaries, not raw telemetry dumps.",
            "eventLimit": 5,
            "changeLimit": 5,
            "source": "hermes-life-os",
        },
    }
    system = (
        "You compress Hermes profile context into Circulatio's LifeContextSnapshot schema. Return JSON only. "
        "Use concise summaries, preserve concrete source references when available, and never fabricate ids. "
        "Return JSON matching this schema:\n"
        f"{schema_text(LIFE_CONTEXT_OUTPUT_SCHEMA)}"
    )
    user = json.dumps(payload, indent=2, sort_keys=True, default=str)
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def build_practice_messages(input_data: PracticeRecommendationInput) -> list[dict[str, str]]:
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
        "adaptationHints": input_data.get("adaptationHints"),
        "options": dict(input_data.get("options", {})),
        "symbolicMemory": {
            "recurringSymbols": memory["recurringSymbols"][:8],
            "recentMaterialSummaries": memory["recentMaterialSummaries"][:5],
            "practiceOutcomes": memory["practiceOutcomes"][:5],
            "suppressedHypotheses": memory["suppressedHypotheses"][:5],
        },
        "instructions": {
            "style": "Keep the witness language gentle, bounded, and easy to skip without guilt.",
            "practicePolicy": "Return one bounded practice recommendation. The content must remain LLM-shaped rather than template-routed.",
            "consentPolicy": "Do not push active imagination or somatic tracking when the supplied consent or method context blocks it.",
            "adaptationPolicy": "Use adaptation hints as soft preference guidance except for explicit maxDurationMinutes, which is a hard ceiling.",
        },
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


def build_rhythmic_brief_messages(input_data: RhythmicBriefInput) -> list[dict[str, str]]:
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
        "instructions": {
            "style": "Brief, witness-like, non-pressuring, and easy to ignore without guilt.",
            "briefPolicy": "Surface one pattern without over-interpreting it. Prefer one suggested action or an explicit option to simply note it.",
            "consentPolicy": "Do not smuggle deeper active imagination, shadow, or projection work into the brief when the supplied method context blocks it.",
        },
    }
    system = (
        "You write short Circulatio rhythmic briefs. Return JSON only. "
        "The brief should feel like a gentle pattern surfacing, not a demand or notification. "
        "Return JSON matching this schema:\n"
        f"{schema_text(RHYTHMIC_BRIEF_OUTPUT_SCHEMA)}"
    )
    user = json.dumps(payload, indent=2, sort_keys=True, default=str)
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def build_threshold_review_messages(input_data: ThresholdReviewInput) -> list[dict[str, str]]:
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
        "instructions": {
            "style": "Hold liminal material carefully, pacing depth with grounding and evidence.",
            "thresholdPolicy": "Describe threshold processes as containers, not fixed stages. If grounding is weak, prefer pacing, containment, or grounding-first language.",
            "consentPolicy": "Do not intensify archetypal or projection language when consent or method readiness is missing.",
            "proposalPolicy": "Threshold-derived durable writes remain approval-gated. If you emit proposalCandidates, supportingRefs must cite existing item ids from the payload so infrastructure can carry evidence without reinterpreting the result.",
        },
    }
    system = (
        "You write Circulatio threshold reviews. Return JSON only. "
        "Hold threshold processes lightly, avoid doctrine or fixed-stage claims, and keep symbolic language paced by grounding. "
        "Return JSON matching this schema:\n"
        f"{schema_text(THRESHOLD_REVIEW_OUTPUT_SCHEMA)}"
    )
    user = json.dumps(payload, indent=2, sort_keys=True, default=str)
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def build_living_myth_review_messages(input_data: LivingMythReviewInput) -> list[dict[str, str]]:
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
        "instructions": {
            "style": "Weave longitudinal material into a collaborative life-chapter reading without turning it into identity or doctrine.",
            "chapterPolicy": "A life chapter is a provisional snapshot, not an essence, score, or permanent stage.",
            "consentPolicy": "If living myth synthesis feels too strong for the supplied consent or readiness, return lighter chapter/question material rather than forcing mythic closure.",
            "proposalPolicy": "Durable chapter, contour, and wellbeing records remain approval-gated. If you emit proposalCandidates, supportingRefs must cite existing item ids from the payload so infrastructure can carry evidence without reinterpreting the result.",
        },
    }
    system = (
        "You write Circulatio living myth reviews. Return JSON only. "
        "Treat life chapters, mythic questions, and integration contours as qualitative, user-owned, and lightly held. "
        "Return JSON matching this schema:\n"
        f"{schema_text(LIVING_MYTH_REVIEW_OUTPUT_SCHEMA)}"
    )
    user = json.dumps(payload, indent=2, sort_keys=True, default=str)
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def build_analysis_packet_messages(input_data: AnalysisPacketInput) -> list[dict[str, str]]:
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
        "instructions": {
            "style": "Build a bounded packet that is legible for reflection, journaling, or analysis without pretending to replace the human encounter.",
            "packetPolicy": "Prefer concise sections with evidence-grounded items. Do not dump raw material text or expand beyond what stayed alive in the window.",
            "boundaryPolicy": "Package existing summaries and tensions. Do not invent new durable claims or a mythic master theory.",
            "provenancePolicy": "includedMaterialIds, includedRecordRefs, evidenceIds, and supportingRefs must cite existing ids from the payload only. Do not invent ids or derive metadata from free text.",
        },
    }
    system = (
        "You write bounded Circulatio analysis packets. Return JSON only. "
        "Keep the packet evidence-grounded, concise, and useful for reflection or analysis rather than exhaustive. "
        "Return JSON matching this schema:\n"
        f"{schema_text(ANALYSIS_PACKET_OUTPUT_SCHEMA)}"
    )
    user = json.dumps(payload, indent=2, sort_keys=True, default=str)
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]
