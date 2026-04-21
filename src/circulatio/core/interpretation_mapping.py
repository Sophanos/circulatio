from __future__ import annotations

import logging
from typing import cast

from ..domain.ids import create_id, normalize_claim_key, now_iso
from ..domain.types import (
    AmplificationPromptSummary,
    AnalysisPacketInput,
    AnalysisPacketRecordRef,
    ClarificationPlan,
    CollectiveAmplificationWritePayload,
    ComplexCandidateWritePayload,
    DepthReadinessAssessment,
    DreamSeriesLinkWritePayload,
    DreamSeriesSuggestion,
    EvidenceItem,
    FigureMention,
    GoalTensionWritePayload,
    HermesMemoryContext,
    Hypothesis,
    IndividuationAssessment,
    InterpretationResult,
    LifeContextLink,
    LivingMythReviewInput,
    LlmInterpretationHealth,
    MaterialInterpretationInput,
    MemoryWritePlan,
    MemoryWriteProposal,
    MethodContextSnapshot,
    MethodGateResult,
    MotifMention,
    Observation,
    PersonalSymbolWritePayload,
    SymbolMention,
    ThresholdReviewInput,
    TypologyAssessment,
)
from ..llm.contracts import (
    LlmInterpretationOutput,
    LlmPracticeCandidate,
    LlmProposalCandidate,
)
from ..llm.ports import CirculatioLlmPort
from .evidence import EvidenceIntegrityError, EvidenceLedger
from .interpretation_sanitizers import (
    clamp_float,
    locate_text_span,
    sanitize_confidence,
    sanitize_duration,
    sanitize_figure_role,
    sanitize_hypothesis_type,
    sanitize_motif_type,
    sanitize_phrasing_policy,
    sanitize_practice_type,
    sanitize_symbol_category,
    truncate_text,
)

LOGGER = logging.getLogger(__name__)

_SUPPORTED_MEMORY_WRITE_ACTIONS = {
    "upsert_personal_symbol",
    "upsert_complex_candidate",
    "record_practice_outcome",
    "store_material_summary",
    "store_typology_lens",
    "create_conscious_attitude_snapshot",
    "record_personal_amplification",
    "create_amplification_prompt",
    "record_body_state",
    "upsert_goal_tension",
    "create_dream_series",
    "link_material_to_dream_series",
    "update_dream_series",
    "create_collective_amplification",
    "create_reality_anchor_summary",
    "create_self_orientation_snapshot",
    "upsert_psychic_opposition",
    "create_emergent_third_signal",
    "create_bridge_moment",
    "create_numinous_encounter",
    "create_aesthetic_resonance",
    "upsert_archetypal_pattern",
    "upsert_threshold_process",
    "upsert_relational_scene",
    "upsert_projection_hypothesis",
    "upsert_inner_outer_correspondence",
    "create_life_chapter_snapshot",
    "upsert_mythic_question",
    "create_threshold_marker",
    "upsert_complex_encounter",
    "create_integration_contour",
    "create_symbolic_wellbeing_snapshot",
}

_PACKET_RECORD_FIELDS = {
    "currentDreamSeries": "DreamSeries",
    "activeThresholdProcesses": "ThresholdProcess",
    "bodyEchoes": "BodyState",
    "relationalScenes": "RelationalScene",
    "projectionHypotheses": "ProjectionHypothesis",
    "innerOuterCorrespondences": "InnerOuterCorrespondence",
    "activeMythicQuestions": "MythicQuestion",
}

_MATERIAL_EVIDENCE_TYPES = {"material_text_span", "dream_text_span", "prior_material"}


async def try_llm_interpretation(
    llm: CirculatioLlmPort | None,
    input_data: MaterialInterpretationInput,
) -> LlmInterpretationOutput | None:
    if llm is None:
        return None
    try:
        output = await llm.interpret_material(input_data)
    except Exception:
        LOGGER.warning(
            "Circulatio interpretation LLM path failed; using minimal fallback.", exc_info=True
        )
        return None
    if not llm_output_has_content(output):
        LOGGER.warning(
            "Circulatio interpretation LLM path returned no usable structured "
            "content; using minimal fallback."
        )
        return None
    return output


def llm_output_has_content(output: LlmInterpretationOutput) -> bool:
    return any(
        [
            bool(output.get("symbolMentions")),
            bool(output.get("figureMentions")),
            bool(output.get("motifMentions")),
            bool(output.get("observations")),
            bool(output.get("hypotheses")),
            bool(output.get("proposalCandidates")),
            bool(output.get("depthReadiness")),
            bool(output.get("methodGate")),
            bool(output.get("amplificationPrompts")),
            bool(output.get("dreamSeriesSuggestions")),
            bool(output.get("individuation")),
            bool(str(output.get("clarifyingQuestion", "")).strip())
            and not bool(str(output.get("userFacingResponse", "")).strip()),
        ]
    )


def build_llm_interpretation_health(
    *,
    source: str,
    reason: str,
    symbol_mentions: list[SymbolMention],
    figure_mentions: list[FigureMention],
    motif_mentions: list[MotifMention],
    observations: list[Observation],
    hypotheses: list[Hypothesis],
    proposal_candidates: list[MemoryWriteProposal] | list[LlmProposalCandidate],
) -> LlmInterpretationHealth:
    return {
        "status": "structured" if source == "llm" else "fallback",
        "reason": reason,
        "source": "llm" if source == "llm" else "fallback",
        "symbolMentions": len(symbol_mentions),
        "figureMentions": len(figure_mentions),
        "motifMentions": len(motif_mentions),
        "observations": len(observations),
        "hypotheses": len(hypotheses),
        "proposalCandidates": len(proposal_candidates),
    }


def build_life_context_links_from_llm(
    *,
    input_data: MaterialInterpretationInput,
    material_id: str,
    llm_output: LlmInterpretationOutput,
    evidence_ledger: EvidenceLedger,
) -> tuple[list[LifeContextLink], dict[str, list[str]]]:
    if input_data.get("options", {}).get("allowLifeContextLinks") is False:
        return [], {}
    snapshot = input_data.get("lifeContextSnapshot")
    if not snapshot:
        return [], {}
    links: list[LifeContextLink] = []
    ref_map: dict[str, list[str]] = {}
    seen: set[str] = set()
    event_refs = {str(item["id"]): item for item in snapshot.get("lifeEventRefs", [])}
    for candidate in llm_output.get("lifeContextLinks", [])[:5]:
        ref_key = str(candidate.get("refKey") or "").strip()
        life_event_ref_id = str(candidate.get("lifeEventRefId") or "").strip()
        state_field = str(candidate.get("stateSnapshotField") or "").strip()
        if life_event_ref_id and life_event_ref_id in event_refs:
            if f"event:{life_event_ref_id}" in seen:
                continue
            event_ref = event_refs[life_event_ref_id]
            summary = str(
                event_ref.get("symbolicAnnotation") or event_ref.get("summary") or ""
            ).strip()
            if not summary:
                continue
            evidence_id = evidence_ledger.add(
                evidence_type="life_event_ref",
                source_id=life_event_ref_id,
                quote_or_summary=summary,
                privacy_class="approved_summary",
                reliability="medium",
            )
            links.append(
                {"lifeEventRefId": life_event_ref_id, "summary": summary, "evidenceId": evidence_id}
            )
            seen.add(f"event:{life_event_ref_id}")
            if ref_key:
                ref_map[ref_key] = [evidence_id]
            continue
        if state_field in {
            "focusSummary",
            "energySummary",
            "moodSummary",
            "mentalStateSummary",
            "habitSummary",
        }:
            value = snapshot.get(state_field)
            if not value or f"state:{state_field}" in seen:
                continue
            evidence_id = evidence_ledger.add(
                evidence_type="life_os_state_snapshot",
                source_id=material_id,
                quote_or_summary=str(value),
                privacy_class="approved_summary",
                reliability="medium",
            )
            links.append(
                {
                    "stateSnapshotField": state_field,
                    "summary": str(value),
                    "evidenceId": evidence_id,
                }
            )
            seen.add(f"state:{state_field}")
            if ref_key:
                ref_map[ref_key] = [evidence_id]
    return links, ref_map


def build_life_context_links(
    *,
    input_data: MaterialInterpretationInput,
    material_id: str,
    evidence_ledger: EvidenceLedger,
) -> list[LifeContextLink]:
    if input_data.get("options", {}).get("allowLifeContextLinks") is False:
        return []
    snapshot = input_data.get("lifeContextSnapshot")
    if not snapshot:
        return []
    links: list[LifeContextLink] = []
    for event_ref in snapshot.get("lifeEventRefs", [])[:3]:
        evidence_id = evidence_ledger.add(
            evidence_type="life_event_ref",
            source_id=event_ref["id"],
            quote_or_summary=event_ref.get("symbolicAnnotation", event_ref["summary"]),
            privacy_class="approved_summary",
            reliability="medium",
        )
        links.append(
            {
                "lifeEventRefId": event_ref["id"],
                "summary": event_ref.get("symbolicAnnotation", event_ref["summary"]),
                "evidenceId": evidence_id,
            }
        )
    for field in (
        "focusSummary",
        "energySummary",
        "moodSummary",
        "mentalStateSummary",
        "habitSummary",
    ):
        value = snapshot.get(field)
        if not value:
            continue
        evidence_id = evidence_ledger.add(
            evidence_type="life_os_state_snapshot",
            source_id=material_id,
            quote_or_summary=value,
            privacy_class="approved_summary",
            reliability="medium",
        )
        links.append({"stateSnapshotField": field, "summary": value, "evidenceId": evidence_id})
    return links


def build_symbol_mentions_from_llm(
    *,
    input_data: MaterialInterpretationInput,
    material_id: str,
    llm_output: LlmInterpretationOutput,
    evidence_ledger: EvidenceLedger,
) -> tuple[list[SymbolMention], dict[str, list[str]]]:
    mentions: list[SymbolMention] = []
    ref_map: dict[str, list[str]] = {}
    seen: set[tuple[str, str]] = set()
    for candidate in llm_output.get("symbolMentions", [])[:8]:
        surface_text = str(candidate.get("surfaceText") or "").strip()
        canonical_name = str(candidate.get("canonicalName") or "").strip().lower()
        if not surface_text or not canonical_name:
            continue
        key = (surface_text.lower(), canonical_name)
        if key in seen:
            continue
        seen.add(key)
        evidence_id = evidence_ledger.add(
            evidence_type="dream_text_span"
            if input_data["materialType"] == "dream"
            else "material_text_span",
            source_id=material_id,
            quote_or_summary=surface_text,
            privacy_class=input_data.get("privacyClass", "session_only"),
            reliability="medium",
        )
        mention: SymbolMention = {
            "id": create_id("symbol_mention"),
            "surfaceText": surface_text,
            "canonicalName": canonical_name,
            "category": sanitize_symbol_category(candidate.get("category")),
            "textSpan": locate_text_span(input_data["materialText"], surface_text),
            "salience": clamp_float(candidate.get("salience"), default=0.5),
            "evidenceId": evidence_id,
        }
        tone = str(candidate.get("tone") or "").strip()
        if tone:
            mention["tone"] = tone
        mentions.append(mention)
        ref_key = str(candidate.get("refKey") or canonical_name).strip()
        if ref_key:
            ref_map[ref_key] = [evidence_id]
    return mentions, ref_map


