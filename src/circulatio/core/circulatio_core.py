from __future__ import annotations

import hashlib
import json
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
from ..domain.presentation import (
    PresentationRitualPlanningInput,
    PresentationRitualPlanResult,
    PresentationSourceRef,
    RequestedRitualSurfaces,
    RitualRenderPolicy,
    VoiceScriptSegment,
)
from ..domain.presentation_surfaces import normalize_requested_ritual_surfaces
from ..domain.types import (
    AnalysisPacketInput,
    AnalysisPacketResult,
    CirculationSummaryInput,
    CirculationSummaryResult,
    CoachMoveKind,
    DepthReadinessAssessment,
    InterpretationResult,
    LivingMythReviewInput,
    LivingMythReviewResult,
    MaterialInterpretationInput,
    MethodContextSnapshot,
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
    build_clarification_plan_from_llm,
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
    build_packet_function_dynamics_from_llm,
    build_practice_from_llm,
    build_proposals_from_llm,
    build_review_memory_write_plan,
    build_supporting_ref_map,
    build_symbol_mentions_from_llm,
    build_typology_assessment_from_llm,
    try_llm_interpretation,
    validate_evidence_integrity,
)
from .method_state_policy import (
    derive_runtime_method_state_policy,
    get_active_goal_tension_items,
    merge_method_gate_with_policy,
    reconcile_depth_readiness_with_policy,
)
from .practice_engine import PracticeEngine
from .safety_gate import SafetyGate
from .typology_evidence import build_typology_packet_fallback

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
        llm_output, llm_fallback_reason = await try_llm_interpretation(self._llm, normalized_input)
        if llm_output is None:
            return build_unavailable_llm_result(
                run_id=run_id,
                material_id=material_id,
                safety=safety,
                evidence_ledger=evidence_ledger,
                input_data=normalized_input,
                fallback_reason=llm_fallback_reason,
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
        runtime_policy = derive_runtime_method_state_policy(
            normalized_input.get("methodContextSnapshot")
        )
        method_gate = merge_method_gate_with_policy(method_gate, runtime_policy)
        depth_readiness = reconcile_depth_readiness_with_policy(depth_readiness, runtime_policy)
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
            goal_tensions=self._practice_goal_tensions(
                normalized_input.get("methodContextSnapshot")
            ),
            body_states=self._practice_body_states(normalized_input.get("methodContextSnapshot")),
            practice_hints=normalized_input.get("practiceHints"),
            method_context=normalized_input.get("methodContextSnapshot"),
            runtime_policy=runtime_policy,
            fallback_reason="llm_missing_practice_fallback_to_journaling",
        )

        clarification_plan = build_clarification_plan_from_llm(
            llm_output,
            preferred_targets=runtime_policy.get("preferredClarificationTargets"),
        )
        clarifying_question = (
            str(clarification_plan.get("questionText", "")).strip()
            if clarification_plan
            else str(llm_output.get("clarifyingQuestion", "")).strip()
        ) or None
        clarification_intent = llm_output.get("clarificationIntent")
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
            status="structured",
            reason="structured_interpretation_available",
            diagnostic_reason=None,
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

        compensation = build_compensation_assessment(
            hypotheses,
            normalized_input.get("methodContextSnapshot"),
        )
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
        if clarification_plan:
            result["clarificationPlan"] = clarification_plan
        if isinstance(clarification_intent, dict) and clarification_intent.get("refKey"):
            result["clarificationIntent"] = dict(clarification_intent)
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
        runtime_policy = derive_runtime_method_state_policy(input_data.get("methodContextSnapshot"))
        method_gate = merge_method_gate_with_policy(None, runtime_policy)
        depth_readiness = reconcile_depth_readiness_with_policy(None, runtime_policy)
        selected_move = self._coach_selected_move(input_data.get("methodContextSnapshot"))
        selected_move_kind = str(selected_move.get("kind") or "").strip()
        llm_alive_today: dict[str, object] | None = None
        if self._llm is not None:
            try:
                llm_alive_today = await self._llm.generate_alive_today(input_data)
            except Exception:
                LOGGER.warning(
                    "Circulatio alive-today LLM path failed; using bounded fallback.",
                    exc_info=True,
                )
                llm_alive_today = None

        practice_candidate = (
            build_practice_from_llm(llm_alive_today.get("practiceRecommendation"))
            if llm_alive_today
            else None
        )
        resource_invitation = self._resource_invitation_from_value(
            llm_alive_today.get("resourceInvitation") if llm_alive_today else None
        ) or self._resource_invitation_from_value(selected_move.get("resourceInvitation"))
        practice = self._practice_engine.reconcile_llm_practice(
            practice=practice_candidate,
            method_gate=method_gate,
            depth_readiness=depth_readiness,
            safety=self._clear_safety_disposition(),
            consent_preferences=input_data.get("methodContextSnapshot", {}).get(
                "consentPreferences", []
            ),
            goal_tensions=self._practice_goal_tensions(input_data.get("methodContextSnapshot")),
            body_states=self._practice_body_states(input_data.get("methodContextSnapshot")),
            practice_hints=input_data.get("practiceHints"),
            method_context=input_data.get("methodContextSnapshot"),
            runtime_policy=runtime_policy,
            fallback_reason="llm_missing_practice_fallback_to_journaling",
        )
        active_themes = (
            [str(item) for item in llm_alive_today.get("activeThemes", [])]
            if llm_alive_today
            else []
        )
        response = (
            str(llm_alive_today.get("userFacingResponse", "")).strip() if llm_alive_today else ""
        )
        if not response:
            response = self._alive_today_fallback_response(
                selected_move=selected_move,
                resource_invitation=resource_invitation,
                method_context=input_data.get("methodContextSnapshot"),
            )
        result: CirculationSummaryResult = {
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
        selected_loop_key = str(
            (llm_alive_today or {}).get("selectedCoachLoopKey")
            or selected_move.get("loopKey")
            or ""
        ).strip()
        if selected_loop_key:
            result["selectedCoachLoopKey"] = selected_loop_key
        coach_move_kind = str(
            (llm_alive_today or {}).get("coachMoveKind") or selected_move.get("kind") or ""
        ).strip()
        if coach_move_kind:
            result["coachMoveKind"] = cast(CoachMoveKind, coach_move_kind)
        follow_up_question = (
            str(llm_alive_today.get("followUpQuestion", "")).strip() if llm_alive_today else ""
        )
        if not follow_up_question:
            follow_up_question = self._alive_today_fallback_question(selected_move=selected_move)
        if follow_up_question:
            result["followUpQuestion"] = follow_up_question
        suggested_action = (
            str(llm_alive_today.get("suggestedAction", "")).strip() if llm_alive_today else ""
        )
        if not suggested_action and resource_invitation is not None:
            suggested_action = str(resource_invitation["resource"].get("title") or "").strip()
        if suggested_action:
            result["suggestedAction"] = suggested_action
        if resource_invitation is not None:
            result["resourceInvitation"] = resource_invitation
        withheld_reason = (
            str(llm_alive_today.get("withheldReason", "")).strip() if llm_alive_today else ""
        )
        if not withheld_reason and not selected_move_kind:
            withheld_reason = "coach_state_no_eligible_move"
        if withheld_reason:
            result["withheldReason"] = withheld_reason
        return result

    async def generate_weekly_review_summary(
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

        runtime_policy = derive_runtime_method_state_policy(input_data.get("methodContextSnapshot"))
        method_gate = merge_method_gate_with_policy(None, runtime_policy)
        depth_readiness = reconcile_depth_readiness_with_policy(None, runtime_policy)
        practice = self._practice_engine.reconcile_llm_practice(
            practice=build_practice_from_llm(
                llm_review.get("practiceRecommendation") if llm_review else None
            ),
            method_gate=method_gate,
            depth_readiness=depth_readiness,
            safety=self._clear_safety_disposition(),
            consent_preferences=input_data.get("methodContextSnapshot", {}).get(
                "consentPreferences", []
            ),
            goal_tensions=self._practice_goal_tensions(input_data.get("methodContextSnapshot")),
            body_states=self._practice_body_states(input_data.get("methodContextSnapshot")),
            practice_hints=input_data.get("practiceHints"),
            method_context=input_data.get("methodContextSnapshot"),
            runtime_policy=runtime_policy,
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

    async def plan_presentation_ritual(
        self,
        input_data: PresentationRitualPlanningInput,
    ) -> PresentationRitualPlanResult:
        requested, surface_warnings = self._presentation_requested_surfaces(
            input_data.get("requestedSurfaces", {})
        )
        render_policy = self._presentation_render_policy(input_data.get("renderPolicy", {}))
        safety_context = input_data.get("safetyContext", {})
        activation = str(safety_context.get("userReportedActivation") or "").strip()
        grounding_only = activation in {"high", "overwhelming"} or bool(
            safety_context.get("intoxicationReported")
        )
        warnings: list[str] = list(surface_warnings)
        blocked_surfaces: list[str] = []
        if grounding_only:
            warnings.append("presentation_grounding_only_safety_adjustment")
            blocked_surfaces.extend(["cinema", "intense_breath_holds"])
        video_allowed = bool(render_policy.get("videoAllowed", False))
        external_allowed = bool(render_policy.get("externalProvidersAllowed", False))
        if requested.get("cinema", {}).get("enabled") and not video_allowed:
            requested["cinema"] = {**requested.get("cinema", {}), "enabled": False}
            blocked_surfaces.append("cinema")
            warnings.append("cinema_disabled_without_video_allowed")
        if grounding_only and requested.get("cinema", {}).get("enabled"):
            requested["cinema"] = {**requested.get("cinema", {}), "enabled": False}
        image_requested = bool(requested.get("image", {}).get("enabled"))
        if image_requested and not external_allowed:
            requested["image"] = {**requested.get("image", {}), "enabled": False}
            blocked_surfaces.append("image")
            warnings.append("image_disabled_without_external_providers")
        duration = self._presentation_duration(render_policy)
        source_digest = input_data["sourceDigest"]
        source_refs = input_data.get("sourceRefs", [])
        source_ref_ids = self._presentation_source_ref_ids(source_refs)
        title = str(source_digest.get("title") or "Weekly ritual").strip() or "Weekly ritual"
        summary = str(source_digest.get("summary") or "").strip()
        if not summary:
            summary = "A short ritual from the material already available in Circulatio."
        active_themes = [
            str(item) for item in source_digest.get("activeThemes", []) if str(item).strip()
        ]
        recurring_symbols = [
            str(item) for item in source_digest.get("recurringSymbols", []) if str(item).strip()
        ]
        segments = self._presentation_voice_segments(
            summary=summary,
            active_themes=active_themes,
            recurring_symbols=recurring_symbols,
            source_ref_ids=source_ref_ids,
            requested=requested,
            grounding_only=grounding_only,
        )
        body = "\n\n".join(segment["text"] for segment in segments if segment.get("text"))
        plan_id = create_id("ritual_plan")
        breath = self._presentation_breath_spec(requested, grounding_only=grounding_only)
        meditation = self._presentation_meditation_spec(
            requested,
            source_ref_ids=source_ref_ids,
            target_seconds=duration["targetSeconds"],
            grounding_only=grounding_only,
        )
        image_plan = self._presentation_image_plan(
            requested=requested,
            external_allowed=external_allowed,
            source_digest=source_digest,
            source_ref_ids=source_ref_ids,
        )
        cinema_plan = {
            "enabled": bool(requested.get("cinema", {}).get("enabled")),
            "storyboard": [],
            "maxDurationSeconds": min(
                int(requested.get("cinema", {}).get("maxDurationSeconds", 30) or 30), 30
            ),
        }
        render_mode = cast(str, render_policy.get("mode", "dry_run_manifest"))
        frontend_route = "/artifacts/{artifactId}"
        evidence_ids = [str(item) for item in source_digest.get("evidenceIds", []) if str(item)]
        context_snapshot_ids = [
            str(item) for item in source_digest.get("contextSnapshotIds", []) if str(item)
        ]
        thread_keys = [str(item) for item in source_digest.get("threadKeys", []) if str(item)]
        provider_restrictions = ["no_raw_material_to_external_provider"]
        if not external_allowed:
            provider_restrictions.append("external_providers_disabled")
        plan = {
            "id": plan_id,
            "schemaVersion": "circulatio.presentation.plan.v1",
            "userId": input_data["userId"],
            "title": title,
            "ritualIntent": input_data["ritualIntent"],
            "narrativeMode": input_data["narrativeMode"],
            "sourceType": input_data["sourceType"],
            "sourceRefs": source_refs,
            "generatedAt": input_data["generatedAt"],
            "windowStart": input_data["windowStart"],
            "windowEnd": input_data["windowEnd"],
            "privacyClass": input_data.get("privacyClass", "private"),
            "locale": input_data.get("locale", "en-US"),
            "duration": duration,
            "text": {
                "summary": self._presentation_compact_text(summary, limit=220),
                "body": body,
            },
            "voiceScript": {
                "segments": segments,
                "silenceMarkers": [
                    {
                        "afterSegmentId": "seg_breath",
                        "durationMs": 8000,
                        "purpose": "settling",
                    }
                ],
                "contraindications": ["high_activation"] if grounding_only else [],
            },
            "speechMarkupPlan": {
                "format": "structured_intent",
                "ssmlAllowed": False,
                "pausePolicy": "renderer_may_render_pauses",
            },
            "breath": breath,
            "meditation": meditation,
            "visualPromptPlan": {"image": image_plan, "cinema": cinema_plan},
            "interactionSpec": {
                "finishPrompt": str(
                    input_data.get("completionPolicy", {}).get(
                        "reflectionPrompt",
                        "What did you notice in your body or attention after this?",
                    )
                ),
                "captureReactionTime": False,
                "captureBodyResponse": True,
                "maxPrompts": 1,
            },
            "deliveryPolicy": {
                "renderMode": render_mode,
                "frontendRoute": frontend_route,
                **(
                    {"expiresAt": render_policy["delivery"]["expiresAt"]}
                    if isinstance(render_policy.get("delivery"), dict)
                    and render_policy["delivery"].get("expiresAt")
                    else {}
                ),
            },
            "safetyBoundary": {
                "depthWorkAllowed": not grounding_only,
                "blockedSurfaces": list(dict.fromkeys(blocked_surfaces)),
                "groundingInstruction": ("Stop if this increases activation; orient to the room."),
                "providerRestrictions": provider_restrictions,
            },
            "provenance": {
                "evidenceIds": evidence_ids,
                "contextSnapshotIds": context_snapshot_ids,
                "threadKeys": thread_keys,
                "generatedFromSurface": input_data["sourceType"],
            },
        }
        stable_hash = self._presentation_stable_hash(plan)
        plan["stableHash"] = stable_hash
        allowed_surfaces = ["text"]
        for surface in ("captions", "breath", "meditation", "audio", "image", "cinema"):
            if requested.get(surface, {}).get("enabled"):
                allowed_surfaces.append(surface)
        cost_estimate = {
            "currency": "USD",
            "totalEstimated": 0.0,
            "components": [
                {
                    "surface": surface,
                    "providerKind": "mock",
                    "estimated": 0.0,
                    "cacheKey": f"{stable_hash}:{surface}:mock",
                }
                for surface in allowed_surfaces
                if surface != "text"
            ],
            "budgetExceeded": False,
        }
        render_request = {
            "planId": plan_id,
            "rendererVersion": "ritual-renderer.v1",
            "allowedSurfaces": allowed_surfaces,
            "artifactCacheKey": stable_hash,
            "dryRunAvailable": True,
        }
        return {
            "plan": plan,
            "costEstimate": cost_estimate,
            "renderRequest": render_request,
            "warnings": warnings,
        }

    def _presentation_requested_surfaces(
        self,
        requested: RequestedRitualSurfaces,
    ) -> tuple[RequestedRitualSurfaces, list[str]]:
        normalized, warnings = normalize_requested_ritual_surfaces(requested)
        normalized = dict(normalized)
        text_config = dict(normalized.get("text", {}))
        text_config["enabled"] = True
        normalized["text"] = text_config
        normalized.setdefault("captions", {"enabled": True, "format": "segments"})
        normalized.setdefault("breath", {"enabled": True, "request": {}})
        normalized.setdefault("meditation", {"enabled": True, "request": {}})
        normalized.setdefault("audio", {"enabled": False})
        normalized.setdefault("image", {"enabled": False})
        normalized.setdefault("cinema", {"enabled": False, "maxDurationSeconds": 30})
        return cast(RequestedRitualSurfaces, normalized), warnings

    def _presentation_render_policy(self, policy: RitualRenderPolicy) -> RitualRenderPolicy:
        normalized = dict(policy)
        normalized.setdefault("mode", "dry_run_manifest")
        normalized.setdefault("defaultDurationSeconds", 300)
        normalized.setdefault("maxDurationSeconds", 480)
        normalized.setdefault("externalProvidersAllowed", False)
        normalized.setdefault("providerAllowlist", ["mock", "local"])
        normalized.setdefault("videoAllowed", False)
        normalized.setdefault("maxCost", {"currency": "USD", "amount": 0})
        normalized.setdefault(
            "cachePolicy", {"read": True, "write": True, "cacheScope": "local_dev"}
        )
        normalized.setdefault(
            "sourceDataPolicy",
            {
                "allowRawMaterialTextInPlan": False,
                "allowRawMaterialTextToProviders": False,
                "providerPromptPolicy": "derived_user_facing_only",
            },
        )
        return cast(RitualRenderPolicy, normalized)

    def _presentation_duration(self, render_policy: RitualRenderPolicy) -> dict[str, int]:
        default_seconds = int(render_policy.get("defaultDurationSeconds", 300) or 300)
        max_seconds = int(render_policy.get("maxDurationSeconds", 480) or 480)
        target_seconds = min(max(default_seconds, 60), max(max_seconds, 60))
        return {
            "targetSeconds": target_seconds,
            "minSeconds": min(180, target_seconds),
            "maxSeconds": max(max_seconds, target_seconds),
        }

    def _presentation_voice_segments(
        self,
        *,
        summary: str,
        active_themes: list[str],
        recurring_symbols: list[str],
        source_ref_ids: list[str],
        requested: RequestedRitualSurfaces,
        grounding_only: bool,
    ) -> list[VoiceScriptSegment]:
        tone = "steady"
        pace = "measured"
        segments: list[VoiceScriptSegment] = [
            {
                "id": "seg_opening",
                "role": "opening",
                "text": "Let this arrive as material already held, not as a task to solve.",
                "pace": pace,
                "tone": tone,
                "pauseAfterMs": 1200,
                "sourceRefIds": source_ref_ids,
            }
        ]
        if requested.get("breath", {}).get("enabled"):
            breath_text = (
                "Keep the breath natural and orient to the room."
                if grounding_only
                else "Take a few measured breaths, letting the exhale be slightly longer."
            )
            segments.append(
                {
                    "id": "seg_breath",
                    "role": "breath_instruction",
                    "text": breath_text,
                    "pace": pace,
                    "tone": tone,
                    "pauseAfterMs": 1600,
                    "sourceRefIds": [],
                    **({"safetyNote": "grounding_only"} if grounding_only else {}),
                }
            )
        source_lines = [summary]
        if active_themes:
            source_lines.append("Active themes: " + ", ".join(active_themes[:4]) + ".")
        if recurring_symbols:
            source_lines.append("Recurring images: " + ", ".join(recurring_symbols[:4]) + ".")
        segments.append(
            {
                "id": "seg_source",
                "role": "source_reflection",
                "text": self._presentation_compact_text(" ".join(source_lines), limit=620),
                "pace": pace,
                "tone": tone,
                "pauseAfterMs": 1800,
                "sourceRefIds": source_ref_ids,
            }
        )
        if requested.get("meditation", {}).get("enabled"):
            segments.append(
                {
                    "id": "seg_meditation",
                    "role": "meditation_instruction",
                    "text": (
                        "Let the field settle around what is already known. "
                        "Nothing else has to be produced."
                    ),
                    "pace": pace,
                    "tone": tone,
                    "pauseAfterMs": 2200,
                    "sourceRefIds": source_ref_ids,
                }
            )
        segments.append(
            {
                "id": "seg_closing",
                "role": "closing",
                "text": "When you are ready, notice one body response and leave the rest unforced.",
                "pace": pace,
                "tone": tone,
                "pauseAfterMs": 1000,
                "sourceRefIds": source_ref_ids,
            }
        )
        return segments

    def _presentation_breath_spec(
        self,
        requested: RequestedRitualSurfaces,
        *,
        grounding_only: bool,
    ) -> dict[str, object]:
        breath = requested.get("breath", {})
        request = breath.get("request", {}) if isinstance(breath.get("request"), dict) else {}
        pattern = str(request.get("pattern") or "lengthened_exhale")
        if grounding_only:
            pattern = "orienting"
        if pattern == "box_breath" and not grounding_only:
            inhale, hold, exhale, rest = 4, 4, 4, 0
        elif pattern == "steadying" and not grounding_only:
            inhale, hold, exhale, rest = 4, 1, 6, 2
        else:
            inhale, hold, exhale, rest = 4, 0, 6, 2
        cycles = int(request.get("cycles", 5) or 5)
        return {
            "enabled": bool(breath.get("enabled", True)),
            "pattern": pattern,
            "inhaleSeconds": inhale,
            "holdSeconds": 0 if grounding_only else hold,
            "exhaleSeconds": exhale,
            "restSeconds": rest,
            "cycles": min(max(cycles, 1), 12),
            "visualForm": "pacer",
            "syncMarkers": [],
        }

    def _presentation_meditation_spec(
        self,
        requested: RequestedRitualSurfaces,
        *,
        source_ref_ids: list[str],
        target_seconds: int,
        grounding_only: bool,
    ) -> dict[str, object]:
        meditation = requested.get("meditation", {})
        request = (
            meditation.get("request", {}) if isinstance(meditation.get("request"), dict) else {}
        )
        duration_ms = int(request.get("durationMs", min(target_seconds * 1000, 180000)) or 180000)
        return {
            "enabled": bool(meditation.get("enabled", True)),
            "fieldType": str(request.get("fieldType") or "coherence_convergence"),
            "durationMs": max(min(duration_ms, target_seconds * 1000), 30000),
            "sourceRefs": source_ref_ids,
            "macroProgressPolicy": "session_progress",
            "microMotion": "convergence",
            "instructionDensity": str(request.get("instructionDensity") or "sparse"),
            "safetyBoundary": (
                "grounding_only" if grounding_only else "grounding_only_if_activation_high"
            ),
            "syncMarkers": [],
        }

    def _presentation_image_plan(
        self,
        *,
        requested: RequestedRitualSurfaces,
        external_allowed: bool,
        source_digest: dict[str, object],
        source_ref_ids: list[str],
    ) -> dict[str, object]:
        enabled = bool(requested.get("image", {}).get("enabled")) and external_allowed
        prompt = ""
        if enabled:
            prompt = self._presentation_compact_text(
                "Abstract non-literal ritual field from: "
                + str(source_digest.get("summary") or "held Circulatio material"),
                limit=240,
            )
        return {
            "enabled": enabled,
            **({"prompt": prompt} if prompt else {}),
            "privacyNotes": ["no raw dream text", "derived user-facing summary only"],
            "sourceRefIds": source_ref_ids,
            "providerPromptPolicy": "sanitized_visual_only" if enabled else "none",
        }

    def _presentation_source_ref_ids(self, refs: list[PresentationSourceRef]) -> list[str]:
        result: list[str] = []
        for item in refs:
            candidate = str(item.get("id") or item.get("recordId") or "").strip()
            if candidate and candidate not in result:
                result.append(candidate)
        return result

    def _presentation_compact_text(self, text: str, *, limit: int) -> str:
        normalized = " ".join(str(text).split())
        if len(normalized) <= limit:
            return normalized
        return normalized[: limit - 3].rstrip() + "..."

    def _presentation_stable_hash(self, plan: dict[str, object]) -> str:
        stable = {
            key: value
            for key, value in plan.items()
            if key not in {"id", "generatedAt", "stableHash"}
        }
        encoded = json.dumps(stable, sort_keys=True, ensure_ascii=False, default=str).encode()
        return hashlib.sha256(encoded).hexdigest()

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
        runtime_policy = derive_runtime_method_state_policy(
            normalized_input.get("methodContextSnapshot")
        )
        method_gate = merge_method_gate_with_policy(None, runtime_policy)
        depth_readiness = reconcile_depth_readiness_with_policy(None, runtime_policy)
        if not safety["depthWorkAllowed"]:
            practice = self._practice_engine.reconcile_llm_practice(
                practice=None,
                safety=safety,
                method_gate=method_gate,
                depth_readiness=depth_readiness,
                consent_preferences=consent_preferences,
                goal_tensions=self._practice_goal_tensions(
                    normalized_input.get("methodContextSnapshot")
                ),
                body_states=self._practice_body_states(
                    normalized_input.get("methodContextSnapshot")
                ),
                method_context=normalized_input.get("methodContextSnapshot"),
                runtime_policy=runtime_policy,
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
            method_gate=method_gate,
            depth_readiness=depth_readiness,
            consent_preferences=consent_preferences,
            goal_tensions=self._practice_goal_tensions(
                normalized_input.get("methodContextSnapshot")
            ),
            body_states=self._practice_body_states(normalized_input.get("methodContextSnapshot")),
            method_context=normalized_input.get("methodContextSnapshot"),
            runtime_policy=runtime_policy,
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
        runtime_policy = derive_runtime_method_state_policy(
            normalized_input.get("methodContextSnapshot")
        )
        method_gate = merge_method_gate_with_policy(None, runtime_policy)
        depth_readiness = reconcile_depth_readiness_with_policy(None, runtime_policy)
        if not safety["depthWorkAllowed"]:
            practice = self._practice_engine.reconcile_llm_practice(
                practice=None,
                safety=safety,
                method_gate=method_gate,
                depth_readiness=depth_readiness,
                consent_preferences=consent_preferences,
                goal_tensions=self._practice_goal_tensions(
                    normalized_input.get("methodContextSnapshot")
                ),
                body_states=self._practice_body_states(
                    normalized_input.get("methodContextSnapshot")
                ),
                method_context=normalized_input.get("methodContextSnapshot"),
                runtime_policy=runtime_policy,
                fallback_reason="safety_gate_blocks_living_myth_review",
            )
            return {
                "userFacingResponse": (
                    "Living-myth synthesis is withheld while depth work is paused."
                ),
                "mythicQuestions": [],
                "thresholdMarkers": [],
                "complexEncounters": [],
                "practiceRecommendation": practice,
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
            method_gate=method_gate,
            depth_readiness=depth_readiness,
            consent_preferences=consent_preferences,
            goal_tensions=self._practice_goal_tensions(
                normalized_input.get("methodContextSnapshot")
            ),
            body_states=self._practice_body_states(normalized_input.get("methodContextSnapshot")),
            method_context=normalized_input.get("methodContextSnapshot"),
            runtime_policy=runtime_policy,
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
        analytic_lens = str(normalized_input.get("analyticLens") or "generic").strip() or "generic"
        typology_digest = (
            cast(dict[str, object], normalized_input.get("typologyEvidenceDigest"))
            if isinstance(normalized_input.get("typologyEvidenceDigest"), dict)
            else None
        )
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
            function_dynamics = None
            if analytic_lens == "typology_function_dynamics":
                supporting_ref_map = build_supporting_ref_map(
                    payload=normalized_input,
                    evidence_items=cast(
                        list[dict[str, object]],
                        normalized_input.get("evidence", []),
                    ),
                )
                function_dynamics = build_packet_function_dynamics_from_llm(
                    llm_output.get("functionDynamics"),
                    supporting_ref_map=supporting_ref_map,
                )
                if function_dynamics is None:
                    _, function_dynamics = build_typology_packet_fallback(typology_digest)
            result: AnalysisPacketResult = {
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
            if function_dynamics is not None:
                result["functionDynamics"] = function_dynamics
            return result
        sections: list[dict[str, object]] = []
        included_record_refs: list[dict[str, object]] = []
        evidence_ids: list[str] = []
        function_dynamics = None
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
        if analytic_lens == "typology_function_dynamics" and safety["depthWorkAllowed"]:
            function_dynamics_section, function_dynamics = build_typology_packet_fallback(
                typology_digest
            )
            if function_dynamics_section is not None:
                sections.append(function_dynamics_section)
                for item in function_dynamics_section.get("items", []):
                    if not isinstance(item, dict):
                        continue
                    for record_ref in item.get("relatedRecordRefs", []):
                        if not isinstance(record_ref, dict):
                            continue
                        record_type = str(record_ref.get("recordType") or "").strip()
                        record_id = str(record_ref.get("recordId") or "").strip()
                        if record_type and record_id:
                            included_record_refs.append(
                                {"recordType": record_type, "recordId": record_id}
                            )
                    for evidence_id in item.get("evidenceIds", []):
                        candidate = str(evidence_id or "").strip()
                        if candidate and candidate not in evidence_ids:
                            evidence_ids.append(candidate)
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
        user_facing_response = (
            "A bounded packet is available using existing approved summaries "
            "rather than new symbolic synthesis."
        )
        if isinstance(function_dynamics, dict):
            status = str(function_dynamics.get("status") or "").strip()
            if status == "readable":
                user_facing_response = (
                    "A bounded function-dynamics packet is available from evidence already in view."
                )
            elif status == "signals_only":
                user_facing_response = (
                    "A bounded packet is available with tentative "
                    "function-dynamics signals from the current window."
                )
        result: AnalysisPacketResult = {
            "packetTitle": "Analysis packet",
            "sections": cast(list[dict[str, object]], sections),
            "includedMaterialIds": included_material_ids,
            "includedRecordRefs": cast(list[dict[str, str]], deduped_record_refs),
            "evidenceIds": evidence_ids,
            "source": "bounded_fallback",
            "userFacingResponse": user_facing_response,
            "llmHealth": {
                "status": "fallback",
                "reason": "bounded_analysis_packet_fallback",
                "source": "fallback",
            },
        }
        if function_dynamics is not None:
            result["functionDynamics"] = function_dynamics
        return result

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
        selected_move = self._coach_selected_move(normalized_input.get("methodContextSnapshot"))
        selected_resource_invitation = self._resource_invitation_from_value(
            selected_move.get("resourceInvitation")
        )
        runtime_policy = derive_runtime_method_state_policy(
            normalized_input.get("methodContextSnapshot")
        )
        method_gate = merge_method_gate_with_policy(None, runtime_policy)
        depth_readiness = reconcile_depth_readiness_with_policy(None, runtime_policy)
        if not safety["depthWorkAllowed"]:
            practice = self._practice_engine.reconcile_llm_practice(
                practice=None,
                safety=safety,
                method_gate=method_gate,
                depth_readiness=depth_readiness,
                consent_preferences=consent_preferences,
                goal_tensions=self._practice_goal_tensions(
                    normalized_input.get("methodContextSnapshot")
                ),
                body_states=self._practice_body_states(
                    normalized_input.get("methodContextSnapshot")
                ),
                method_context=normalized_input.get("methodContextSnapshot"),
                runtime_policy=runtime_policy,
                fallback_reason="safety_blocked_grounding_fallback",
            )
            return {
                "practiceRecommendation": practice,
                "userFacingResponse": (
                    "Depth work is paused for now. A short grounding step is available, "
                    "and you can ignore it without guilt."
                ),
                **(
                    {"resourceInvitation": selected_resource_invitation}
                    if selected_resource_invitation is not None
                    else {}
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
            method_gate=method_gate,
            depth_readiness=depth_readiness,
            consent_preferences=consent_preferences,
            goal_tensions=self._practice_goal_tensions(
                normalized_input.get("methodContextSnapshot")
            ),
            body_states=self._practice_body_states(normalized_input.get("methodContextSnapshot")),
            practice_hints=normalized_input.get("practiceHints")
            or normalized_input.get("adaptationHints"),
            adaptation_hints=normalized_input.get("adaptationHints"),
            method_context=normalized_input.get("methodContextSnapshot"),
            runtime_policy=runtime_policy,
            fallback_reason="llm_missing_practice_fallback_to_journaling",
        )
        response = str(llm_output.get("userFacingResponse", "")).strip() if llm_output else ""
        if not response:
            response = (
                "A bounded practice is available if you want it. You can skip it without guilt."
            )
        result: PracticeRecommendationResult = {
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
        resource_invitation = (
            self._resource_invitation_from_value(
                llm_output.get("resourceInvitation") if llm_output else None
            )
            or selected_resource_invitation
        )
        if resource_invitation is not None:
            result["resourceInvitation"] = resource_invitation
        return result

    async def generate_rhythmic_brief(
        self,
        input_data: RhythmicBriefInput,
    ) -> RhythmicBriefResult:
        synthetic = self._synthetic_brief_material_input(input_data)
        safety = self._safety_gate.assess(synthetic)
        seed = cast(dict[str, object], input_data.get("seed", {}))
        brief_type = str(seed.get("briefType") or "daily")
        resource_invitation = self._resource_invitation_from_value(seed.get("resourceInvitation"))
        runtime_policy = derive_runtime_method_state_policy(input_data.get("methodContextSnapshot"))
        if runtime_policy.get("depthLevel") == "grounding_only" and brief_type not in {
            "practice_followup",
            "resource_invitation",
            "ritual_invitation",
        }:
            return {
                "withheld": True,
                "withheldReason": "method_state_policy_blocks_symbolic_brief",
            }
        if not safety["depthWorkAllowed"] and brief_type not in {
            "practice_followup",
            "resource_invitation",
            "ritual_invitation",
        }:
            return {
                "withheld": True,
                "withheldReason": "safety_gate_blocks_symbolic_brief",
            }
        if brief_type == "ritual_invitation":
            return {
                "title": str(seed.get("titleHint") or "Weekly ritual invitation"),
                "summary": str(
                    seed.get("summaryHint")
                    or "A weekly ritual can be prepared if you explicitly accept it."
                ),
                "suggestedAction": str(
                    seed.get("suggestedActionHint")
                    or "Accept to prepare the plan; ignore it and nothing is rendered."
                ),
                "userFacingResponse": (
                    "A weekly ritual invitation is available. Accept it to prepare a plan; "
                    "nothing is planned or rendered until then."
                ),
                "llmHealth": {
                    "status": "fallback",
                    "reason": "ritual_invitation_fallback",
                    "source": "fallback",
                },
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
            llm_resource_invitation = self._resource_invitation_from_value(
                llm_output.get("resourceInvitation")
            )
            if llm_resource_invitation is not None:
                result["resourceInvitation"] = llm_resource_invitation
            elif resource_invitation is not None:
                result["resourceInvitation"] = resource_invitation
            return result
        if brief_type in {"practice_followup", "resource_invitation"}:
            return {
                "title": str(
                    seed.get("titleHint")
                    or (
                        "Resource invitation"
                        if brief_type == "resource_invitation"
                        else "Practice follow-up"
                    )
                ),
                "summary": str(
                    seed.get("summaryHint")
                    or (
                        "A grounded support resource is available if you want it."
                        if brief_type == "resource_invitation"
                        else "A prior practice may be ready for a gentle follow-up."
                    )
                ),
                "suggestedAction": str(
                    seed.get("suggestedActionHint")
                    or (
                        "You can try the resource, or simply leave it for later."
                        if brief_type == "resource_invitation"
                        else "You can note what happened, or simply leave it for later."
                    )
                ),
                "userFacingResponse": (
                    (
                        "A grounded resource is available if you want it. "
                        "You can ignore this without guilt."
                    )
                    if brief_type == "resource_invitation"
                    else "A prior practice may be ready for a light check-in. "
                    "You can ignore this without guilt."
                ),
                **(
                    {"resourceInvitation": resource_invitation}
                    if resource_invitation is not None
                    else {}
                ),
                "llmHealth": {
                    "status": "fallback",
                    "reason": "resource_invitation_fallback"
                    if brief_type == "resource_invitation"
                    else "practice_followup_fallback",
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
        goal_tensions: list[dict[str, object]] | None = None,
        body_states: list[dict[str, object]] | None = None,
        method_context: dict[str, object] | None = None,
        runtime_policy: dict[str, object] | None = None,
    ) -> dict[str, object]:
        return self._practice_engine.reconcile_llm_practice(
            practice=cast(object, practice),
            method_gate=method_gate,
            depth_readiness=depth_readiness,
            safety=safety,
            consent_preferences=consent_preferences,
            goal_tensions=goal_tensions,
            body_states=body_states,
            method_context=cast(MethodContextSnapshot | None, method_context),
            runtime_policy=runtime_policy,
        )

    def _clear_safety_disposition(self) -> SafetyDisposition:
        return {"status": "clear", "flags": ["none"], "depthWorkAllowed": True}

    def _practice_goal_tensions(self, method_context: object | None) -> list[dict[str, object]]:
        return get_active_goal_tension_items(cast(MethodContextSnapshot | None, method_context))

    def _practice_body_states(self, method_context: object | None) -> list[dict[str, object]]:
        if not isinstance(method_context, dict):
            return []
        return [
            item for item in method_context.get("recentBodyStates", []) if isinstance(item, dict)
        ]

    def _coach_selected_move(self, method_context: object | None) -> dict[str, object]:
        if not isinstance(method_context, dict):
            return {}
        coach_state = method_context.get("coachState")
        if not isinstance(coach_state, dict):
            return {}
        selected_move = coach_state.get("selectedMove")
        return dict(selected_move) if isinstance(selected_move, dict) else {}

    def _resource_invitation_from_value(self, value: object) -> dict[str, object] | None:
        if not isinstance(value, dict):
            return None
        resource = value.get("resource")
        if not isinstance(resource, dict):
            return None
        if not str(resource.get("id") or "").strip():
            return None
        return dict(value)

    def _alive_today_fallback_response(
        self,
        *,
        selected_move: dict[str, object],
        resource_invitation: dict[str, object] | None,
        method_context: MethodContextSnapshot | None,
    ) -> str:
        if resource_invitation is not None:
            title = str(resource_invitation.get("resource", {}).get("title") or "").strip()
            if title:
                return (
                    f"{title} is available as a gentler next step. "
                    "You can leave it alone if now is not the moment."
                )
            return (
                "A grounded resource is available as a gentler next step. "
                "You can leave it alone if now is not the moment."
            )
        summary_hint = str(selected_move.get("summaryHint") or "").strip()
        if summary_hint:
            return summary_hint
        if isinstance(method_context, dict) and method_context.get("recentBodyStates"):
            return "A recent body signal is being held without forcing meaning."
        return (
            "Nothing needs to be forced right now. Circulatio is holding the live threads lightly."
        )

    def _alive_today_fallback_question(self, *, selected_move: dict[str, object]) -> str:
        if not selected_move:
            return ""
        if str(selected_move.get("kind") or "").strip() == "offer_resource":
            return ""
        prompt_frame = selected_move.get("promptFrame")
        if not isinstance(prompt_frame, dict):
            return ""
        ask_about = str(prompt_frame.get("askAbout") or "").strip()
        if ask_about:
            return ask_about[:1].upper() + ask_about[1:] + "?"
        title = str(selected_move.get("titleHint") or "").strip()
        if title:
            return f"What feels most alive around {title.lower()}?"
        return ""

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
