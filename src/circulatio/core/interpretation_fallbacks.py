from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from typing import cast

from ..domain.ids import create_id
from ..domain.types import InterpretationResult, MaterialInterpretationInput
from .evidence import EvidenceLedger
from .interpretation_mapping import (
    build_life_context_links,
    build_llm_interpretation_health,
    validate_evidence_integrity,
)

_GROUNDING_FALLBACK: dict[str, object] = {
    "id": create_id("practice"),
    "type": "grounding",
    "reason": "Safety gate recommends grounding instead of symbolic depth work.",
    "contraindicationsChecked": [],
    "durationMinutes": 3,
    "requiresConsent": False,
    "instructions": [
        "Name five things you can see.",
        "Feel your feet or body supported by the surface beneath you.",
        "Slow your exhale for several breaths.",
        "Reach out to human support if you feel unsafe or overwhelmed.",
    ],
}

_JOURNALING_FALLBACK: dict[str, object] = {
    "id": create_id("practice"),
    "type": "journaling",
    "reason": (
        "The interpretation model is unavailable. Stay close to the material in your own words."
    ),
    "contraindicationsChecked": [],
    "durationMinutes": 8,
    "requiresConsent": False,
    "instructions": [
        "Write what happened in your own words.",
        "Note any image, feeling, or figure that stands out.",
        "Stop after one page; do not force a conclusion.",
    ],
}


def _fresh_fallback_practice(template: dict[str, object]) -> dict[str, object]:
    practice = deepcopy(template)
    practice["id"] = create_id("practice")
    return practice


def _fallback_clarifying_question(input_data: MaterialInterpretationInput) -> str:
    return (
        (
            "What personal association comes up around the part of the dream "
            "that feels most alive right now?"
        )
        if input_data["materialType"] == "dream"
        else (
            "What personal association comes up around the image or feeling "
            "that feels most alive right now?"
        )
    )


def _fallback_clarification_ref_key(input_data: MaterialInterpretationInput) -> str:
    return (
        "clarify_dream_primary_image"
        if input_data["materialType"] == "dream"
        else "clarify_primary_image"
    )


def _fallback_clarification_intent(
    *,
    run_id: str,
    material_id: str,
    question_text: str,
    ref_key: str,
) -> dict[str, object]:
    expires_at = (datetime.now(UTC) + timedelta(days=14)).replace(microsecond=0)
    return {
        "refKey": ref_key,
        "questionText": question_text,
        "expectedTargets": ["personal_amplification"],
        "anchorRefs": {"runId": run_id, "materialId": material_id},
        "consentScopes": [],
        "storagePolicy": "no_storage_without_confirmation",
        "expiresAt": expires_at.isoformat().replace("+00:00", "Z"),
    }


def _fallback_clarification_plan(
    *,
    question_text: str,
    ref_key: str,
    run_id: str,
    material_id: str,
    input_data: MaterialInterpretationInput,
) -> dict[str, object]:
    surface_text = str(input_data.get("materialText") or "").strip()[:240]
    canonical_name = (
        "most alive dream image"
        if input_data["materialType"] == "dream"
        else "most alive material image"
    )
    return {
        "questionText": question_text,
        "questionKey": ref_key,
        "intent": "personal_association",
        "captureTarget": "personal_amplification",
        "expectedAnswerKind": "free_text",
        "routingHints": {
            "source": "fallback_collaborative_opening",
            "continuationMode": "personal_amplification",
            "expectedTargets": ["personal_amplification"],
            "anchorRefs": {"runId": run_id, "materialId": material_id},
            "canonicalName": canonical_name,
            "surfaceText": surface_text,
        },
        "anchorRefs": {"runId": run_id, "materialId": material_id},
        "consentScopes": [],
    }


def _fallback_method_gate(question_text: str) -> dict[str, object]:
    return {
        "depthLevel": "personal_amplification_needed",
        "missingPrerequisites": ["personal_association"],
        "blockedMoves": [
            "symbolic_conclusion",
            "collective_amplification",
            "memory_write_proposals",
        ],
        "requiredPrompts": [
            question_text,
            "Ask for the user's own associations before offering symbolic framing.",
        ],
        "responseConstraints": [
            "Ask exactly one question.",
            "Render the clarifying question verbatim; do not add examples, choices, "
            "or a second question.",
            "Stay with the image, action, or feeling that carries charge.",
        ],
    }