def build_figure_mentions_from_llm(
    *,
    input_data: MaterialInterpretationInput,
    material_id: str,
    llm_output: LlmInterpretationOutput,
    evidence_ledger: EvidenceLedger,
) -> tuple[list[FigureMention], dict[str, list[str]]]:
    mentions: list[FigureMention] = []
    ref_map: dict[str, list[str]] = {}
    seen: set[tuple[str, str]] = set()
    for candidate in llm_output.get("figureMentions", [])[:6]:
        surface_text = str(candidate.get("surfaceText") or "").strip()
        label = str(candidate.get("label") or "").strip()
        if not surface_text or not label:
            continue
        key = (surface_text.lower(), label.lower())
        if key in seen:
            continue
        seen.add(key)
        evidence_id = evidence_ledger.add(
            evidence_type="dream_text_span"
            if input_data["materialType"] == "dream"
            else "material_text_span",
            source_id=material_id,
            quote_or_summary=surface_text,
            privacy_class=input_data.get("privacyClass", "session_only"),
            reliability="medium",
        )
        mention: FigureMention = {
            "id": create_id("figure_mention"),
            "surfaceText": surface_text,
            "label": label,
            "role": sanitize_figure_role(candidate.get("role")),
            "textSpan": locate_text_span(input_data["materialText"], surface_text),
            "salience": clamp_float(candidate.get("salience"), default=0.5),
            "evidenceId": evidence_id,
        }
        mentions.append(mention)
        ref_key = str(candidate.get("refKey") or label.lower()).strip()
        if ref_key:
            ref_map[ref_key] = [evidence_id]
    return mentions, ref_map


def build_motif_mentions_from_llm(
    *,
    input_data: MaterialInterpretationInput,
    material_id: str,
    llm_output: LlmInterpretationOutput,
    evidence_ledger: EvidenceLedger,
) -> tuple[list[MotifMention], dict[str, list[str]]]:
    mentions: list[MotifMention] = []
    ref_map: dict[str, list[str]] = {}
    seen: set[tuple[str, str]] = set()
    for candidate in llm_output.get("motifMentions", [])[:6]:
        surface_text = str(candidate.get("surfaceText") or "").strip()
        canonical_name = str(candidate.get("canonicalName") or "").strip().lower()
        if not surface_text or not canonical_name:
            continue
        key = (surface_text.lower(), canonical_name)
        if key in seen:
            continue
        seen.add(key)
        evidence_id = evidence_ledger.add(
            evidence_type="dream_text_span"
            if input_data["materialType"] == "dream"
            else "material_text_span",
            source_id=material_id,
            quote_or_summary=surface_text,
            privacy_class=input_data.get("privacyClass", "session_only"),
            reliability="medium",
        )
        mention: MotifMention = {
            "id": create_id("motif_mention"),
            "surfaceText": surface_text,
            "canonicalName": canonical_name,
            "motifType": sanitize_motif_type(candidate.get("motifType")),
            "textSpan": locate_text_span(input_data["materialText"], surface_text),
            "salience": clamp_float(candidate.get("salience"), default=0.5),
            "evidenceId": evidence_id,
        }
        mentions.append(mention)
        ref_key = str(candidate.get("refKey") or canonical_name).strip()
        if ref_key:
            ref_map[ref_key] = [evidence_id]
    return mentions, ref_map


def build_observations_from_llm(
    *,
    llm_output: LlmInterpretationOutput,
    supporting_ref_map: dict[str, list[str]],
) -> list[Observation]:
    observations: list[Observation] = []
    for candidate in llm_output.get("observations", [])[:6]:
        statement = truncate_text(candidate.get("statement"), 280)
        evidence_ids = evidence_ids_for_refs(candidate.get("supportingRefs"), supporting_ref_map)
        if not statement or not evidence_ids:
            continue
        kind = str(candidate.get("kind") or "image").strip()
        if kind not in {
            "image",
            "figure",
            "tone",
            "structure",
            "recurrence",
            "life_context_link",
            "practice_outcome",
            "motif",
        }:
            kind = "image"
        observations.append(
            {
                "id": create_id("observation"),
                "kind": cast(object, kind),
                "statement": statement,
                "evidenceIds": evidence_ids,
            }
        )
    return observations


def build_hypotheses_from_llm(
    *,
    llm_output: LlmInterpretationOutput,
    memory: HermesMemoryContext,
    supporting_ref_map: dict[str, list[str]],
    max_hypotheses: int,
) -> list[Hypothesis]:
    hypotheses: list[Hypothesis] = []
    for candidate in llm_output.get("hypotheses", []):
        claim = truncate_text(candidate.get("claim"), 320)
        hypothesis_type = sanitize_hypothesis_type(candidate.get("hypothesisType"))
        if not claim or hypothesis_type is None:
            continue
        normalized_claim_key = normalize_claim_key(hypothesis_type, claim)
        if is_suppressed(normalized_claim_key, memory):
            continue
        evidence_ids = evidence_ids_for_refs(candidate.get("supportingRefs"), supporting_ref_map)
        if not evidence_ids:
            continue
        hypotheses.append(
            {
                "id": create_id("hypothesis"),
                "claim": claim,
                "hypothesisType": hypothesis_type,
                "confidence": sanitize_confidence(candidate.get("confidence")),
                "evidenceIds": evidence_ids,
                "counterevidenceIds": evidence_ids_for_refs(
                    candidate.get("counterRefs"), supporting_ref_map
                ),
                "userTestPrompt": truncate_text(candidate.get("userTestPrompt"), 220)
                or "What fits here, and what does not?",
                "phrasingPolicy": sanitize_phrasing_policy(candidate.get("phrasingPolicy")),
                "normalizedClaimKey": normalized_claim_key,
            }
        )
        if len(hypotheses) >= max_hypotheses:
            break
    return hypotheses


def build_proposals_from_llm(
    *,
    input_data: MaterialInterpretationInput,
    material_id: str,
    symbol_mentions: list[SymbolMention],
    life_context_links: list[LifeContextLink],
    llm_proposals: list[LlmProposalCandidate],
    supporting_ref_map: dict[str, list[str]],
    method_gate: MethodGateResult | None = None,
) -> tuple[
    list[MemoryWriteProposal], list[PersonalSymbolWritePayload], list[ComplexCandidateWritePayload]
]:
    life_event_refs = [
        link["lifeEventRefId"] for link in life_context_links if link.get("lifeEventRefId")
    ]
    proposals: list[MemoryWriteProposal] = []
    personal_updates: list[PersonalSymbolWritePayload] = []
    complex_updates: list[ComplexCandidateWritePayload] = []
    proposal_keys: set[tuple[str, str]] = set()
    for candidate in llm_proposals[:8]:
        action = str(candidate.get("action") or "").strip()
        payload = candidate.get("payload") if isinstance(candidate.get("payload"), dict) else {}
        reason = truncate_text(candidate.get("reason"), 220)
        evidence_ids = evidence_ids_for_refs(candidate.get("supportingRefs"), supporting_ref_map)
        if action == "upsert_personal_symbol":
            canonical_name = truncate_text(payload.get("canonicalName"), 80).lower()
            if not canonical_name or not evidence_ids:
                continue
            key = (action, canonical_name)
            if key in proposal_keys:
                continue
            proposal_keys.add(key)
            update: PersonalSymbolWritePayload = {
                "canonicalName": canonical_name,
                "category": sanitize_symbol_category(payload.get("category")),
                "sourceMaterialId": material_id,
                "linkedLifeEventRefs": list(life_event_refs),
            }
            aliases = [
                str(item).strip() for item in payload.get("aliases", []) if str(item).strip()
            ]
            if aliases:
                update["aliases"] = aliases[:6]
            tone = truncate_text(payload.get("tone"), 80)
            if tone:
                update["tone"] = tone
            personal_updates.append(update)
            proposals.append(
                {
                    "id": create_id("proposal"),
                    "action": "upsert_personal_symbol",
                    "entityType": "PersonalSymbol",
                    "payload": update,
                    "evidenceIds": evidence_ids,
                    "reason": reason or "Save this symbol only if the user explicitly approves it.",
                    "requiresUserApproval": True,
                    "status": "pending_user_approval",
                }
            )
        if action == "upsert_complex_candidate":
            formulation = truncate_text(payload.get("formulation"), 280)
            if not formulation or not evidence_ids:
                continue
            key = (action, formulation)
            if key in proposal_keys:
                continue
            proposal_keys.add(key)
            update = {
                "label": truncate_text(payload.get("label"), 120) or "Possible recurring tension",
                "formulation": formulation,
                "linkedSymbols": [item["canonicalName"] for item in symbol_mentions[:4]],
                "linkedLifeEventRefs": list(life_event_refs),
                "confidence": sanitize_confidence(payload.get("confidence")),
            }
            complex_updates.append(update)
            proposals.append(
                {
                    "id": create_id("proposal"),
                    "action": "upsert_complex_candidate",
                    "entityType": "ComplexCandidate",
                    "payload": update,
                    "evidenceIds": evidence_ids,
                    "reason": reason
                    or "Save this recurring tension only if the user explicitly approves it.",
                    "requiresUserApproval": True,
                    "status": "pending_user_approval",
                }
            )
        if action == "upsert_goal_tension":
            tension_summary = truncate_text(payload.get("tensionSummary"), 220)
            goal_ids = [str(item) for item in payload.get("goalIds", []) if str(item).strip()]
            if not tension_summary or not goal_ids or not evidence_ids:
                continue
            key = (action, "|".join(sorted(goal_ids)), tension_summary)
            if key in proposal_keys:
                continue
            proposal_keys.add(key)
            goal_tension: GoalTensionWritePayload = {
                "goalIds": goal_ids,
                "tensionSummary": tension_summary,
                "polarityLabels": [
                    str(item) for item in payload.get("polarityLabels", []) if str(item).strip()
                ][:4],
                "evidenceIds": list(evidence_ids),
                "status": str(payload.get("status") or "candidate"),
            }
            proposals.append(
                {
                    "id": create_id("proposal"),
                    "action": "upsert_goal_tension",
                    "entityType": "GoalTension",
                    "payload": goal_tension,
                    "evidenceIds": evidence_ids,
                    "reason": reason
                    or (
                        "Hold this goal tension as a user-approved formulation, "
                        "not an imposed meaning."
                    ),
                    "requiresUserApproval": True,
                    "status": "pending_user_approval",
                }
            )
        if action == "create_collective_amplification":
            blocked_moves = set(method_gate.get("blockedMoves", []) if method_gate else [])
            consent_status = {
                item["scope"]: item["status"]
                for item in input_data.get("methodContextSnapshot", {}).get(
                    "consentPreferences", []
                )
            }
            has_personal_ground = bool(input_data.get("userAssociations")) or bool(
                input_data.get("methodContextSnapshot", {}).get("personalAmplifications")
            )
            if not input_data.get("options", {}).get("allowCulturalAmplification", True):
                continue
            if "collective_amplification" in blocked_moves:
                continue
            if (
                not has_personal_ground
                and consent_status.get("collective_amplification") != "allow"
            ):
                continue
            amplification_text = truncate_text(
                payload.get("amplificationText") or payload.get("reference"), 280
            )
            canonical_name = truncate_text(payload.get("canonicalName"), 120)
            if not canonical_name or not amplification_text or not evidence_ids:
                continue
            key = (action, canonical_name, amplification_text)
            if key in proposal_keys:
                continue
            proposal_keys.add(key)
            collective: CollectiveAmplificationWritePayload = {
                "canonicalName": canonical_name,
                "amplificationText": amplification_text,
                "confidence": sanitize_confidence(payload.get("confidence")),
            }
            symbol_id = truncate_text(payload.get("symbolId"), 120)
            if symbol_id:
                collective["symbolId"] = symbol_id
            cultural_frame_id = truncate_text(payload.get("culturalFrameId"), 120)
            if cultural_frame_id:
                collective["culturalFrameId"] = cultural_frame_id
            lens_label = truncate_text(payload.get("lensLabel"), 120)
            if lens_label:
                collective["lensLabel"] = lens_label
            fit_reason = truncate_text(payload.get("fitReason"), 220)
            if fit_reason:
                collective["fitReason"] = fit_reason
            caveat = truncate_text(payload.get("caveat"), 180)
            if caveat:
                collective["caveat"] = caveat
            collective["reference"] = amplification_text
            proposals.append(
                {
                    "id": create_id("proposal"),
                    "action": "create_collective_amplification",
                    "entityType": "CollectiveAmplification",
                    "payload": collective,
                    "evidenceIds": evidence_ids,
                    "reason": reason
                    or "Offer this collective lens only if the user wants it remembered.",
                    "requiresUserApproval": True,
                    "status": "pending_user_approval",
                }
            )
    return proposals, personal_updates, complex_updates


