from __future__ import annotations

import asyncio
import json
import logging
import os
from collections.abc import Awaitable, Callable
from typing import Literal, NotRequired, TypedDict

from ..domain.normalization import compact_life_context_snapshot
from ..domain.types import (
    AnalysisPacketInput,
    CirculationSummaryInput,
    LifeContextSnapshot,
    LivingMythReviewInput,
    MaterialInterpretationInput,
    PracticeRecommendationInput,
    RhythmicBriefInput,
    ThresholdReviewInput,
)
from .contracts import (
    LlmAnalysisPacketOutput,
    LlmInterpretationOutput,
    LlmLivingMythReviewOutput,
    LlmPracticeOutput,
    LlmRhythmicBriefOutput,
    LlmThresholdReviewOutput,
    LlmWeeklyReviewOutput,
)
from .json_schema import (
    INTERPRETATION_OUTPUT_SCHEMA,
    extract_json_object,
    schema_text,
)
from .ports import CirculatioLlmPort
from .prompt_builder import (
    build_analysis_packet_messages,
    build_interpretation_messages,
    build_life_context_messages,
    build_living_myth_review_messages,
    build_practice_messages,
    build_rhythmic_brief_messages,
    build_threshold_review_messages,
    build_weekly_review_messages,
)

LOGGER = logging.getLogger(__name__)


class HermesAuxiliaryClientFns(TypedDict):
    async_call_llm: Callable[..., Awaitable[object]]
    extract_content_or_reasoning: Callable[[object], str]


class ModelPathProbeResult(TypedDict, total=False):
    status: Literal["ok", "unavailable", "call_failed", "invalid_json"]
    imported: bool
    functionsPresent: bool
    callAttempted: bool
    jsonParsed: bool
    message: str
    details: NotRequired[dict[str, object]]


