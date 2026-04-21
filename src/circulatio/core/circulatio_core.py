from __future__ import annotations

import logging
from typing import cast

from ..domain.ids import create_id, now_iso
from ..domain.normalization import (
    compact_life_context_snapshot,
    normalize_hermes_memory_context,
    normalize_options,
    normalize_session_context,
    validate_material_input,
)
from ..domain.types import (
    AnalysisPacketInput,
    AnalysisPacketResult,
    CirculationSummaryInput,
    CirculationSummaryResult,
    DepthReadinessAssessment,
    InterpretationResult,
    LivingMythReviewInput,
    LivingMythReviewResult,
    MaterialInterpretationInput,
    MethodGateResult,
    PracticeRecommendationInput,
    PracticeRecommendationResult,
    RecordIntegrationInput,
    RecordIntegrationResult,
    RhythmicBriefInput,
    RhythmicBriefResult,
    SafetyDisposition,
    ThresholdReviewInput,
    ThresholdReviewResult,
)
from ..llm.ports import CirculatioLlmPort
from ..repositories.graph_memory_repository import GraphMemoryRepository
from .evidence import EvidenceLedger
from .interpretation_fallbacks import (
    build_blocked_by_safety_result,
    build_unavailable_llm_result,
)
from .interpretation_mapping import (
    build_amplification_prompts_from_llm,
    build_analysis_packet_provenance,
    build_compensation_assessment,
    build_depth_readiness_from_llm,
    build_dream_series_proposals,
    build_dream_series_suggestions_from_llm,
    build_figure_mentions_from_llm,
    build_hypotheses_from_llm,
    build_individuation_from_llm,
    build_life_context_links,
    build_life_context_links_from_llm,
    build_llm_interpretation_health,
    build_memory_write_plan,
    build_method_gate_from_llm,
    build_motif_mentions_from_llm,
    build_observations_from_llm,
    build_practice_from_llm,
    build_proposals_from_llm,
    build_review_memory_write_plan,
    build_symbol_mentions_from_llm,
    build_typology_assessment_from_llm,
    try_llm_interpretation,
    validate_evidence_integrity,
)
from .practice_engine import PracticeEngine
from .safety_gate import SafetyGate

LOGGER = logging.getLogger(__name__)