def _consent_status_map(input_data: MaterialInterpretationInput) -> dict[str, str]:
    return {
        str(item["scope"]): str(item["status"])
        for item in input_data.get("methodContextSnapshot", {}).get("consentPreferences", [])
        if isinstance(item, dict) and item.get("scope") and item.get("status")
    }


def _sanitize_choice(value: object, *, allowed: set[str], default: str) -> str:
    candidate = str(value or "").strip()
    return candidate if candidate in allowed else default


def _string_list(values: object, *, limit: int = 6, item_limit: int = 160) -> list[str]:
    if not isinstance(values, list):
        return []
    result: list[str] = []
    for value in values:
        text = truncate_text(value, item_limit)
        if text and text not in result:
            result.append(text)
        if len(result) >= limit:
            break
    return result


def _role_summaries(values: object) -> list[dict[str, object]]:
    if not isinstance(values, list):
        return []
    result: list[dict[str, object]] = []
    for value in values[:5]:
        if not isinstance(value, dict):
            continue
        role_label = truncate_text(value.get("roleLabel"), 80)
        if not role_label:
            continue
        item: dict[str, object] = {"roleLabel": role_label}
        affect_tone = truncate_text(value.get("affectTone"), 80)
        ego_stance = truncate_text(value.get("egoStance"), 120)
        if affect_tone:
            item["affectTone"] = affect_tone
        if ego_stance:
            item["egoStance"] = ego_stance
        result.append(item)
    return result


def _proposal_reason(candidate: dict[str, object], default: str) -> str:
    return truncate_text(candidate.get("reason"), 220) or default


def _build_individuation_proposal(
    *,
    action: str,
    entity_type: str,
    payload: dict[str, object],
    evidence_ids: list[str],
    reason: str,
) -> MemoryWriteProposal:
    return {
        "id": create_id("proposal"),
        "action": cast(object, action),
        "entityType": cast(object, entity_type),
        "payload": payload,
        "evidenceIds": list(evidence_ids),
        "reason": reason,
        "requiresUserApproval": True,
        "status": "pending_user_approval",
    }


