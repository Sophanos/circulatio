from __future__ import annotations

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


def build_blocked_by_safety_result(
    *,
    run_id: str,
    material_id: str,
    safety: dict[str, object],
) -> InterpretationResult:
    practice = _GROUNDING_FALLBACK
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
) -> InterpretationResult:
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
            "statement": (
                "The material was preserved, but the LLM interpretation path did "
                "not return usable structured output, so Circulatio is "
                "withholding symbolic conclusions and write proposals for this run."
            ),
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
    practice = _JOURNALING_FALLBACK
    clarifying_question = (
        "What part of the dream feels most alive right now?"
        if input_data["materialType"] == "dream"
        else "What image or feeling from this feels most alive right now?"
    )
    user_facing_response = (
        "The structured interpretation pass did not return usable structured output, "
        "so I do not want to fake a reading.\n\n"
        f"{clarifying_question}"
    )
    llm_health = build_llm_interpretation_health(
        source="fallback",
        reason="llm_missing_or_unusable_structured_output",
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
        "llmInterpretationHealth": llm_health,
        "depthEngineHealth": {
            "status": "fallback",
            "reason": "llm_missing_or_unusable_structured_output",
            "source": "fallback",
        },
    }
    validate_evidence_integrity(result)
    return result