class CirculatioCore:
    def __init__(
        self,
        repository: GraphMemoryRepository,
        safety_gate: SafetyGate | None = None,
        llm: CirculatioLlmPort | None = None,
        practice_engine: PracticeEngine | None = None,
    ) -> None:
        self._repository = repository
        self._safety_gate = safety_gate or SafetyGate()
        self._llm = llm
        self._practice_engine = practice_engine or PracticeEngine()

    async def interpret_dream(
        self, input_data: MaterialInterpretationInput
    ) -> InterpretationResult:
        payload = dict(input_data)
        payload["materialType"] = "dream"
        return await self.interpret_material(cast(MaterialInterpretationInput, payload))

    async def interpret_material(
        self, input_data: MaterialInterpretationInput
    ) -> InterpretationResult:
        validate_material_input(input_data)
        options = normalize_options(input_data.get("options"))
        timestamp = now_iso()
        run_id = create_id("run")
        material_id = input_data.get("materialId") or create_id(input_data["materialType"])
        memory = normalize_hermes_memory_context(input_data.get("hermesMemoryContext"))
        if not input_data.get("hermesMemoryContext"):
            memory = normalize_hermes_memory_context(
                await self._repository.get_hermes_memory_context(
                    input_data["userId"],
                    max_items=options["maxHistoricalItems"],
                )
            )

        normalized_input: MaterialInterpretationInput = {
            **input_data,
            "sessionContext": normalize_session_context(input_data.get("sessionContext")),
            "hermesMemoryContext": memory,
            "options": options,
        }
        if input_data.get("lifeContextSnapshot"):
            normalized_input["lifeContextSnapshot"] = compact_life_context_snapshot(
                input_data["lifeContextSnapshot"]
            )

        # Pre-LLM deterministic safety floor.
        safety = self._safety_gate.assess(normalized_input)
        if not safety["depthWorkAllowed"]:
            return build_blocked_by_safety_result(
                run_id=run_id, material_id=material_id, safety=safety
            )

        evidence_ledger = EvidenceLedger(timestamp=timestamp)
        llm_output = await try_llm_interpretation(self._llm, normalized_input)
        if llm_output is None:
            return build_unavailable_llm_result(
                run_id=run_id,
                material_id=material_id,
                safety=safety,
                evidence_ledger=evidence_ledger,
                input_data=normalized_input,
            )

        life_context_links, life_ref_map = build_life_context_links_from_llm(
            input_data=normalized_input,
            material_id=material_id,
            llm_output=llm_output,
            evidence_ledger=evidence_ledger,
        )
        if not life_context_links:
            life_context_links = build_life_context_links(
                input_data=normalized_input,
                material_id=material_id,
                evidence_ledger=evidence_ledger,
            )
            life_ref_map = {}

        symbol_mentions, symbol_ref_map = build_symbol_mentions_from_llm(
            input_data=normalized_input,
            material_id=material_id,
            llm_output=llm_output,
            evidence_ledger=evidence_ledger,
        )
        figure_mentions, figure_ref_map = build_figure_mentions_from_llm(
            input_data=normalized_input,
            material_id=material_id,
            llm_output=llm_output,
            evidence_ledger=evidence_ledger,
        )
        motif_mentions, motif_ref_map = build_motif_mentions_from_llm(
            input_data=normalized_input,
            material_id=material_id,
            llm_output=llm_output,
            evidence_ledger=evidence_ledger,
        )
        ref_map = {**symbol_ref_map, **figure_ref_map, **motif_ref_map, **life_ref_map}
        observations = build_observations_from_llm(
            llm_output=llm_output,
            supporting_ref_map=ref_map,
        )
        depth_readiness = build_depth_readiness_from_llm(llm_output.get("depthReadiness"))
        method_gate = build_method_gate_from_llm(llm_output.get("methodGate"))
        amplification_prompts = build_amplification_prompts_from_llm(
            llm_output.get("amplificationPrompts"),
            symbol_ref_map=symbol_ref_map,
            symbol_mentions=symbol_mentions,
        )
        dream_series_suggestions = build_dream_series_suggestions_from_llm(
            llm_output.get("dreamSeriesSuggestions"),
            ref_map,
        )
        hypotheses = build_hypotheses_from_llm(
            llm_output=llm_output,
            memory=memory,
            supporting_ref_map=ref_map,
            max_hypotheses=options["maxHypotheses"],
        )
        llm_proposals, personal_updates, complex_updates = build_proposals_from_llm(
            input_data=normalized_input,
            material_id=material_id,
            symbol_mentions=symbol_mentions,
            life_context_links=life_context_links,
            llm_proposals=llm_output.get("proposalCandidates", []),
            supporting_ref_map=ref_map,
            method_gate=method_gate,
        )
        individuation_assessment, individuation_proposals = build_individuation_from_llm(
            input_data=normalized_input,
            material_id=material_id,
            llm_output=llm_output,
            supporting_ref_map=ref_map,
        )
        llm_proposals.extend(individuation_proposals)
        llm_proposals.extend(
            build_dream_series_proposals(
                material_id=material_id,
                suggestions=dream_series_suggestions,
                symbol_mentions=symbol_mentions,
                motif_mentions=motif_mentions,
            )
        )
        memory_write_plan = build_memory_write_plan(
            run_id=run_id,
            evidence_items=evidence_ledger.all(),
            prebuilt_proposals=llm_proposals,
        )
        practice = self._practice_engine.reconcile_llm_practice(
            practice=build_practice_from_llm(llm_output.get("practiceRecommendation")),
            method_gate=method_gate,
            depth_readiness=depth_readiness,
            safety=safety,
            consent_preferences=normalized_input.get("methodContextSnapshot", {}).get(
                "consentPreferences", []
            ),
            fallback_reason="llm_missing_practice_fallback_to_journaling",
        )

        clarifying_question = str(llm_output.get("clarifyingQuestion", "")).strip() or None
        user_facing_response = str(llm_output.get("userFacingResponse", "")).strip()
        if not user_facing_response and clarifying_question:
            user_facing_response = clarifying_question
        if not user_facing_response:
            user_facing_response = (
                "The interpretation model returned structured data but no user-facing "
                "narrative. Use the next question as the opening move."
            )
        llm_health = build_llm_interpretation_health(
            source="llm",
            reason="structured_interpretation_available",
            symbol_mentions=symbol_mentions,
            figure_mentions=figure_mentions,
            motif_mentions=motif_mentions,
            observations=observations,
            hypotheses=hypotheses,
            proposal_candidates=memory_write_plan["proposals"],
        )

        # Post-LLM safety reconciliation: deterministic gate wins if it disagrees.
        llm_safety = llm_output.get("safetyDisposition")
        if isinstance(llm_safety, dict) and not llm_safety.get("depthWorkAllowed", True):
            if safety["depthWorkAllowed"]:
                LOGGER.warning(
                    "LLM flagged safety concern that deterministic gate missed; "
                    "honoring LLM safety block."
                )
                safety = {
                    "status": str(llm_safety.get("status", "grounding_only")),
                    "flags": list(llm_safety.get("flags", [])),
                    "depthWorkAllowed": False,
                    "message": str(
                        llm_safety.get("message", "Depth work paused based on model assessment.")
                    ),
                    "suggestedSupport": list(llm_safety.get("suggestedSupport", [])),
                }
                return build_blocked_by_safety_result(
                    run_id=run_id, material_id=material_id, safety=safety
                )

        compensation = build_compensation_assessment(hypotheses)
        typology_assessment = build_typology_assessment_from_llm(
            llm_output.get("typologyAssessment")
        )

        depth_engine_health = {
            "status": "structured"
            if any((depth_readiness, method_gate, amplification_prompts, dream_series_suggestions))
            else "fallback",
            "reason": (
                "practice_reconciled_by_method_gate"
                if practice["type"] != llm_output.get("practiceRecommendation", {}).get("type")
                else "llm_depth_contract_available"
            )
            if any((depth_readiness, method_gate, amplification_prompts, dream_series_suggestions))
            else "fallback_depth_engine_used",
            "source": "llm"
            if any((depth_readiness, method_gate, amplification_prompts, dream_series_suggestions))
            else "fallback",
        }

        result: InterpretationResult = {
            "runId": run_id,
            "materialId": material_id,
            "safetyDisposition": safety,
            "observations": observations,
            "evidence": evidence_ledger.all(),
            "symbolMentions": symbol_mentions,
            "figureMentions": figure_mentions,
            "motifMentions": motif_mentions,
            "personalSymbolUpdates": personal_updates,
            "culturalAmplifications": [],
            "hypotheses": hypotheses,
            "complexCandidateUpdates": complex_updates,
            "lifeContextLinks": life_context_links,
            "practiceRecommendation": practice,
            "memoryWritePlan": memory_write_plan,
            "userFacingResponse": user_facing_response,
            "llmInterpretationHealth": llm_health,
            "depthEngineHealth": depth_engine_health,
        }
        if method_gate:
            result["methodGate"] = method_gate
        if depth_readiness:
            result["depthReadiness"] = depth_readiness
        if individuation_assessment:
            result["individuationAssessment"] = individuation_assessment
        if amplification_prompts:
            result["amplificationPrompts"] = amplification_prompts
        if dream_series_suggestions:
            result["dreamSeriesSuggestions"] = dream_series_suggestions
        if compensation:
            result["compensationAssessment"] = compensation
        if typology_assessment and typology_assessment.get("status") != "skipped":
            result["typologyAssessment"] = typology_assessment
        if clarifying_question:
            result["clarifyingQuestion"] = clarifying_question
        validate_evidence_integrity(result)
        return result

    async def generate_circulation_summary(
        self, input_data: CirculationSummaryInput
    ) -> CirculationSummaryResult:
        summary_id = create_id("circulation_summary")
        recurring_symbols = input_data["hermesMemoryContext"]["recurringSymbols"][:8]
        active_candidates = [
            candidate
            for candidate in input_data["hermesMemoryContext"]["activeComplexCandidates"]
            if candidate["status"] != "disconfirmed"
        ][:5]
        life_links = []
        snapshot = input_data.get("lifeContextSnapshot")
        if snapshot:
            life_links = build_life_context_links(
                input_data={
                    **input_data,
                    "lifeContextSnapshot": snapshot,
                },
                material_id=summary_id,
                evidence_ledger=EvidenceLedger(timestamp=now_iso()),
            )
        llm_review: dict[str, object] | None = None
        if self._llm is not None:
            try:
                llm_review = await self._llm.generate_weekly_review(input_data)
            except Exception:
                LOGGER.warning(
                    "Circulatio weekly review LLM path failed; using minimal fallback.",
                    exc_info=True,
                )
                llm_review = None

        practice = self._practice_engine.reconcile_llm_practice(
            practice=build_practice_from_llm(
                llm_review.get("practiceRecommendation") if llm_review else None
            ),
            method_gate=input_data.get("methodContextSnapshot", {}).get("methodGate"),
            depth_readiness=None,
            safety=self._clear_safety_disposition(),
            consent_preferences=input_data.get("methodContextSnapshot", {}).get(
                "consentPreferences", []
            ),
            fallback_reason="llm_missing_practice_fallback_to_journaling",
        )
        active_themes = (
            [str(item) for item in llm_review.get("activeThemes", [])] if llm_review else []
        )
        response = str(llm_review.get("userFacingResponse", "")).strip() if llm_review else ""
        if not response:
            response = (
                "Hermes-Circulation supports reflection and symbolic interpretation. "
                "It does not provide therapy, diagnosis, crisis counseling, or medical advice.\n\n"
                "The weekly review model path was unavailable for this window, "
                "so Circulatio is withholding a synthetic review narrative.\n\n"
                "Next step:\n"
                + "\n".join(
                    f"- {instruction}" for instruction in cast(list, practice["instructions"])
                )
            )
        return {
            "summaryId": summary_id,
            "windowStart": input_data["windowStart"],
            "windowEnd": input_data["windowEnd"],
            "recurringSymbols": recurring_symbols,
            "activeThemes": active_themes,
            "activeComplexCandidates": active_candidates,
            "notableLifeContextLinks": life_links,
            "practiceSuggestion": practice,
            "userFacingResponse": response,
        }

    async def generate_threshold_review(
        self,
        input_data: ThresholdReviewInput,
    ) -> ThresholdReviewResult:
        normalized_input: ThresholdReviewInput = {
            **input_data,
            "hermesMemoryContext": normalize_hermes_memory_context(
                input_data.get("hermesMemoryContext")
            ),
        }
        synthetic = self._synthetic_threshold_material_input(normalized_input)
        safety = self._safety_gate.assess(synthetic)
        consent_preferences = normalized_input.get("methodContextSnapshot", {}).get(
            "consentPreferences", []
        )
        if not safety["depthWorkAllowed"]:
            practice = self._practice_engine.reconcile_llm_practice(
                practice=None,
                safety=safety,
                method_gate=None,
                depth_readiness=None,
                consent_preferences=consent_preferences,
                fallback_reason="safety_gate_blocks_threshold_review",
            )
            return {
                "userFacingResponse": (
                    "Depth work is paused for now. "
                    "A grounding-first step is available if you want it."
                ),
                "thresholdProcesses": [],
                "practiceRecommendation": practice,
                "withheld": True,
                "withheldReason": "safety_gate_blocks_threshold_review",
                "withheldReasons": ["safety_gate_blocks_threshold_review"],
                "llmHealth": {
                    "status": "fallback",
                    "reason": "safety_gate_blocks_threshold_review",
                    "source": "fallback",
                },
            }
        llm_output = None
        if self._llm is not None:
            try:
                llm_output = await self._llm.generate_threshold_review(normalized_input)
            except Exception:
                LOGGER.warning(
                    "Circulatio threshold review LLM path failed; withholding symbolic review.",
                    exc_info=True,
                )
                llm_output = None
        if llm_output is None:
            return {
                "userFacingResponse": (
                    "The threshold review model path is unavailable right now. "
                    "An evidence-only analysis packet may be a better next step."
                ),
                "thresholdProcesses": [],
                "withheld": True,
                "withheldReason": "llm_missing_for_threshold_review",
                "withheldReasons": ["llm_missing_for_threshold_review"],
                "llmHealth": {
                    "status": "fallback",
                    "reason": "llm_missing_for_threshold_review",
                    "source": "fallback",
                },
            }
        practice = self._practice_engine.reconcile_llm_practice(
            practice=build_practice_from_llm(llm_output.get("practiceRecommendation")),
            safety=safety,
            method_gate=None,
            depth_readiness=None,
            consent_preferences=consent_preferences,
            fallback_reason="llm_missing_practice_fallback_to_journaling",
        )
        result: ThresholdReviewResult = {
            "userFacingResponse": str(llm_output.get("userFacingResponse", "")).strip(),
            "thresholdProcesses": cast(
                list[dict[str, object]], llm_output.get("thresholdProcesses", [])
            ),
            "llmHealth": {
                "status": "structured",
                "reason": "llm_threshold_review_available",
                "source": "llm",
            },
        }
        if llm_output.get("realityAnchors"):
            result["realityAnchors"] = cast(list[dict[str, object]], llm_output["realityAnchors"])
        if practice:
            result["practiceRecommendation"] = practice
        memory_write_plan = build_review_memory_write_plan(
            plan_id=create_id("threshold_review_plan"),
            review_input=normalized_input,
            proposal_candidates=cast(
                list[dict[str, object]], llm_output.get("proposalCandidates", [])
            ),
        )
        if memory_write_plan:
            result["memoryWritePlan"] = memory_write_plan
        return result

    async def generate_living_myth_review(
        self,
        input_data: LivingMythReviewInput,
    ) -> LivingMythReviewResult:
        normalized_input: LivingMythReviewInput = {
            **input_data,
            "hermesMemoryContext": normalize_hermes_memory_context(
                input_data.get("hermesMemoryContext")
            ),
        }
        synthetic = self._synthetic_living_myth_material_input(normalized_input)
        safety = self._safety_gate.assess(synthetic)
        consent_preferences = normalized_input.get("methodContextSnapshot", {}).get(
            "consentPreferences", []
        )
        if not safety["depthWorkAllowed"]:
            return {
                "userFacingResponse": (
                    "Living-myth synthesis is withheld while depth work is paused."
                ),
                "mythicQuestions": [],
                "thresholdMarkers": [],
                "complexEncounters": [],
                "withheld": True,
                "withheldReason": "safety_gate_blocks_living_myth_review",
                "withheldReasons": ["safety_gate_blocks_living_myth_review"],
                "llmHealth": {
                    "status": "fallback",
                    "reason": "safety_gate_blocks_living_myth_review",
                    "source": "fallback",
                },
            }
        llm_output = None
        if self._llm is not None:
            try:
                llm_output = await self._llm.generate_living_myth_review(normalized_input)
            except Exception:
                LOGGER.warning(
                    "Circulatio living myth review LLM path failed; withholding mythic synthesis.",
                    exc_info=True,
                )
                llm_output = None
        if llm_output is None:
            return {
                "userFacingResponse": (
                    "The living-myth review model path is unavailable right now. "
                    "A bounded analysis packet may still help."
                ),
                "mythicQuestions": [],
                "thresholdMarkers": [],
                "complexEncounters": [],
                "withheld": True,
                "withheldReason": "llm_missing_for_living_myth_review",
                "withheldReasons": ["llm_missing_for_living_myth_review"],
                "llmHealth": {
                    "status": "fallback",
                    "reason": "llm_missing_for_living_myth_review",
                    "source": "fallback",
                },
            }
        practice = self._practice_engine.reconcile_llm_practice(
            practice=build_practice_from_llm(llm_output.get("practiceRecommendation")),
            safety=safety,
            method_gate=None,
            depth_readiness=None,
            consent_preferences=consent_preferences,
            fallback_reason="llm_missing_practice_fallback_to_journaling",
        )
        result: LivingMythReviewResult = {
            "userFacingResponse": str(llm_output.get("userFacingResponse", "")).strip(),
            "mythicQuestions": cast(list[dict[str, object]], llm_output.get("mythicQuestions", [])),
            "thresholdMarkers": cast(
                list[dict[str, object]], llm_output.get("thresholdMarkers", [])
            ),
            "complexEncounters": cast(
                list[dict[str, object]], llm_output.get("complexEncounters", [])
            ),
            "llmHealth": {
                "status": "structured",
                "reason": "llm_living_myth_review_available",
                "source": "llm",
            },
        }
        if llm_output.get("lifeChapter"):
            result["lifeChapter"] = cast(dict[str, object], llm_output["lifeChapter"])
        if llm_output.get("integrationContour"):
            result["integrationContour"] = cast(dict[str, object], llm_output["integrationContour"])
        if llm_output.get("symbolicWellbeing"):
            result["symbolicWellbeing"] = cast(dict[str, object], llm_output["symbolicWellbeing"])
        if practice:
            result["practiceRecommendation"] = practice
        memory_write_plan = build_review_memory_write_plan(
            plan_id=create_id("living_myth_review_plan"),
            review_input=normalized_input,
            proposal_candidates=cast(
                list[dict[str, object]], llm_output.get("proposalCandidates", [])
            ),
        )
        if memory_write_plan:
            result["memoryWritePlan"] = memory_write_plan
        return result

    async def generate_analysis_packet(
        self,
        input_data: AnalysisPacketInput,
    ) -> AnalysisPacketResult:
        normalized_input: AnalysisPacketInput = {
            **input_data,
            "hermesMemoryContext": normalize_hermes_memory_context(
                input_data.get("hermesMemoryContext")
            ),
        }
        synthetic = self._synthetic_analysis_packet_material_input(normalized_input)
        safety = self._safety_gate.assess(synthetic)
        llm_output = None
        if safety["depthWorkAllowed"] and self._llm is not None:
            try:
                llm_output = await self._llm.generate_analysis_packet(normalized_input)
            except Exception:
                LOGGER.warning(
                    "Circulatio analysis packet LLM path failed; using bounded fallback.",
                    exc_info=True,
                )
                llm_output = None
        if llm_output is not None:
            included_material_ids, included_record_refs, evidence_ids = (
                build_analysis_packet_provenance(
                    input_data=normalized_input,
                    llm_output=cast(dict[str, object], llm_output),
                )
            )
            return {
                "packetTitle": str(llm_output.get("packetTitle", "")).strip() or "Analysis packet",
                "sections": cast(list[dict[str, object]], llm_output.get("sections", [])),
                "includedMaterialIds": included_material_ids,
                "includedRecordRefs": included_record_refs,
                "evidenceIds": evidence_ids,
                "source": "llm",
                "userFacingResponse": str(llm_output.get("userFacingResponse", "")).strip(),
                "llmHealth": {
                    "status": "structured",
                    "reason": "llm_analysis_packet_available",
                    "source": "llm",
                },
            }
        sections: list[dict[str, object]] = []
        included_record_refs: list[dict[str, object]] = []
        evidence_ids: list[str] = []
        if normalized_input.get("activeThresholdProcesses"):
            for item in normalized_input.get("activeThresholdProcesses", [])[:5]:
                record_id = str(item.get("id") or "").strip()
                if record_id:
                    included_record_refs.append(
                        {"recordType": "ThresholdProcess", "recordId": record_id}
                    )
                for evidence_id in item.get("evidenceIds", []):
                    if evidence_id not in evidence_ids:
                        evidence_ids.append(evidence_id)
            sections.append(
                {
                    "title": "Threshold processes",
                    "purpose": "Hold the active liminal processes in bounded form.",
                    "items": [
                        {
                            "label": item.get("label", "Threshold process"),
                            "summary": item.get("summary", ""),
                            "evidenceIds": list(item.get("evidenceIds", [])),
                            "relatedRecordRefs": [],
                        }
                        for item in normalized_input.get("activeThresholdProcesses", [])[:5]
                    ],
                }
            )
        if normalized_input.get("relationalScenes"):
            for item in normalized_input.get("relationalScenes", [])[:5]:
                record_id = str(item.get("id") or "").strip()
                if record_id:
                    included_record_refs.append(
                        {"recordType": "RelationalScene", "recordId": record_id}
                    )
                for evidence_id in item.get("evidenceIds", []):
                    if evidence_id not in evidence_ids:
                        evidence_ids.append(evidence_id)
            sections.append(
                {
                    "title": "Relational scenes",
                    "purpose": "Keep repeated emotional scenes visible without forcing verdicts.",
                    "items": [
                        {
                            "label": item.get("label", "Relational scene"),
                            "summary": item.get("summary", ""),
                            "evidenceIds": list(item.get("evidenceIds", [])),
                            "relatedRecordRefs": [],
                        }
                        for item in normalized_input.get("relationalScenes", [])[:5]
                    ],
                }
            )
        if normalized_input.get("activeMythicQuestions"):
            for item in normalized_input.get("activeMythicQuestions", [])[:5]:
                record_id = str(item.get("id") or "").strip()
                if record_id:
                    included_record_refs.append(
                        {"recordType": "MythicQuestion", "recordId": record_id}
                    )
                for evidence_id in item.get("evidenceIds", []):
                    if evidence_id not in evidence_ids:
                        evidence_ids.append(evidence_id)
            sections.append(
                {
                    "title": "Active questions",
                    "purpose": (
                        "Keep the current questions explicit without collapsing them into answers."
                    ),
                    "items": [
                        {
                            "label": item.get("label", "Mythic question"),
                            "summary": item.get("summary", ""),
                            "evidenceIds": list(item.get("evidenceIds", [])),
                            "relatedRecordRefs": [],
                        }
                        for item in normalized_input.get("activeMythicQuestions", [])[:5]
                    ],
                }
            )
        if not sections:
            sections.append(
                {
                    "title": "Bounded packet",
                    "purpose": (
                        "No major longitudinal material was available in the requested window."
                    ),
                    "items": [],
                }
            )
        included_material_ids: list[str] = []
        for item in normalized_input.get("evidence", []):
            source_id = str(item.get("sourceId") or "").strip()
            if (
                source_id
                and item.get("type") in {"material_text_span", "dream_text_span", "prior_material"}
                and source_id not in included_material_ids
            ):
                included_material_ids.append(source_id)
            evidence_id = str(item.get("id") or "").strip()
            if evidence_id and evidence_id in evidence_ids:
                continue
            if evidence_id and any(source_id == included for included in included_material_ids):
                evidence_ids.append(evidence_id)
        deduped_record_refs: list[dict[str, object]] = []
        seen_record_refs: set[tuple[str, str]] = set()
        for item in included_record_refs:
            key = (str(item["recordType"]), str(item["recordId"]))
            if key in seen_record_refs:
                continue
            seen_record_refs.add(key)
            deduped_record_refs.append(item)
        return {
            "packetTitle": "Analysis packet",
            "sections": cast(list[dict[str, object]], sections),
            "includedMaterialIds": included_material_ids,
            "includedRecordRefs": cast(list[dict[str, str]], deduped_record_refs),
            "evidenceIds": evidence_ids,
            "source": "bounded_fallback",
            "userFacingResponse": (
                "A bounded packet is available using existing approved summaries "
                "rather than new symbolic synthesis."
            ),
            "llmHealth": {
                "status": "fallback",
                "reason": "bounded_analysis_packet_fallback",
                "source": "fallback",
            },
        }

    async def generate_practice(
        self,
        input_data: PracticeRecommendationInput,
    ) -> PracticeRecommendationResult:
        options = normalize_options(input_data.get("options"))
        normalized_input: PracticeRecommendationInput = {
            **input_data,
            "sessionContext": normalize_session_context(input_data.get("sessionContext")),
            "hermesMemoryContext": normalize_hermes_memory_context(
                input_data.get("hermesMemoryContext")
            ),
            "options": options,
        }
        synthetic = self._synthetic_practice_material_input(normalized_input)
        safety = self._safety_gate.assess(synthetic)
        consent_preferences = normalized_input.get("methodContextSnapshot", {}).get(
            "consentPreferences", []
        )
        if not safety["depthWorkAllowed"]:
            practice = self._practice_engine.reconcile_llm_practice(
                practice=None,
                safety=safety,
                method_gate=None,
                depth_readiness=None,
                consent_preferences=consent_preferences,
                fallback_reason="safety_blocked_grounding_fallback",
            )
            return {
                "practiceRecommendation": practice,
                "userFacingResponse": (
                    "Depth work is paused for now. A short grounding step is available, "
                    "and you can ignore it without guilt."
                ),
                "llmHealth": {
                    "status": "fallback",
                    "reason": "safety_gate_blocks_depth",
                    "source": "fallback",
                },
            }
        llm_output = None
        if self._llm is not None:
            try:
                llm_output = await self._llm.generate_practice(normalized_input)
            except Exception:
                LOGGER.warning(
                    "Circulatio practice LLM path failed; using bounded fallback.",
                    exc_info=True,
                )
                llm_output = None
        practice_candidate = (
            build_practice_from_llm(llm_output.get("practiceRecommendation"))
            if llm_output
            else None
        )
        if practice_candidate and llm_output:
            follow_up_prompt = str(llm_output.get("followUpPrompt", "")).strip()
            if follow_up_prompt and not practice_candidate.get("followUpPrompt"):
                practice_candidate["followUpPrompt"] = follow_up_prompt
            adaptation_notes = [
                str(item) for item in llm_output.get("adaptationNotes", []) if str(item).strip()
            ]
            if adaptation_notes:
                practice_candidate["adaptationNotes"] = list(
                    dict.fromkeys(
                        [
                            *[
                                str(item)
                                for item in practice_candidate.get("adaptationNotes", [])
                                if str(item).strip()
                            ],
                            *adaptation_notes,
                        ]
                    )
                )[:6]
        practice = self._practice_engine.reconcile_llm_practice(
            practice=practice_candidate,
            safety=safety,
            method_gate=None,
            depth_readiness=None,
            consent_preferences=consent_preferences,
            adaptation_hints=normalized_input.get("adaptationHints"),
            fallback_reason="llm_missing_practice_fallback_to_journaling",
        )
        response = str(llm_output.get("userFacingResponse", "")).strip() if llm_output else ""
        if not response:
            response = (
                "A bounded practice is available if you want it. You can skip it without guilt."
            )
        return {
            "practiceRecommendation": practice,
            "userFacingResponse": response,
            "llmHealth": {
                "status": "structured" if llm_output else "fallback",
                "reason": "llm_practice_available"
                if llm_output
                else "llm_missing_practice_fallback_to_journaling",
                "source": "llm" if llm_output else "fallback",
            },
        }

    async def generate_rhythmic_brief(
        self,
        input_data: RhythmicBriefInput,
    ) -> RhythmicBriefResult:
        synthetic = self._synthetic_brief_material_input(input_data)
        safety = self._safety_gate.assess(synthetic)
        brief_type = str(input_data.get("seed", {}).get("briefType") or "daily")
        if not safety["depthWorkAllowed"] and brief_type != "practice_followup":
            return {
                "withheld": True,
                "withheldReason": "safety_gate_blocks_symbolic_brief",
            }
        llm_output = None
        if self._llm is not None:
            try:
                llm_output = await self._llm.generate_rhythmic_brief(input_data)
            except Exception:
                LOGGER.warning(
                    "Circulatio rhythmic brief LLM path failed; using bounded fallback.",
                    exc_info=True,
                )
                llm_output = None
        if llm_output and all(
            str(llm_output.get(field, "")).strip()
            for field in ("title", "summary", "userFacingResponse")
        ):
            result: RhythmicBriefResult = {
                "title": str(llm_output["title"]).strip(),
                "summary": str(llm_output["summary"]).strip(),
                "userFacingResponse": str(llm_output["userFacingResponse"]).strip(),
                "llmHealth": {
                    "status": "structured",
                    "reason": "llm_rhythmic_brief_available",
                    "source": "llm",
                },
            }
            suggested_action = str(llm_output.get("suggestedAction", "")).strip()
            if suggested_action:
                result["suggestedAction"] = suggested_action
            return result
        if brief_type == "practice_followup":
            seed = input_data["seed"]
            return {
                "title": str(seed.get("titleHint") or "Practice follow-up"),
                "summary": str(
                    seed.get("summaryHint")
                    or "A prior practice may be ready for a gentle follow-up."
                ),
                "suggestedAction": str(
                    seed.get("suggestedActionHint")
                    or "You can note what happened, or simply leave it for later."
                ),
                "userFacingResponse": (
                    "A prior practice may be ready for a light check-in. "
                    "You can ignore this without guilt."
                ),
                "llmHealth": {
                    "status": "fallback",
                    "reason": "practice_followup_fallback",
                    "source": "fallback",
                },
            }
        return {
            "withheld": True,
            "withheldReason": "llm_missing_for_symbolic_brief",
            "llmHealth": {
                "status": "fallback",
                "reason": "llm_missing_for_symbolic_brief",
                "source": "fallback",
            },
        }

    async def record_integration(
        self, input_data: RecordIntegrationInput
    ) -> RecordIntegrationResult:
        return await self._repository.record_integration(input_data)

    def _reconcile_practice_with_method_gate(
        self,
        *,
        practice: dict[str, object],
        method_gate: MethodGateResult | None,
        depth_readiness: DepthReadinessAssessment | None,
        safety: SafetyDisposition,
        consent_preferences: list[dict[str, object]],
    ) -> dict[str, object]:
        return self._practice_engine.reconcile_llm_practice(
            practice=cast(object, practice),
            method_gate=method_gate,
            depth_readiness=depth_readiness,
            safety=safety,
            consent_preferences=consent_preferences,
        )

    def _clear_safety_disposition(self) -> SafetyDisposition:
        return {"status": "clear", "flags": ["none"], "depthWorkAllowed": True}

    def _synthetic_practice_material_input(
        self, input_data: PracticeRecommendationInput
    ) -> MaterialInterpretationInput:
        text = (
            "\n".join(
                [
                    str(input_data.get("explicitQuestion") or "").strip(),
                    *normalize_session_context(input_data.get("sessionContext")).get(
                        "currentStateNotes", []
                    ),
                    str(input_data.get("trigger", {}).get("reason") or "").strip(),
                ]
            ).strip()
            or "practice request"
        )
        result: MaterialInterpretationInput = {
            "userId": input_data["userId"],
            "materialType": "reflection",
            "materialText": text,
            "sessionContext": normalize_session_context(input_data.get("sessionContext")),
            "hermesMemoryContext": normalize_hermes_memory_context(
                input_data.get("hermesMemoryContext")
            ),
            "options": normalize_options(input_data.get("options")),
        }
        if input_data.get("lifeContextSnapshot"):
            result["lifeContextSnapshot"] = compact_life_context_snapshot(
                input_data["lifeContextSnapshot"]
            )
        if input_data.get("methodContextSnapshot"):
            result["methodContextSnapshot"] = input_data["methodContextSnapshot"]
        if input_data.get("safetyContext"):
            result["safetyContext"] = input_data["safetyContext"]
        return result

    def _synthetic_threshold_material_input(
        self, input_data: ThresholdReviewInput
    ) -> MaterialInterpretationInput:
        target = input_data.get("targetThresholdProcess") or {}
        text = (
            "\n".join(
                [
                    str(input_data.get("explicitQuestion") or "").strip(),
                    str(target.get("label") or "").strip(),
                    str(target.get("summary") or "").strip(),
                    str(target.get("whatIsEnding") or "").strip(),
                    str(target.get("notYetBegun") or "").strip(),
                ]
            ).strip()
            or "threshold review request"
        )
        result: MaterialInterpretationInput = {
            "userId": input_data["userId"],
            "materialType": "reflection",
            "materialText": text,
            "sessionContext": normalize_session_context(None),
            "hermesMemoryContext": normalize_hermes_memory_context(
                input_data.get("hermesMemoryContext")
            ),
            "options": normalize_options(None),
        }
        if input_data.get("lifeContextSnapshot"):
            result["lifeContextSnapshot"] = compact_life_context_snapshot(
                input_data["lifeContextSnapshot"]
            )
        if input_data.get("methodContextSnapshot"):
            result["methodContextSnapshot"] = input_data["methodContextSnapshot"]
        if input_data.get("safetyContext"):
            result["safetyContext"] = input_data["safetyContext"]
        return result

    def _synthetic_living_myth_material_input(
        self, input_data: LivingMythReviewInput
    ) -> MaterialInterpretationInput:
        chapter = (
            (input_data.get("methodContextSnapshot") or {})
            .get("livingMythContext", {})
            .get("currentLifeChapter", {})
        )
        text = (
            "\n".join(
                [
                    str(input_data.get("explicitQuestion") or "").strip(),
                    str(chapter.get("label") or chapter.get("chapterLabel") or "").strip(),
                    str(chapter.get("summary") or chapter.get("chapterSummary") or "").strip(),
                ]
            ).strip()
            or "living myth review request"
        )
        result: MaterialInterpretationInput = {
            "userId": input_data["userId"],
            "materialType": "reflection",
            "materialText": text,
            "sessionContext": normalize_session_context(None),
            "hermesMemoryContext": normalize_hermes_memory_context(
                input_data.get("hermesMemoryContext")
            ),
            "options": normalize_options(None),
        }
        if input_data.get("lifeContextSnapshot"):
            result["lifeContextSnapshot"] = compact_life_context_snapshot(
                input_data["lifeContextSnapshot"]
            )
        if input_data.get("methodContextSnapshot"):
            result["methodContextSnapshot"] = input_data["methodContextSnapshot"]
        if input_data.get("safetyContext"):
            result["safetyContext"] = input_data["safetyContext"]
        return result

    def _synthetic_analysis_packet_material_input(
        self, input_data: AnalysisPacketInput
    ) -> MaterialInterpretationInput:
        text = "\n".join(
            [
                str(input_data.get("explicitQuestion") or "").strip(),
                str(input_data.get("packetFocus") or "").strip(),
                "analysis packet",
            ]
        ).strip()
        result: MaterialInterpretationInput = {
            "userId": input_data["userId"],
            "materialType": "reflection",
            "materialText": text or "analysis packet request",
            "sessionContext": normalize_session_context(None),
            "hermesMemoryContext": normalize_hermes_memory_context(
                input_data.get("hermesMemoryContext")
            ),
            "options": normalize_options(None),
        }
        if input_data.get("lifeContextSnapshot"):
            result["lifeContextSnapshot"] = compact_life_context_snapshot(
                input_data["lifeContextSnapshot"]
            )
        if input_data.get("methodContextSnapshot"):
            result["methodContextSnapshot"] = input_data["methodContextSnapshot"]
        if input_data.get("safetyContext"):
            result["safetyContext"] = input_data["safetyContext"]
        return result

    def _synthetic_brief_material_input(
        self, input_data: RhythmicBriefInput
    ) -> MaterialInterpretationInput:
        seed = input_data["seed"]
        result: MaterialInterpretationInput = {
            "userId": input_data["userId"],
            "materialType": "reflection",
            "materialText": str(
                seed.get("summaryHint") or seed.get("titleHint") or "brief request"
            ),
            "sessionContext": normalize_session_context(None),
            "hermesMemoryContext": normalize_hermes_memory_context(
                input_data.get("hermesMemoryContext")
            ),
            "options": normalize_options(None),
        }
        if input_data.get("lifeContextSnapshot"):
            result["lifeContextSnapshot"] = compact_life_context_snapshot(
                input_data["lifeContextSnapshot"]
            )
        if input_data.get("methodContextSnapshot"):
            result["methodContextSnapshot"] = input_data["methodContextSnapshot"]
        if input_data.get("safetyContext"):
            result["safetyContext"] = input_data["safetyContext"]
        return result