def build_individuation_from_llm(
    *,
    input_data: MaterialInterpretationInput,
    material_id: str,
    llm_output: LlmInterpretationOutput,
    supporting_ref_map: dict[str, list[str]],
) -> tuple[IndividuationAssessment | None, list[MemoryWriteProposal]]:
    individuation = llm_output.get("individuation")
    if not isinstance(individuation, dict):
        return None, []

    timestamp = now_iso()
    consent_status = _consent_status_map(input_data)
    related_material_ids = [material_id]
    proposals: list[MemoryWriteProposal] = []
    assessment: IndividuationAssessment = {
        "oppositions": [],
        "emergentThirdSignals": [],
        "thresholdProcesses": [],
        "relationalScenes": [],
        "projectionHypotheses": [],
        "innerOuterCorrespondences": [],
        "numinousEncounters": [],
        "aestheticResonances": [],
        "archetypalPatterns": [],
        "bridgeMoments": [],
        "withheldReasons": [],
    }

    for candidate in cast(list[object], individuation.get("realityAnchors", []))[:1]:
        if not isinstance(candidate, dict):
            continue
        evidence_ids = evidence_ids_for_refs(candidate.get("supportingRefs"), supporting_ref_map)
        if not evidence_ids:
            continue
        summary_text = truncate_text(candidate.get("summary"), 220) or truncate_text(
            candidate.get("anchorSummary"), 220
        )
        anchor_summary = truncate_text(candidate.get("anchorSummary"), 220) or summary_text
        if not summary_text or not anchor_summary:
            continue
        confidence = sanitize_confidence(candidate.get("confidence"))
        reasons = _string_list(candidate.get("reasons"), limit=4, item_limit=120)
        assessment["realityAnchors"] = {
            "id": create_id("reality_anchor_summary"),
            "label": truncate_text(candidate.get("label"), 120) or "Reality anchors",
            "summary": summary_text,
            "confidence": confidence,
            "evidenceIds": evidence_ids,
            "anchorSummary": anchor_summary,
            "workDailyLifeContinuity": _sanitize_choice(
                candidate.get("workDailyLifeContinuity"),
                allowed={"stable", "strained", "unknown"},
                default="unknown",
            ),
            "sleepBodyRegulation": _sanitize_choice(
                candidate.get("sleepBodyRegulation"),
                allowed={"stable", "strained", "unknown"},
                default="unknown",
            ),
            "relationshipContact": _sanitize_choice(
                candidate.get("relationshipContact"),
                allowed={"available", "thin", "unknown"},
                default="unknown",
            ),
            "reflectiveCapacity": _sanitize_choice(
                candidate.get("reflectiveCapacity"),
                allowed={"steady", "fragile", "unknown"},
                default="unknown",
            ),
            "groundingRecommendation": _sanitize_choice(
                candidate.get("groundingRecommendation"),
                allowed={"clear_for_depth", "pace_gently", "grounding_first"},
                default="pace_gently",
            ),
            "reasons": reasons,
            "status": "proposed",
            "updatedAt": timestamp,
        }
        proposals.append(
            _build_individuation_proposal(
                action="create_reality_anchor_summary",
                entity_type="RealityAnchorSummary",
                payload={
                    "anchorSummary": anchor_summary,
                    "workDailyLifeContinuity": assessment["realityAnchors"][
                        "workDailyLifeContinuity"
                    ],
                    "sleepBodyRegulation": assessment["realityAnchors"]["sleepBodyRegulation"],
                    "relationshipContact": assessment["realityAnchors"]["relationshipContact"],
                    "reflectiveCapacity": assessment["realityAnchors"]["reflectiveCapacity"],
                    "groundingRecommendation": assessment["realityAnchors"][
                        "groundingRecommendation"
                    ],
                    "reasons": reasons,
                    "relatedMaterialIds": related_material_ids,
                },
                evidence_ids=evidence_ids,
                reason=_proposal_reason(
                    candidate,
                    "Hold this grounding context only if the user wants it remembered.",
                ),
            )
        )
        break

    for candidate in cast(list[object], individuation.get("selfOrientationSnapshots", []))[:1]:
        if not isinstance(candidate, dict):
            continue
        evidence_ids = evidence_ids_for_refs(candidate.get("supportingRefs"), supporting_ref_map)
        if not evidence_ids:
            continue
        summary_text = truncate_text(candidate.get("summary"), 220) or truncate_text(
            candidate.get("orientationSummary"), 220
        )
        orientation_summary = (
            truncate_text(candidate.get("orientationSummary"), 220) or summary_text
        )
        emergent_direction = truncate_text(candidate.get("emergentDirection"), 180)
        if not summary_text or not orientation_summary or not emergent_direction:
            continue
        confidence = sanitize_confidence(candidate.get("confidence"))
        movement_language = _string_list(candidate.get("movementLanguage"), limit=5, item_limit=80)
        assessment["selfOrientation"] = {
            "id": create_id("self_orientation_snapshot"),
            "label": truncate_text(candidate.get("label"), 120) or "Self orientation",
            "summary": summary_text,
            "confidence": confidence,
            "evidenceIds": evidence_ids,
            "orientationSummary": orientation_summary,
            "emergentDirection": emergent_direction,
            "egoRelation": _sanitize_choice(
                candidate.get("egoRelation"),
                allowed={"aligned", "conflicted", "avoidant", "curious", "unknown"},
                default="unknown",
            ),
            "movementLanguage": movement_language,
            "notMetaphysicalClaim": True,
            "status": "proposed",
            "updatedAt": timestamp,
        }
        proposals.append(
            _build_individuation_proposal(
                action="create_self_orientation_snapshot",
                entity_type="SelfOrientationSnapshot",
                payload={
                    "orientationSummary": orientation_summary,
                    "emergentDirection": emergent_direction,
                    "egoRelation": assessment["selfOrientation"]["egoRelation"],
                    "movementLanguage": movement_language,
                    "relatedMaterialIds": related_material_ids,
                },
                evidence_ids=evidence_ids,
                reason=_proposal_reason(
                    candidate,
                    "Hold this orientation snapshot only if the user wants it remembered.",
                ),
            )
        )
        break

    for candidate in cast(list[object], individuation.get("psychicOppositions", []))[:5]:
        if not isinstance(candidate, dict):
            continue
        evidence_ids = evidence_ids_for_refs(candidate.get("supportingRefs"), supporting_ref_map)
        pole_a = truncate_text(candidate.get("poleA"), 120)
        pole_b = truncate_text(candidate.get("poleB"), 120)
        opposition_summary = truncate_text(candidate.get("oppositionSummary"), 220)
        holding_pattern = truncate_text(candidate.get("currentHoldingPattern"), 180)
        normalized_key = truncate_text(candidate.get("normalizedOppositionKey"), 120)
        if (
            not evidence_ids
            or not pole_a
            or not pole_b
            or not opposition_summary
            or not holding_pattern
        ):
            continue
        if not normalized_key:
            continue
        confidence = sanitize_confidence(candidate.get("confidence"))
        item = {
            "id": create_id("psychic_opposition"),
            "label": truncate_text(candidate.get("label"), 120) or f"{pole_a} / {pole_b}",
            "summary": truncate_text(candidate.get("summary"), 220) or opposition_summary,
            "confidence": confidence,
            "evidenceIds": evidence_ids,
            "poleA": pole_a,
            "poleB": pole_b,
            "oppositionSummary": opposition_summary,
            "currentHoldingPattern": holding_pattern,
            "normalizedOppositionKey": normalized_key,
            "status": "proposed",
            "updatedAt": timestamp,
        }
        pressure_tone = truncate_text(candidate.get("pressureTone"), 120)
        holding_instruction = truncate_text(candidate.get("holdingInstruction"), 180)
        if pressure_tone:
            item["pressureTone"] = pressure_tone
        if holding_instruction:
            item["holdingInstruction"] = holding_instruction
        assessment["oppositions"].append(item)
        payload = {
            "poleA": pole_a,
            "poleB": pole_b,
            "oppositionSummary": opposition_summary,
            "currentHoldingPattern": holding_pattern,
            "normalizedOppositionKey": normalized_key,
            "relatedMaterialIds": related_material_ids,
        }
        if pressure_tone:
            payload["pressureTone"] = pressure_tone
        if holding_instruction:
            payload["holdingInstruction"] = holding_instruction
        proposals.append(
            _build_individuation_proposal(
                action="upsert_psychic_opposition",
                entity_type="PsychicOpposition",
                payload=payload,
                evidence_ids=evidence_ids,
                reason=_proposal_reason(
                    candidate,
                    "Hold this opposition only if the user wants it remembered.",
                ),
            )
        )

    for candidate in cast(list[object], individuation.get("emergentThirdSignals", []))[:5]:
        if not isinstance(candidate, dict):
            continue
        evidence_ids = evidence_ids_for_refs(candidate.get("supportingRefs"), supporting_ref_map)
        signal_summary = truncate_text(candidate.get("signalSummary"), 220)
        if not evidence_ids or not signal_summary:
            continue
        signal_type = _sanitize_choice(
            candidate.get("signalType"),
            allowed={
                "symbol",
                "attitude",
                "practice",
                "relationship_move",
                "dream_lysis",
                "body_shift",
                "unknown",
            },
            default="unknown",
        )
        item = {
            "id": create_id("emergent_third_signal"),
            "label": truncate_text(candidate.get("label"), 120) or "Emergent third signal",
            "summary": truncate_text(candidate.get("summary"), 220) or signal_summary,
            "confidence": sanitize_confidence(candidate.get("confidence")),
            "evidenceIds": evidence_ids,
            "signalType": signal_type,
            "signalSummary": signal_summary,
            "oppositionIds": _string_list(candidate.get("oppositionIds"), limit=6, item_limit=80),
            "novelty": _sanitize_choice(
                candidate.get("novelty"),
                allowed={"new", "returning", "unclear"},
                default="unclear",
            ),
            "status": "proposed",
            "updatedAt": timestamp,
        }
        assessment["emergentThirdSignals"].append(item)
        proposals.append(
            _build_individuation_proposal(
                action="create_emergent_third_signal",
                entity_type="EmergentThirdSignal",
                payload={
                    "signalType": signal_type,
                    "signalSummary": signal_summary,
                    "oppositionIds": list(item["oppositionIds"]),
                    "novelty": item["novelty"],
                    "relatedMaterialIds": related_material_ids,
                },
                evidence_ids=evidence_ids,
                reason=_proposal_reason(
                    candidate,
                    "Hold this emergent signal only if the user wants it remembered.",
                ),
            )
        )

    for candidate in cast(list[object], individuation.get("bridgeMoments", []))[:5]:
        if not isinstance(candidate, dict):
            continue
        evidence_ids = evidence_ids_for_refs(candidate.get("supportingRefs"), supporting_ref_map)
        bridge_summary = truncate_text(candidate.get("bridgeSummary"), 220)
        if not evidence_ids or not bridge_summary:
            continue
        bridge_type = _sanitize_choice(
            candidate.get("bridgeType"),
            allowed={
                "dream_to_waking",
                "body_to_symbol",
                "practice_to_dream",
                "relationship_to_dream",
                "aesthetic_to_symbol",
                "unknown",
            },
            default="unknown",
        )
        item = {
            "id": create_id("bridge_moment"),
            "label": truncate_text(candidate.get("label"), 120) or "Bridge moment",
            "summary": truncate_text(candidate.get("summary"), 220) or bridge_summary,
            "confidence": sanitize_confidence(candidate.get("confidence")),
            "evidenceIds": evidence_ids,
            "bridgeType": bridge_type,
            "bridgeSummary": bridge_summary,
            "status": "proposed",
            "updatedAt": timestamp,
        }
        before_after = truncate_text(candidate.get("beforeAfter"), 180)
        if before_after:
            item["beforeAfter"] = before_after
        assessment["bridgeMoments"].append(item)
        payload = {
            "bridgeType": bridge_type,
            "bridgeSummary": bridge_summary,
            "relatedMaterialIds": related_material_ids,
        }
        if before_after:
            payload["beforeAfter"] = before_after
        proposals.append(
            _build_individuation_proposal(
                action="create_bridge_moment",
                entity_type="BridgeMoment",
                payload=payload,
                evidence_ids=evidence_ids,
                reason=_proposal_reason(
                    candidate,
                    "Hold this bridge moment only if the user wants it remembered.",
                ),
            )
        )

    for candidate in cast(list[object], individuation.get("numinousEncounters", []))[:5]:
        if not isinstance(candidate, dict):
            continue
        evidence_ids = evidence_ids_for_refs(candidate.get("supportingRefs"), supporting_ref_map)
        interpretation_constraint = truncate_text(candidate.get("interpretationConstraint"), 220)
        affect_tone = truncate_text(candidate.get("affectTone"), 120)
        if not evidence_ids or not interpretation_constraint or not affect_tone:
            continue
        encounter_medium = _sanitize_choice(
            candidate.get("encounterMedium"),
            allowed={"dream", "waking_event", "body", "art", "place", "conversation", "unknown"},
            default="unknown",
        )
        containment_need = _sanitize_choice(
            candidate.get("containmentNeed"),
            allowed={"ordinary_reflection", "pace_gently", "grounding_first"},
            default="ordinary_reflection",
        )
        item = {
            "id": create_id("numinous_encounter"),
            "label": truncate_text(candidate.get("label"), 120) or "Numinous encounter",
            "summary": truncate_text(candidate.get("summary"), 220) or interpretation_constraint,
            "confidence": sanitize_confidence(candidate.get("confidence")),
            "evidenceIds": evidence_ids,
            "encounterMedium": encounter_medium,
            "affectTone": affect_tone,
            "containmentNeed": containment_need,
            "interpretationConstraint": interpretation_constraint,
            "status": "proposed",
            "updatedAt": timestamp,
        }
        assessment["numinousEncounters"].append(item)
        proposals.append(
            _build_individuation_proposal(
                action="create_numinous_encounter",
                entity_type="NuminousEncounter",
                payload={
                    "encounterMedium": encounter_medium,
                    "affectTone": affect_tone,
                    "containmentNeed": containment_need,
                    "interpretationConstraint": interpretation_constraint,
                    "relatedMaterialIds": related_material_ids,
                },
                evidence_ids=evidence_ids,
                reason=_proposal_reason(
                    candidate,
                    "Hold this encounter only if the user wants it remembered.",
                ),
            )
        )

    for candidate in cast(list[object], individuation.get("aestheticResonances", []))[:5]:
        if not isinstance(candidate, dict):
            continue
        evidence_ids = evidence_ids_for_refs(candidate.get("supportingRefs"), supporting_ref_map)
        medium = truncate_text(candidate.get("medium"), 80)
        object_description = truncate_text(candidate.get("objectDescription"), 180)
        resonance_summary = truncate_text(candidate.get("resonanceSummary"), 220)
        if not evidence_ids or not medium or not object_description or not resonance_summary:
            continue
        item = {
            "id": create_id("aesthetic_resonance"),
            "label": truncate_text(candidate.get("label"), 120) or "Aesthetic resonance",
            "summary": truncate_text(candidate.get("summary"), 220) or resonance_summary,
            "confidence": sanitize_confidence(candidate.get("confidence")),
            "evidenceIds": evidence_ids,
            "medium": medium,
            "objectDescription": object_description,
            "resonanceSummary": resonance_summary,
            "bodySensations": _string_list(candidate.get("bodySensations"), limit=5, item_limit=80),
            "status": "proposed",
            "updatedAt": timestamp,
        }
        feeling_tone = truncate_text(candidate.get("feelingTone"), 120)
        if feeling_tone:
            item["feelingTone"] = feeling_tone
        assessment["aestheticResonances"].append(item)
        payload = {
            "medium": medium,
            "objectDescription": object_description,
            "resonanceSummary": resonance_summary,
            "bodySensations": list(item["bodySensations"]),
            "relatedMaterialIds": related_material_ids,
        }
        if feeling_tone:
            payload["feelingTone"] = feeling_tone
        proposals.append(
            _build_individuation_proposal(
                action="create_aesthetic_resonance",
                entity_type="AestheticResonance",
                payload=payload,
                evidence_ids=evidence_ids,
                reason=_proposal_reason(
                    candidate,
                    "Hold this resonance only if the user wants it remembered.",
                ),
            )
        )

    for candidate in cast(list[object], individuation.get("thresholdProcesses", []))[:5]:
        if not isinstance(candidate, dict):
            continue
        evidence_ids = evidence_ids_for_refs(candidate.get("supportingRefs"), supporting_ref_map)
        threshold_name = truncate_text(candidate.get("thresholdName"), 120)
        what_is_ending = truncate_text(candidate.get("whatIsEnding"), 220)
        not_yet_begun = truncate_text(candidate.get("notYetBegun"), 220)
        normalized_key = truncate_text(candidate.get("normalizedThresholdKey"), 120)
        if not evidence_ids or not threshold_name or not what_is_ending or not not_yet_begun:
            continue
        if not normalized_key:
            continue
        phase = _sanitize_choice(
            candidate.get("phase"),
            allowed={"ending", "liminal", "reorientation", "return", "unknown"},
            default="unknown",
        )
        grounding_status = _sanitize_choice(
            candidate.get("groundingStatus"),
            allowed={"steady", "strained", "unknown"},
            default="unknown",
        )
        invitation_readiness = _sanitize_choice(
            candidate.get("invitationReadiness"),
            allowed={"not_now", "ask", "ready"},
            default="ask",
        )
        item = {
            "id": create_id("threshold_process"),
            "label": truncate_text(candidate.get("label"), 120) or threshold_name,
            "summary": truncate_text(candidate.get("summary"), 220) or what_is_ending,
            "confidence": sanitize_confidence(candidate.get("confidence")),
            "evidenceIds": evidence_ids,
            "thresholdName": threshold_name,
            "phase": phase,
            "whatIsEnding": what_is_ending,
            "notYetBegun": not_yet_begun,
            "groundingStatus": grounding_status,
            "invitationReadiness": invitation_readiness,
            "normalizedThresholdKey": normalized_key,
            "status": "proposed",
            "updatedAt": timestamp,
        }
        body_carrying = truncate_text(candidate.get("bodyCarrying"), 180)
        symbolic_lens = truncate_text(candidate.get("symbolicLens"), 180)
        if body_carrying:
            item["bodyCarrying"] = body_carrying
        if symbolic_lens:
            item["symbolicLens"] = symbolic_lens
        assessment["thresholdProcesses"].append(item)
        payload = {
            "thresholdName": threshold_name,
            "phase": phase,
            "whatIsEnding": what_is_ending,
            "notYetBegun": not_yet_begun,
            "groundingStatus": grounding_status,
            "invitationReadiness": invitation_readiness,
            "normalizedThresholdKey": normalized_key,
            "relatedMaterialIds": related_material_ids,
        }
        if body_carrying:
            payload["bodyCarrying"] = body_carrying
        if symbolic_lens:
            payload["symbolicLens"] = symbolic_lens
        proposals.append(
            _build_individuation_proposal(
                action="upsert_threshold_process",
                entity_type="ThresholdProcess",
                payload=payload,
                evidence_ids=evidence_ids,
                reason=_proposal_reason(
                    candidate,
                    "Hold this threshold process only if the user wants it remembered.",
                ),
            )
        )

    for candidate in cast(list[object], individuation.get("relationalScenes", []))[:5]:
        if not isinstance(candidate, dict):
            continue
        evidence_ids = evidence_ids_for_refs(candidate.get("supportingRefs"), supporting_ref_map)
        scene_summary = truncate_text(candidate.get("sceneSummary"), 220)
        normalized_key = truncate_text(candidate.get("normalizedSceneKey"), 120)
        charged_roles = _role_summaries(candidate.get("chargedRoles"))
        if not evidence_ids or not scene_summary or not normalized_key or not charged_roles:
            continue
        item = {
            "id": create_id("relational_scene"),
            "label": truncate_text(candidate.get("label"), 120) or "Relational scene",
            "summary": truncate_text(candidate.get("summary"), 220) or scene_summary,
            "confidence": sanitize_confidence(candidate.get("confidence")),
            "evidenceIds": evidence_ids,
            "sceneSummary": scene_summary,
            "chargedRoles": charged_roles,
            "recurringAffect": _string_list(
                candidate.get("recurringAffect"), limit=5, item_limit=80
            ),
            "recurrenceContexts": _string_list(
                candidate.get("recurrenceContexts"), limit=5, item_limit=80
            ),
            "normalizedSceneKey": normalized_key,
            "status": "proposed",
            "updatedAt": timestamp,
        }
        assessment["relationalScenes"].append(item)
        proposals.append(
            _build_individuation_proposal(
                action="upsert_relational_scene",
                entity_type="RelationalScene",
                payload={
                    "sceneSummary": scene_summary,
                    "chargedRoles": charged_roles,
                    "recurringAffect": list(item["recurringAffect"]),
                    "recurrenceContexts": list(item["recurrenceContexts"]),
                    "normalizedSceneKey": normalized_key,
                    "relatedMaterialIds": related_material_ids,
                },
                evidence_ids=evidence_ids,
                reason=_proposal_reason(
                    candidate,
                    "Hold this relational scene only if the user wants it remembered.",
                ),
            )
        )

    projection_candidates = cast(list[object], individuation.get("projectionHypotheses", []))
    if projection_candidates and consent_status.get("projection_language") != "allow":
        assessment["withheldReasons"].append("projection_language_withheld_by_consent")
    for candidate in projection_candidates[:5]:
        if consent_status.get("projection_language") != "allow":
            break
        if not isinstance(candidate, dict):
            continue
        evidence_ids = evidence_ids_for_refs(candidate.get("supportingRefs"), supporting_ref_map)
        summary_text = truncate_text(candidate.get("hypothesisSummary"), 220)
        projection_pattern = truncate_text(candidate.get("projectionPattern"), 220)
        user_test_prompt = truncate_text(candidate.get("userTestPrompt"), 220)
        normalized_key = truncate_text(candidate.get("normalizedHypothesisKey"), 120)
        if not evidence_ids or not summary_text or not projection_pattern or not user_test_prompt:
            continue
        if not normalized_key:
            continue
        confidence = sanitize_confidence(candidate.get("confidence"))
        if confidence == "high":
            confidence = "medium"
        counterevidence_ids = evidence_ids_for_refs(
            candidate.get("counterRefs"), supporting_ref_map
        )
        item = {
            "id": create_id("projection_hypothesis"),
            "label": truncate_text(candidate.get("label"), 120) or "Projection hypothesis",
            "summary": truncate_text(candidate.get("summary"), 220) or summary_text,
            "confidence": confidence,
            "evidenceIds": evidence_ids,
            "hypothesisSummary": summary_text,
            "projectionPattern": projection_pattern,
            "userTestPrompt": user_test_prompt,
            "counterevidenceIds": counterevidence_ids,
            "phrasingPolicy": "very_tentative",
            "consentScope": "projection_language",
            "normalizedHypothesisKey": normalized_key,
            "status": "proposed",
            "updatedAt": timestamp,
        }
        relational_scene_id = truncate_text(candidate.get("relationalSceneId"), 120)
        if relational_scene_id:
            item["relationalSceneId"] = relational_scene_id
        assessment["projectionHypotheses"].append(item)
        payload = {
            "hypothesisSummary": summary_text,
            "projectionPattern": projection_pattern,
            "userTestPrompt": user_test_prompt,
            "counterevidenceIds": counterevidence_ids,
            "normalizedHypothesisKey": normalized_key,
            "relatedMaterialIds": related_material_ids,
        }
        if relational_scene_id:
            payload["relationalSceneId"] = relational_scene_id
        proposals.append(
            _build_individuation_proposal(
                action="upsert_projection_hypothesis",
                entity_type="ProjectionHypothesis",
                payload=payload,
                evidence_ids=evidence_ids,
                reason=_proposal_reason(
                    candidate,
                    "Hold this hypothesis only with explicit projection-language consent.",
                ),
            )
        )

    correspondence_candidates = cast(
        list[object], individuation.get("innerOuterCorrespondences", [])
    )
    if correspondence_candidates and consent_status.get("inner_outer_correspondence") != "allow":
        assessment["withheldReasons"].append("inner_outer_correspondence_withheld_by_consent")
    for candidate in correspondence_candidates[:5]:
        if consent_status.get("inner_outer_correspondence") != "allow":
            break
        if not isinstance(candidate, dict):
            continue
        evidence_ids = evidence_ids_for_refs(candidate.get("supportingRefs"), supporting_ref_map)
        summary_text = truncate_text(candidate.get("correspondenceSummary"), 220)
        normalized_key = truncate_text(candidate.get("normalizedCorrespondenceKey"), 120)
        caveat = truncate_text(candidate.get("caveat"), 180)
        inner_refs = _string_list(candidate.get("innerRefs"), limit=8, item_limit=80)
        outer_refs = _string_list(candidate.get("outerRefs"), limit=8, item_limit=80)
        symbol_ids = _string_list(candidate.get("symbolIds"), limit=8, item_limit=80)
        if not evidence_ids or not summary_text or not caveat:
            continue
        if not normalized_key or not inner_refs or not outer_refs:
            continue
        confidence = sanitize_confidence(candidate.get("confidence"))
        if confidence == "high":
            confidence = "medium"
        item = {
            "id": create_id("inner_outer_correspondence"),
            "label": truncate_text(candidate.get("label"), 120) or "Inner-outer correspondence",
            "summary": truncate_text(candidate.get("summary"), 220) or summary_text,
            "confidence": confidence,
            "evidenceIds": evidence_ids,
            "correspondenceSummary": summary_text,
            "innerRefs": inner_refs,
            "outerRefs": outer_refs,
            "symbolIds": symbol_ids,
            "userCharge": _sanitize_choice(
                candidate.get("userCharge"),
                allowed={"explicitly_charged", "implicitly_charged", "unclear"},
                default="unclear",
            ),
            "caveat": caveat,
            "causalityPolicy": "no_causal_claim",
            "normalizedCorrespondenceKey": normalized_key,
            "status": "proposed",
            "updatedAt": timestamp,
        }
        time_window_start = truncate_text(candidate.get("timeWindowStart"), 40)
        time_window_end = truncate_text(candidate.get("timeWindowEnd"), 40)
        if time_window_start:
            item["timeWindowStart"] = time_window_start
        if time_window_end:
            item["timeWindowEnd"] = time_window_end
        assessment["innerOuterCorrespondences"].append(item)
        payload = {
            "correspondenceSummary": summary_text,
            "innerRefs": inner_refs,
            "outerRefs": outer_refs,
            "symbolIds": symbol_ids,
            "userCharge": item["userCharge"],
            "caveat": caveat,
            "normalizedCorrespondenceKey": normalized_key,
            "relatedMaterialIds": related_material_ids,
        }
        if time_window_start:
            payload["timeWindowStart"] = time_window_start
        if time_window_end:
            payload["timeWindowEnd"] = time_window_end
        proposals.append(
            _build_individuation_proposal(
                action="upsert_inner_outer_correspondence",
                entity_type="InnerOuterCorrespondence",
                payload=payload,
                evidence_ids=evidence_ids,
                reason=_proposal_reason(
                    candidate,
                    "Hold this correspondence only with explicit correspondence consent.",
                ),
            )
        )

    archetypal_candidates = cast(list[object], individuation.get("archetypalPatterns", []))
    if archetypal_candidates and consent_status.get("archetypal_patterning") != "allow":
        assessment["withheldReasons"].append("archetypal_patterning_withheld_by_consent")
    for candidate in archetypal_candidates[:5]:
        if consent_status.get("archetypal_patterning") != "allow":
            break
        if not isinstance(candidate, dict):
            continue
        evidence_ids = evidence_ids_for_refs(candidate.get("supportingRefs"), supporting_ref_map)
        resonance_summary = truncate_text(candidate.get("resonanceSummary"), 220)
        caveat = truncate_text(candidate.get("caveat"), 180)
        if not evidence_ids or not resonance_summary or not caveat:
            continue
        confidence = sanitize_confidence(candidate.get("confidence"))
        if confidence == "high":
            confidence = "medium"
        counterevidence_ids = evidence_ids_for_refs(
            candidate.get("counterRefs"), supporting_ref_map
        )
        pattern_family = _sanitize_choice(
            candidate.get("patternFamily"),
            allowed={
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
            },
            default="unknown",
        )
        item = {
            "id": create_id("archetypal_pattern"),
            "label": truncate_text(candidate.get("label"), 120) or "Archetypal pattern",
            "summary": truncate_text(candidate.get("summary"), 220) or resonance_summary,
            "confidence": confidence,
            "evidenceIds": evidence_ids,
            "patternFamily": pattern_family,
            "resonanceSummary": resonance_summary,
            "caveat": caveat,
            "counterevidenceIds": counterevidence_ids,
            "phrasingPolicy": "very_tentative",
            "status": "proposed",
            "updatedAt": timestamp,
        }
        assessment["archetypalPatterns"].append(item)
        proposals.append(
            _build_individuation_proposal(
                action="upsert_archetypal_pattern",
                entity_type="ArchetypalPattern",
                payload={
                    "patternFamily": pattern_family,
                    "resonanceSummary": resonance_summary,
                    "caveat": caveat,
                    "counterevidenceIds": counterevidence_ids,
                    "relatedMaterialIds": related_material_ids,
                },
                evidence_ids=evidence_ids,
                reason=_proposal_reason(
                    candidate,
                    "Hold this pattern only with explicit archetypal-patterning consent.",
                ),
            )
        )

    has_content = any(
        [
            assessment.get("realityAnchors"),
            assessment.get("selfOrientation"),
            assessment["oppositions"],
            assessment["emergentThirdSignals"],
            assessment["thresholdProcesses"],
            assessment["relationalScenes"],
            assessment["projectionHypotheses"],
            assessment["innerOuterCorrespondences"],
            assessment["numinousEncounters"],
            assessment["aestheticResonances"],
            assessment["archetypalPatterns"],
            assessment["bridgeMoments"],
            assessment["withheldReasons"],
        ]
    )
    return (assessment if has_content else None), proposals