def _fallback_association_ready_gate() -> dict[str, object]:
    return {
        "depthLevel": "cautious_pattern_note",
        "missingPrerequisites": [],
        "blockedMoves": [
            "symbolic_conclusion",
            "collective_amplification",
            "memory_write_proposals",
        ],
        "requiredPrompts": [],
        "responseConstraints": [
            "Do not ask for the same personal association again.",
            "Do not substitute a host-authored symbolic interpretation.",
            "Acknowledge that the associations are held and pause cleanly.",
        ],
    }


def _input_has_personal_ground(input_data: MaterialInterpretationInput) -> bool:
    if input_data.get("userAssociations"):
        return True
    method_context = input_data.get("methodContextSnapshot")
    return isinstance(method_context, dict) and bool(method_context.get("personalAmplifications"))


def build_blocked_by_safety_result(
    *,
    run_id: str,
    material_id: str,
    safety: dict[str, object],
) -> InterpretationResult:
    practice = _fresh_fallback_practice(_GROUNDING_FALLBACK)
    return {
        "runId": run_id,
        "materialId": material_id,
        "safetyDisposition": safety,
        "observations": [],
        "evidence": [],
        "symbolMentions": [],
        "figureMentions": [],
        "motifMentions": [],
        "personalSymbolUpdates": [],
        "culturalAmplifications": [],
        "hypotheses": [],
        "complexCandidateUpdates": [],
        "lifeContextLinks": [],
        "practiceRecommendation": practice,
        "memoryWritePlan": {"runId": run_id, "proposals": [], "evidenceItems": []},
        "userFacingResponse": (
            "Hermes-Circulation supports reflection and symbolic interpretation. "
            "It does not provide therapy, diagnosis, crisis counseling, or medical advice.\n\n"
            f"{safety.get('message', '')}\n\n"
            "Safer next step:\n"
            + "\n".join(f"- {instruction}" for instruction in cast(list, practice["instructions"]))
        ),
        "depthEngineHealth": {
            "status": "fallback",
            "reason": "safety_gate_blocks_depth",
            "source": "fallback",
        },
    }