class HermesModelAdapter(CirculatioLlmPort):
    """Hermes-backed model adapter with JSON-only responses.

    Imports from the Hermes runtime are intentionally lazy so repository tests can
    run without Hermes installed on the active Python path.
    """

    def __init__(
        self,
        *,
        provider: str | None = "auto",
        model: str | None = None,
        temperature: float = 0.2,
        max_interpret_tokens: int = 2600,
        max_review_tokens: int = 1800,
        max_practice_tokens: int = 1400,
        max_brief_tokens: int = 1000,
        max_life_context_tokens: int = 1600,
        request_timeout_seconds: float | None = None,
    ) -> None:
        self._provider = provider
        self._model = model
        self._temperature = temperature
        self._max_interpret_tokens = max_interpret_tokens
        self._max_review_tokens = max_review_tokens
        self._max_practice_tokens = max_practice_tokens
        self._max_brief_tokens = max_brief_tokens
        self._max_life_context_tokens = max_life_context_tokens
        self._request_timeout_seconds = self._normalize_timeout_seconds(
            request_timeout_seconds
            if request_timeout_seconds is not None
            else os.environ.get("CIRCULATIO_LLM_TIMEOUT_SECONDS"),
            default=30.0,
        )
        self._debug_llm = os.environ.get("CIRCULATIO_DEBUG_LLM") == "1"

    async def interpret_material(
        self,
        input_data: MaterialInterpretationInput,
    ) -> LlmInterpretationOutput:
        messages = build_interpretation_messages(input_data)
        client = self._load_auxiliary_client()
        payload = await self._call_json_with_client(
            client,
            messages,
            max_tokens=self._max_interpret_tokens,
            schema=INTERPRETATION_OUTPUT_SCHEMA,
            schema_name="circulatio_interpretation",
        )
        output = self._normalize_interpretation_output(payload)
        contract = self._assess_interpretation_output(output)
        self._debug_log_llm_event(
            "interpretation_contract_assessed",
            payload=output,
            details=contract,
        )
        if contract["status"] not in {"structured", "thin_structured"}:
            repaired = await self._repair_interpretation_contract(
                client=client,
                messages=messages,
                output=output,
                max_tokens=self._max_interpret_tokens,
            )
            if repaired is not None:
                repaired_contract = self._assess_interpretation_output(repaired)
                self._debug_log_llm_event(
                    "interpretation_contract_reassessed",
                    payload=repaired,
                    details=repaired_contract,
                )
                if repaired_contract["status"] == "structured":
                    return repaired
        return output

    async def generate_weekly_review(
        self,
        input_data: CirculationSummaryInput,
    ) -> LlmWeeklyReviewOutput:
        payload = await self._call_json(
            build_weekly_review_messages(input_data),
            max_tokens=self._max_review_tokens,
        )
        result: LlmWeeklyReviewOutput = {
            "userFacingResponse": str(payload.get("userFacingResponse", "")).strip(),
        }
        active_themes = self._list_of_scalars(payload.get("activeThemes"))
        if active_themes:
            result["activeThemes"] = active_themes
        practice_recommendation = self._dict_value(payload.get("practiceRecommendation"))
        if practice_recommendation:
            result["practiceRecommendation"] = practice_recommendation
        return result

    async def generate_practice(
        self,
        input_data: PracticeRecommendationInput,
    ) -> LlmPracticeOutput:
        payload = await self._call_json(
            build_practice_messages(input_data),
            max_tokens=self._max_practice_tokens,
        )
        practice_recommendation = self._dict_value(payload.get("practiceRecommendation"))
        if not self._is_practice_candidate(practice_recommendation):
            practice_recommendation = {}
        follow_up_prompt = str(payload.get("followUpPrompt", "")).strip()
        adaptation_notes = self._list_of_scalars(payload.get("adaptationNotes"))
        if practice_recommendation:
            if follow_up_prompt and not practice_recommendation.get("followUpPrompt"):
                practice_recommendation["followUpPrompt"] = follow_up_prompt
            if adaptation_notes and not practice_recommendation.get("adaptationNotes"):
                practice_recommendation["adaptationNotes"] = adaptation_notes
        result: LlmPracticeOutput = {
            "practiceRecommendation": practice_recommendation,
            "userFacingResponse": str(payload.get("userFacingResponse", "")).strip(),
        }
        if follow_up_prompt:
            result["followUpPrompt"] = follow_up_prompt
        if adaptation_notes:
            result["adaptationNotes"] = adaptation_notes
        return result

    async def generate_rhythmic_brief(
        self,
        input_data: RhythmicBriefInput,
    ) -> LlmRhythmicBriefOutput:
        payload = await self._call_json(
            build_rhythmic_brief_messages(input_data),
            max_tokens=self._max_brief_tokens,
        )
        result: LlmRhythmicBriefOutput = {
            "title": str(payload.get("title", "")).strip(),
            "summary": str(payload.get("summary", "")).strip(),
            "userFacingResponse": str(payload.get("userFacingResponse", "")).strip(),
        }
        suggested_action = str(payload.get("suggestedAction", "")).strip()
        if suggested_action:
            result["suggestedAction"] = suggested_action
        supporting_refs = self._list_of_scalars(payload.get("supportingRefs"))
        if supporting_refs:
            result["supportingRefs"] = supporting_refs
        return result

    async def generate_threshold_review(
        self,
        input_data: ThresholdReviewInput,
    ) -> LlmThresholdReviewOutput:
        payload = await self._call_json(
            build_threshold_review_messages(input_data),
            max_tokens=self._max_review_tokens,
        )
        result: LlmThresholdReviewOutput = {
            "userFacingResponse": str(payload.get("userFacingResponse", "")).strip(),
            "thresholdProcesses": self._list_of_dicts(payload.get("thresholdProcesses")),
        }
        reality_anchors = self._list_of_dicts(payload.get("realityAnchors"))
        if reality_anchors:
            result["realityAnchors"] = reality_anchors
        invitations = self._list_of_dicts(payload.get("invitations"))
        if invitations:
            result["invitations"] = invitations
        practice_recommendation = self._dict_value(payload.get("practiceRecommendation"))
        if self._is_practice_candidate(practice_recommendation):
            result["practiceRecommendation"] = practice_recommendation
        proposal_candidates = self._filter_dicts(
            payload.get("proposalCandidates"), validator=self._is_proposal_candidate
        )
        if proposal_candidates:
            result["proposalCandidates"] = proposal_candidates
        return result

    async def generate_living_myth_review(
        self,
        input_data: LivingMythReviewInput,
    ) -> LlmLivingMythReviewOutput:
        payload = await self._call_json(
            build_living_myth_review_messages(input_data),
            max_tokens=self._max_review_tokens,
        )
        result: LlmLivingMythReviewOutput = {
            "userFacingResponse": str(payload.get("userFacingResponse", "")).strip(),
            "mythicQuestions": self._list_of_dicts(payload.get("mythicQuestions")),
            "thresholdMarkers": self._list_of_dicts(payload.get("thresholdMarkers")),
            "complexEncounters": self._list_of_dicts(payload.get("complexEncounters")),
        }
        life_chapter = self._dict_value(payload.get("lifeChapter"))
        if life_chapter:
            result["lifeChapter"] = life_chapter
        integration_contour = self._dict_value(payload.get("integrationContour"))
        if integration_contour:
            result["integrationContour"] = integration_contour
        symbolic_wellbeing = self._dict_value(payload.get("symbolicWellbeing"))
        if symbolic_wellbeing:
            result["symbolicWellbeing"] = symbolic_wellbeing
        practice_recommendation = self._dict_value(payload.get("practiceRecommendation"))
        if self._is_practice_candidate(practice_recommendation):
            result["practiceRecommendation"] = practice_recommendation
        proposal_candidates = self._filter_dicts(
            payload.get("proposalCandidates"), validator=self._is_proposal_candidate
        )
        if proposal_candidates:
            result["proposalCandidates"] = proposal_candidates
        return result

    async def generate_analysis_packet(
        self,
        input_data: AnalysisPacketInput,
    ) -> LlmAnalysisPacketOutput:
        payload = await self._call_json(
            build_analysis_packet_messages(input_data),
            max_tokens=self._max_review_tokens,
        )
        return {
            "packetTitle": str(payload.get("packetTitle", "")).strip(),
            "sections": self._list_of_dicts(payload.get("sections")),
            "includedMaterialIds": self._list_of_scalars(payload.get("includedMaterialIds")),
            "includedRecordRefs": self._list_of_dicts(payload.get("includedRecordRefs")),
            "evidenceIds": self._list_of_scalars(payload.get("evidenceIds")),
            "userFacingResponse": str(payload.get("userFacingResponse", "")).strip(),
            "supportingRefs": self._list_of_scalars(payload.get("supportingRefs")),
        }

    async def summarize_life_context(
        self,
        *,
        user_id: str,
        window_start: str,
        window_end: str,
        raw_context: dict[str, object],
    ) -> LifeContextSnapshot:
        payload = await self._call_json(
            build_life_context_messages(
                user_id=user_id,
                window_start=window_start,
                window_end=window_end,
                raw_context=raw_context,
            ),
            max_tokens=self._max_life_context_tokens,
        )
        snapshot: LifeContextSnapshot = {
            "windowStart": str(payload.get("windowStart") or window_start),
            "windowEnd": str(payload.get("windowEnd") or window_end),
            "source": "hermes-life-os",
        }
        life_event_refs = self._list_of_dicts(payload.get("lifeEventRefs"))
        if life_event_refs:
            snapshot["lifeEventRefs"] = life_event_refs
        for field in (
            "moodSummary",
            "energySummary",
            "focusSummary",
            "mentalStateSummary",
            "habitSummary",
        ):
            value = payload.get(field)
            if value:
                snapshot[field] = str(value)  # type: ignore[index]
        notable_changes = self._list_of_scalars(payload.get("notableChanges"))
        if notable_changes:
            snapshot["notableChanges"] = notable_changes
        return compact_life_context_snapshot(snapshot) or snapshot

    def _list_of_dicts(self, value: object) -> list[dict[str, object]]:
        if not isinstance(value, list):
            return []
        return [dict(item) for item in value if isinstance(item, dict)]

    def _filter_dicts(
        self,
        value: object,
        *,
        validator: Callable[[dict[str, object]], bool],
    ) -> list[dict[str, object]]:
        if not isinstance(value, list):
            return []
        result: list[dict[str, object]] = []
        for item in value:
            if not isinstance(item, dict):
                continue
            candidate = dict(item)
            if validator(candidate):
                result.append(candidate)
        return result

    def _dict_value(self, value: object) -> dict[str, object]:
        if not isinstance(value, dict):
            return {}
        return dict(value)

    def _list_of_scalars(self, value: object) -> list[str]:
        if not isinstance(value, list):
            return []
        return [str(item) for item in value if isinstance(item, (str, int, float, bool))]

    def _debug_log_llm_event(
        self,
        stage: str,
        *,
        response: object | None = None,
        text: str | None = None,
        payload: dict[str, object] | None = None,
        details: dict[str, object] | None = None,
        error: Exception | None = None,
    ) -> None:
        if not self._debug_llm:
            return
        event: dict[str, object] = {
            "stage": stage,
            "provider": self._provider,
            "model": self._model,
        }
        if response is not None:
            event["responseType"] = type(response).__name__
            event["responsePreview"] = self._truncate_text(repr(response), 1200)
        if text is not None:
            event["textPreview"] = self._truncate_text(text, 4000)
            event["textLength"] = len(text)
        if payload is not None:
            keys = sorted(str(key) for key in payload.keys())
            event["parsedKeys"] = keys
            event["parsedShape"] = {
                key: self._describe_json_value(payload.get(key)) for key in keys
            }
        if details is not None:
            event["details"] = details
        if error is not None:
            event["errorType"] = type(error).__name__
            event["error"] = str(error)
        LOGGER.warning(
            "Circulatio Hermes adapter debug: %s", json.dumps(event, sort_keys=True, default=str)
        )

    def _normalize_interpretation_output(
        self, payload: dict[str, object]
    ) -> LlmInterpretationOutput:
        practice_recommendation = self._dict_value(payload.get("practiceRecommendation"))
        result: LlmInterpretationOutput = {
            "symbolMentions": self._filter_dicts(
                payload.get("symbolMentions"), validator=self._is_symbol_candidate
            ),
            "figureMentions": self._filter_dicts(
                payload.get("figureMentions"), validator=self._is_figure_candidate
            ),
            "motifMentions": self._filter_dicts(
                payload.get("motifMentions"), validator=self._is_motif_candidate
            ),
            "lifeContextLinks": self._filter_dicts(
                payload.get("lifeContextLinks"), validator=self._is_life_context_link_candidate
            ),
            "observations": self._filter_dicts(
                payload.get("observations"), validator=self._is_observation_candidate
            ),
            "hypotheses": self._filter_dicts(
                payload.get("hypotheses"), validator=self._is_hypothesis_candidate
            ),
            "practiceRecommendation": practice_recommendation
            if self._is_practice_candidate(practice_recommendation)
            else {},
            "proposalCandidates": self._filter_dicts(
                payload.get("proposalCandidates"), validator=self._is_proposal_candidate
            ),
            "userFacingResponse": str(payload.get("userFacingResponse", "")).strip(),
            "clarifyingQuestion": str(payload.get("clarifyingQuestion", "")).strip(),
        }
        depth_readiness = self._dict_value(payload.get("depthReadiness"))
        if self._is_depth_readiness_candidate(depth_readiness):
            result["depthReadiness"] = depth_readiness
        method_gate = self._dict_value(payload.get("methodGate"))
        if self._is_method_gate_candidate(method_gate):
            result["methodGate"] = method_gate
        amplification_prompts = self._filter_dicts(
            payload.get("amplificationPrompts"), validator=self._is_amplification_prompt_candidate
        )
        if amplification_prompts:
            result["amplificationPrompts"] = amplification_prompts
        dream_series_suggestions = self._filter_dicts(
            payload.get("dreamSeriesSuggestions"),
            validator=self._is_dream_series_suggestion_candidate,
        )
        if dream_series_suggestions:
            result["dreamSeriesSuggestions"] = dream_series_suggestions
        individuation = self._dict_value(payload.get("individuation"))
        if individuation:
            result["individuation"] = individuation
        return result

    def _has_required_text_fields(self, candidate: dict[str, object], *fields: str) -> bool:
        return all(str(candidate.get(field) or "").strip() for field in fields)

    def _has_scalar_list(self, value: object) -> bool:
        return bool(self._list_of_scalars(value))

    def _is_symbol_candidate(self, candidate: dict[str, object]) -> bool:
        return self._has_required_text_fields(
            candidate, "refKey", "surfaceText", "canonicalName", "category"
        )

    def _is_figure_candidate(self, candidate: dict[str, object]) -> bool:
        return self._has_required_text_fields(candidate, "refKey", "surfaceText", "label", "role")

    def _is_motif_candidate(self, candidate: dict[str, object]) -> bool:
        return self._has_required_text_fields(
            candidate, "refKey", "surfaceText", "canonicalName", "motifType"
        )

    def _is_life_context_link_candidate(self, candidate: dict[str, object]) -> bool:
        if not self._has_required_text_fields(candidate, "refKey", "summary"):
            return False
        return bool(
            str(candidate.get("lifeEventRefId") or "").strip()
            or str(candidate.get("stateSnapshotField") or "").strip()
        )

    def _is_observation_candidate(self, candidate: dict[str, object]) -> bool:
        return self._has_required_text_fields(
            candidate, "kind", "statement"
        ) and self._has_scalar_list(candidate.get("supportingRefs"))

    def _is_hypothesis_candidate(self, candidate: dict[str, object]) -> bool:
        return self._has_required_text_fields(
            candidate,
            "claim",
            "hypothesisType",
            "confidence",
            "userTestPrompt",
            "phrasingPolicy",
        ) and self._has_scalar_list(candidate.get("supportingRefs"))

    def _is_practice_candidate(self, candidate: dict[str, object]) -> bool:
        return (
            self._has_required_text_fields(candidate, "type", "reason")
            and isinstance(candidate.get("durationMinutes"), int)
            and isinstance(candidate.get("requiresConsent"), bool)
            and self._has_scalar_list(candidate.get("instructions"))
        )

    def _is_proposal_candidate(self, candidate: dict[str, object]) -> bool:
        return (
            self._has_required_text_fields(candidate, "action", "entityType", "reason")
            and isinstance(candidate.get("payload"), dict)
            and self._has_scalar_list(candidate.get("supportingRefs"))
        )

    def _is_depth_readiness_candidate(self, candidate: dict[str, object]) -> bool:
        return (
            self._has_required_text_fields(candidate, "status")
            and isinstance(candidate.get("allowedMoves"), dict)
            and isinstance(candidate.get("reasons"), list)
        )

    def _is_method_gate_candidate(self, candidate: dict[str, object]) -> bool:
        return (
            self._has_required_text_fields(candidate, "depthLevel")
            and isinstance(candidate.get("missingPrerequisites"), list)
            and isinstance(candidate.get("blockedMoves"), list)
            and isinstance(candidate.get("requiredPrompts"), list)
            and isinstance(candidate.get("responseConstraints"), list)
        )

    def _is_amplification_prompt_candidate(self, candidate: dict[str, object]) -> bool:
        return self._has_required_text_fields(
            candidate, "canonicalName", "surfaceText", "promptText", "reason"
        )

    def _is_dream_series_suggestion_candidate(self, candidate: dict[str, object]) -> bool:
        return (
            self._has_required_text_fields(candidate, "label", "narrativeRole", "confidence")
            and isinstance(candidate.get("matchScore"), (int, float))
            and isinstance(candidate.get("matchingFeatures"), list)
        )

    def _has_meaningful_practice_candidate(self, value: dict[str, object]) -> bool:
        if not value:
            return False
        if any(str(value.get(field) or "").strip() for field in ("type", "target", "reason")):
            return True
        return bool(self._list_of_scalars(value.get("instructions")))

    def _assess_interpretation_output(self, output: LlmInterpretationOutput) -> dict[str, object]:
        counts = {
            "symbolMentions": len(output.get("symbolMentions", [])),
            "figureMentions": len(output.get("figureMentions", [])),
            "motifMentions": len(output.get("motifMentions", [])),
            "lifeContextLinks": len(output.get("lifeContextLinks", [])),
            "observations": len(output.get("observations", [])),
            "hypotheses": len(output.get("hypotheses", [])),
            "proposalCandidates": len(output.get("proposalCandidates", [])),
            "depthReadiness": 1 if output.get("depthReadiness") else 0,
            "methodGate": 1 if output.get("methodGate") else 0,
            "amplificationPrompts": len(output.get("amplificationPrompts", [])),
            "dreamSeriesSuggestions": len(output.get("dreamSeriesSuggestions", [])),
            "practiceRecommendation": 1
            if self._has_meaningful_practice_candidate(output.get("practiceRecommendation", {}))
            else 0,
            "userFacingResponse": 1 if str(output.get("userFacingResponse", "")).strip() else 0,
            "clarifyingQuestion": 1 if str(output.get("clarifyingQuestion", "")).strip() else 0,
        }
        interpretive_signal_count = sum(
            counts[field]
            for field in (
                "symbolMentions",
                "figureMentions",
                "motifMentions",
                "observations",
                "hypotheses",
                "proposalCandidates",
                "depthReadiness",
                "methodGate",
                "amplificationPrompts",
                "dreamSeriesSuggestions",
            )
        )
        if interpretive_signal_count > 0:
            return {
                "status": "structured",
                "reason": "interpretive_fields_present",
                "counts": counts,
            }
        if counts["clarifyingQuestion"] and not counts["userFacingResponse"]:
            return {
                "status": "thin_structured",
                "reason": "clarifying_question_present",
                "counts": counts,
            }
        if counts["lifeContextLinks"] or counts["practiceRecommendation"]:
            return {
                "status": "thin_structured",
                "reason": "only_context_or_practice_fields_present",
                "counts": counts,
            }
        if counts["userFacingResponse"]:
            return {
                "status": "narrative_only",
                "reason": "only_narrative_fields_present",
                "counts": counts,
            }
        return {
            "status": "empty",
            "reason": "no_interpretation_fields_present",
            "counts": counts,
        }

    async def _repair_interpretation_contract(
        self,
        *,
        client: HermesAuxiliaryClientFns,
        messages: list[dict[str, str]],
        output: LlmInterpretationOutput,
        max_tokens: int,
    ) -> LlmInterpretationOutput | None:
        repair_messages = messages + [
            {
                "role": "assistant",
                "content": json.dumps(output, sort_keys=True, default=str),
            },
            {
                "role": "user",
                "content": (
                    "Your previous answer did not satisfy Circulatio's "
                    "structured interpretation contract. "
                    "Return JSON only and preserve the same evidence "
                    "boundary.\n"
                    "- Include every required schema key.\n"
                    "- Do not return narrative-only JSON.\n"
                    "- If userFacingResponse is non-empty, also include at "
                    "least one grounded item in symbolMentions, "
                    "figureMentions, motifMentions, observations, "
                    "hypotheses, or proposalCandidates.\n"
                    "- If the material is too thin, keep the interpretive "
                    "arrays empty and use clarifyingQuestion "
                    "instead of a polished interpretation.\n"
                    "Schema:\n"
                    f"{schema_text(INTERPRETATION_OUTPUT_SCHEMA)}"
                ),
            },
        ]
        try:
            payload = await self._call_json_with_client(
                client,
                repair_messages,
                max_tokens=max_tokens,
            )
        except Exception as exc:
            self._debug_log_llm_event(
                "interpretation_contract_repair_failed",
                payload=output,
                error=exc,
            )
            return None
        return self._normalize_interpretation_output(payload)

    def _describe_json_value(self, value: object) -> object:
        if isinstance(value, list):
            first_item = value[0] if value else None
            return {
                "type": "list",
                "length": len(value),
                "firstItemType": type(first_item).__name__ if first_item is not None else None,
            }
        if isinstance(value, dict):
            return {
                "type": "dict",
                "keys": sorted(str(key) for key in value.keys()),
            }
        return {"type": type(value).__name__, "value": self._truncate_text(value, 200)}

    def _truncate_text(self, value: object, limit: int) -> str:
        text = str(value)
        return text if len(text) <= limit else text[: limit - 3] + "..."

    async def verify_model_path(self, *, perform_call: bool = False) -> ModelPathProbeResult:
        try:
            client = self._load_auxiliary_client()
        except Exception as exc:
            return {
                "status": "unavailable",
                "imported": False,
                "functionsPresent": False,
                "callAttempted": False,
                "jsonParsed": False,
                "message": str(exc),
            }
        if not perform_call:
            return {
                "status": "ok",
                "imported": True,
                "functionsPresent": True,
                "callAttempted": False,
                "jsonParsed": False,
                "message": ("Hermes auxiliary client import and function validation succeeded."),
            }
        messages = [{"role": "user", "content": 'Return valid JSON only: {"ok": true}'}]
        try:
            payload = await self._call_json_with_client(client, messages, max_tokens=120)
        except ValueError as exc:
            return {
                "status": "invalid_json",
                "imported": True,
                "functionsPresent": True,
                "callAttempted": True,
                "jsonParsed": False,
                "message": str(exc),
            }
        except Exception as exc:
            return {
                "status": "call_failed",
                "imported": True,
                "functionsPresent": True,
                "callAttempted": True,
                "jsonParsed": False,
                "message": str(exc),
            }
        return {
            "status": "ok",
            "imported": True,
            "functionsPresent": True,
            "callAttempted": True,
            "jsonParsed": isinstance(payload, dict),
            "message": ("Hermes auxiliary client call and JSON parsing succeeded."),
        }

    def _load_auxiliary_client(self) -> HermesAuxiliaryClientFns:
        try:
            from agent import auxiliary_client
        except Exception as exc:
            raise RuntimeError("Hermes auxiliary client is unavailable.") from exc
        async_call_llm = getattr(auxiliary_client, "async_call_llm", None)
        extract_content_or_reasoning = getattr(
            auxiliary_client, "extract_content_or_reasoning", None
        )
        if not callable(async_call_llm) or not callable(extract_content_or_reasoning):
            raise RuntimeError(
                "Hermes auxiliary client is missing async_call_llm() or "
                "extract_content_or_reasoning()."
            )
        return {
            "async_call_llm": async_call_llm,
            "extract_content_or_reasoning": extract_content_or_reasoning,
        }

    async def _call_json(
        self,
        messages: list[dict[str, str]],
        *,
        max_tokens: int,
    ) -> dict[str, object]:
        client = self._load_auxiliary_client()
        return await self._call_json_with_client(client, messages, max_tokens=max_tokens)

    async def _call_json_with_client(
        self,
        client: HermesAuxiliaryClientFns,
        messages: list[dict[str, str]],
        *,
        max_tokens: int,
        schema: dict[str, object] | None = None,
        schema_name: str | None = None,
    ) -> dict[str, object]:
        async_call_llm = client["async_call_llm"]
        extract_content_or_reasoning = client["extract_content_or_reasoning"]
        base_kwargs: dict[str, object] = {
            "provider": self._provider,
            "model": self._model,
            "messages": messages,
            "temperature": self._temperature,
            "max_tokens": max_tokens,
        }
        response = await self._call_llm_json_stage(
            async_call_llm,
            stage="initial_json",
            base_kwargs=base_kwargs,
            schema=schema,
            schema_name=schema_name,
        )
        text = extract_content_or_reasoning(response)
        self._debug_log_llm_event("initial_raw", response=response, text=text)
        try:
            payload = extract_json_object(text)
            self._debug_log_llm_event("initial_parsed", payload=payload)
            return payload
        except ValueError as exc:
            self._debug_log_llm_event("initial_parse_failed", text=text, error=exc)
            repair_response = await self._call_llm_json_stage(
                async_call_llm,
                stage="repair_json",
                base_kwargs={
                    "provider": self._provider,
                    "model": self._model,
                    "messages": messages
                    + [
                        {"role": "assistant", "content": text},
                        {
                            "role": "user",
                            "content": (
                                "Return the exact same answer as valid JSON only. "
                                "No markdown fences, commentary, or extra prose."
                            ),
                        },
                    ],
                    "temperature": 0,
                    "max_tokens": max_tokens,
                },
                schema=schema,
                schema_name=schema_name,
            )
            repair_text = extract_content_or_reasoning(repair_response)
            self._debug_log_llm_event("repair_raw", response=repair_response, text=repair_text)
            payload = extract_json_object(repair_text)
            self._debug_log_llm_event("repair_parsed", payload=payload)
            return payload

    async def _call_llm_json_stage(
        self,
        async_call_llm: Callable[..., Awaitable[object]],
        *,
        stage: str,
        base_kwargs: dict[str, object],
        schema: dict[str, object] | None,
        schema_name: str | None,
    ) -> object:
        request_kwargs = dict(base_kwargs)
        request_kwargs.update(self._json_output_kwargs(schema=schema, schema_name=schema_name))
        try:
            return await self._call_llm_with_timeout(
                async_call_llm,
                stage=stage,
                **request_kwargs,
            )
        except TypeError as exc:
            if (
                not request_kwargs.keys() - base_kwargs.keys()
                or not self._is_unsupported_kwarg_error(exc)
            ):
                raise
            self._debug_log_llm_event(
                f"{stage}_structured_kwargs_rejected",
                details={"schemaName": schema_name},
                error=exc,
            )
            return await self._call_llm_with_timeout(
                async_call_llm,
                stage=stage,
                **base_kwargs,
            )

    def _json_output_kwargs(
        self,
        *,
        schema: dict[str, object] | None,
        schema_name: str | None,
    ) -> dict[str, object]:
        if schema is None:
            return {}
        name = schema_name or "circulatio_json_output"
        return {
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": name,
                    "schema": schema,
                    "strict": True,
                },
            },
            "json_schema": schema,
        }

    def _is_unsupported_kwarg_error(self, exc: TypeError) -> bool:
        message = str(exc)
        return any(
            needle in message
            for needle in (
                "unexpected keyword argument",
                "got an unexpected keyword",
                "takes no keyword arguments",
            )
        )

    def _normalize_timeout_seconds(self, value: object, *, default: float) -> float | None:
        if value is None or value == "":
            return default
        try:
            timeout = float(value)
        except (TypeError, ValueError):
            return default
        if timeout <= 0:
            return None
        return timeout

    async def _call_llm_with_timeout(
        self,
        async_call_llm: Callable[..., Awaitable[object]],
        *,
        stage: str,
        **kwargs: object,
    ) -> object:
        timeout = self._request_timeout_seconds
        if timeout is None:
            return await async_call_llm(**kwargs)
        try:
            return await asyncio.wait_for(async_call_llm(**kwargs), timeout=timeout)
        except TimeoutError as exc:
            self._debug_log_llm_event(
                "timeout",
                details={"stage": stage, "timeoutSeconds": timeout},
                error=exc,
            )
            raise TimeoutError(
                f"Circulatio Hermes LLM {stage} call exceeded {timeout:.1f}s."
            ) from exc