def build_practice_from_llm(candidate: LlmPracticeCandidate | object) -> dict[str, object] | None:
    if not isinstance(candidate, dict):
        return None
    instructions = [
        str(item).strip() for item in candidate.get("instructions", []) if str(item).strip()
    ]
    if not instructions:
        return None
    result: dict[str, object] = {
        "id": create_id("practice"),
        "type": sanitize_practice_type(candidate.get("type")),
        "reason": truncate_text(candidate.get("reason"), 220)
        or "Stay close to the material without forcing it.",
        "contraindicationsChecked": ["none"],
        "durationMinutes": sanitize_duration(candidate.get("durationMinutes")),
        "requiresConsent": bool(candidate.get("requiresConsent", False)),
        "instructions": instructions[:6],
    }
    target = truncate_text(candidate.get("target"), 120)
    if target:
        result["target"] = target
    for key in ("templateId", "modality", "intensity", "followUpPrompt"):
        value = candidate.get(key)
        if value:
            result[key] = value
    if isinstance(candidate.get("adaptationNotes"), list):
        result["adaptationNotes"] = [
            str(item) for item in candidate.get("adaptationNotes", []) if str(item).strip()
        ][:5]
    if isinstance(candidate.get("script"), list):
        result["script"] = [
            dict(item) for item in candidate.get("script", []) if isinstance(item, dict)
        ][:6]
    return result