def build_unavailable_llm_result(
    *,
    run_id: str,
    material_id: str,
    safety: dict[str, object],
    evidence_ledger: EvidenceLedger,
    input_data: MaterialInterpretationInput,
    fallback_reason: str,
) -> InterpretationResult:
    observation_statement = {
        "llm_unavailable": (
            "The material was preserved, but the interpretation model was unavailable for this "
            "pass, so Circulatio opened a collaborative question instead of forcing symbolic "
            "conclusions or write proposals."
        ),
        "llm_execution_error": (
            "The material was preserved, but the interpretation model could not complete this "
            "pass, so Circulatio opened a collaborative question instead of forcing symbolic "
            "conclusions or write proposals."
        ),
        "llm_no_usable_structured_content": (
            "The material was preserved, but the interpretation model did not return usable "
            "structured content, so Circulatio opened a collaborative question instead of "
            "forcing symbolic conclusions or write proposals."
        ),
    }.get(
        fallback_reason,
        "The material was preserved, but Circulatio opened a collaborative question instead "
        "of forcing symbolic conclusions or write proposals.",
    )
    material_evidence_id = evidence_ledger.add(
        evidence_type="dream_text_span"
        if input_data["materialType"] == "dream"
        else "material_text_span",
        source_id=material_id,
        quote_or_summary=input_data["materialText"][:240],
        privacy_class=input_data.get("privacyClass", "session_only"),
        reliability="high",
    )
    life_context_links = build_life_context_links(
        input_data=input_data,
        material_id=material_id,
        evidence_ledger=evidence_ledger,
    )
    observations = [
        {
            "id": create_id("observation"),
            "kind": "structure",
            "statement": observation_statement,
            "evidenceIds": [material_evidence_id],
        }
    ]
    if life_context_links:
        observations.append(
            {
                "id": create_id("observation"),
                "kind": "life_context_link",
                "statement": (
                    "Compact life context was attached and held for a later "
                    "LLM-backed interpretation pass."
                ),
                "evidenceIds": [link["evidenceId"] for link in life_context_links],
            }
        )
    practice = _fresh_fallback_practice(_JOURNALING_FALLBACK)
    if _input_has_personal_ground(input_data):
        user_facing_response = (
            "I have enough of your associations held. I do not want to force a deeper "
            "reading in this pass; pausing is cleaner."
        )
        llm_health = build_llm_interpretation_health(
            source="fallback",
            status="opened",
            reason="association_ready_interpretation_unavailable",
            diagnostic_reason=fallback_reason,
            symbol_mentions=[],
            figure_mentions=[],
            motif_mentions=[],
            observations=observations,
            hypotheses=[],
            proposal_candidates=[],
        )
        result: InterpretationResult = {
            "runId": run_id,
            "materialId": material_id,
            "safetyDisposition": safety,
            "observations": observations,
            "evidence": evidence_ledger.all(),
            "symbolMentions": [],
            "figureMentions": [],
            "motifMentions": [],
            "personalSymbolUpdates": [],
            "culturalAmplifications": [],
            "hypotheses": [],
            "complexCandidateUpdates": [],
            "lifeContextLinks": life_context_links,
            "practiceRecommendation": practice,
            "memoryWritePlan": {
                "runId": run_id,
                "proposals": [],
                "evidenceItems": cast(list, evidence_ledger.all()),
            },
            "userFacingResponse": user_facing_response,
            "methodGate": cast(object, _fallback_association_ready_gate()),
            "llmInterpretationHealth": llm_health,
            "depthEngineHealth": {
                "status": "opened",
                "reason": "association_ready_interpretation_unavailable",
                "diagnosticReason": fallback_reason,
                "source": "fallback",
            },
        }
        validate_evidence_integrity(result)
        return result
    clarifying_question = _fallback_clarifying_question(input_data)
    clarification_ref_key = _fallback_clarification_ref_key(input_data)
    clarification_intent = _fallback_clarification_intent(
        run_id=run_id,
        material_id=material_id,
        question_text=clarifying_question,
        ref_key=clarification_ref_key,
    )
    clarification_plan = _fallback_clarification_plan(
        question_text=clarifying_question,
        ref_key=clarification_ref_key,
        run_id=run_id,
        material_id=material_id,
        input_data=input_data,
    )
    method_gate = _fallback_method_gate(clarifying_question)
    user_facing_response = clarifying_question
    llm_health = build_llm_interpretation_health(
        source="fallback",
        status="opened",
        reason="collaborative_opening_started",
        diagnostic_reason=fallback_reason,
        symbol_mentions=[],
        figure_mentions=[],
        motif_mentions=[],
        observations=observations,
        hypotheses=[],
        proposal_candidates=[],
    )
    result: InterpretationResult = {
        "runId": run_id,
        "materialId": material_id,
        "safetyDisposition": safety,
        "observations": observations,
        "evidence": evidence_ledger.all(),
        "symbolMentions": [],
        "figureMentions": [],
        "motifMentions": [],
        "personalSymbolUpdates": [],
        "culturalAmplifications": [],
        "hypotheses": [],
        "complexCandidateUpdates": [],
        "lifeContextLinks": life_context_links,
        "practiceRecommendation": practice,
        "memoryWritePlan": {
            "runId": run_id,
            "proposals": [],
            "evidenceItems": cast(list, evidence_ledger.all()),
        },
        "userFacingResponse": user_facing_response,
        "clarifyingQuestion": clarifying_question,
        "clarificationPlan": cast(object, clarification_plan),
        "clarificationIntent": cast(object, clarification_intent),
        "methodGate": cast(object, method_gate),
        "llmInterpretationHealth": llm_health,
        "depthEngineHealth": {
            "status": "opened",
            "reason": "collaborative_opening_started",
            "diagnosticReason": fallback_reason,
            "source": "fallback",
        },
    }
    validate_evidence_integrity(result)
    return result