def build_depth_readiness_from_llm(candidate: object) -> DepthReadinessAssessment | None:
    if not isinstance(candidate, dict):
        return None
    status = str(candidate.get("status") or "").strip()
    if status not in {"grounding_only", "limited", "ready"}:
        return None
    allowed_moves = (
        candidate.get("allowedMoves") if isinstance(candidate.get("allowedMoves"), dict) else {}
    )
    reasons = (
        [str(item) for item in candidate.get("reasons", []) if str(item).strip()]
        if isinstance(candidate.get("reasons"), list)
        else []
    )
    result: DepthReadinessAssessment = {
        "status": cast(object, status),
        "allowedMoves": {str(key): str(value) for key, value in allowed_moves.items()},
        "reasons": reasons,
        "evidenceIds": [],
    }
    required_user_action = truncate_text(candidate.get("requiredUserAction"), 120)
    if required_user_action:
        result["requiredUserAction"] = required_user_action
    return result


def build_method_gate_from_llm(candidate: object) -> MethodGateResult | None:
    if not isinstance(candidate, dict):
        return None
    depth_level = str(candidate.get("depthLevel") or "").strip()
    if depth_level not in {
        "grounding_only",
        "observations_only",
        "personal_amplification_needed",
        "cautious_pattern_note",
        "depth_interpretation_allowed",
    }:
        return None
    return {
        "depthLevel": cast(object, depth_level),
        "missingPrerequisites": [
            str(item) for item in candidate.get("missingPrerequisites", []) if str(item).strip()
        ],
        "blockedMoves": [
            str(item) for item in candidate.get("blockedMoves", []) if str(item).strip()
        ],
        "requiredPrompts": [
            str(item) for item in candidate.get("requiredPrompts", []) if str(item).strip()
        ],
        "responseConstraints": [
            str(item) for item in candidate.get("responseConstraints", []) if str(item).strip()
        ],
    }


def build_amplification_prompts_from_llm(
    candidates: object,
    *,
    symbol_ref_map: dict[str, list[str]],
    symbol_mentions: list[SymbolMention],
) -> list[AmplificationPromptSummary]:
    if not isinstance(candidates, list):
        return []
    prompts: list[AmplificationPromptSummary] = []
    timestamp = now_iso()
    mentions_by_evidence_id = {item["evidenceId"]: item for item in symbol_mentions}
    for candidate in candidates[:5]:
        if not isinstance(candidate, dict):
            continue
        canonical_name = truncate_text(candidate.get("canonicalName"), 120)
        surface_text = truncate_text(candidate.get("surfaceText"), 120)
        prompt_text = truncate_text(candidate.get("promptText"), 220)
        reason = truncate_text(candidate.get("reason"), 180)
        if not canonical_name or not surface_text or not prompt_text or not reason:
            continue
        prompt: AmplificationPromptSummary = {
            "id": create_id("amplification_prompt"),
            "canonicalName": canonical_name,
            "surfaceText": surface_text,
            "promptText": prompt_text,
            "reason": reason,
            "status": "pending",
            "createdAt": timestamp,
        }
        symbol_ref_key = truncate_text(candidate.get("symbolRefKey"), 120)
        if symbol_ref_key:
            prompt["symbolRefKey"] = symbol_ref_key
        mention_ref_key = truncate_text(candidate.get("symbolMentionRefKey"), 120)
        resolved_ref_key = mention_ref_key or symbol_ref_key
        if resolved_ref_key:
            evidence_ids = symbol_ref_map.get(resolved_ref_key, [])
            for evidence_id in evidence_ids:
                mention = mentions_by_evidence_id.get(evidence_id)
                if mention is not None:
                    prompt["symbolMentionId"] = mention["id"]
                    break
        prompts.append(prompt)
    return prompts


def build_dream_series_suggestions_from_llm(
    candidates: object,
    supporting_ref_map: dict[str, list[str]],
) -> list[DreamSeriesSuggestion]:
    if not isinstance(candidates, list):
        return []
    suggestions: list[DreamSeriesSuggestion] = []
    for candidate in candidates[:3]:
        if not isinstance(candidate, dict):
            continue
        label = truncate_text(candidate.get("label"), 160)
        role = truncate_text(candidate.get("narrativeRole"), 80)
        confidence = sanitize_confidence(candidate.get("confidence"))
        match_score = candidate.get("matchScore")
        if not label or not role or not isinstance(match_score, (int, float)):
            continue
        suggestion: DreamSeriesSuggestion = {
            "label": label,
            "matchScore": round(float(match_score), 2),
            "matchingFeatures": [
                str(item) for item in candidate.get("matchingFeatures", []) if str(item).strip()
            ],
            "narrativeRole": role,
            "confidence": confidence,
            "evidenceIds": evidence_ids_for_refs(
                candidate.get("supportingRefs"), supporting_ref_map
            ),
        }
        series_id = truncate_text(candidate.get("seriesId"), 120)
        if series_id:
            suggestion["seriesId"] = series_id
        ambiguity_note = truncate_text(candidate.get("ambiguityNote"), 180)
        if ambiguity_note:
            suggestion["ambiguityNote"] = ambiguity_note
        ego_stance = truncate_text(candidate.get("egoStance"), 120)
        if ego_stance:
            suggestion["egoStance"] = ego_stance
        lysis_summary = truncate_text(candidate.get("lysisSummary"), 180)
        if lysis_summary:
            suggestion["lysisSummary"] = lysis_summary
        progression_summary = truncate_text(candidate.get("progressionSummary"), 220)
        if progression_summary:
            suggestion["progressionSummary"] = progression_summary
        compensation_trajectory = truncate_text(candidate.get("compensationTrajectory"), 180)
        if compensation_trajectory:
            suggestion["compensationTrajectory"] = compensation_trajectory
        suggestions.append(suggestion)
    return suggestions


def build_dream_series_proposals(
    *,
    material_id: str,
    suggestions: list[DreamSeriesSuggestion],
    symbol_mentions: list[SymbolMention],
    motif_mentions: list[MotifMention],
) -> list[MemoryWriteProposal]:
    proposals: list[MemoryWriteProposal] = []
    seen: set[tuple[str, str]] = set()
    symbol_ids = [item["symbolId"] for item in symbol_mentions if item.get("symbolId")]
    motif_keys = [item["canonicalName"] for item in motif_mentions]
    for suggestion in suggestions:
        evidence_ids = list(suggestion.get("evidenceIds", []))
        if not evidence_ids:
            continue
        series_id = suggestion.get("seriesId")
        if series_id:
            if any(
                suggestion.get(field)
                for field in (
                    "progressionSummary",
                    "egoStance",
                    "lysisSummary",
                    "compensationTrajectory",
                )
            ):
                key = ("update", series_id)
                if key not in seen:
                    seen.add(key)
                    update_payload: DreamSeriesLinkWritePayload = {
                        "seriesId": series_id,
                        "label": suggestion["label"],
                        "materialIds": [material_id],
                        "progressionSummary": suggestion.get("progressionSummary"),
                        "compensationTrajectory": suggestion.get("compensationTrajectory"),
                        "confidence": suggestion["confidence"],
                        "evidenceIds": evidence_ids,
                    }
                    proposals.append(
                        {
                            "id": create_id("proposal"),
                            "action": "update_dream_series_progression",
                            "entityType": "DreamSeries",
                            "payload": update_payload,
                            "evidenceIds": evidence_ids,
                            "reason": (
                                "Update the stored series trajectory only if "
                                "the user wants this sequence held together."
                            ),
                            "requiresUserApproval": True,
                            "status": "pending_user_approval",
                        }
                    )
            key = ("link", f"{series_id}:{material_id}")
            if key in seen:
                continue
            seen.add(key)
            payload: DreamSeriesLinkWritePayload = {
                "seriesId": series_id,
                "label": suggestion["label"],
                "materialIds": [material_id],
                "confidence": suggestion["confidence"],
                "matchScore": suggestion["matchScore"],
                "matchingFeatures": list(suggestion.get("matchingFeatures", [])),
                "narrativeRole": suggestion["narrativeRole"],
                "egoStance": suggestion.get("egoStance"),
                "lysisSummary": suggestion.get("lysisSummary"),
                "evidenceIds": evidence_ids,
            }
            proposals.append(
                {
                    "id": create_id("proposal"),
                    "action": "link_material_to_dream_series",
                    "entityType": "DreamSeries",
                    "payload": payload,
                    "evidenceIds": evidence_ids,
                    "reason": (
                        "Link this material to the suggested dream series only "
                        "with explicit approval."
                    ),
                    "requiresUserApproval": True,
                    "status": "pending_user_approval",
                }
            )
            continue
        key = ("create", suggestion["label"])
        if key in seen:
            continue
        seen.add(key)
        create_payload: DreamSeriesLinkWritePayload = {
            "label": suggestion["label"],
            "materialIds": [material_id],
            "symbolIds": symbol_ids[:6],
            "motifKeys": motif_keys[:6],
            "progressionSummary": suggestion.get("progressionSummary"),
            "compensationTrajectory": suggestion.get("compensationTrajectory"),
            "confidence": suggestion["confidence"],
            "matchScore": suggestion["matchScore"],
            "matchingFeatures": list(suggestion.get("matchingFeatures", [])),
            "narrativeRole": suggestion["narrativeRole"],
            "egoStance": suggestion.get("egoStance"),
            "lysisSummary": suggestion.get("lysisSummary"),
            "evidenceIds": evidence_ids,
        }
        proposals.append(
            {
                "id": create_id("proposal"),
                "action": "create_dream_series",
                "entityType": "DreamSeries",
                "payload": create_payload,
                "evidenceIds": evidence_ids,
                "reason": (
                    "Create a durable dream-series thread only if the user wants it remembered."
                ),
                "requiresUserApproval": True,
                "status": "pending_user_approval",
            }
        )
    return proposals


def build_typology_assessment_from_llm(candidate: object) -> TypologyAssessment | None:
    if not isinstance(candidate, dict):
        return None
    status = str(candidate.get("status") or "").strip()
    if status not in {"insufficient_evidence", "signals_only", "hypotheses_available"}:
        return None
    result: TypologyAssessment = {
        "status": cast(object, status),
        "typologySignals": [],
        "typologyHypotheses": [],
        "userTestPrompt": candidate.get(
            "userTestPrompt", "Use any typology lens as a tentative test, not an identity claim."
        ),
    }
    signals = candidate.get("typologySignals")
    if isinstance(signals, list):
        for signal in signals[:6]:
            if not isinstance(signal, dict):
                continue
            evidence_ids = _string_list(signal.get("evidenceIds"), limit=8, item_limit=80)
            statement = truncate_text(signal.get("statement"), 220)
            if not evidence_ids or not statement:
                continue
            function = _sanitize_choice(
                signal.get("function"),
                allowed={"thinking", "feeling", "sensation", "intuition"},
                default="intuition",
            )
            orientation = _sanitize_choice(
                signal.get("orientation"),
                allowed={"introverted", "extraverted", "ambiguous"},
                default="ambiguous",
            )
            result["typologySignals"].append(
                {
                    "id": str(signal.get("id") or create_id("typology_signal")),
                    "category": _sanitize_choice(
                        signal.get("category"),
                        allowed={
                            "linguistic_marker",
                            "orientation_marker",
                            "sensation_trigger",
                            "fixation_or_overuse",
                            "compensatory_marker",
                            "longitudinal_pattern",
                            "feedback_signal",
                        },
                        default="feedback_signal",
                    ),
                    "function": function,
                    "orientation": orientation,
                    "statement": statement,
                    "strength": sanitize_confidence(signal.get("strength")),
                    "evidenceIds": evidence_ids,
                }
            )
    hypotheses = candidate.get("typologyHypotheses")
    if isinstance(hypotheses, list):
        for item in hypotheses[:4]:
            if not isinstance(item, dict):
                continue
            evidence_ids = _string_list(item.get("evidenceIds"), limit=8, item_limit=80)
            if not evidence_ids:
                continue
            claim = truncate_text(item.get("claim"), 220)
            user_test_prompt = truncate_text(item.get("userTestPrompt"), 220)
            if not claim or not user_test_prompt:
                continue
            function = _sanitize_choice(
                item.get("function"),
                allowed={"thinking", "feeling", "sensation", "intuition"},
                default="intuition",
            )
            role = _sanitize_choice(
                item.get("role"),
                allowed={"dominant", "auxiliary", "tertiary", "inferior", "compensation_link"},
                default="compensation_link",
            )
            normalized_claim_key = truncate_text(
                item.get("normalizedClaimKey"), 120
            ) or normalize_claim_key(claim)
            result["typologyHypotheses"].append(
                {
                    "id": str(item.get("id") or create_id("typology_hypothesis")),
                    "claim": claim,
                    "role": role,
                    "function": function,
                    "confidence": cast(
                        object,
                        _sanitize_typology_confidence(item.get("confidence")),
                    ),
                    "evidenceIds": evidence_ids,
                    "counterevidenceIds": _string_list(
                        item.get("counterevidenceIds"), limit=8, item_limit=80
                    ),
                    "userTestPrompt": user_test_prompt,
                    "phrasingPolicy": "very_tentative",
                    "normalizedClaimKey": normalized_claim_key,
                }
            )
    result["typologyHypotheses"] = [
        item for item in result["typologyHypotheses"] if item.get("evidenceIds")
    ]
    if not result["typologySignals"] and not result["typologyHypotheses"]:
        return {
            "status": "skipped",
            "typologySignals": [],
            "typologyHypotheses": [],
            "userTestPrompt": result["userTestPrompt"],
        }
    if result["typologyHypotheses"]:
        result["status"] = "hypotheses_available"
    return result


_CLARIFICATION_CAPTURE_TARGETS: set[str] = {
    "answer_only",
    "body_state",
    "conscious_attitude",
    "goal",
    "goal_tension",
    "personal_amplification",
    "reality_anchors",
    "threshold_process",
    "relational_scene",
    "inner_outer_correspondence",
    "numinous_encounter",
    "aesthetic_resonance",
    "consent_preference",
    "interpretation_preference",
    "typology_feedback",
}


def _effective_capture_target(
    llm_target: str | None,
    preferred_targets: list[str] | None,
) -> str:
    if llm_target and llm_target != "answer_only" and llm_target in _CLARIFICATION_CAPTURE_TARGETS:
        return llm_target
    for pt in preferred_targets or []:
        if pt in _CLARIFICATION_CAPTURE_TARGETS:
            return pt
    return "answer_only"


def build_clarification_plan_from_llm(
    llm_output: LlmInterpretationOutput,
    preferred_targets: list[str] | None = None,
) -> ClarificationPlan | None:
    clarifying_question = str(llm_output.get("clarifyingQuestion", "")).strip()
    candidate = llm_output.get("clarificationPlan")
    if isinstance(candidate, dict):
        question_text = truncate_text(candidate.get("questionText"), 220) or clarifying_question
        if question_text:
            plan: ClarificationPlan = {
                "questionText": question_text,
                "intent": cast(
                    object,
                    _sanitize_choice(
                        candidate.get("intent"),
                        allowed={
                            "personal_association",
                            "body_signal",
                            "conscious_stance",
                            "goal_pressure",
                            "reality_anchor",
                            "threshold_orientation",
                            "relational_scene",
                            "consent_check",
                            "interpretation_preference",
                            "safety_pacing",
                            "typology_feedback",
                            "other",
                        },
                        default="other",
                    ),
                ),
                "captureTarget": cast(
                    object,
                    _effective_capture_target(
                        str(candidate.get("captureTarget") or "").strip() or None,
                        preferred_targets,
                    ),
                ),
                "expectedAnswerKind": cast(
                    object,
                    _sanitize_choice(
                        candidate.get("expectedAnswerKind"),
                        allowed={
                            "free_text",
                            "yes_no",
                            "single_choice",
                            "multi_choice",
                            "body_state",
                            "scale",
                            "structured_payload",
                        },
                        default="free_text",
                    ),
                ),
            }
            question_key = truncate_text(candidate.get("questionKey"), 120)
            if question_key:
                plan["questionKey"] = question_key
            answer_slots = candidate.get("answerSlots")
            if isinstance(answer_slots, dict) and answer_slots:
                plan["answerSlots"] = answer_slots
            routing_hints = candidate.get("routingHints")
            if isinstance(routing_hints, dict) and routing_hints:
                plan["routingHints"] = routing_hints
            supporting_refs = _string_list(candidate.get("supportingRefs"), limit=8, item_limit=80)
            if supporting_refs:
                plan["supportingRefs"] = supporting_refs
            anchor_refs = candidate.get("anchorRefs")
            if isinstance(anchor_refs, dict) and anchor_refs:
                plan["anchorRefs"] = anchor_refs
            consent_scopes = _string_list(candidate.get("consentScopes"), limit=6, item_limit=80)
            if consent_scopes:
                plan["consentScopes"] = consent_scopes
            return plan

    if not clarifying_question:
        return None
    plan: ClarificationPlan = {
        "questionText": clarifying_question,
        "intent": "other",
        "captureTarget": _effective_capture_target(None, preferred_targets),
        "expectedAnswerKind": "free_text",
    }
    clarification_intent = llm_output.get("clarificationIntent")
    if isinstance(clarification_intent, dict):
        ref_key = truncate_text(clarification_intent.get("refKey"), 120)
        if ref_key:
            plan["questionKey"] = ref_key
        expected_targets = _string_list(
            clarification_intent.get("expectedTargets"), limit=4, item_limit=80
        )
        if expected_targets:
            plan["captureTarget"] = cast(
                object,
                _effective_capture_target(
                    _capture_target_from_expected_targets(expected_targets),
                    preferred_targets,
                ),
            )
        plan["routingHints"] = {"expectedTargets": expected_targets}
        anchor_refs = clarification_intent.get("anchorRefs")
        if isinstance(anchor_refs, dict) and anchor_refs:
            plan["anchorRefs"] = anchor_refs
        consent_scopes = _string_list(
            clarification_intent.get("consentScopes"), limit=6, item_limit=80
        )
        if consent_scopes:
            plan["consentScopes"] = consent_scopes
    return plan


def evidence_ids_for_refs(
    refs: object,
    supporting_ref_map: dict[str, list[str]],
) -> list[str]:
    evidence_ids: list[str] = []
    if not isinstance(refs, list):
        return evidence_ids
    for ref in refs:
        for evidence_id in supporting_ref_map.get(str(ref), []):
            if evidence_id not in evidence_ids:
                evidence_ids.append(evidence_id)
    return evidence_ids


def build_memory_write_plan(
    *,
    run_id: str,
    evidence_items: list[dict[str, object]],
    prebuilt_proposals: list[MemoryWriteProposal] | None = None,
) -> MemoryWritePlan:
    return {
        "runId": run_id,
        "proposals": list(prebuilt_proposals or []),
        "evidenceItems": cast(list, evidence_items),
    }


def build_supporting_ref_map(
    *,
    payload: object,
    evidence_items: list[EvidenceItem] | None = None,
) -> dict[str, list[str]]:
    ref_map: dict[str, list[str]] = {}

    def add(ref_id: object, evidence_ids: object) -> None:
        ref_key = str(ref_id or "").strip()
        if not ref_key:
            return
        current = ref_map.setdefault(ref_key, [])
        if not isinstance(evidence_ids, list):
            return
        for evidence_id in evidence_ids:
            candidate = str(evidence_id or "").strip()
            if candidate and candidate not in current:
                current.append(candidate)

    def visit(value: object) -> None:
        if isinstance(value, dict):
            add(value.get("id"), value.get("evidenceIds"))
            for nested in value.values():
                visit(nested)
            return
        if isinstance(value, list):
            for item in value:
                visit(item)

    visit(payload)
    for item in evidence_items or []:
        add(item.get("sourceId"), [item.get("id")])
    return ref_map


def build_review_memory_write_plan(
    *,
    plan_id: str,
    review_input: ThresholdReviewInput | LivingMythReviewInput,
    proposal_candidates: list[LlmProposalCandidate] | None,
) -> MemoryWritePlan | None:
    evidence_items = cast(list[EvidenceItem], review_input.get("evidence", []))
    supporting_ref_map = build_supporting_ref_map(
        payload=review_input, evidence_items=evidence_items
    )
    proposals: list[MemoryWriteProposal] = []
    seen: set[tuple[str, str, str]] = set()
    for candidate in proposal_candidates or []:
        action = str(candidate.get("action") or "").strip()
        entity_type = str(candidate.get("entityType") or "").strip()
        payload = candidate.get("payload") if isinstance(candidate.get("payload"), dict) else None
        if (
            not action
            or action not in _SUPPORTED_MEMORY_WRITE_ACTIONS
            or not entity_type
            or payload is None
        ):
            continue
        evidence_ids = evidence_ids_for_refs(candidate.get("supportingRefs"), supporting_ref_map)
        if not evidence_ids:
            continue
        key = (action, entity_type, repr(sorted(payload.items())))
        if key in seen:
            continue
        seen.add(key)
        proposals.append(
            {
                "id": create_id("proposal"),
                "action": cast(object, action),
                "entityType": cast(object, entity_type),
                "payload": payload,
                "evidenceIds": evidence_ids,
                "reason": truncate_text(candidate.get("reason"), 220)
                or "Apply only with explicit user approval.",
                "requiresUserApproval": True,
                "status": "pending_user_approval",
            }
        )
    if not proposals:
        return None
    return build_memory_write_plan(
        run_id=plan_id,
        evidence_items=cast(list[dict[str, object]], evidence_items),
        prebuilt_proposals=proposals,
    )


def build_analysis_packet_provenance(
    *,
    input_data: AnalysisPacketInput,
    llm_output: dict[str, object],
) -> tuple[list[str], list[AnalysisPacketRecordRef], list[str]]:
    evidence_items = cast(list[EvidenceItem], input_data.get("evidence", []))
    evidence_ids_available = {item["id"] for item in evidence_items}
    supporting_ref_map = build_supporting_ref_map(payload=input_data, evidence_items=evidence_items)
    material_ids_available = {
        item["sourceId"] for item in evidence_items if item.get("type") in _MATERIAL_EVIDENCE_TYPES
    }
    available_record_refs: dict[str, AnalysisPacketRecordRef] = {}
    for field_name, record_type in _PACKET_RECORD_FIELDS.items():
        for item in cast(list[dict[str, object]], input_data.get(field_name, [])):
            record_id = str(item.get("id") or "").strip()
            if record_id:
                available_record_refs[record_id] = {
                    "recordType": record_type,
                    "recordId": record_id,
                }

    included_material_ids = [
        item
        for item in [str(value).strip() for value in llm_output.get("includedMaterialIds", [])]
        if item and item in material_ids_available
    ]
    included_record_refs: list[AnalysisPacketRecordRef] = []
    for value in cast(list[dict[str, object]], llm_output.get("includedRecordRefs", [])):
        record_id = str(value.get("recordId") or "").strip()
        if not record_id or record_id not in available_record_refs:
            continue
        record_ref = available_record_refs[record_id]
        if str(value.get("recordType") or "").strip() not in {"", record_ref["recordType"]}:
            continue
        if record_ref not in included_record_refs:
            included_record_refs.append(record_ref)
    evidence_ids = [
        item
        for item in [str(value).strip() for value in llm_output.get("evidenceIds", [])]
        if item and item in evidence_ids_available
    ]

    supporting_refs = [str(value).strip() for value in llm_output.get("supportingRefs", [])]
    if not included_material_ids:
        included_material_ids = [
            ref_id for ref_id in supporting_refs if ref_id and ref_id in material_ids_available
        ]
    if not included_record_refs:
        for ref_id in supporting_refs:
            record_ref = available_record_refs.get(ref_id)
            if record_ref and record_ref not in included_record_refs:
                included_record_refs.append(record_ref)
    if not evidence_ids:
        evidence_ids = evidence_ids_for_refs(supporting_refs, supporting_ref_map)

    return (
        included_material_ids,
        included_record_refs,
        [item for item in evidence_ids if item in evidence_ids_available],
    )


def build_compensation_assessment(
    hypotheses: list[Hypothesis],
    method_context: MethodContextSnapshot | None = None,
) -> dict[str, object] | None:
    method_state = method_context.get("methodState") if isinstance(method_context, dict) else None
    compensation_tendencies = (
        method_state.get("compensationTendencies") if isinstance(method_state, dict) else None
    )
    if isinstance(compensation_tendencies, list):
        for item in compensation_tendencies:
            if not isinstance(item, dict):
                continue
            evidence_ids = _string_list(item.get("evidenceIds"), limit=8, item_limit=80)
            pattern_summary = truncate_text(item.get("patternSummary"), 220)
            user_test_prompt = truncate_text(item.get("userTestPrompt"), 220)
            if not evidence_ids or not pattern_summary or not user_test_prompt:
                continue
            return {
                "claim": pattern_summary,
                "confidence": cast(object, sanitize_confidence(item.get("confidence"), "low")),
                "evidenceIds": evidence_ids,
                "userTestPrompt": user_test_prompt,
            }
    return _build_compensation_assessment_from_hypotheses(hypotheses)


def _build_compensation_assessment_from_hypotheses(
    hypotheses: list[Hypothesis],
) -> dict[str, object] | None:
    for hypothesis in hypotheses:
        if hypothesis["hypothesisType"] == "compensation":
            return {
                "claim": hypothesis["claim"],
                "confidence": hypothesis["confidence"],
                "evidenceIds": hypothesis["evidenceIds"],
                "userTestPrompt": hypothesis["userTestPrompt"],
            }
    return None


def _capture_target_from_expected_targets(expected_targets: list[str]) -> str:
    supported = {
        "body_state",
        "conscious_attitude",
        "goal",
        "goal_tension",
        "personal_amplification",
        "reality_anchors",
        "threshold_process",
        "relational_scene",
        "inner_outer_correspondence",
        "numinous_encounter",
        "aesthetic_resonance",
        "consent_preference",
        "interpretation_preference",
        "typology_feedback",
    }
    for item in expected_targets:
        if item in supported:
            return item
    return "answer_only"


def _sanitize_typology_confidence(value: object) -> str:
    confidence = sanitize_confidence(value, "low")
    return "medium" if confidence == "high" else confidence


def is_suppressed(normalized_claim_key: str, memory: HermesMemoryContext) -> bool:
    return any(
        item["normalizedClaimKey"] == normalized_claim_key
        for item in memory["suppressedHypotheses"]
    )


def validate_evidence_integrity(result: InterpretationResult) -> None:
    available = {item["id"] for item in result["evidence"]}
    referenced: set[str] = set()
    for item in result["observations"]:
        referenced.update(item["evidenceIds"])
    for item in result["symbolMentions"]:
        referenced.add(item["evidenceId"])
    for item in result["figureMentions"]:
        referenced.add(item["evidenceId"])
    for item in result["motifMentions"]:
        referenced.add(item["evidenceId"])
    for item in result["hypotheses"]:
        referenced.update(item["evidenceIds"])
        referenced.update(item["counterevidenceIds"])
    if result.get("compensationAssessment"):
        referenced.update(result["compensationAssessment"]["evidenceIds"])
    for item in result["lifeContextLinks"]:
        referenced.add(item["evidenceId"])
    if result.get("typologyAssessment"):
        for signal in result["typologyAssessment"]["typologySignals"]:
            referenced.update(signal["evidenceIds"])
        for hypothesis in result["typologyAssessment"]["typologyHypotheses"]:
            referenced.update(hypothesis["evidenceIds"])
            referenced.update(hypothesis["counterevidenceIds"])
    if result.get("individuationAssessment"):
        individuation = result["individuationAssessment"]
        for key in (
            "realityAnchors",
            "selfOrientation",
        ):
            item = individuation.get(key)
            if isinstance(item, dict):
                referenced.update(cast(list[str], item.get("evidenceIds", [])))
                referenced.update(cast(list[str], item.get("counterevidenceIds", [])))
        for key in (
            "oppositions",
            "emergentThirdSignals",
            "thresholdProcesses",
            "relationalScenes",
            "projectionHypotheses",
            "innerOuterCorrespondences",
            "numinousEncounters",
            "aestheticResonances",
            "archetypalPatterns",
            "bridgeMoments",
        ):
            for item in cast(list[dict[str, object]], individuation.get(key, [])):
                referenced.update(cast(list[str], item.get("evidenceIds", [])))
                referenced.update(cast(list[str], item.get("counterevidenceIds", [])))
    for item in result["memoryWritePlan"]["proposals"]:
        referenced.update(item["evidenceIds"])
    missing = sorted(item for item in referenced if item not in available)
    if missing:
        raise EvidenceIntegrityError(f"Dangling evidence ids: {missing}")
