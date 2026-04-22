from __future__ import annotations

import logging
import re
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from typing import Literal, cast

from ..adapters.context_adapter import BuildContextInput, BuildPracticeContextInput, ContextAdapter
from ..core.adaptation_engine import AdaptationEngine
from ..core.circulatio_core import CirculatioCore
from ..core.coach_engine import CoachEngine
from ..core.method_state_policy import derive_runtime_method_state_policy
from ..core.practice_engine import PracticeEngine
from ..core.proactive_engine import ProactiveEngine
from ..core.resource_engine import ResourceEngine
from ..domain.adaptation import AdaptationSignalEvent
from ..domain.amplifications import AmplificationPromptRecord, PersonalAmplificationRecord
from ..domain.clarifications import (
    ClarificationAnswerRecord,
    ClarificationCaptureTarget,
    ClarificationPromptRecord,
)
from ..domain.conscious_attitude import ConsciousAttitudeSnapshotRecord
from ..domain.context import ContextSnapshot
from ..domain.culture import CulturalFrameRecord
from ..domain.errors import ConflictError, EntityNotFoundError, ValidationError
from ..domain.feedback import InteractionFeedbackRecord
from ..domain.goals import GoalRecord, GoalTensionRecord
from ..domain.graph import GraphNodeType, GraphQuery, GraphQueryResult
from ..domain.ids import create_id, now_iso
from ..domain.individuation import IndividuationRecord
from ..domain.integration import IntegrationRecord
from ..domain.interpretations import InterpretationRunRecord, ProposalDecisionRecord
from ..domain.journeys import JourneyRecord
from ..domain.living_myth import AnalysisPacketRecord, LivingMythReviewRecord
from ..domain.materials import MaterialRecord, MaterialRevision, StoredDreamStructure
from ..domain.memory import MemoryKernelSnapshot, MemoryRetrievalQuery
from ..domain.method_state import (
    MethodStateAppliedEntityRef,
    MethodStateCaptureCandidate,
    MethodStateCaptureRunRecord,
    MethodStateCaptureTargetKind,
)
from ..domain.normalization import normalize_options, normalize_session_context
from ..domain.patterns import PatternHistoryEntry
from ..domain.practices import PracticeSessionRecord
from ..domain.proactive import ProactiveBriefRecord
from ..domain.readiness import ConsentPreferenceRecord
from ..domain.records import DeletionMode
from ..domain.reviews import DashboardSummary, WeeklyReviewRecord
from ..domain.soma import BodyStateRecord
from ..domain.symbols import SymbolHistoryEntry, SymbolRecord
from ..domain.types import (
    AdaptationPreferenceScope,
    AmplificationSourceSummary,
    AnalysisPacketInput,
    CirculationSummaryInput,
    CirculationSummaryResult,
    CoachCaptureContract,
    CoachLoopKind,
    CoachMoveKind,
    CoachStateSummary,
    EvidenceItem,
    FeedbackValue,
    Id,
    InterpretationInteractionFeedback,
    InterpretationOptions,
    InterpretationResult,
    LifeContextSnapshot,
    LivingMythReviewInput,
    MaterialInterpretationInput,
    MemoryWritePlan,
    MemoryWriteProposal,
    MethodContextSnapshot,
    PracticeInteractionFeedback,
    PracticeOutcomeWritePayload,
    PracticePlan,
    PracticeRecommendationInput,
    ResourceInvitationSummary,
    RhythmicBriefInput,
    SafetyContext,
    SessionContext,
    ThreadDigest,
    ThresholdReviewInput,
    UserAdaptationProfileSummary,
    UserAssociationInput,
    WitnessStateSummary,
)
from ..domain.typology import TypologyLensRecord
from ..llm.ports import CirculatioMethodStateLlmPort
from ..repositories.circulatio_repository import CirculatioRepository
from .workflow_types import (
    AliveTodayResult,
    AnalysisPacketWorkflowResult,
    AnswerAmplificationPromptInput,
    AnswerClarificationInput,
    AnswerClarificationResult,
    CaptureConsciousAttitudeInput,
    CaptureRealityAnchorsInput,
    CreateAndInterpretMaterialInput,
    CreateBodyStateInput,
    CreateJourneyInput,
    CreateMaterialInput,
    DiscoveryDigestItem,
    DiscoveryResult,
    DiscoverySection,
    DiscoverySourceCounts,
    GenerateAnalysisPacketInput,
    GenerateDiscoveryInput,
    GenerateJourneyPageInput,
    GenerateLivingMythReviewInput,
    GeneratePracticeInput,
    GenerateRhythmicBriefsInput,
    GenerateThresholdReviewInput,
    GetJourneyInput,
    IntakeAnchorMaterial,
    IntakeContextItem,
    IntakeContextPacket,
    IntakeContextSourceCounts,
    IntakeHostGuidance,
    JourneyAliveTodaySurface,
    JourneyAnalysisPacketItem,
    JourneyAnalysisPacketPreview,
    JourneyAnalysisPacketSection,
    JourneyInvitationPreview,
    JourneyPageAction,
    JourneyPageCard,
    JourneyPageResult,
    JourneyPracticeContainer,
    JourneyWeeklySurface,
    ListJourneysInput,
    LivingMythReviewWorkflowResult,
    MaterialWorkflowResult,
    MethodStateWorkflowResult,
    PatternHistoryResult,
    PracticeWorkflowResult,
    ProcessMethodStateResponseInput,
    RecordAestheticResonanceInput,
    RecordInnerOuterCorrespondenceInput,
    RecordNuminousEncounterInput,
    RecordRelationalSceneInput,
    RespondPracticeInput,
    RespondRhythmicBriefInput,
    RhythmicBriefWorkflowResult,
    SetConsentPreferenceInput,
    SetCulturalFrameInput,
    SetJourneyStatusInput,
    StoreBodyStateResult,
    StoreMaterialWithIntakeContextResult,
    SymbolHistoryResult,
    ThresholdReviewWorkflowResult,
    UpdateJourneyInput,
    UpsertGoalInput,
    UpsertGoalTensionInput,
    UpsertThresholdProcessInput,
)

LOGGER = logging.getLogger(__name__)

_METHOD_STATE_POLICY_TARGETS_BY_BLOCKED_MOVE: dict[
    str, tuple[MethodStateCaptureTargetKind, ...]
] = {
    "active_imagination": ("threshold_process", "numinous_encounter"),
    "projection_language": ("projection_hypothesis",),
    "inner_outer_correspondence": ("inner_outer_correspondence",),
    "archetypal_patterning": ("typology_lens",),
    "living_myth_synthesis": ("living_myth_question",),
}

_METHOD_STATE_GROUNDING_ONLY_BLOCKED_TARGETS: tuple[MethodStateCaptureTargetKind, ...] = (
    "projection_hypothesis",
    "inner_outer_correspondence",
    "typology_lens",
    "living_myth_question",
    "threshold_process",
    "numinous_encounter",
)


class CirculatioService:
    def __init__(
        self,
        repository: CirculatioRepository,
        core: CirculatioCore,
        context_adapter: ContextAdapter | None = None,
        adaptation_engine: AdaptationEngine | None = None,
        practice_engine: PracticeEngine | None = None,
        proactive_engine: ProactiveEngine | None = None,
        coach_engine: CoachEngine | None = None,
        resource_engine: ResourceEngine | None = None,
        method_state_llm: CirculatioMethodStateLlmPort | None = None,
        trusted_amplification_sources: list[AmplificationSourceSummary] | None = None,
    ) -> None:
        self._repository = repository
        self._core = core
        self._context_adapter = context_adapter or ContextAdapter(repository)
        self._adaptation_engine = adaptation_engine or AdaptationEngine()
        self._practice_engine = practice_engine or PracticeEngine()
        self._proactive_engine = proactive_engine or ProactiveEngine()
        self._coach_engine = coach_engine or CoachEngine()
        self._resource_engine = resource_engine or ResourceEngine()
        self._method_state_llm = method_state_llm
        self._trusted_amplification_sources = deepcopy(trusted_amplification_sources or [])

    @property
    def repository(self) -> CirculatioRepository:
        return self._repository

    async def store_material(self, input_data: CreateMaterialInput) -> MaterialRecord:
        payload = deepcopy(input_data)
        payload.setdefault("source", "hermes_ui")
        return await self.create_material(payload)

    async def store_material_with_intake_context(
        self,
        input_data: CreateMaterialInput,
    ) -> StoreMaterialWithIntakeContextResult:
        payload = deepcopy(input_data)
        payload.setdefault("source", "hermes_ui")
        material = await self.create_material(payload)
        warnings: list[str] = []
        try:
            window_start, window_end = self._resolve_window(
                anchor=str(material.get("materialDate") or material.get("createdAt") or ""),
            )
        except Exception:
            LOGGER.exception(
                "Post-store intake window resolution failed for material %s",
                material["id"],
            )
            warnings.append("intake_window_fallback")
            window_start, window_end = self._resolve_window(
                anchor=str(material.get("createdAt") or now_iso()),
            )
        method_context: MethodContextSnapshot | None = None
        dashboard: DashboardSummary | None = None
        thread_digests: list[ThreadDigest] = []
        try:
            method_snapshot = await self._repository.build_method_context_snapshot_from_records(
                material["userId"],
                window_start=window_start,
                window_end=window_end,
                material_id=material["id"],
            )
            method_context = self._enrich_method_context_snapshot(
                method_snapshot,
                window_start=window_start,
                window_end=window_end,
                surface="generic",
            )
        except Exception:
            LOGGER.exception(
                "Post-store method context derivation failed for material %s",
                material["id"],
            )
            warnings.append("method_context_unavailable")
        coach_loop_digests = self._build_coach_loop_thread_digests(method_context)
        try:
            thread_digests = await self._repository.build_thread_digests_from_records(
                material["userId"],
                window_start=window_start,
                window_end=window_end,
                material_id=material["id"],
            )
        except Exception:
            LOGGER.exception(
                "Post-store thread digest derivation failed for material %s",
                material["id"],
            )
            warnings.append("thread_digest_unavailable")
        thread_digests = self._merge_thread_digests(thread_digests, coach_loop_digests)
        try:
            dashboard = await self._repository.get_dashboard_summary(material["userId"])
        except Exception:
            LOGGER.exception(
                "Post-store dashboard summary derivation failed for material %s",
                material["id"],
            )
            warnings.append("dashboard_summary_unavailable")
        warnings = list(dict.fromkeys(warnings))
        if warnings:
            warnings.append("intake_context_partial")
        try:
            intake_context = self._build_intake_context_packet(
                material=material,
                window_start=window_start,
                window_end=window_end,
                method_context=method_context,
                thread_digests=thread_digests,
                dashboard=dashboard,
                warnings=warnings,
            )
        except Exception:
            LOGGER.exception(
                "Post-store intake context packet derivation failed for material %s",
                material["id"],
            )
            fallback_warnings = list(
                dict.fromkeys([*warnings, "intake_context_unavailable", "intake_context_partial"])
            )
            intake_context = {
                "packetId": create_id("intake_context"),
                "visibility": "host_only",
                "status": "partial",
                "source": "circulatio-post-store",
                "generatedAt": now_iso(),
                "userId": material["userId"],
                "materialId": material["id"],
                "materialType": material["materialType"],
                "windowStart": window_start,
                "windowEnd": window_end,
                "anchorMaterial": self._intake_anchor_material(material),
                "hostGuidance": self._build_intake_host_guidance(
                    method_context=method_context,
                    item_count=0,
                    warnings=fallback_warnings,
                ),
                "items": [],
                "entityRefs": {},
                "sourceCounts": {
                    "recentMaterialCount": 0,
                    "recurringSymbolCount": 0,
                    "activePatternCount": 0,
                    "activeJourneyCount": 0,
                    "longitudinalSignalCount": 0,
                    "threadDigestCount": 0,
                    "intakeItemCount": 0,
                    "pendingProposalCount": 0,
                },
                "warnings": fallback_warnings,
            }
        return {"material": material, "intakeContext": intake_context}

    async def create_material(self, input_data: CreateMaterialInput) -> MaterialRecord:
        text = (input_data.get("text") or "").strip()
        summary = (input_data.get("summary") or "").strip()
        if not text and not summary:
            raise ValidationError("Material text or summary is required")
        timestamp = now_iso()
        record: MaterialRecord = {
            "id": create_id(input_data["materialType"]),
            "userId": input_data["userId"],
            "materialType": input_data["materialType"],
            "materialDate": input_data.get("materialDate", timestamp),
            "createdAt": timestamp,
            "updatedAt": timestamp,
            "status": "active",
            "privacyClass": input_data.get("privacyClass", "session_only"),
            "source": input_data.get("source", "hermes_command"),
            "linkedContextSnapshotIds": [],
            "linkedPracticeSessionIds": [],
            "tags": list(input_data.get("tags", [])),
        }
        if input_data.get("title"):
            record["title"] = input_data["title"]
        if text:
            record["text"] = text
        if summary:
            record["summary"] = summary
        if input_data.get("dreamStructure"):
            record["dreamStructure"] = deepcopy(input_data["dreamStructure"])
        return await self._repository.create_material(record)

    async def store_body_state(self, input_data: CreateBodyStateInput) -> StoreBodyStateResult:
        sensation = (input_data.get("sensation") or "").strip()
        if not sensation:
            raise ValidationError("Body-state sensation is required")
        timestamp = now_iso()
        observed_at = input_data.get("observedAt", timestamp)
        privacy_class = input_data.get("privacyClass", "session_only")
        note_text = (input_data.get("noteText") or "").strip()
        note_material: MaterialRecord | None = None
        linked_material_ids: list[Id] = list(input_data.get("linkedMaterialIds", []))
        if note_text:
            note_material = await self.store_material(
                {
                    "userId": input_data["userId"],
                    "materialType": "reflection",
                    "text": note_text,
                    "materialDate": observed_at,
                    "privacyClass": privacy_class,
                    "tags": self._merge_tags([], ["soma"]),
                }
            )
            linked_material_ids.append(note_material["id"])
        record: BodyStateRecord = {
            "id": create_id("body_state"),
            "userId": input_data["userId"],
            "source": "manual_body_note",
            "observedAt": observed_at,
            "sensation": sensation,
            "linkedMaterialIds": linked_material_ids,
            "linkedSymbolIds": [],
            "linkedGoalIds": list(input_data.get("linkedGoalIds", [])),
            "evidenceIds": list(input_data.get("evidenceIds", [])),
            "privacyClass": privacy_class,
            "status": "active",
            "createdAt": timestamp,
            "updatedAt": timestamp,
        }
        if note_material is not None:
            record["materialId"] = note_material["id"]
        for key in ("bodyRegion", "activation", "tone", "temporalContext"):
            value = input_data.get(key)
            if value:
                record[key] = value  # type: ignore[index]
        result: StoreBodyStateResult = {
            "bodyState": await self._repository.create_body_state(record)
        }
        if note_material is not None:
            result["noteMaterial"] = note_material
        return result

    async def answer_amplification_prompt(
        self,
        input_data: AnswerAmplificationPromptInput,
    ) -> PersonalAmplificationRecord:
        association_text = (input_data.get("associationText") or "").strip()
        if not association_text:
            raise ValidationError("associationText is required")
        prompt: AmplificationPromptRecord | None = None
        if input_data.get("promptId"):
            prompt = await self._repository.get_amplification_prompt(
                input_data["userId"], input_data["promptId"]
            )
            if prompt["userId"] != input_data["userId"]:
                raise ValidationError("Amplification prompt belongs to a different user.")
            if prompt.get("status") == "answered":
                response_id = prompt.get("responseAmplificationId")
                if response_id:
                    existing = await self._repository.get_personal_amplification(
                        input_data["userId"], response_id
                    )
                    comparable_existing = {
                        "canonicalName": existing["canonicalName"],
                        "surfaceText": existing["surfaceText"],
                        "associationText": existing["associationText"],
                        "feelingTone": existing.get("feelingTone"),
                        "bodySensations": list(existing.get("bodySensations", [])),
                    }
                    comparable_new = {
                        "canonicalName": input_data.get("canonicalName", prompt["canonicalName"]),
                        "surfaceText": input_data.get("surfaceText", prompt["surfaceText"]),
                        "associationText": association_text,
                        "feelingTone": input_data.get("feelingTone"),
                        "bodySensations": list(input_data.get("bodySensations", [])),
                    }
                    if comparable_existing != comparable_new:
                        raise ValidationError(
                            "Amplification prompt already has a different stored answer."
                        )
                    return existing
        timestamp = now_iso()
        record: PersonalAmplificationRecord = {
            "id": create_id("personal_amplification"),
            "userId": input_data["userId"],
            "canonicalName": (
                input_data.get("canonicalName") or prompt.get("canonicalName") if prompt else ""
            ).strip(),
            "surfaceText": (
                input_data.get("surfaceText") or prompt.get("surfaceText") if prompt else ""
            ).strip(),
            "associationText": association_text,
            "memoryRefs": list(input_data.get("memoryRefs", [])),
            "bodySensations": list(input_data.get("bodySensations", [])),
            "source": "user_answered_prompt" if prompt else "user_response",
            "evidenceIds": list(input_data.get("evidenceIds", [])),
            "privacyClass": input_data.get("privacyClass", "user_private"),
            "status": "active",
            "createdAt": timestamp,
            "updatedAt": timestamp,
        }
        if not record["canonicalName"] or not record["surfaceText"]:
            raise ValidationError("canonicalName and surfaceText are required")
        for key in ("materialId", "runId", "symbolId", "promptId"):
            value = input_data.get(key)
            if value:
                record[key] = value  # type: ignore[index]
        if prompt is not None:
            for key in ("materialId", "runId", "symbolId"):
                if prompt.get(key) and key not in record:
                    record[key] = prompt[key]  # type: ignore[index]
            record["promptId"] = prompt["id"]
        if input_data.get("feelingTone"):
            record["feelingTone"] = str(input_data["feelingTone"])
        created = await self._repository.create_personal_amplification(record)
        if prompt is not None:
            await self._repository.update_amplification_prompt(
                input_data["userId"],
                prompt["id"],
                {
                    "status": "answered",
                    "answeredAt": timestamp,
                    "responseAmplificationId": created["id"],
                    "updatedAt": timestamp,
                },
            )
        await self._record_adaptation_signal(
            user_id=input_data["userId"],
            event_type="amplification_prompt_answered",
            signals={"canonicalName": created["canonicalName"]},
        )
        return created

    async def answer_clarification(
        self,
        input_data: AnswerClarificationInput,
    ) -> AnswerClarificationResult:
        answer_text = (input_data.get("answerText") or "").strip()
        if not input_data.get("skip") and not answer_text:
            raise ValidationError("answerText is required")
        prompt: ClarificationPromptRecord | None = None
        if input_data.get("promptId"):
            prompt = await self._repository.get_clarification_prompt(
                input_data["userId"], input_data["promptId"]
            )
            if prompt["userId"] != input_data["userId"]:
                raise ValidationError("Clarification prompt belongs to a different user.")
            existing_answer_id = prompt.get("answerRecordId")
            if existing_answer_id:
                existing_answer = await self._repository.get_clarification_answer(
                    input_data["userId"], existing_answer_id
                )
                if input_data.get("skip"):
                    return {
                        "prompt": prompt,
                        "answer": existing_answer,
                        "createdRecordRefs": list(existing_answer.get("createdRecordRefs", [])),
                        "routingStatus": str(existing_answer.get("routingStatus") or "skipped"),
                    }
                comparable_existing = {
                    "answerText": str(existing_answer.get("answerText") or "").strip(),
                    "answerPayload": deepcopy(existing_answer.get("answerPayload", {})),
                }
                comparable_new = {
                    "answerText": answer_text,
                    "answerPayload": deepcopy(input_data.get("answerPayload", {})),
                }
                if comparable_existing != comparable_new:
                    raise ValidationError(
                        "Clarification prompt already has a different stored answer."
                    )
                result: AnswerClarificationResult = {
                    "answer": existing_answer,
                    "createdRecordRefs": list(existing_answer.get("createdRecordRefs", [])),
                    "routingStatus": str(existing_answer.get("routingStatus") or "routed"),
                }
                if prompt is not None:
                    result["prompt"] = prompt
                return result

        timestamp = now_iso()
        target = cast(
            ClarificationCaptureTarget,
            input_data.get("captureTargetOverride")
            or (prompt.get("captureTarget") if prompt else None)
            or "answer_only",
        )
        answer_record: ClarificationAnswerRecord = {
            "id": create_id("clarification_answer"),
            "userId": input_data["userId"],
            "answerText": answer_text,
            "captureTarget": target,
            "routingStatus": "routing_pending",
            "createdRecordRefs": [],
            "privacyClass": str(
                input_data.get("privacyClass")
                or (prompt.get("privacyClass") if prompt else None)
                or "session_only"
            ),
            "createdAt": timestamp,
            "updatedAt": timestamp,
        }
        for key in ("promptId", "materialId", "runId"):
            value = input_data.get(key) or (prompt.get(key) if prompt else None)
            if value:
                answer_record[key] = value  # type: ignore[index]
        if isinstance(input_data.get("answerPayload"), dict):
            answer_record["answerPayload"] = deepcopy(input_data["answerPayload"])

        stored_answer = await self._repository.create_clarification_answer(answer_record)
        if input_data.get("skip"):
            stored_answer = await self._repository.update_clarification_answer(
                input_data["userId"],
                stored_answer["id"],
                {
                    "routingStatus": "skipped",
                    "updatedAt": now_iso(),
                },
            )
            if prompt is not None:
                prompt = await self._repository.update_clarification_prompt(
                    input_data["userId"],
                    prompt["id"],
                    {
                        "status": "skipped",
                        "answerRecordId": stored_answer["id"],
                        "answeredAt": stored_answer["updatedAt"],
                        "updatedAt": stored_answer["updatedAt"],
                    },
                )
            await self._record_adaptation_signal(
                user_id=input_data["userId"],
                event_type="clarification_skipped",
                signals={
                    "intent": prompt.get("intent") if prompt else "other",
                    "captureTarget": target,
                    "routingStatus": "skipped",
                },
            )
            result: AnswerClarificationResult = {
                "answer": stored_answer,
                "createdRecordRefs": [],
                "routingStatus": "skipped",
            }
            if prompt is not None:
                result["prompt"] = prompt
            return result

        routing_payload = (
            deepcopy(input_data.get("answerPayload"))
            if isinstance(input_data.get("answerPayload"), dict)
            else None
        )
        created_record_refs: list[dict[str, str]] = []
        routed_record: dict[str, object] | None = None
        routing_status = "unrouted"
        validation_errors: list[str] = []

        if target == "answer_only":
            routing_status = "unrouted"
        elif routing_payload is None:
            rerouted = await self._route_clarification_answer_from_text(
                user_id=input_data["userId"],
                prompt=prompt,
                answer=stored_answer,
                capture_target=target,
            )
            if rerouted is None:
                routing_status = "needs_review"
                validation_errors.append(
                    "Structured answerPayload is required for this clarification target."
                )
            else:
                created_record_refs, routed_record, reroute_errors = rerouted
                if created_record_refs:
                    routing_status = "routed"
                else:
                    routing_status = "needs_review"
                    validation_errors.extend(reroute_errors)
        else:
            try:
                created_record_refs, routed_record = await self._route_clarification_answer(
                    user_id=input_data["userId"],
                    prompt=prompt,
                    answer=stored_answer,
                    capture_target=target,
                    payload=routing_payload,
                )
                routing_status = "routed"
            except ValidationError as exc:
                routing_status = "needs_review"
                validation_errors.append(str(exc))

        stored_answer = await self._repository.update_clarification_answer(
            input_data["userId"],
            stored_answer["id"],
            {
                "routingStatus": routing_status,
                "createdRecordRefs": created_record_refs,
                "validationErrors": validation_errors,
                "updatedAt": now_iso(),
            },
        )
        if prompt is not None:
            prompt = await self._repository.update_clarification_prompt(
                input_data["userId"],
                prompt["id"],
                {
                    "status": "answered" if routing_status == "routed" else "answered_unrouted",
                    "answerRecordId": stored_answer["id"],
                    "answeredAt": stored_answer["updatedAt"],
                    "updatedAt": stored_answer["updatedAt"],
                },
            )
        await self._record_adaptation_signal(
            user_id=input_data["userId"],
            event_type="clarification_answered"
            if routing_status == "routed"
            else "clarification_unrouted",
            signals={
                "intent": prompt.get("intent") if prompt else "other",
                "captureTarget": target,
                "expectedAnswerKind": prompt.get("expectedAnswerKind") if prompt else "free_text",
                "routingStatus": routing_status,
            },
        )
        result = {
            "answer": stored_answer,
            "createdRecordRefs": created_record_refs,
            "routingStatus": routing_status,
        }
        if prompt is not None:
            result["prompt"] = prompt
        if routed_record is not None:
            result["routedRecord"] = routed_record
        return result

    async def capture_conscious_attitude(
        self,
        input_data: CaptureConsciousAttitudeInput,
    ) -> ConsciousAttitudeSnapshotRecord:
        stance_summary = (input_data.get("stanceSummary") or "").strip()
        if not stance_summary:
            raise ValidationError("stanceSummary is required")
        timestamp = now_iso()
        record: ConsciousAttitudeSnapshotRecord = {
            "id": create_id("conscious_attitude"),
            "userId": input_data["userId"],
            "source": str(input_data.get("source") or "manual_checkin"),
            "status": str(input_data.get("status") or "user_confirmed"),
            "windowStart": input_data["windowStart"],
            "windowEnd": input_data["windowEnd"],
            "stanceSummary": stance_summary,
            "activeValues": list(input_data.get("activeValues", [])),
            "activeConflicts": list(input_data.get("activeConflicts", [])),
            "avoidedThemes": list(input_data.get("avoidedThemes", [])),
            "confidence": str(input_data.get("confidence") or "low"),
            "evidenceIds": list(input_data.get("evidenceIds", [])),
            "relatedMaterialIds": list(input_data.get("relatedMaterialIds", [])),
            "relatedGoalIds": list(input_data.get("relatedGoalIds", [])),
            "privacyClass": input_data.get("privacyClass", "user_private"),
            "createdAt": timestamp,
            "updatedAt": timestamp,
        }
        for key in ("emotionalTone", "egoPosition"):
            value = input_data.get(key)
            if value:
                record[key] = str(value)  # type: ignore[index]
        created = await self._repository.create_conscious_attitude_snapshot(record)
        await self._record_adaptation_signal(
            user_id=input_data["userId"],
            event_type="conscious_attitude_captured",
            signals={"confidence": created["confidence"]},
        )
        return created

    async def set_consent_preference(
        self,
        input_data: SetConsentPreferenceInput,
    ) -> ConsentPreferenceRecord:
        valid_scopes = {
            "shadow_work",
            "projection_language",
            "collective_amplification",
            "active_imagination",
            "somatic_correlation",
            "proactive_briefing",
            "archetypal_patterning",
            "inner_outer_correspondence",
            "living_myth_synthesis",
        }
        if input_data["scope"] not in valid_scopes:
            raise ValidationError(f"Invalid consent scope: {input_data['scope']}")
        if input_data["status"] not in {"allow", "ask_each_time", "declined", "revoked"}:
            raise ValidationError(f"Invalid consent status: {input_data['status']}")
        existing = next(
            (
                item
                for item in await self._repository.list_consent_preferences(input_data["userId"])
                if item["scope"] == input_data["scope"]
            ),
            None,
        )
        timestamp = now_iso()
        if existing is not None:
            record = await self._repository.update_consent_preference(
                input_data["userId"],
                existing["id"],
                {
                    "status": input_data["status"],
                    "note": input_data.get("note"),
                    "source": str(input_data.get("source") or "explicit_user"),
                    "updatedAt": timestamp,
                },
            )
        else:
            record = await self._repository.create_consent_preference(
                {
                    "id": create_id("consent_preference"),
                    "userId": input_data["userId"],
                    "scope": input_data["scope"],
                    "status": input_data["status"],
                    "note": input_data.get("note"),
                    "source": str(input_data.get("source") or "explicit_user"),
                    "createdAt": timestamp,
                    "updatedAt": timestamp,
                }
            )
        await self._record_adaptation_signal(
            user_id=input_data["userId"],
            event_type="consent_preference_changed",
            signals={"scope": record["scope"], "status": record["status"]},
        )
        return record

    async def set_adaptation_preferences(
        self,
        *,
        user_id: Id,
        scope: AdaptationPreferenceScope,
        preferences: dict[str, object],
    ) -> UserAdaptationProfileSummary:
        current = await self._repository.get_adaptation_profile(user_id)
        profile = self._adaptation_engine.ensure_profile(user_id=user_id, current=current)
        try:
            updated = self._adaptation_engine.set_explicit_preferences(
                profile=profile,
                scope=scope,
                preferences=preferences,
            )
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        await self._persist_adaptation_profile(user_id=user_id, current=current, updated=updated)
        summary = self._adaptation_engine.summarize(updated)
        if summary is None:
            raise ValidationError("Adaptation profile could not be summarized.")
        return summary

    async def apply_learned_policy_update(
        self,
        *,
        user_id: Id,
        scope: AdaptationPreferenceScope,
        policy: dict[str, object],
    ) -> UserAdaptationProfileSummary:
        current = await self._repository.get_adaptation_profile(user_id)
        profile = self._adaptation_engine.ensure_profile(user_id=user_id, current=current)
        try:
            updated = self._adaptation_engine.set_learned_policy(
                profile=profile,
                scope=scope,
                policy=policy,
            )
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        await self._persist_adaptation_profile(user_id=user_id, current=current, updated=updated)
        summary = self._adaptation_engine.summarize(updated)
        if summary is None:
            raise ValidationError("Adaptation profile could not be summarized.")
        return summary

    async def record_interpretation_feedback(
        self,
        user_id: Id,
        run_id: Id,
        feedback: InterpretationInteractionFeedback,
        note: str | None = None,
        locale: str | None = None,
    ) -> InteractionFeedbackRecord:
        self._validate_interpretation_feedback(feedback)
        await self._repository.get_interpretation_run(user_id, run_id)
        timestamp = now_iso()
        record: InteractionFeedbackRecord = {
            "id": create_id("interaction_feedback"),
            "userId": user_id,
            "domain": "interpretation",
            "targetType": "interpretation_run",
            "targetId": run_id,
            "feedback": feedback,
            "createdAt": timestamp,
        }
        if note is not None:
            record["note"] = str(note)
        normalized_locale = self._optional_str(locale)
        if normalized_locale:
            record["locale"] = normalized_locale
        stored = await self._repository.create_interaction_feedback(record)
        await self._record_adaptation_signal(
            user_id=user_id,
            event_type="interaction_feedback_interpretation",
            signals={
                "feedback": feedback,
                "locale": normalized_locale,
                "targetId": run_id,
            },
            success=feedback in {"good_level", "helpful"},
        )
        return stored

    async def record_practice_feedback(
        self,
        user_id: Id,
        practice_session_id: Id,
        feedback: PracticeInteractionFeedback,
        note: str | None = None,
        locale: str | None = None,
    ) -> InteractionFeedbackRecord:
        self._validate_practice_feedback(feedback)
        practice = await self._repository.get_practice_session(user_id, practice_session_id)
        timestamp = now_iso()
        record: InteractionFeedbackRecord = {
            "id": create_id("interaction_feedback"),
            "userId": user_id,
            "domain": "practice",
            "targetType": "practice_session",
            "targetId": practice_session_id,
            "feedback": feedback,
            "createdAt": timestamp,
        }
        if note is not None:
            record["note"] = str(note)
        normalized_locale = self._optional_str(locale)
        if normalized_locale:
            record["locale"] = normalized_locale
        stored = await self._repository.create_interaction_feedback(record)
        await self._record_adaptation_signal(
            user_id=user_id,
            event_type="interaction_feedback_practice",
            signals={
                "feedback": feedback,
                "locale": normalized_locale,
                "targetId": practice_session_id,
                "practiceType": practice["practiceType"],
                "modality": practice.get("modality"),
                "durationMinutes": practice.get("durationMinutes"),
            },
            success=feedback in {"good_fit", "helpful"},
        )
        return stored

    async def get_witness_state(
        self,
        *,
        user_id: Id,
        window_start: str,
        window_end: str,
        material_id: Id | None = None,
    ) -> MethodContextSnapshot:
        snapshot = await self._repository.build_method_context_snapshot_from_records(
            user_id,
            window_start=window_start,
            window_end=window_end,
            material_id=material_id,
        )
        return self._enrich_method_context_snapshot(
            snapshot,
            window_start=window_start,
            window_end=window_end,
            surface="generic",
        )

    def _enrich_method_context_snapshot(
        self,
        snapshot: MethodContextSnapshot | None,
        *,
        window_start: str | None = None,
        window_end: str | None = None,
        surface: str = "generic",
        existing_briefs: list[ProactiveBriefRecord] | None = None,
        recent_practices: list[PracticeSessionRecord] | None = None,
        journeys: list[JourneyRecord] | None = None,
        dashboard: DashboardSummary | None = None,
        adaptation_profile: UserAdaptationProfileSummary | None = None,
        safety_context: SafetyContext | None = None,
    ) -> MethodContextSnapshot:
        enriched: MethodContextSnapshot = deepcopy(snapshot) if snapshot is not None else {}
        if window_start and not enriched.get("windowStart"):
            enriched["windowStart"] = window_start
        if window_end and not enriched.get("windowEnd"):
            enriched["windowEnd"] = window_end
        enriched.setdefault("source", "circulatio-backend")
        if adaptation_profile is not None and not isinstance(
            enriched.get("adaptationProfile"), dict
        ):
            enriched["adaptationProfile"] = deepcopy(adaptation_profile)
        runtime_policy = derive_runtime_method_state_policy(enriched)
        try:
            enriched["witnessState"] = self._build_witness_state_summary(
                method_context=enriched,
                runtime_policy=runtime_policy,
            )
            coach_state = self._coach_engine.build_coach_state(
                method_context=enriched,
                runtime_policy=runtime_policy,
                surface=cast(
                    Literal[
                        "generic",
                        "alive_today",
                        "weekly_review",
                        "journey_page",
                        "rhythmic_brief",
                        "practice_followup",
                        "method_state_response",
                        "analysis_packet",
                    ],
                    surface,
                ),
                existing_briefs=existing_briefs or [],
                recent_practices=recent_practices or [],
                journeys=journeys or [],
                dashboard=dashboard,
                adaptation_profile=adaptation_profile,
                now=str(enriched.get("windowEnd") or window_end or now_iso()),
            )
            enriched["coachState"] = self._attach_resource_invitations_to_coach_state(
                coach_state=coach_state,
                runtime_policy=runtime_policy,
                safety_context=safety_context,
                now=str(enriched.get("windowEnd") or window_end or now_iso()),
            )
        except Exception:
            enriched["witnessState"] = self._build_witness_state_summary(
                method_context=enriched,
                runtime_policy=runtime_policy,
            )
            enriched["coachState"] = {
                "generatedAt": str(enriched.get("windowEnd") or window_end or now_iso()),
                "surface": cast(
                    Literal[
                        "generic",
                        "alive_today",
                        "weekly_review",
                        "journey_page",
                        "rhythmic_brief",
                        "practice_followup",
                        "method_state_response",
                        "analysis_packet",
                    ],
                    surface,
                ),
                "runtimePolicyVersion": "coach_state_v1",
                "witness": deepcopy(enriched["witnessState"]),
                "activeLoops": [],
                "withheldMoves": [
                    {
                        "loopKey": "coach:derivation_failed",
                        "kind": "resource_support",
                        "moveKind": "hold_silence",
                        "reason": "coach_state_derivation_failed",
                        "blockedMoves": [],
                        "consentScopes": [],
                    }
                ],
                "globalConstraints": {
                    "depthLevel": "gentle",
                    "blockedMoves": [],
                    "maxQuestionsPerTurn": 1,
                    "doNotAskReasons": ["coach_state_derivation_failed"],
                },
                "cooldownKeys": [],
                "sourceRecordRefs": [],
                "evidenceIds": [],
                "reasons": ["coach_state_derivation_failed"],
            }
        return enriched

    def _sync_longitudinal_input_fields(self, payload: dict[str, object]) -> dict[str, object]:
        synced = deepcopy(payload)
        method_context = synced.get("methodContextSnapshot")
        if not isinstance(method_context, dict):
            return synced
        method_state = (
            method_context.get("methodState")
            if isinstance(method_context.get("methodState"), dict)
            else {}
        )
        living_myth_context = (
            method_context.get("livingMythContext")
            if isinstance(method_context.get("livingMythContext"), dict)
            else {}
        )
        active_goal_tension = (
            deepcopy(method_state.get("activeGoalTension"))
            if isinstance(method_state.get("activeGoalTension"), dict)
            else None
        )
        if active_goal_tension is not None:
            synced["activeGoalTension"] = active_goal_tension
        else:
            synced.pop("activeGoalTension", None)
        practice_loop = (
            deepcopy(method_state.get("practiceLoop"))
            if isinstance(method_state.get("practiceLoop"), dict)
            else None
        )
        if practice_loop is not None:
            synced["practiceLoop"] = practice_loop
        else:
            synced.pop("practiceLoop", None)
        symbolic_wellbeing = (
            deepcopy(living_myth_context.get("latestSymbolicWellbeing"))
            if isinstance(living_myth_context.get("latestSymbolicWellbeing"), dict)
            else None
        )
        if symbolic_wellbeing is not None:
            synced["latestSymbolicWellbeing"] = symbolic_wellbeing
        else:
            synced.pop("latestSymbolicWellbeing", None)
        active_journeys = [
            deepcopy(item)
            for item in method_context.get("activeJourneys", [])
            if isinstance(item, dict)
        ]
        if active_journeys:
            synced["activeJourneys"] = active_journeys
        else:
            synced.pop("activeJourneys", None)
        witness_state = (
            deepcopy(method_context.get("witnessState"))
            if isinstance(method_context.get("witnessState"), dict)
            else None
        )
        if witness_state is not None:
            synced["witnessState"] = witness_state
        else:
            synced.pop("witnessState", None)
        return synced

    def _build_witness_state_summary(
        self,
        *,
        method_context: MethodContextSnapshot,
        runtime_policy: dict[str, object],
    ) -> WitnessStateSummary:
        return self._coach_engine.build_witness_state(
            method_context=method_context,
            runtime_policy=runtime_policy,
        )

    def _attach_resource_invitations_to_coach_state(
        self,
        *,
        coach_state: CoachStateSummary,
        runtime_policy: dict[str, object],
        safety_context: SafetyContext | None,
        now: str,
    ) -> CoachStateSummary:
        enriched = cast(CoachStateSummary, deepcopy(coach_state))
        loops = []
        for loop in enriched.get("activeLoops", []):
            loop_copy = cast(dict[str, object], deepcopy(loop))
            if str(loop_copy.get("moveKind") or "").strip() == "offer_resource":
                invitation = self._resource_engine.select_resource_for_loop(
                    loop=cast(dict[str, object], loop_copy),
                    coach_state=enriched,
                    runtime_policy=runtime_policy,
                    safety_context=cast(dict[str, object] | None, deepcopy(safety_context)),
                    now=now,
                )
                if invitation is not None:
                    loop_copy["resourceInvitation"] = deepcopy(invitation)
                    loop_copy["relatedResourceIds"] = [invitation["resource"]["id"]]
                    capture = dict(loop_copy.get("capture", {}))
                    capture_anchor_refs = dict(capture.get("anchorRefs", {}))
                    capture_anchor_refs["resourceInvitationId"] = invitation["id"]
                    capture["anchorRefs"] = capture_anchor_refs
                    loop_copy["capture"] = capture
            loops.append(cast(dict[str, object], loop_copy))
        enriched["activeLoops"] = cast(list[dict[str, object]], loops)
        selected_move = enriched.get("selectedMove")
        if isinstance(selected_move, dict):
            matched = next(
                (
                    loop
                    for loop in enriched.get("activeLoops", [])
                    if isinstance(loop, dict)
                    and str(loop.get("loopKey") or "").strip()
                    == str(selected_move.get("loopKey") or "").strip()
                ),
                None,
            )
            if isinstance(matched, dict):
                selected_copy = cast(dict[str, object], deepcopy(selected_move))
                if isinstance(matched.get("resourceInvitation"), dict):
                    selected_copy["resourceInvitation"] = deepcopy(matched["resourceInvitation"])
                    selected_copy["relatedResourceIds"] = list(
                        matched.get("relatedResourceIds", [])
                    )
                    capture = dict(selected_copy.get("capture", {}))
                    capture_anchor_refs = dict(capture.get("anchorRefs", {}))
                    capture_anchor_refs["resourceInvitationId"] = matched["resourceInvitation"][
                        "id"
                    ]
                    capture["anchorRefs"] = capture_anchor_refs
                    selected_copy["capture"] = capture
                enriched["selectedMove"] = cast(dict[str, object], selected_copy)
        return enriched

    async def _load_coach_runtime_inputs(
        self,
        *,
        user_id: Id,
        include_dashboard: bool = False,
    ) -> dict[str, object]:
        recent_practices = await self._repository.list_practice_sessions(
            user_id,
            statuses=["recommended", "accepted", "completed", "skipped"],
            include_deleted=False,
            limit=100,
        )
        journeys = await self._repository.list_journeys(
            user_id,
            include_deleted=False,
            limit=50,
        )
        existing_briefs = await self._repository.list_proactive_briefs(
            user_id,
            include_deleted=False,
            limit=100,
        )
        profile = await self._repository.get_adaptation_profile(user_id)
        adaptation_summary = self._adaptation_engine.summarize(profile)
        result: dict[str, object] = {
            "recentPractices": recent_practices,
            "journeys": journeys,
            "existingBriefs": existing_briefs,
            "profile": profile,
            "adaptationSummary": adaptation_summary,
        }
        if include_dashboard:
            result["dashboard"] = await self._repository.get_dashboard_summary(user_id=user_id)
        return result

    def _merge_thread_digests(
        self,
        base: list[ThreadDigest] | None,
        additions: list[ThreadDigest] | None,
    ) -> list[ThreadDigest]:
        merged: list[ThreadDigest] = []
        seen_keys: set[str] = set()
        for digest in [*(base or []), *(additions or [])]:
            if not isinstance(digest, dict):
                continue
            thread_key = self._optional_str(digest.get("threadKey"))
            if not thread_key or thread_key in seen_keys:
                continue
            seen_keys.add(thread_key)
            merged.append(cast(ThreadDigest, deepcopy(digest)))
        merged.sort(
            key=lambda item: str(item.get("lastTouchedAt") or ""),
            reverse=True,
        )
        return merged

    def _build_coach_loop_thread_digests(
        self,
        method_context: MethodContextSnapshot | None,
    ) -> list[ThreadDigest]:
        if not isinstance(method_context, dict):
            return []
        coach_state = method_context.get("coachState")
        if not isinstance(coach_state, dict):
            return []
        generated_at = str(
            coach_state.get("generatedAt") or method_context.get("windowEnd") or now_iso()
        )
        digests: list[ThreadDigest] = []
        seen_loop_keys: set[str] = set()
        loop_candidates = [
            item for item in coach_state.get("activeLoops", []) if isinstance(item, dict)
        ]
        selected_move = coach_state.get("selectedMove")
        if isinstance(selected_move, dict):
            loop_candidates.append(selected_move)
        for loop in loop_candidates:
            loop_key = self._optional_str(loop.get("loopKey"))
            if not loop_key or loop_key in seen_loop_keys:
                continue
            seen_loop_keys.add(loop_key)
            summary = (
                self._optional_str(loop.get("summaryHint"))
                or self._optional_str(loop.get("titleHint"))
                or self._optional_str(
                    (
                        loop.get("promptFrame") if isinstance(loop.get("promptFrame"), dict) else {}
                    ).get("askAbout")
                )
                or "Coach loop remains live."
            )
            status = self._optional_str(loop.get("status")) or "eligible"
            surface_readiness = {
                "aliveToday": "ready" if status == "eligible" else "available",
                "journeyPage": "ready" if status == "eligible" else "available",
                "rhythmicBrief": "ready" if status == "eligible" else "available",
                "methodStateResponse": "available",
            }
            entity_refs: dict[str, list[Id]] = {}
            for key, ref_key in (
                ("journeys", "relatedJourneyIds"),
                ("materials", "relatedMaterialIds"),
                ("symbols", "relatedSymbolIds"),
                ("practiceSessions", "relatedPracticeSessionIds"),
            ):
                values = [
                    str(value)
                    for value in loop.get(ref_key, [])
                    if isinstance(value, str) and value.strip()
                ]
                if values:
                    entity_refs[key] = values
            digests.append(
                {
                    "threadKey": f"coach_loop:{loop_key}",
                    "kind": "coach_loop",
                    "status": status,
                    "summary": self._compact_page_text(summary, max_length=220),
                    "entityRefs": entity_refs,
                    "evidenceIds": [
                        str(value)
                        for value in loop.get("evidenceIds", [])
                        if isinstance(value, str) and value.strip()
                    ],
                    "journeyIds": list(entity_refs.get("journeys", [])),
                    "sourceRecordRefs": [
                        {
                            "recordType": "CoachLoop",
                            "recordId": loop_key,
                            "summary": self._compact_page_text(summary, max_length=180),
                        }
                    ],
                    "lastTouchedAt": generated_at,
                    "surfaceReadiness": surface_readiness,
                }
            )
        return digests

    def _thread_digest_label(self, digest: ThreadDigest) -> str:
        kind = self._optional_str(digest.get("kind")) or "thread"
        mapping = {
            "journey": "Journey thread",
            "dream_series": "Dream series",
            "threshold_process": "Threshold process",
            "relational_scene": "Relational scene",
            "goal_tension": "Goal tension",
            "practice_loop": "Practice loop",
            "longitudinal_signal": "Longitudinal signal",
            "coach_loop": "Coach loop",
        }
        return mapping.get(kind, kind.replace("_", " ").title())

    async def _load_surface_context_bundle(
        self,
        *,
        user_id: Id,
        window_start: str,
        window_end: str,
        surface: str = "generic",
        payload: dict[str, object] | None = None,
        material_id: Id | None = None,
        include_dashboard: bool = False,
        memory_query: MemoryRetrievalQuery | None = None,
        explicit_question: str | None = None,
        safety_context: SafetyContext | None = None,
        sync_longitudinal: bool = False,
    ) -> dict[str, object]:
        prepared_payload = (
            deepcopy(payload)
            if payload is not None
            else deepcopy(
                await self._repository.build_circulation_summary_input(
                    user_id,
                    window_start=window_start,
                    window_end=window_end,
                )
            )
        )
        coach_runtime = await self._load_coach_runtime_inputs(
            user_id=user_id,
            include_dashboard=include_dashboard,
        )
        dashboard = cast(DashboardSummary | None, coach_runtime.get("dashboard"))
        method_context = self._enrich_method_context_snapshot(
            cast(MethodContextSnapshot | None, prepared_payload.get("methodContextSnapshot")),
            window_start=window_start,
            window_end=window_end,
            surface=surface,
            existing_briefs=cast(list[ProactiveBriefRecord], coach_runtime["existingBriefs"]),
            recent_practices=cast(list[PracticeSessionRecord], coach_runtime["recentPractices"]),
            journeys=cast(list[JourneyRecord], coach_runtime["journeys"]),
            dashboard=dashboard,
            adaptation_profile=cast(
                UserAdaptationProfileSummary | None, coach_runtime["adaptationSummary"]
            ),
            safety_context=safety_context,
        )
        thread_digests = self._merge_thread_digests(
            await self._repository.build_thread_digests_from_records(
                user_id,
                window_start=window_start,
                window_end=window_end,
                material_id=material_id,
            ),
            self._build_coach_loop_thread_digests(method_context),
        )
        prepared_payload["methodContextSnapshot"] = deepcopy(method_context)
        if thread_digests:
            prepared_payload["threadDigests"] = deepcopy(thread_digests)
        else:
            prepared_payload.pop("threadDigests", None)
        if explicit_question:
            prepared_payload["explicitQuestion"] = explicit_question
        if safety_context is not None:
            prepared_payload["safetyContext"] = deepcopy(safety_context)
        if sync_longitudinal:
            prepared_payload = cast(
                dict[str, object],
                self._sync_longitudinal_input_fields(prepared_payload),
            )
        memory_snapshot = None
        if memory_query is not None:
            memory_snapshot = await self._repository.build_memory_kernel_snapshot(
                user_id,
                query=memory_query,
            )
        return {
            "preparedPayload": prepared_payload,
            "methodContextSnapshot": method_context,
            "threadDigests": thread_digests,
            "dashboard": dashboard,
            "memorySnapshot": memory_snapshot,
            "recentPractices": coach_runtime["recentPractices"],
            "journeys": coach_runtime["journeys"],
            "existingBriefs": coach_runtime["existingBriefs"],
            "profile": coach_runtime["profile"],
            "adaptationSummary": coach_runtime["adaptationSummary"],
        }

    def _coach_expected_targets_from_context(
        self,
        *,
        method_context: MethodContextSnapshot | None,
        loop_key: str,
    ) -> list[MethodStateCaptureTargetKind]:
        if not isinstance(method_context, dict):
            return []
        coach_state = method_context.get("coachState")
        if not isinstance(coach_state, dict):
            return []
        for loop in coach_state.get("activeLoops", []):
            if not isinstance(loop, dict):
                continue
            if str(loop.get("loopKey") or "").strip() != loop_key:
                continue
            capture = loop.get("capture")
            if not isinstance(capture, dict):
                return []
            return [
                cast(MethodStateCaptureTargetKind, str(item))
                for item in capture.get("expectedTargets", [])
                if str(item).strip()
            ]
        selected = coach_state.get("selectedMove")
        if (
            isinstance(selected, dict)
            and str(selected.get("loopKey") or "").strip() == loop_key
            and isinstance(selected.get("capture"), dict)
        ):
            return [
                cast(MethodStateCaptureTargetKind, str(item))
                for item in selected["capture"].get("expectedTargets", [])
                if str(item).strip()
            ]
        return []

    async def set_cultural_frame(
        self,
        input_data: SetCulturalFrameInput,
    ) -> CulturalFrameRecord:
        timestamp = now_iso()
        label = self._optional_str(input_data.get("label"))
        if not label:
            raise ValidationError("label is required")
        frame_type = self._validate_cultural_frame_type(input_data.get("type"))
        status = self._validate_cultural_frame_status(input_data.get("status"))
        allowed_uses = self._normalize_cultural_frame_use_list(input_data.get("allowedUses"))
        avoid_uses = self._normalize_cultural_frame_use_list(input_data.get("avoidUses"))
        notes = self._optional_str(input_data.get("notes"))
        if input_data.get("culturalFrameId"):
            record = await self._repository.update_cultural_frame(
                input_data["userId"],
                input_data["culturalFrameId"],
                {
                    "label": label,
                    "frameType": frame_type,
                    "allowedUses": allowed_uses,
                    "avoidUses": avoid_uses,
                    "notes": notes,
                    "status": status,
                    "updatedAt": timestamp,
                },
            )
        else:
            record = await self._repository.create_cultural_frame(
                {
                    "id": create_id("cultural_frame"),
                    "userId": input_data["userId"],
                    "label": label,
                    "frameType": frame_type,
                    "allowedUses": allowed_uses,
                    "avoidUses": avoid_uses,
                    "notes": notes,
                    "status": status,
                    "createdAt": timestamp,
                    "updatedAt": timestamp,
                }
            )
        await self._record_adaptation_signal(
            user_id=input_data["userId"],
            event_type="cultural_frame_set",
            signals={"label": record["label"], "status": record["status"]},
        )
        return record

    async def upsert_goal(self, input_data: UpsertGoalInput) -> GoalRecord:
        label = (input_data.get("label") or "").strip()
        if not label:
            raise ValidationError("label is required")
        timestamp = now_iso()
        goal_id = input_data.get("goalId")
        if goal_id:
            record = await self._repository.update_goal(
                input_data["userId"],
                goal_id,
                {
                    "label": label,
                    "description": input_data.get("description"),
                    "status": str(input_data.get("status") or "active"),
                    "valueTags": list(input_data.get("valueTags", [])),
                    "linkedMaterialIds": list(input_data.get("linkedMaterialIds", [])),
                    "linkedSymbolIds": list(input_data.get("linkedSymbolIds", [])),
                    "evidenceIds": list(input_data.get("evidenceIds", [])),
                    "updatedAt": timestamp,
                },
            )
        else:
            existing = next(
                (
                    item
                    for item in await self._repository.list_goals(input_data["userId"])
                    if item.get("status") != "deleted"
                    and item["label"].strip().lower() == label.lower()
                ),
                None,
            )
            if existing is not None:
                record = await self._repository.update_goal(
                    input_data["userId"],
                    existing["id"],
                    {
                        "description": input_data.get("description", existing.get("description")),
                        "status": str(
                            input_data.get("status") or existing.get("status") or "active"
                        ),
                        "valueTags": self._merge_tags(
                            list(existing.get("valueTags", [])),
                            list(input_data.get("valueTags", [])),
                        ),
                        "linkedMaterialIds": self._merge_ids(
                            list(existing.get("linkedMaterialIds", [])),
                            list(input_data.get("linkedMaterialIds", [])),
                        ),
                        "linkedSymbolIds": self._merge_ids(
                            list(existing.get("linkedSymbolIds", [])),
                            list(input_data.get("linkedSymbolIds", [])),
                        ),
                        "evidenceIds": self._merge_ids(
                            list(existing.get("evidenceIds", [])),
                            list(input_data.get("evidenceIds", [])),
                        ),
                        "updatedAt": timestamp,
                    },
                )
            else:
                record = await self._repository.create_goal(
                    {
                        "id": create_id("goal"),
                        "userId": input_data["userId"],
                        "label": label,
                        "description": input_data.get("description"),
                        "status": str(input_data.get("status") or "active"),
                        "valueTags": list(input_data.get("valueTags", [])),
                        "linkedMaterialIds": list(input_data.get("linkedMaterialIds", [])),
                        "linkedSymbolIds": list(input_data.get("linkedSymbolIds", [])),
                        "evidenceIds": list(input_data.get("evidenceIds", [])),
                        "createdAt": timestamp,
                        "updatedAt": timestamp,
                    }
                )
        await self._record_adaptation_signal(
            user_id=input_data["userId"],
            event_type="goal_upserted",
            signals={"goalId": record["id"], "status": record["status"]},
        )
        return record

    async def upsert_goal_tension(
        self,
        input_data: UpsertGoalTensionInput,
    ) -> GoalTensionRecord:
        if not input_data.get("goalIds"):
            raise ValidationError("goalIds are required")
        tension_summary = (input_data.get("tensionSummary") or "").strip()
        if not tension_summary:
            raise ValidationError("tensionSummary is required")
        timestamp = now_iso()
        if input_data.get("tensionId"):
            record = await self._repository.update_goal_tension(
                input_data["userId"],
                input_data["tensionId"],
                {
                    "goalIds": list(input_data["goalIds"]),
                    "tensionSummary": tension_summary,
                    "polarityLabels": list(input_data.get("polarityLabels", [])),
                    "evidenceIds": list(input_data.get("evidenceIds", [])),
                    "status": str(input_data.get("status") or "active"),
                    "updatedAt": timestamp,
                },
            )
        else:
            record = await self._repository.create_goal_tension(
                {
                    "id": create_id("goal_tension"),
                    "userId": input_data["userId"],
                    "goalIds": list(input_data["goalIds"]),
                    "tensionSummary": tension_summary,
                    "polarityLabels": list(input_data.get("polarityLabels", [])),
                    "evidenceIds": list(input_data.get("evidenceIds", [])),
                    "status": str(input_data.get("status") or "active"),
                    "createdAt": timestamp,
                    "updatedAt": timestamp,
                }
            )
        await self._record_adaptation_signal(
            user_id=input_data["userId"],
            event_type="goal_tension_upserted",
            signals={"tensionId": record["id"], "status": record["status"]},
        )
        return record

    async def create_journey(self, input_data: CreateJourneyInput) -> JourneyRecord:
        label = (input_data.get("label") or "").strip()
        if not label:
            raise ValidationError("label is required")
        timestamp = now_iso()
        record: JourneyRecord = {
            "id": create_id("journey"),
            "userId": input_data["userId"],
            "label": label,
            "status": self._validate_journey_status(
                str(input_data.get("status") or "active"),
                allow_deleted=False,
            ),
            "relatedMaterialIds": await self._validate_journey_material_ids(
                input_data["userId"],
                input_data.get("relatedMaterialIds"),
            ),
            "relatedSymbolIds": await self._validate_journey_symbol_ids(
                input_data["userId"],
                input_data.get("relatedSymbolIds"),
            ),
            "relatedPatternIds": await self._validate_journey_pattern_ids(
                input_data["userId"],
                input_data.get("relatedPatternIds"),
            ),
            "relatedDreamSeriesIds": await self._validate_journey_dream_series_ids(
                input_data["userId"],
                input_data.get("relatedDreamSeriesIds"),
            ),
            "relatedGoalIds": await self._validate_journey_goal_ids(
                input_data["userId"],
                input_data.get("relatedGoalIds"),
            ),
            "createdAt": timestamp,
            "updatedAt": timestamp,
        }
        current_question = self._optional_str(input_data.get("currentQuestion"))
        if current_question:
            record["currentQuestion"] = current_question
        next_review_due_at = self._optional_str(input_data.get("nextReviewDueAt"))
        if next_review_due_at:
            record["nextReviewDueAt"] = next_review_due_at
        return await self._repository.create_journey(record)

    async def list_journeys(
        self,
        input_data: ListJourneysInput,
    ) -> list[JourneyRecord]:
        include_deleted = bool(input_data.get("includeDeleted", False))
        limit = max(int(input_data.get("limit", 50)), 0)
        journeys = await self._repository.list_journeys(
            input_data["userId"],
            include_deleted=include_deleted,
            limit=limit,
        )
        requested_statuses = input_data.get("statuses")
        if not requested_statuses:
            return journeys
        status_set = {
            self._validate_journey_status(str(item), allow_deleted=True)
            for item in requested_statuses
        }
        return [item for item in journeys if item.get("status") in status_set]

    async def get_journey(self, input_data: GetJourneyInput) -> JourneyRecord:
        return await self._resolve_journey_reference(
            user_id=input_data["userId"],
            journey_id=input_data.get("journeyId"),
            journey_label=input_data.get("journeyLabel"),
            include_deleted=bool(input_data.get("includeDeleted", False)),
        )

    async def update_journey(self, input_data: UpdateJourneyInput) -> JourneyRecord:
        journey = await self._resolve_journey_reference(
            user_id=input_data["userId"],
            journey_id=input_data.get("journeyId"),
            journey_label=input_data.get("journeyLabel"),
        )
        updates: dict[str, object] = {}
        if "label" in input_data:
            label = (input_data.get("label") or "").strip()
            if not label:
                raise ValidationError("label cannot be empty")
            if label != journey.get("label"):
                updates["label"] = label
        if "currentQuestion" in input_data:
            current_question = (input_data.get("currentQuestion") or "").strip()
            if not current_question:
                raise ValidationError("currentQuestion cannot be empty")
            if current_question != journey.get("currentQuestion"):
                updates["currentQuestion"] = current_question
        if "nextReviewDueAt" in input_data:
            next_review_due_at = self._optional_str(input_data.get("nextReviewDueAt"))
            if next_review_due_at is None:
                raise ValidationError("nextReviewDueAt cannot be empty")
            if next_review_due_at != journey.get("nextReviewDueAt"):
                updates["nextReviewDueAt"] = next_review_due_at

        material_updates = self._journey_link_update_requested(
            input_data,
            add_key="addRelatedMaterialIds",
            remove_key="removeRelatedMaterialIds",
        )
        if material_updates:
            updates["relatedMaterialIds"] = self._apply_journey_link_update(
                list(journey.get("relatedMaterialIds", [])),
                await self._validate_journey_material_ids(
                    input_data["userId"],
                    input_data.get("addRelatedMaterialIds"),
                ),
                self._normalize_id_list(input_data.get("removeRelatedMaterialIds")),
            )
        symbol_updates = self._journey_link_update_requested(
            input_data,
            add_key="addRelatedSymbolIds",
            remove_key="removeRelatedSymbolIds",
        )
        if symbol_updates:
            updates["relatedSymbolIds"] = self._apply_journey_link_update(
                list(journey.get("relatedSymbolIds", [])),
                await self._validate_journey_symbol_ids(
                    input_data["userId"],
                    input_data.get("addRelatedSymbolIds"),
                ),
                self._normalize_id_list(input_data.get("removeRelatedSymbolIds")),
            )
        pattern_updates = self._journey_link_update_requested(
            input_data,
            add_key="addRelatedPatternIds",
            remove_key="removeRelatedPatternIds",
        )
        if pattern_updates:
            updates["relatedPatternIds"] = self._apply_journey_link_update(
                list(journey.get("relatedPatternIds", [])),
                await self._validate_journey_pattern_ids(
                    input_data["userId"],
                    input_data.get("addRelatedPatternIds"),
                ),
                self._normalize_id_list(input_data.get("removeRelatedPatternIds")),
            )
        dream_series_updates = self._journey_link_update_requested(
            input_data,
            add_key="addRelatedDreamSeriesIds",
            remove_key="removeRelatedDreamSeriesIds",
        )
        if dream_series_updates:
            updates["relatedDreamSeriesIds"] = self._apply_journey_link_update(
                list(journey.get("relatedDreamSeriesIds", [])),
                await self._validate_journey_dream_series_ids(
                    input_data["userId"],
                    input_data.get("addRelatedDreamSeriesIds"),
                ),
                self._normalize_id_list(input_data.get("removeRelatedDreamSeriesIds")),
            )
        goal_updates = self._journey_link_update_requested(
            input_data,
            add_key="addRelatedGoalIds",
            remove_key="removeRelatedGoalIds",
        )
        if goal_updates:
            updates["relatedGoalIds"] = self._apply_journey_link_update(
                list(journey.get("relatedGoalIds", [])),
                await self._validate_journey_goal_ids(
                    input_data["userId"],
                    input_data.get("addRelatedGoalIds"),
                ),
                self._normalize_id_list(input_data.get("removeRelatedGoalIds")),
            )
        if not updates:
            return journey
        updates["updatedAt"] = now_iso()
        return await self._repository.update_journey(
            input_data["userId"],
            journey["id"],
            updates,
        )

    async def set_journey_status(
        self,
        input_data: SetJourneyStatusInput,
    ) -> JourneyRecord:
        journey = await self._resolve_journey_reference(
            user_id=input_data["userId"],
            journey_id=input_data.get("journeyId"),
            journey_label=input_data.get("journeyLabel"),
        )
        status = self._validate_journey_status(str(input_data["status"]), allow_deleted=False)
        if journey.get("status") == status:
            return journey
        return await self._repository.update_journey(
            input_data["userId"],
            journey["id"],
            {
                "status": status,
                "updatedAt": now_iso(),
            },
        )

    async def capture_reality_anchors(
        self,
        input_data: CaptureRealityAnchorsInput,
    ) -> IndividuationRecord:
        summary = (input_data.get("summary") or "").strip()
        anchor_summary = (input_data.get("anchorSummary") or "").strip()
        if not summary:
            raise ValidationError("summary is required")
        if not anchor_summary:
            raise ValidationError("anchorSummary is required")
        timestamp = now_iso()
        record: IndividuationRecord = {
            "id": create_id("reality_anchor_summary"),
            "userId": input_data["userId"],
            "recordType": "reality_anchor_summary",
            "status": "user_confirmed",
            "source": "user_reported",
            "label": str(input_data.get("label") or "Reality anchors").strip() or "Reality anchors",
            "summary": summary,
            "confidence": "high",
            "evidenceIds": list(input_data.get("evidenceIds", [])),
            "relatedMaterialIds": list(input_data.get("relatedMaterialIds", [])),
            "relatedSymbolIds": list(input_data.get("relatedSymbolIds", [])),
            "relatedGoalIds": list(input_data.get("relatedGoalIds", [])),
            "relatedDreamSeriesIds": [],
            "relatedJourneyIds": list(input_data.get("relatedJourneyIds", [])),
            "relatedPracticeSessionIds": [],
            "privacyClass": str(input_data.get("privacyClass") or "user_private"),
            "details": {
                "anchorSummary": anchor_summary,
                "workDailyLifeContinuity": str(
                    input_data.get("workDailyLifeContinuity") or "unknown"
                ),
                "sleepBodyRegulation": str(input_data.get("sleepBodyRegulation") or "unknown"),
                "relationshipContact": str(input_data.get("relationshipContact") or "unknown"),
                "reflectiveCapacity": str(input_data.get("reflectiveCapacity") or "unknown"),
                "groundingRecommendation": str(
                    input_data.get("groundingRecommendation") or "pace_gently"
                ),
                "reasons": list(input_data.get("reasons", [])),
            },
            "createdAt": timestamp,
            "updatedAt": timestamp,
        }
        created = await self._repository.create_individuation_record(record)
        await self._record_adaptation_signal(
            user_id=input_data["userId"],
            event_type="reality_anchors_captured",
            signals={"recordId": created["id"]},
        )
        return created

    async def upsert_threshold_process(
        self,
        input_data: UpsertThresholdProcessInput,
    ) -> IndividuationRecord:
        summary = (input_data.get("summary") or "").strip()
        threshold_name = (input_data.get("thresholdName") or "").strip()
        normalized_key = (input_data.get("normalizedThresholdKey") or "").strip()
        if not summary:
            raise ValidationError("summary is required")
        if not threshold_name:
            raise ValidationError("thresholdName is required")
        if not normalized_key:
            raise ValidationError("normalizedThresholdKey is required")
        timestamp = now_iso()
        existing: IndividuationRecord | None = None
        if input_data.get("thresholdId"):
            existing = await self._repository.get_individuation_record(
                input_data["userId"],
                input_data["thresholdId"],
            )
        else:
            existing = await self._find_individuation_record_by_detail(
                user_id=input_data["userId"],
                record_type="threshold_process",
                detail_key="normalizedThresholdKey",
                detail_value=normalized_key,
            )
        details = {
            "thresholdName": threshold_name,
            "phase": str(input_data.get("phase") or "unknown"),
            "whatIsEnding": str(input_data.get("whatIsEnding") or "").strip(),
            "notYetBegun": str(input_data.get("notYetBegun") or "").strip(),
            "groundingStatus": str(input_data.get("groundingStatus") or "unknown"),
            "invitationReadiness": str(input_data.get("invitationReadiness") or "ask"),
            "normalizedThresholdKey": normalized_key,
        }
        if input_data.get("bodyCarrying"):
            details["bodyCarrying"] = str(input_data["bodyCarrying"]).strip()
        if input_data.get("symbolicLens"):
            details["symbolicLens"] = str(input_data["symbolicLens"]).strip()
        if existing is None:
            record: IndividuationRecord = {
                "id": create_id("threshold_process"),
                "userId": input_data["userId"],
                "recordType": "threshold_process",
                "status": "user_confirmed",
                "source": "user_reported",
                "label": str(input_data.get("label") or threshold_name).strip() or threshold_name,
                "summary": summary,
                "confidence": "high",
                "evidenceIds": list(input_data.get("evidenceIds", [])),
                "relatedMaterialIds": list(input_data.get("relatedMaterialIds", [])),
                "relatedSymbolIds": list(input_data.get("relatedSymbolIds", [])),
                "relatedGoalIds": list(input_data.get("relatedGoalIds", [])),
                "relatedDreamSeriesIds": list(input_data.get("relatedDreamSeriesIds", [])),
                "relatedJourneyIds": list(input_data.get("relatedJourneyIds", [])),
                "relatedPracticeSessionIds": [],
                "privacyClass": str(input_data.get("privacyClass") or "user_private"),
                "details": details,
                "createdAt": timestamp,
                "updatedAt": timestamp,
            }
            stored = await self._repository.create_individuation_record(record)
        else:
            merged_details = deepcopy(existing.get("details", {}))
            merged_details.update(details)
            stored = await self._repository.update_individuation_record(
                input_data["userId"],
                existing["id"],
                {
                    "status": "user_confirmed",
                    "source": "user_reported",
                    "label": str(input_data.get("label") or threshold_name).strip()
                    or existing.get("label", threshold_name),
                    "summary": summary,
                    "confidence": "high",
                    "evidenceIds": self._merge_ids(
                        list(existing.get("evidenceIds", [])),
                        list(input_data.get("evidenceIds", [])),
                    ),
                    "relatedMaterialIds": self._merge_ids(
                        list(existing.get("relatedMaterialIds", [])),
                        list(input_data.get("relatedMaterialIds", [])),
                    ),
                    "relatedSymbolIds": self._merge_ids(
                        list(existing.get("relatedSymbolIds", [])),
                        list(input_data.get("relatedSymbolIds", [])),
                    ),
                    "relatedGoalIds": self._merge_ids(
                        list(existing.get("relatedGoalIds", [])),
                        list(input_data.get("relatedGoalIds", [])),
                    ),
                    "relatedDreamSeriesIds": self._merge_ids(
                        list(existing.get("relatedDreamSeriesIds", [])),
                        list(input_data.get("relatedDreamSeriesIds", [])),
                    ),
                    "relatedJourneyIds": self._merge_ids(
                        list(existing.get("relatedJourneyIds", [])),
                        list(input_data.get("relatedJourneyIds", [])),
                    ),
                    "privacyClass": str(
                        input_data.get("privacyClass")
                        or existing.get("privacyClass")
                        or "user_private"
                    ),
                    "details": merged_details,
                    "updatedAt": timestamp,
                },
            )
        await self._record_adaptation_signal(
            user_id=input_data["userId"],
            event_type="threshold_process_recorded",
            signals={"recordId": stored["id"]},
        )
        return stored

    async def record_relational_scene(
        self,
        input_data: RecordRelationalSceneInput,
    ) -> IndividuationRecord:
        summary = (input_data.get("summary") or "").strip()
        scene_summary = (input_data.get("sceneSummary") or "").strip()
        normalized_key = (input_data.get("normalizedSceneKey") or "").strip()
        if not summary:
            raise ValidationError("summary is required")
        if not scene_summary:
            raise ValidationError("sceneSummary is required")
        if not normalized_key:
            raise ValidationError("normalizedSceneKey is required")
        timestamp = now_iso()
        existing: IndividuationRecord | None = None
        if input_data.get("sceneId"):
            existing = await self._repository.get_individuation_record(
                input_data["userId"],
                input_data["sceneId"],
            )
        else:
            existing = await self._find_individuation_record_by_detail(
                user_id=input_data["userId"],
                record_type="relational_scene",
                detail_key="normalizedSceneKey",
                detail_value=normalized_key,
            )
        roles = [deepcopy(item) for item in input_data.get("chargedRoles", []) if item]
        if existing is None:
            record: IndividuationRecord = {
                "id": create_id("relational_scene"),
                "userId": input_data["userId"],
                "recordType": "relational_scene",
                "status": "user_confirmed",
                "source": "user_reported",
                "label": str(input_data.get("label") or "Relational scene").strip()
                or "Relational scene",
                "summary": summary,
                "confidence": "high",
                "evidenceIds": list(input_data.get("evidenceIds", [])),
                "relatedMaterialIds": list(input_data.get("relatedMaterialIds", [])),
                "relatedSymbolIds": [],
                "relatedGoalIds": list(input_data.get("relatedGoalIds", [])),
                "relatedDreamSeriesIds": [],
                "relatedJourneyIds": list(input_data.get("relatedJourneyIds", [])),
                "relatedPracticeSessionIds": [],
                "privacyClass": str(input_data.get("privacyClass") or "user_private"),
                "details": {
                    "sceneSummary": scene_summary,
                    "chargedRoles": roles,
                    "recurringAffect": list(input_data.get("recurringAffect", [])),
                    "recurrenceContexts": list(input_data.get("recurrenceContexts", [])),
                    "normalizedSceneKey": normalized_key,
                },
                "createdAt": timestamp,
                "updatedAt": timestamp,
            }
            stored = await self._repository.create_individuation_record(record)
        else:
            merged_details = deepcopy(existing.get("details", {}))
            merged_roles = list(merged_details.get("chargedRoles", []))
            for role in roles:
                if role not in merged_roles:
                    merged_roles.append(role)
            merged_details["chargedRoles"] = merged_roles
            merged_details["recurringAffect"] = self._merge_tags(
                list(merged_details.get("recurringAffect", [])),
                list(input_data.get("recurringAffect", [])),
            )
            merged_details["recurrenceContexts"] = self._merge_tags(
                list(merged_details.get("recurrenceContexts", [])),
                list(input_data.get("recurrenceContexts", [])),
            )
            merged_details["sceneSummary"] = scene_summary
            merged_details["normalizedSceneKey"] = normalized_key
            stored = await self._repository.update_individuation_record(
                input_data["userId"],
                existing["id"],
                {
                    "status": "user_confirmed",
                    "source": "user_reported",
                    "label": str(
                        input_data.get("label") or existing.get("label") or "Relational scene"
                    ),
                    "summary": summary,
                    "confidence": "high",
                    "relatedMaterialIds": self._merge_ids(
                        list(existing.get("relatedMaterialIds", [])),
                        list(input_data.get("relatedMaterialIds", [])),
                    ),
                    "relatedGoalIds": self._merge_ids(
                        list(existing.get("relatedGoalIds", [])),
                        list(input_data.get("relatedGoalIds", [])),
                    ),
                    "relatedJourneyIds": self._merge_ids(
                        list(existing.get("relatedJourneyIds", [])),
                        list(input_data.get("relatedJourneyIds", [])),
                    ),
                    "privacyClass": str(
                        input_data.get("privacyClass")
                        or existing.get("privacyClass")
                        or "user_private"
                    ),
                    "details": merged_details,
                    "updatedAt": timestamp,
                },
            )
        await self._record_adaptation_signal(
            user_id=input_data["userId"],
            event_type="relational_scene_recorded",
            signals={"recordId": stored["id"]},
        )
        return stored

    async def record_inner_outer_correspondence(
        self,
        input_data: RecordInnerOuterCorrespondenceInput,
    ) -> IndividuationRecord:
        summary = (input_data.get("summary") or "").strip()
        correspondence_summary = (input_data.get("correspondenceSummary") or "").strip()
        normalized_key = (input_data.get("normalizedCorrespondenceKey") or "").strip()
        if not summary:
            raise ValidationError("summary is required")
        if not correspondence_summary:
            raise ValidationError("correspondenceSummary is required")
        if not normalized_key:
            raise ValidationError("normalizedCorrespondenceKey is required")
        timestamp = now_iso()
        existing: IndividuationRecord | None = None
        if input_data.get("correspondenceId"):
            existing = await self._repository.get_individuation_record(
                input_data["userId"],
                input_data["correspondenceId"],
            )
        else:
            existing = await self._find_individuation_record_by_detail(
                user_id=input_data["userId"],
                record_type="inner_outer_correspondence",
                detail_key="normalizedCorrespondenceKey",
                detail_value=normalized_key,
            )
        details = {
            "correspondenceSummary": correspondence_summary,
            "innerRefs": list(input_data.get("innerRefs", [])),
            "outerRefs": list(input_data.get("outerRefs", [])),
            "symbolIds": list(input_data.get("symbolIds", [])),
            "userCharge": str(input_data.get("userCharge") or "unclear"),
            "caveat": str(input_data.get("caveat") or "Held without causal claim."),
            "causalityPolicy": "no_causal_claim",
            "normalizedCorrespondenceKey": normalized_key,
        }
        if existing is None:
            record: IndividuationRecord = {
                "id": create_id("inner_outer_correspondence"),
                "userId": input_data["userId"],
                "recordType": "inner_outer_correspondence",
                "status": "user_confirmed",
                "source": "user_reported",
                "label": str(input_data.get("label") or "Inner-outer correspondence").strip()
                or "Inner-outer correspondence",
                "summary": summary,
                "confidence": "high",
                "evidenceIds": list(input_data.get("evidenceIds", [])),
                "relatedMaterialIds": [],
                "relatedSymbolIds": list(input_data.get("symbolIds", [])),
                "relatedGoalIds": [],
                "relatedDreamSeriesIds": [],
                "relatedJourneyIds": list(input_data.get("relatedJourneyIds", [])),
                "relatedPracticeSessionIds": [],
                "privacyClass": str(input_data.get("privacyClass") or "user_private"),
                "details": details,
                "createdAt": timestamp,
                "updatedAt": timestamp,
            }
            stored = await self._repository.create_individuation_record(record)
        else:
            merged_details = deepcopy(existing.get("details", {}))
            merged_details["innerRefs"] = self._merge_ids(
                list(merged_details.get("innerRefs", [])),
                list(input_data.get("innerRefs", [])),
            )
            merged_details["outerRefs"] = self._merge_ids(
                list(merged_details.get("outerRefs", [])),
                list(input_data.get("outerRefs", [])),
            )
            merged_details["symbolIds"] = self._merge_ids(
                list(merged_details.get("symbolIds", [])),
                list(input_data.get("symbolIds", [])),
            )
            merged_details["correspondenceSummary"] = correspondence_summary
            merged_details["userCharge"] = str(input_data.get("userCharge") or "unclear")
            merged_details["caveat"] = str(input_data.get("caveat") or "Held without causal claim.")
            merged_details["causalityPolicy"] = "no_causal_claim"
            merged_details["normalizedCorrespondenceKey"] = normalized_key
            stored = await self._repository.update_individuation_record(
                input_data["userId"],
                existing["id"],
                {
                    "status": "user_confirmed",
                    "source": "user_reported",
                    "label": str(
                        input_data.get("label")
                        or existing.get("label")
                        or "Inner-outer correspondence"
                    ),
                    "summary": summary,
                    "confidence": "high",
                    "evidenceIds": self._merge_ids(
                        list(existing.get("evidenceIds", [])),
                        list(input_data.get("evidenceIds", [])),
                    ),
                    "relatedSymbolIds": self._merge_ids(
                        list(existing.get("relatedSymbolIds", [])),
                        list(input_data.get("symbolIds", [])),
                    ),
                    "relatedJourneyIds": self._merge_ids(
                        list(existing.get("relatedJourneyIds", [])),
                        list(input_data.get("relatedJourneyIds", [])),
                    ),
                    "privacyClass": str(
                        input_data.get("privacyClass")
                        or existing.get("privacyClass")
                        or "user_private"
                    ),
                    "details": merged_details,
                    "updatedAt": timestamp,
                },
            )
        await self._record_adaptation_signal(
            user_id=input_data["userId"],
            event_type="inner_outer_correspondence_recorded",
            signals={"recordId": stored["id"]},
        )
        return stored

    async def record_numinous_encounter(
        self,
        input_data: RecordNuminousEncounterInput,
    ) -> IndividuationRecord:
        summary = (input_data.get("summary") or "").strip()
        interpretation_constraint = (input_data.get("interpretationConstraint") or "").strip()
        if not summary:
            raise ValidationError("summary is required")
        if not interpretation_constraint:
            raise ValidationError("interpretationConstraint is required")
        timestamp = now_iso()
        record: IndividuationRecord = {
            "id": create_id("numinous_encounter"),
            "userId": input_data["userId"],
            "recordType": "numinous_encounter",
            "status": "user_confirmed",
            "source": "user_reported",
            "label": str(input_data.get("label") or "Numinous encounter").strip()
            or "Numinous encounter",
            "summary": summary,
            "confidence": "high",
            "evidenceIds": list(input_data.get("evidenceIds", [])),
            "relatedMaterialIds": list(input_data.get("relatedMaterialIds", [])),
            "relatedSymbolIds": list(input_data.get("relatedSymbolIds", [])),
            "relatedGoalIds": [],
            "relatedDreamSeriesIds": [],
            "relatedJourneyIds": list(input_data.get("relatedJourneyIds", [])),
            "relatedPracticeSessionIds": [],
            "privacyClass": str(input_data.get("privacyClass") or "user_private"),
            "details": {
                "encounterMedium": str(input_data.get("encounterMedium") or "unknown"),
                "affectTone": str(input_data.get("affectTone") or "").strip(),
                "containmentNeed": str(input_data.get("containmentNeed") or "ordinary_reflection"),
                "interpretationConstraint": interpretation_constraint,
            },
            "createdAt": timestamp,
            "updatedAt": timestamp,
        }
        created = await self._repository.create_individuation_record(record)
        await self._record_adaptation_signal(
            user_id=input_data["userId"],
            event_type="numinous_encounter_recorded",
            signals={"recordId": created["id"]},
        )
        return created

    async def record_aesthetic_resonance(
        self,
        input_data: RecordAestheticResonanceInput,
    ) -> IndividuationRecord:
        summary = (input_data.get("summary") or "").strip()
        resonance_summary = (input_data.get("resonanceSummary") or "").strip()
        if not summary:
            raise ValidationError("summary is required")
        if not resonance_summary:
            raise ValidationError("resonanceSummary is required")
        timestamp = now_iso()
        details = {
            "medium": str(input_data.get("medium") or "unknown"),
            "objectDescription": str(input_data.get("objectDescription") or "").strip(),
            "resonanceSummary": resonance_summary,
            "bodySensations": list(input_data.get("bodySensations", [])),
        }
        if input_data.get("feelingTone"):
            details["feelingTone"] = str(input_data["feelingTone"]).strip()
        record: IndividuationRecord = {
            "id": create_id("aesthetic_resonance"),
            "userId": input_data["userId"],
            "recordType": "aesthetic_resonance",
            "status": "user_confirmed",
            "source": "user_reported",
            "label": str(input_data.get("label") or "Aesthetic resonance").strip()
            or "Aesthetic resonance",
            "summary": summary,
            "confidence": "high",
            "evidenceIds": list(input_data.get("evidenceIds", [])),
            "relatedMaterialIds": list(input_data.get("relatedMaterialIds", [])),
            "relatedSymbolIds": list(input_data.get("relatedSymbolIds", [])),
            "relatedGoalIds": [],
            "relatedDreamSeriesIds": [],
            "relatedJourneyIds": list(input_data.get("relatedJourneyIds", [])),
            "relatedPracticeSessionIds": [],
            "privacyClass": str(input_data.get("privacyClass") or "user_private"),
            "details": details,
            "createdAt": timestamp,
            "updatedAt": timestamp,
        }
        created = await self._repository.create_individuation_record(record)
        await self._record_adaptation_signal(
            user_id=input_data["userId"],
            event_type="aesthetic_resonance_recorded",
            signals={"recordId": created["id"]},
        )
        return created

    async def create_and_interpret_material(
        self,
        input_data: CreateAndInterpretMaterialInput,
    ) -> MaterialWorkflowResult:
        material = await self.create_material(input_data)
        return await self.interpret_existing_material(
            user_id=input_data["userId"],
            material_id=material["id"],
            session_context=input_data.get("sessionContext"),
            life_context_snapshot=input_data.get("lifeContextSnapshot"),
            life_os_window=input_data.get("lifeOsWindow"),
            user_associations=input_data.get("userAssociations"),
            explicit_question=input_data.get("explicitQuestion"),
            cultural_origins=input_data.get("culturalOrigins"),
            safety_context=input_data.get("safetyContext"),
            options=input_data.get("options"),
        )

    async def interpret_existing_material(
        self,
        *,
        user_id: Id,
        material_id: Id,
        session_context: SessionContext | None = None,
        life_context_snapshot: LifeContextSnapshot | None = None,
        life_os_window: dict[str, str] | None = None,
        user_associations: list[UserAssociationInput] | None = None,
        explicit_question: str | None = None,
        cultural_origins: list[dict[str, object]] | None = None,
        safety_context: SafetyContext | None = None,
        options: InterpretationOptions | None = None,
        dream_structure: StoredDreamStructure | None = None,
    ) -> MaterialWorkflowResult:
        material = await self._repository.get_material(user_id, material_id)
        if material["materialType"] == "dream" and dream_structure:
            material = await self._repository.update_material(
                user_id,
                material_id,
                {
                    "dreamStructure": deepcopy(dream_structure),
                    "updatedAt": now_iso(),
                },
            )
        reused = await self._maybe_reuse_latest_open_interpretation(
            user_id=user_id,
            material=material,
            life_context_snapshot=life_context_snapshot,
            life_os_window=life_os_window,
            user_associations=user_associations,
            explicit_question=explicit_question,
            cultural_origins=cultural_origins,
            safety_context=safety_context,
            options=options,
            dream_structure=dream_structure,
        )
        if reused is not None:
            return reused
        material_input = await self._build_material_input(
            material=material,
            session_context=session_context,
            life_context_snapshot=life_context_snapshot,
            life_os_window=life_os_window,
            user_associations=user_associations,
            explicit_question=explicit_question,
            cultural_origins=cultural_origins,
            safety_context=safety_context,
            options=options,
        )
        context_snapshot = await self._store_context_snapshot(
            material=material,
            material_input=material_input,
        )
        interpretation = await self._core.interpret_material(material_input)
        practice_session = await self._store_practice_recommendation(
            user_id=user_id,
            material_id=material_id,
            interpretation=interpretation,
        )
        await self._repository.store_evidence_items(user_id, interpretation["evidence"])
        run = await self._store_interpretation_run(
            material=material,
            material_input=material_input,
            interpretation=interpretation,
            context_snapshot=context_snapshot,
            practice_session=practice_session,
        )
        await self._ensure_amplification_prompts_for_run(
            user_id=user_id,
            material_id=material_id,
            run_id=run["id"],
            interpretation=interpretation,
        )
        clarification_prompts = await self._ensure_clarification_prompt_for_run(
            user_id=user_id,
            material=material,
            run_id=run["id"],
            interpretation=interpretation,
        )
        material_updates: dict[str, object] = {
            "latestInterpretationRunId": run["id"],
            "updatedAt": now_iso(),
        }
        if context_snapshot is not None:
            material_updates["linkedContextSnapshotIds"] = self._merge_ids(
                material.get("linkedContextSnapshotIds", []),
                [context_snapshot["id"]],
            )
        if practice_session is not None:
            material_updates["linkedPracticeSessionIds"] = self._merge_ids(
                material.get("linkedPracticeSessionIds", []),
                [practice_session["id"]],
            )
        material = await self._repository.update_material(user_id, material_id, material_updates)
        result: MaterialWorkflowResult = {
            "material": material,
            "run": run,
            "interpretation": interpretation,
            "pendingProposals": interpretation["memoryWritePlan"]["proposals"],
        }
        if clarification_prompts:
            result["pendingClarificationPrompts"] = clarification_prompts
        if context_snapshot is not None:
            result["contextSnapshot"] = context_snapshot
        if practice_session is not None:
            result["practiceSession"] = practice_session
        await self._record_adaptation_signal(
            user_id=user_id,
            event_type="interpretation_completed",
            signals={
                "runId": run["id"],
                "practiceType": interpretation.get("practiceRecommendation", {}).get("type"),
                "depthLevel": interpretation.get("methodGate", {}).get("depthLevel"),
            },
        )
        return result

    async def _maybe_reuse_latest_open_interpretation(
        self,
        *,
        user_id: Id,
        material: MaterialRecord,
        life_context_snapshot: LifeContextSnapshot | None,
        life_os_window: dict[str, str] | None,
        user_associations: list[UserAssociationInput] | None,
        explicit_question: str | None,
        cultural_origins: list[dict[str, object]] | None,
        safety_context: SafetyContext | None,
        options: InterpretationOptions | None,
        dream_structure: StoredDreamStructure | None,
    ) -> MaterialWorkflowResult | None:
        if (
            life_context_snapshot is not None
            or life_os_window is not None
            or user_associations
            or explicit_question
            or cultural_origins
            or safety_context is not None
            or options is not None
            or dream_structure is not None
        ):
            return None
        latest_run_id = self._optional_str(material.get("latestInterpretationRunId"))
        if not latest_run_id:
            return None
        try:
            latest_run = await self._repository.get_interpretation_run(user_id, latest_run_id)
        except EntityNotFoundError:
            return None
        if not self._interpretation_result_is_waiting_for_follow_up(latest_run):
            return None
        clarification_prompts = await self._repository.list_clarification_prompts(
            user_id,
            run_id=latest_run_id,
            limit=20,
        )
        if clarification_prompts and not any(
            str(item.get("status") or "").strip() == "pending" for item in clarification_prompts
        ):
            return None
        return await self._materialize_interpretation_workflow(
            user_id=user_id,
            material=material,
            run=latest_run,
        )

    def _interpretation_result_is_waiting_for_follow_up(self, run: InterpretationRunRecord) -> bool:
        result = run.get("result")
        if not isinstance(result, dict):
            return False
        if self._optional_str(result.get("clarifyingQuestion")):
            return True
        method_gate = result.get("methodGate")
        if not isinstance(method_gate, dict):
            return False
        if any(str(item).strip() for item in method_gate.get("missingPrerequisites", [])):
            return True
        if any(str(item).strip() for item in method_gate.get("requiredPrompts", [])):
            return True
        return self._optional_str(method_gate.get("depthLevel")) in {
            "grounding_only",
            "observations_only",
            "personal_amplification_needed",
            "cautious_pattern_note",
        }

    async def _materialize_interpretation_workflow(
        self,
        *,
        user_id: Id,
        material: MaterialRecord,
        run: InterpretationRunRecord,
    ) -> MaterialWorkflowResult:
        interpretation = deepcopy(run["result"])
        pending_proposals: list[MemoryWriteProposal] = []
        memory_write_plan = interpretation.get("memoryWritePlan")
        proposals = (
            memory_write_plan.get("proposals")
            if isinstance(memory_write_plan, dict)
            else None
        )
        if isinstance(proposals, list):
            pending_proposals = [
                deepcopy(proposal)
                for proposal in proposals
                if isinstance(proposal, dict)
                and proposal.get("id")
                and self._decision_status(run, str(proposal["id"])) == "pending"
            ]
        workflow: MaterialWorkflowResult = {
            "material": deepcopy(material),
            "run": deepcopy(run),
            "interpretation": interpretation,
            "pendingProposals": pending_proposals,
        }
        clarification_prompts = await self._repository.list_clarification_prompts(
            user_id,
            status="pending",
            run_id=run["id"],
            limit=20,
        )
        if clarification_prompts:
            workflow["pendingClarificationPrompts"] = clarification_prompts
        snapshot_id = self._optional_str(run.get("inputSnapshotId"))
        if snapshot_id:
            try:
                workflow["contextSnapshot"] = await self._repository.get_context_snapshot(
                    user_id, snapshot_id
                )
            except EntityNotFoundError:
                pass
        practice_session_id = self._optional_str(run.get("practiceRecommendationId"))
        if practice_session_id:
            try:
                workflow["practiceSession"] = await self._repository.get_practice_session(
                    user_id, practice_session_id
                )
            except EntityNotFoundError:
                pass
        return workflow

    async def approve_proposals(
        self,
        *,
        user_id: Id,
        run_id: Id,
        proposal_ids: list[Id],
        integration_note: str | None = None,
    ) -> IntegrationRecord:
        run = await self._repository.get_interpretation_run(user_id, run_id)
        proposals = self._proposal_records(run, proposal_ids)
        for proposal in proposals:
            self._assert_proposal_transition(run, proposal["id"], "approved")
        applied = await self._repository.apply_approved_proposals(
            user_id=user_id,
            memory_write_plan=run["result"]["memoryWritePlan"],
            approved_proposal_ids=[proposal["id"] for proposal in proposals],
        )
        timestamp = now_iso()
        integration: IntegrationRecord = {
            "id": create_id("integration"),
            "userId": user_id,
            "runId": run_id,
            "materialId": run["materialId"],
            "action": "approved_proposals",
            "approvedProposalIds": list(applied["appliedProposalIds"]),
            "rejectedProposalIds": [],
            "suppressedHypothesisIds": [],
            "affectedEntityIds": list(applied.get("affectedEntityIds", [])),
            "createdAt": timestamp,
        }
        if integration_note:
            integration["note"] = integration_note
        await self._repository.create_integration_record(integration)
        await self._repository.update_proposal_decisions(
            user_id,
            run_id,
            [
                {
                    "proposalId": proposal["id"],
                    "action": proposal["action"],
                    "entityType": proposal["entityType"],
                    "status": "approved",
                    "decidedAt": timestamp,
                    "integrationRecordId": integration["id"],
                }
                for proposal in proposals
            ],
        )
        await self._record_adaptation_signal(
            user_id=user_id,
            event_type="proposal_approved",
            signals={"count": len(proposals)},
        )
        return integration

    async def reject_proposals(
        self,
        *,
        user_id: Id,
        run_id: Id,
        proposal_ids: list[Id],
        reason: str | None = None,
    ) -> IntegrationRecord:
        run = await self._repository.get_interpretation_run(user_id, run_id)
        proposals = self._proposal_records(run, proposal_ids)
        for proposal in proposals:
            self._assert_proposal_transition(run, proposal["id"], "rejected")
        timestamp = now_iso()
        integration: IntegrationRecord = {
            "id": create_id("integration"),
            "userId": user_id,
            "runId": run_id,
            "materialId": run["materialId"],
            "action": "rejected_proposals",
            "approvedProposalIds": [],
            "rejectedProposalIds": [proposal["id"] for proposal in proposals],
            "suppressedHypothesisIds": [],
            "affectedEntityIds": [],
            "createdAt": timestamp,
        }
        if reason:
            integration["note"] = reason
        await self._repository.create_integration_record(integration)
        await self._repository.update_proposal_decisions(
            user_id,
            run_id,
            [
                {
                    "proposalId": proposal["id"],
                    "action": proposal["action"],
                    "entityType": proposal["entityType"],
                    "status": "rejected",
                    "decidedAt": timestamp,
                    "integrationRecordId": integration["id"],
                    "reason": reason,
                }
                for proposal in proposals
            ],
        )
        await self._record_adaptation_signal(
            user_id=user_id,
            event_type="proposal_rejected",
            signals={"count": len(proposals)},
        )
        return integration

    async def get_method_state_capture_run(
        self, *, user_id: Id, capture_run_id: Id
    ) -> MethodStateCaptureRunRecord:
        return await self._repository.get_method_state_capture_run(user_id, capture_run_id)

    async def process_method_state_response(
        self,
        input_data: ProcessMethodStateResponseInput,
    ) -> MethodStateWorkflowResult:
        response_text = str(input_data.get("responseText") or "").strip()
        if not response_text:
            raise ValidationError("responseText is required")
        user_id = input_data["userId"]
        idempotency_key = str(input_data.get("idempotencyKey") or "").strip()
        if not idempotency_key:
            raise ValidationError("idempotencyKey is required")
        source = str(input_data.get("source") or "").strip()
        if not source:
            raise ValidationError("source is required")
        if source not in {
            "clarifying_answer",
            "freeform_followup",
            "body_note",
            "amplification_answer",
            "relational_scene",
            "dream_dynamics",
            "goal_feedback",
            "practice_feedback",
            "consent_update",
        }:
            raise ValidationError(f"Unsupported method-state source: {source}")
        anchor_refs = deepcopy(input_data.get("anchorRefs", {}))
        anchor_refs_for_load = deepcopy(anchor_refs)
        if source == "clarifying_answer":
            anchor_refs_for_load.pop("promptId", None)
        if source not in {"body_note", "consent_update"} and not self._method_state_has_anchor(
            anchor_refs
        ):
            raise ValidationError("anchorRefs are required for this method-state response")
        existing_run = await self._repository.get_method_state_capture_run_by_idempotency_key(
            user_id,
            idempotency_key,
        )
        if existing_run is not None:
            if existing_run.get("status") in {"completed", "no_capture"}:
                return await self._materialize_method_state_result(existing_run)
            raise ConflictError(
                "Method-state response with idempotency key "
                f"{idempotency_key} is already in progress."
            )

        observed_at = str(input_data.get("observedAt") or now_iso())
        response_material = await self.create_material(
            {
                "userId": user_id,
                "materialType": "reflection",
                "text": response_text,
                "materialDate": observed_at,
                "privacyClass": input_data.get("privacyClass", "user_private"),
                "source": "hermes_ui",
                "tags": ["method-state", source],
            }
        )
        anchors = await self._load_method_state_anchors(
            user_id=user_id,
            anchor_refs=anchor_refs_for_load,
        )
        clarification_prompt: ClarificationPromptRecord | None = None
        if source == "clarifying_answer":
            clarification_prompt = await self._resolve_clarification_prompt_for_method_state_response(
                user_id=user_id,
                anchor_refs=anchor_refs,
                anchors=anchors,
            )
        expected_targets = self._resolve_expected_capture_targets(
            source=source,
            expected_targets=input_data.get("expectedTargets", []),
            anchors=anchors,
        )
        context_only_fallback = self._is_context_only_fallback_clarification(
            anchors=anchors,
            prompt=clarification_prompt,
            expected_targets=expected_targets,
        )
        if context_only_fallback:
            expected_targets = []
        capture_run_id = create_id("method_state_capture")
        empty_plan: MemoryWritePlan = {
            "runId": capture_run_id,
            "proposals": [],
            "evidenceItems": [],
        }
        await self._repository.create_method_state_capture_run(
            {
                "id": capture_run_id,
                "userId": user_id,
                "idempotencyKey": idempotency_key,
                "source": source,
                "status": "processing",
                "anchorRefs": deepcopy(anchor_refs),
                "responseMaterialId": response_material["id"],
                "evidenceIds": [],
                "expectedTargets": list(expected_targets),
                "extractionResult": {},
                "appliedEntityRefs": [],
                "memoryWritePlan": deepcopy(empty_plan),
                "proposalDecisions": [],
                "createdAt": now_iso(),
                "updatedAt": now_iso(),
            }
        )

        window_start, window_end = self._resolve_window(anchor=observed_at)
        method_context = await self._repository.build_method_context_snapshot_from_records(
            user_id,
            window_start=window_start,
            window_end=window_end,
            material_id=str(anchor_refs.get("materialId") or response_material["id"]),
        )
        bundle = await self._load_surface_context_bundle(
            user_id=user_id,
            window_start=window_start,
            window_end=window_end,
            surface="method_state_response",
            payload={"methodContextSnapshot": method_context},
            material_id=cast(
                Id | None,
                anchor_refs.get("materialId") or response_material["id"],
            ),
            safety_context=cast(SafetyContext | None, input_data.get("safetyContext")),
        )
        method_context = cast(MethodContextSnapshot, bundle["methodContextSnapshot"])
        thread_digests = cast(list[ThreadDigest], bundle["threadDigests"])
        warnings: list[str] = []
        if not expected_targets and not context_only_fallback:
            coach_loop_key = str(anchor_refs.get("coachLoopKey") or "").strip()
            if coach_loop_key:
                expected_targets = self._coach_expected_targets_from_context(
                    method_context=method_context,
                    loop_key=coach_loop_key,
                )
                if not expected_targets:
                    warnings.append("coach_loop_anchor_not_found")
        runtime_policy = derive_runtime_method_state_policy(method_context)
        life_context = deepcopy(input_data.get("lifeContextSnapshot"))
        if life_context is None:
            life_context = await self._repository.build_life_context_snapshot_from_records(
                user_id,
                window_start=window_start,
                window_end=window_end,
                exclude_material_id=response_material["id"],
            )
        hermes_memory = await self._repository.build_hermes_memory_context_from_records(
            user_id,
            max_items=20,
        )
        consent_preferences = (
            list(method_context.get("consentPreferences", [])) if method_context else []
        )
        routing_output: dict[str, object] = {
            "answerSummary": "",
            "evidenceSpans": [],
            "captureCandidates": [],
            "followUpPrompts": [],
            "routingWarnings": [],
        }
        if expected_targets and self._method_state_llm is not None:
            routing_output = await self._method_state_llm.route_method_state_response(
                {
                    "userId": user_id,
                    "responseText": response_text,
                    "source": source,
                    "anchorRefs": deepcopy(anchor_refs),
                    "expectedTargets": list(expected_targets),
                    "clarificationIntent": deepcopy(anchors.get("clarificationIntent", {})),
                    "methodContextSnapshot": deepcopy(method_context or {}),
                    "threadDigests": deepcopy(thread_digests),
                    "lifeContextSnapshot": deepcopy(life_context or {}),
                    "hermesMemoryContext": deepcopy(hermes_memory),
                    "safetyContext": deepcopy(input_data.get("safetyContext", {})),
                    "consentPreferences": deepcopy(consent_preferences),
                    "recentPromptOrRunSummary": self._method_state_anchor_summary(anchors),
                    "options": deepcopy(normalize_options(input_data.get("options"))),
                }
            )
            warnings.extend(str(item) for item in routing_output.get("routingWarnings", []))
        elif expected_targets:
            warnings.append("method_state_routing_unavailable")

        evidence_items = await self._create_method_state_evidence(
            user_id=user_id,
            response_material_id=response_material["id"],
            response_text=response_text,
            observed_at=observed_at,
            privacy_class=str(input_data.get("privacyClass") or "user_private"),
            spans=routing_output.get("evidenceSpans"),
        )
        evidence_ids_by_ref = {str(item.get("sourceId") or item["id"]): item["id"] for item in []}
        for item in routing_output.get("evidenceSpans", []):
            if not isinstance(item, dict):
                continue
            ref_key = str(item.get("refKey") or "").strip()
            if not ref_key:
                continue
            matching = next(
                (
                    evidence["id"]
                    for evidence in evidence_items
                    if evidence.get("quoteOrSummary")
                    == self._method_state_evidence_text(response_text=response_text, span=item)
                ),
                None,
            )
            if matching:
                evidence_ids_by_ref[ref_key] = matching

        pending_proposals: list[MemoryWriteProposal] = []
        withheld_candidates: list[dict[str, object]] = []
        applied_entity_refs: list[MethodStateAppliedEntityRef] = []
        for raw_candidate in routing_output.get("captureCandidates", []):
            if not isinstance(raw_candidate, dict):
                continue
            candidate = deepcopy(raw_candidate)
            outcome = await self._apply_method_state_candidate(
                user_id=user_id,
                source=source,
                response_material=response_material,
                observed_at=observed_at,
                expected_targets=expected_targets,
                anchors=anchors,
                candidate=candidate,
                evidence_ids_by_ref=evidence_ids_by_ref,
                consent_preferences=consent_preferences,
                safety_context=input_data.get("safetyContext"),
                runtime_policy=runtime_policy,
                window_start=window_start,
                window_end=window_end,
            )
            proposal = outcome.get("proposal")
            if isinstance(proposal, dict):
                pending_proposals.append(proposal)
            applied_ref = outcome.get("appliedEntityRef")
            if isinstance(applied_ref, dict):
                applied_entity_refs.append(applied_ref)
            withheld = outcome.get("withheld")
            if isinstance(withheld, dict):
                withheld_candidates.append(withheld)
            warning = outcome.get("warning")
            if warning:
                warnings.append(str(warning))

        if source == "clarifying_answer":
            await self._record_clarification_answer_from_method_state(
                user_id=user_id,
                prompt=clarification_prompt,
                response_text=response_text,
                response_material=response_material,
                anchor_refs=anchor_refs,
                applied_entity_refs=applied_entity_refs,
                pending_proposals=pending_proposals,
                warnings=warnings,
                privacy_class=str(input_data.get("privacyClass") or "user_private"),
                capture_target=cast(
                    ClarificationCaptureTarget,
                    "answer_only"
                    if context_only_fallback
                    else (
                        clarification_prompt.get("captureTarget")
                        if clarification_prompt is not None
                        else "answer_only"
                    ),
                ),
            )

        warnings = list(dict.fromkeys(str(item) for item in warnings if str(item).strip()))
        extraction_result = deepcopy(routing_output)
        extraction_result["routingWarnings"] = warnings
        extraction_result["withheldCandidates"] = deepcopy(withheld_candidates)
        memory_write_plan: MemoryWritePlan = {
            "runId": capture_run_id,
            "proposals": deepcopy(pending_proposals),
            "evidenceItems": deepcopy(evidence_items),
        }
        final_status = "completed" if (applied_entity_refs or pending_proposals) else "no_capture"
        updated_run = await self._repository.update_method_state_capture_run(
            user_id,
            capture_run_id,
            {
                "status": final_status,
                "evidenceIds": [item["id"] for item in evidence_items],
                "extractionResult": extraction_result,
                "appliedEntityRefs": deepcopy(applied_entity_refs),
                "memoryWritePlan": deepcopy(memory_write_plan),
                "proposalDecisions": self._proposal_decisions_from_memory_write_plan(
                    memory_write_plan
                ),
                "updatedAt": now_iso(),
            },
        )
        await self._record_adaptation_signal(
            user_id=user_id,
            event_type="method_state_response_processed",
            signals={
                "source": source,
                "appliedCount": len(applied_entity_refs),
                "proposalCount": len(pending_proposals),
            },
        )
        adaptation_event_by_entity = {
            "BodyState": "body_state_captured_from_response",
            "PersonalAmplification": "amplification_answer_captured",
            "PracticeSession": "practice_feedback_recorded",
            "Goal": "goal_feedback_recorded",
            "GoalTension": "goal_feedback_recorded",
            "RelationalScene": "relational_scene_recorded",
        }
        for applied_ref in applied_entity_refs:
            event_type = adaptation_event_by_entity.get(str(applied_ref.get("entityType") or ""))
            if not event_type:
                continue
            await self._record_adaptation_signal(
                user_id=user_id,
                event_type=event_type,
                signals={
                    "source": source,
                    "entityType": applied_ref.get("entityType"),
                    "entityId": applied_ref.get("entityId"),
                },
            )
        return {
            "captureRun": updated_run,
            "responseMaterial": response_material,
            "evidence": evidence_items,
            "appliedEntityRefs": applied_entity_refs,
            "pendingProposals": pending_proposals,
            "followUpPrompts": [
                str(item) for item in routing_output.get("followUpPrompts", []) if str(item).strip()
            ],
            "withheldCandidates": withheld_candidates,
            "warnings": warnings,
        }

    async def approve_method_state_capture_proposals(
        self,
        *,
        user_id: Id,
        capture_run_id: Id,
        proposal_ids: list[Id],
        integration_note: str | None = None,
    ) -> MethodStateCaptureRunRecord:
        capture_run = await self._repository.get_method_state_capture_run(user_id, capture_run_id)
        plan = capture_run.get("memoryWritePlan")
        if not plan:
            raise ValidationError(
                f"Method-state capture run {capture_run_id} has no memory write plan."
            )
        proposals = self._proposal_records_from_memory_write_plan(
            memory_write_plan=plan,
            proposal_ids=proposal_ids,
            owner_label="method-state capture run",
            owner_id=capture_run_id,
        )
        for proposal in proposals:
            self._assert_transition_from_decisions(
                capture_run.get("proposalDecisions", []),
                proposal["id"],
                "approved",
            )
        applied = await self._repository.apply_approved_proposals(
            user_id=user_id,
            memory_write_plan=plan,
            approved_proposal_ids=[proposal["id"] for proposal in proposals],
        )
        timestamp = now_iso()
        integration: IntegrationRecord = {
            "id": create_id("integration"),
            "userId": user_id,
            "materialId": capture_run.get("responseMaterialId"),
            "action": "approved_proposals",
            "approvedProposalIds": list(applied["appliedProposalIds"]),
            "rejectedProposalIds": [],
            "suppressedHypothesisIds": [],
            "affectedEntityIds": list(applied.get("affectedEntityIds", [])),
            "createdAt": timestamp,
        }
        if integration_note:
            integration["note"] = integration_note
        await self._repository.create_integration_record(integration)
        updated_run = await self._repository.update_method_state_capture_run(
            user_id,
            capture_run_id,
            {
                "proposalDecisions": self._merge_proposal_decisions(
                    capture_run.get("proposalDecisions", []),
                    [
                        {
                            "proposalId": proposal["id"],
                            "action": proposal["action"],
                            "entityType": proposal["entityType"],
                            "status": "approved",
                            "decidedAt": timestamp,
                            "integrationRecordId": integration["id"],
                        }
                        for proposal in proposals
                    ],
                ),
                "updatedAt": timestamp,
            },
        )
        return updated_run

    async def reject_method_state_capture_proposals(
        self,
        *,
        user_id: Id,
        capture_run_id: Id,
        proposal_ids: list[Id],
        reason: str | None = None,
    ) -> MethodStateCaptureRunRecord:
        capture_run = await self._repository.get_method_state_capture_run(user_id, capture_run_id)
        plan = capture_run.get("memoryWritePlan")
        if not plan:
            raise ValidationError(
                f"Method-state capture run {capture_run_id} has no memory write plan."
            )
        proposals = self._proposal_records_from_memory_write_plan(
            memory_write_plan=plan,
            proposal_ids=proposal_ids,
            owner_label="method-state capture run",
            owner_id=capture_run_id,
        )
        for proposal in proposals:
            self._assert_transition_from_decisions(
                capture_run.get("proposalDecisions", []),
                proposal["id"],
                "rejected",
            )
        timestamp = now_iso()
        integration: IntegrationRecord = {
            "id": create_id("integration"),
            "userId": user_id,
            "materialId": capture_run.get("responseMaterialId"),
            "action": "rejected_proposals",
            "approvedProposalIds": [],
            "rejectedProposalIds": [proposal["id"] for proposal in proposals],
            "suppressedHypothesisIds": [],
            "affectedEntityIds": [],
            "createdAt": timestamp,
        }
        if reason:
            integration["note"] = reason
        await self._repository.create_integration_record(integration)
        updated_run = await self._repository.update_method_state_capture_run(
            user_id,
            capture_run_id,
            {
                "proposalDecisions": self._merge_proposal_decisions(
                    capture_run.get("proposalDecisions", []),
                    [
                        {
                            "proposalId": proposal["id"],
                            "action": proposal["action"],
                            "entityType": proposal["entityType"],
                            "status": "rejected",
                            "decidedAt": timestamp,
                            "integrationRecordId": integration["id"],
                            "reason": reason,
                        }
                        for proposal in proposals
                    ],
                ),
                "updatedAt": timestamp,
            },
        )
        return updated_run

    async def approve_living_myth_review_proposals(
        self,
        *,
        user_id: Id,
        review_id: Id,
        proposal_ids: list[Id],
    ) -> LivingMythReviewRecord:
        review = await self._repository.get_living_myth_review(user_id, review_id)
        plan = review.get("memoryWritePlan")
        if not plan:
            raise ValidationError(f"Living myth review {review_id} has no memory write plan.")
        proposals = self._review_proposal_records(review, proposal_ids)
        for proposal in proposals:
            self._assert_review_proposal_transition(review, proposal["id"], "approved")
        await self._repository.apply_approved_proposals(
            user_id=user_id,
            memory_write_plan=plan,
            approved_proposal_ids=[proposal["id"] for proposal in proposals],
        )
        timestamp = now_iso()
        updated_review = await self._repository.update_living_myth_review(
            user_id,
            review_id,
            {
                "proposalDecisions": self._merge_proposal_decisions(
                    review.get("proposalDecisions", []),
                    [
                        {
                            "proposalId": proposal["id"],
                            "action": proposal["action"],
                            "entityType": proposal["entityType"],
                            "status": "approved",
                            "decidedAt": timestamp,
                        }
                        for proposal in proposals
                    ],
                ),
                "updatedAt": timestamp,
            },
        )
        await self._record_adaptation_signal(
            user_id=user_id,
            event_type="living_myth_review_proposal_approved",
            signals={"count": len(proposals)},
        )
        return updated_review

    async def reject_living_myth_review_proposals(
        self,
        *,
        user_id: Id,
        review_id: Id,
        proposal_ids: list[Id],
        reason: str | None = None,
    ) -> LivingMythReviewRecord:
        review = await self._repository.get_living_myth_review(user_id, review_id)
        plan = review.get("memoryWritePlan")
        if not plan:
            raise ValidationError(f"Living myth review {review_id} has no memory write plan.")
        proposals = self._review_proposal_records(review, proposal_ids)
        for proposal in proposals:
            self._assert_review_proposal_transition(review, proposal["id"], "rejected")
        timestamp = now_iso()
        updated_review = await self._repository.update_living_myth_review(
            user_id,
            review_id,
            {
                "proposalDecisions": self._merge_proposal_decisions(
                    review.get("proposalDecisions", []),
                    [
                        {
                            "proposalId": proposal["id"],
                            "action": proposal["action"],
                            "entityType": proposal["entityType"],
                            "status": "rejected",
                            "decidedAt": timestamp,
                            "reason": reason,
                        }
                        for proposal in proposals
                    ],
                ),
                "updatedAt": timestamp,
            },
        )
        await self._record_adaptation_signal(
            user_id=user_id,
            event_type="living_myth_review_proposal_rejected",
            signals={"count": len(proposals)},
        )
        return updated_review

    async def reject_hypotheses(
        self,
        *,
        user_id: Id,
        run_id: Id,
        feedback_by_hypothesis_id: dict[Id, FeedbackValue],
    ) -> IntegrationRecord:
        run = await self._repository.get_interpretation_run(user_id, run_id)
        hydrated_feedback = self._hydrate_feedback_keys(run["result"], feedback_by_hypothesis_id)
        compatibility_result = await self._repository.record_integration(
            {
                "userId": user_id,
                "runId": run_id,
                "memoryWritePlan": run["result"]["memoryWritePlan"],
                "approvedProposalIds": [],
                "feedbackByHypothesisId": hydrated_feedback,
            }
        )
        if compatibility_result.get("integrationNoteId"):
            return await self._repository.get_integration_record(
                user_id,
                compatibility_result["integrationNoteId"],
            )
        action = (
            "refined_hypotheses"
            if any(value["feedback"] == "partially_refined" for value in hydrated_feedback.values())
            else "rejected_hypotheses"
        )
        integration: IntegrationRecord = {
            "id": create_id("integration"),
            "userId": user_id,
            "runId": run_id,
            "materialId": run["materialId"],
            "action": action,
            "approvedProposalIds": [],
            "rejectedProposalIds": [],
            "suppressedHypothesisIds": list(compatibility_result["suppressedHypothesisIds"]),
            "feedbackByHypothesisId": deepcopy(hydrated_feedback),
            "affectedEntityIds": [],
            "createdAt": now_iso(),
        }
        await self._repository.create_integration_record(integration)
        await self._record_adaptation_signal(
            user_id=user_id,
            event_type="hypothesis_rejected",
            signals={"count": len(hydrated_feedback)},
        )
        return integration

    async def revise_entity(
        self,
        *,
        user_id: Id,
        entity_type: GraphNodeType,
        entity_id: Id,
        revision_note: str,
        replacement: dict[str, object] | None = None,
    ) -> IntegrationRecord:
        replacement = replacement or {}
        affected_entity_ids = [entity_id]
        timestamp = now_iso()
        if entity_type in {"MaterialEntry", "DreamEntry", "ReflectionEntry", "ChargedEventNote"}:
            material = await self._repository.get_material(user_id, entity_id, include_deleted=True)
            revision: MaterialRevision = {
                "id": create_id("material_revision"),
                "userId": user_id,
                "materialId": entity_id,
                "revisionNumber": len(
                    await self._repository.list_material_revisions(user_id, entity_id)
                )
                + 1,
                "previousText": material.get("text"),
                "newText": replacement.get("text", material.get("text")),
                "previousSummary": material.get("summary"),
                "newSummary": replacement.get("summary", material.get("summary")),
                "reason": "user_requested",
                "note": revision_note,
                "createdAt": timestamp,
            }
            await self._repository.create_material_revision(revision)
            updates = {
                "updatedAt": timestamp,
                "status": "revised",
                "currentRevisionId": revision["id"],
            }
            if "text" in replacement:
                updates["text"] = str(replacement["text"])
            if "summary" in replacement:
                updates["summary"] = str(replacement["summary"])
            if "title" in replacement:
                updates["title"] = str(replacement["title"])
            await self._repository.update_material(user_id, entity_id, updates)
        elif entity_type == "PersonalSymbol":
            before = await self._repository.get_symbol(user_id, entity_id, include_deleted=True)
            updates = {"updatedAt": timestamp, "status": "revised"}
            for field in (
                "canonicalName",
                "aliases",
                "category",
                "linkedMaterialIds",
                "linkedLifeEventRefs",
            ):
                if field in replacement:
                    updates[field] = replacement[field]
            after = await self._repository.update_symbol(user_id, entity_id, updates)
            history: SymbolHistoryEntry = {
                "id": create_id("symbol_history"),
                "userId": user_id,
                "symbolId": entity_id,
                "eventType": "revised",
                "evidenceIds": [],
                "previousValue": before,
                "newValue": after,
                "note": revision_note,
                "createdAt": timestamp,
            }
            await self._repository.append_symbol_history(history)
        elif entity_type in {"Theme", "ComplexCandidate"}:
            before = await self._repository.get_pattern(user_id, entity_id, include_deleted=True)
            updates = {"updatedAt": timestamp}
            for field in (
                "label",
                "formulation",
                "status",
                "activationIntensity",
                "confidence",
                "linkedSymbols",
                "linkedSymbolIds",
                "linkedMaterialIds",
                "linkedLifeEventRefs",
            ):
                if field in replacement:
                    updates[field] = replacement[field]
            after = await self._repository.update_pattern(user_id, entity_id, updates)
            history: PatternHistoryEntry = {
                "id": create_id("pattern_history"),
                "userId": user_id,
                "patternId": entity_id,
                "eventType": "formulation_revised"
                if "formulation" in replacement
                else "status_changed",
                "evidenceIds": [],
                "previousValue": before,
                "newValue": after,
                "note": revision_note,
                "createdAt": timestamp,
            }
            await self._repository.append_pattern_history(history)
        elif entity_type == "TypologyLens":
            updates = {"updatedAt": timestamp}
            for field in (
                "role",
                "function",
                "claim",
                "confidence",
                "status",
                "evidenceIds",
                "counterevidenceIds",
                "userTestPrompt",
                "linkedMaterialIds",
            ):
                if field in replacement:
                    updates[field] = replacement[field]
            await self._repository.update_typology_lens(user_id, entity_id, updates)
        elif entity_type in {"PracticePlan", "PracticeSession"}:
            updates = {"updatedAt": timestamp}
            for field in (
                "practiceType",
                "target",
                "reason",
                "instructions",
                "durationMinutes",
                "contraindicationsChecked",
                "requiresConsent",
                "status",
                "outcome",
                "activationBefore",
                "activationAfter",
                "completedAt",
            ):
                if field in replacement:
                    updates[field] = replacement[field]
            await self._repository.update_practice_session(user_id, entity_id, updates)
        else:
            await self._repository.revise_entity(
                {
                    "userId": user_id,
                    "entityId": entity_id,
                    "entityType": entity_type,
                    "revisionNote": revision_note,
                    "replacementSummary": str(replacement.get("summary", revision_note)),
                }
            )
        integration: IntegrationRecord = {
            "id": create_id("integration"),
            "userId": user_id,
            "action": "revision",
            "approvedProposalIds": [],
            "rejectedProposalIds": [],
            "suppressedHypothesisIds": [],
            "affectedEntityIds": affected_entity_ids,
            "note": revision_note,
            "createdAt": timestamp,
        }
        await self._repository.create_integration_record(integration)
        return integration

    async def delete_entity(
        self,
        *,
        user_id: Id,
        entity_type: GraphNodeType,
        entity_id: Id,
        mode: DeletionMode = "tombstone",
        reason: str | None = None,
    ) -> IntegrationRecord:
        timestamp = now_iso()
        if entity_type in {"MaterialEntry", "DreamEntry", "ReflectionEntry", "ChargedEventNote"}:
            await self._repository.delete_material(user_id, entity_id, mode=mode, reason=reason)
        elif entity_type == "PersonalSymbol":
            before = await self._repository.get_symbol(user_id, entity_id, include_deleted=True)
            await self._repository.delete_symbol(user_id, entity_id, mode=mode, reason=reason)
            after = await self._repository.get_symbol(user_id, entity_id, include_deleted=True)
            await self._repository.append_symbol_history(
                {
                    "id": create_id("symbol_history"),
                    "userId": user_id,
                    "symbolId": entity_id,
                    "eventType": "deleted",
                    "evidenceIds": [],
                    "previousValue": before,
                    "newValue": after,
                    "note": reason,
                    "createdAt": timestamp,
                }
            )
        elif entity_type in {"Theme", "ComplexCandidate"}:
            before = await self._repository.get_pattern(user_id, entity_id, include_deleted=True)
            await self._repository.delete_pattern(user_id, entity_id, mode=mode, reason=reason)
            after = await self._repository.get_pattern(user_id, entity_id, include_deleted=True)
            await self._repository.append_pattern_history(
                {
                    "id": create_id("pattern_history"),
                    "userId": user_id,
                    "patternId": entity_id,
                    "eventType": "deleted",
                    "evidenceIds": [],
                    "previousValue": before,
                    "newValue": after,
                    "note": reason,
                    "createdAt": timestamp,
                }
            )
        elif entity_type == "TypologyLens":
            await self._repository.delete_typology_lens(
                user_id, entity_id, mode=mode, reason=reason
            )
        elif entity_type in {"PracticePlan", "PracticeSession"}:
            await self._repository.delete_practice_session(user_id, entity_id, mode=mode)
        elif entity_type == "WeeklyReview":
            await self._repository.delete_weekly_review(user_id, entity_id, mode=mode)
        elif entity_type == "ContextSnapshot":
            await self._repository.delete_context_snapshot(user_id, entity_id, mode=mode)
        else:
            await self._repository.delete_entity(
                {
                    "userId": user_id,
                    "entityId": entity_id,
                    "entityType": entity_type,
                    "reason": "privacy" if mode == "erase" else "user_requested",
                }
            )
        integration: IntegrationRecord = {
            "id": create_id("integration"),
            "userId": user_id,
            "action": "deletion",
            "approvedProposalIds": [],
            "rejectedProposalIds": [],
            "suppressedHypothesisIds": [],
            "affectedEntityIds": [entity_id],
            "createdAt": timestamp,
        }
        if reason:
            integration["note"] = reason
        await self._repository.create_integration_record(integration)
        return integration

    async def get_symbol_history(
        self, *, user_id: Id, symbol_id: Id, limit: int = 50
    ) -> SymbolHistoryResult:
        symbol = await self.get_symbol(user_id=user_id, symbol_id=symbol_id)
        history = await self._repository.list_symbol_history(user_id, symbol_id, limit=limit)
        linked_materials = await self._load_materials(user_id, symbol.get("linkedMaterialIds", []))
        return {"symbol": symbol, "history": history, "linkedMaterials": linked_materials}

    async def get_pattern_history(
        self, *, user_id: Id, pattern_id: Id, limit: int = 50
    ) -> PatternHistoryResult:
        pattern = await self._repository.get_pattern(user_id, pattern_id)
        history = await self._repository.list_pattern_history(user_id, pattern_id, limit=limit)
        linked_materials = await self._load_materials(user_id, pattern.get("linkedMaterialIds", []))
        return {"pattern": pattern, "history": history, "linkedMaterials": linked_materials}

    async def generate_weekly_review(
        self,
        *,
        user_id: Id,
        window_start: str,
        window_end: str,
    ) -> WeeklyReviewRecord:
        bundle = await self._load_surface_context_bundle(
            user_id=user_id,
            window_start=window_start,
            window_end=window_end,
            surface="weekly_review",
        )
        summary_input = cast(CirculationSummaryInput, bundle["preparedPayload"])
        result = await self._core.generate_weekly_review_summary(summary_input)
        practice_session = await self._store_review_practice(user_id=user_id, result=result)
        context_snapshots = await self._repository.list_context_snapshots(
            user_id,
            window_start=window_start,
            window_end=window_end,
        )
        materials = [
            item
            for item in await self._repository.list_materials(user_id)
            if window_start <= item.get("materialDate", item.get("createdAt", "")) <= window_end
        ]
        evidence_ids = self._merge_ids(
            [link["evidenceId"] for link in result["notableLifeContextLinks"]],
            [
                evidence_id
                for candidate in result["activeComplexCandidates"]
                for evidence_id in candidate.get("evidenceIds", [])
            ],
        )
        review: WeeklyReviewRecord = {
            "id": create_id("weekly_review"),
            "userId": user_id,
            "windowStart": window_start,
            "windowEnd": window_end,
            "createdAt": now_iso(),
            "recurringSymbolIds": [item["id"] for item in result["recurringSymbols"]],
            "activePatternIds": [item["id"] for item in result["activeComplexCandidates"]],
            "materialIds": [item["id"] for item in materials],
            "contextSnapshotIds": [item["id"] for item in context_snapshots],
            "evidenceIds": evidence_ids,
            "result": result,
            "status": "active",
        }
        if practice_session is not None:
            review["practiceSuggestionId"] = practice_session["id"]
        return await self._repository.create_weekly_review(review)

    async def generate_discovery(
        self,
        input_data: GenerateDiscoveryInput,
    ) -> DiscoveryResult:
        resolved_start, resolved_end = self._resolve_window(
            anchor=self._optional_str(input_data.get("windowEnd")),
            fallback_start=self._optional_str(input_data.get("windowStart")),
            fallback_end=self._optional_str(input_data.get("windowEnd")),
        )
        if self._parse_datetime(resolved_start) > self._parse_datetime(resolved_end):
            raise ValidationError("Discovery windowStart cannot be after windowEnd.")
        explicit_question = self._optional_str(input_data.get("explicitQuestion"))
        max_items = min(max(int(input_data.get("maxItems", 5)), 1), 8)
        memory_limit = min(max(max_items * 4, 12), 30)
        graph_limit = min(max(max_items * 20, 40), 100)
        memory_query: MemoryRetrievalQuery = {
            "windowStart": resolved_start,
            "windowEnd": resolved_end,
            "rankingProfile": self._discovery_ranking_profile(input_data.get("rankingProfile")),
            "limit": memory_limit,
        }
        text_query = self._optional_str(input_data.get("textQuery")) or explicit_question
        if text_query:
            memory_query["textQuery"] = text_query
        raw_namespaces = input_data.get("memoryNamespaces")
        if isinstance(raw_namespaces, list):
            namespaces = [str(value) for value in raw_namespaces if str(value).strip()]
            if namespaces:
                memory_query["namespaces"] = namespaces  # type: ignore[typeddict-item]
        bundle = await self._load_surface_context_bundle(
            user_id=input_data["userId"],
            window_start=resolved_start,
            window_end=resolved_end,
            include_dashboard=True,
            memory_query=memory_query,
            explicit_question=explicit_question,
        )
        method_context = cast(MethodContextSnapshot | None, bundle["methodContextSnapshot"])
        thread_digests = cast(list[ThreadDigest], bundle["threadDigests"])
        dashboard = cast(DashboardSummary, bundle["dashboard"])
        memory_snapshot = cast(MemoryKernelSnapshot, bundle["memorySnapshot"])
        root_node_ids = self._normalize_discovery_root_ids(input_data.get("rootNodeIds"))
        if not root_node_ids:
            root_node_ids = self._derive_discovery_root_ids(
                dashboard=dashboard,
                memory_snapshot=memory_snapshot,
                method_context=method_context,
            )
        graph_query: GraphQuery = {
            "maxDepth": 2,
            "direction": "both",
            "includeEvidence": True,
            "limit": graph_limit,
        }
        if root_node_ids:
            graph_query["rootNodeIds"] = root_node_ids
        graph = await self.query_graph(user_id=input_data["userId"], query=graph_query)
        sections = self._build_discovery_sections(
            dashboard=dashboard,
            memory_snapshot=memory_snapshot,
            graph=graph,
            method_context=method_context,
            thread_digests=thread_digests,
            max_items=max_items,
        )
        warnings = [
            str(value)
            for value in graph.get("warnings", [])
            if isinstance(value, str) and value.strip()
        ]
        source_counts: DiscoverySourceCounts = {
            "recentMaterialCount": len(dashboard["recentMaterials"]),
            "recurringSymbolCount": len(dashboard["recurringSymbols"]),
            "activePatternCount": len(dashboard["activePatterns"]),
            "pendingProposalCount": dashboard["pendingProposalCount"],
            "memoryItemCount": len(memory_snapshot["items"]),
            "threadDigestCount": len(thread_digests),
            "graphNodeCount": len(graph["nodes"]),
            "graphEdgeCount": len(graph["edges"]),
        }
        discovery: DiscoveryResult = {
            "discoveryId": create_id("discovery"),
            "userId": input_data["userId"],
            "generatedAt": now_iso(),
            "windowStart": resolved_start,
            "windowEnd": resolved_end,
            "sections": sections,
            "sourceCounts": source_counts,
            "fallbackText": self._render_discovery_fallback(
                sections=sections,
                window_start=resolved_start,
                window_end=resolved_end,
                explicit_question=explicit_question,
            ),
            "warnings": warnings,
        }
        if explicit_question:
            discovery["explicitQuestion"] = explicit_question
        return discovery

    async def generate_alive_today(
        self,
        *,
        user_id: Id,
        window_start: str | None = None,
        window_end: str | None = None,
        explicit_question: str | None = None,
    ) -> AliveTodayResult:
        resolved_start, resolved_end = self._resolve_window(
            anchor=window_end,
            fallback_start=window_start,
            fallback_end=window_end,
        )
        _, summary = await self._build_ephemeral_circulation_summary(
            user_id=user_id,
            window_start=resolved_start,
            window_end=resolved_end,
            explicit_question=explicit_question,
            surface="alive_today",
        )
        return {"summary": summary}

    async def generate_journey_page(
        self,
        input_data: GenerateJourneyPageInput,
    ) -> JourneyPageResult:
        resolved_start, resolved_end = self._resolve_window(
            anchor=input_data.get("windowEnd"),
            fallback_start=input_data.get("windowStart"),
            fallback_end=input_data.get("windowEnd"),
        )
        max_invitations = min(max(int(input_data.get("maxInvitations", 3)), 0), 5)
        include_analysis_packet = bool(input_data.get("includeAnalysisPacket", True))
        summary_input, summary = await self._build_ephemeral_circulation_summary(
            user_id=input_data["userId"],
            window_start=resolved_start,
            window_end=resolved_end,
            explicit_question=self._optional_str(input_data.get("explicitQuestion")),
            surface="journey_page",
        )
        dashboard = await self._repository.get_dashboard_summary(user_id=input_data["userId"])
        weekly_reviews = await self._repository.list_weekly_reviews(input_data["userId"], limit=5)
        memory_snapshot = await self._repository.build_memory_kernel_snapshot(input_data["userId"])
        recent_practices = await self._repository.list_practice_sessions(
            input_data["userId"],
            statuses=["recommended", "accepted", "completed", "skipped"],
            include_deleted=False,
            limit=100,
        )
        journeys = await self._repository.list_journeys(
            input_data["userId"],
            include_deleted=False,
            limit=50,
        )
        existing_briefs = await self._repository.list_proactive_briefs(
            input_data["userId"],
            include_deleted=False,
            limit=100,
        )
        profile = await self._repository.get_adaptation_profile(input_data["userId"])
        cadence_hints = self._adaptation_engine.derive_rhythm_hints(profile=profile)
        adaptation_summary = self._adaptation_engine.summarize(profile)
        method_context = summary_input.get("methodContextSnapshot")
        thread_digests = cast(
            list[ThreadDigest],
            [item for item in summary_input.get("threadDigests", []) if isinstance(item, dict)],
        )
        generated_at = now_iso()
        seeds = self._proactive_engine.build_candidate_seeds(
            user_id=input_data["userId"],
            memory_snapshot=memory_snapshot,
            dashboard=dashboard,
            method_context=method_context,
            thread_digests=thread_digests,
            recent_practices=recent_practices,
            journeys=journeys,
            existing_briefs=existing_briefs,
            adaptation_profile=adaptation_summary,
            source="manual",
            now=generated_at,
            limit=max(10, max_invitations + 3),
        )
        due_seeds = self._proactive_engine.filter_due_candidates(
            seeds=seeds,
            existing_briefs=existing_briefs,
            cadence_hints=cadence_hints,
            source="manual",
            now=generated_at,
        )
        alive_surface = self._build_journey_alive_surface(summary)
        weekly_surface = self._build_journey_weekly_surface(
            weekly_reviews=weekly_reviews,
            existing_briefs=existing_briefs,
            due_seeds=due_seeds,
            window_start=resolved_start,
            window_end=resolved_end,
        )
        rhythmic_invitations = self._build_journey_rhythmic_invitations(
            existing_briefs=existing_briefs,
            due_seeds=due_seeds,
            max_invitations=max_invitations,
            window_start=resolved_start,
            window_end=resolved_end,
        )
        practice_container = self._build_journey_practice_container(
            recent_practices=recent_practices,
            practice_suggestion=summary.get("practiceSuggestion"),
            window_start=resolved_start,
            window_end=resolved_end,
            now=generated_at,
        )
        analysis_packet = (
            self._build_journey_analysis_packet_preview(
                summary=summary,
                summary_input=summary_input,
                recent_practices=recent_practices,
                window_start=resolved_start,
                window_end=resolved_end,
            )
            if include_analysis_packet
            else None
        )
        cards: list[JourneyPageCard] = [
            self._journey_card(
                section="alive_today",
                title=alive_surface["title"],
                body=alive_surface["response"],
                actions=[],
                entity_refs={"symbols": list(alive_surface["recurringSymbolIds"])},
                payload={"activeThemes": list(alive_surface["activeThemes"])},
            ),
            self._journey_card(
                section="weekly_reflection",
                title=weekly_surface["title"],
                body=weekly_surface["summary"],
                status=weekly_surface["kind"],
                actions=weekly_surface["actions"],
                entity_refs={"reviews": [weekly_surface["reviewId"]]}
                if weekly_surface.get("reviewId")
                else None,
            ),
            self._journey_card(
                section="rhythmic_invitations",
                title="Rhythmic invitations",
                body=self._render_invitation_body(rhythmic_invitations),
                actions=self._card_actions_from_invitations(rhythmic_invitations),
                payload={"items": deepcopy(rhythmic_invitations)},
            ),
            self._journey_card(
                section="practice_container",
                title=practice_container["title"],
                body=practice_container["summary"],
                status=practice_container["kind"],
                actions=practice_container["actions"],
                entity_refs={"practiceSessions": [practice_container["practiceSessionId"]]}
                if practice_container.get("practiceSessionId")
                else None,
                payload={
                    "practiceRecommendation": deepcopy(
                        practice_container.get("practiceRecommendation")
                    )
                }
                if practice_container.get("practiceRecommendation")
                else None,
            ),
        ]
        if analysis_packet is not None:
            cards.append(
                self._journey_card(
                    section="analysis_packet",
                    title="Analysis preview",
                    body=self._render_analysis_preview_body(analysis_packet),
                    status=analysis_packet["status"],
                    actions=[],
                    payload={"sections": deepcopy(analysis_packet["sections"])},
                )
            )
        result: JourneyPageResult = {
            "pageId": create_id("journey_page"),
            "userId": input_data["userId"],
            "title": "Journey page",
            "generatedAt": generated_at,
            "windowStart": resolved_start,
            "windowEnd": resolved_end,
            "cards": cards,
            "aliveToday": alive_surface,
            "weeklySurface": weekly_surface,
            "rhythmicInvitations": rhythmic_invitations,
            "practiceContainer": practice_container,
            "fallbackText": self._render_journey_page_fallback(
                cards=cards,
                window_start=resolved_start,
                window_end=resolved_end,
            ),
            "warnings": [],
        }
        if analysis_packet is not None:
            result["analysisPacket"] = analysis_packet
        return result

    async def generate_threshold_review(
        self,
        input_data: GenerateThresholdReviewInput,
    ) -> ThresholdReviewWorkflowResult:
        anchor = input_data.get("windowEnd") or now_iso()
        default_start = self._format_datetime(self._parse_datetime(anchor) - timedelta(days=30))
        resolved_start, resolved_end = self._resolve_window(
            anchor=input_data.get("windowEnd"),
            fallback_start=input_data.get("windowStart") or default_start,
            fallback_end=input_data.get("windowEnd") or anchor,
        )
        review_input = await self._repository.build_threshold_review_input(
            input_data["userId"],
            window_start=resolved_start,
            window_end=resolved_end,
            threshold_process_id=input_data.get("thresholdProcessId"),
            explicit_question=input_data.get("explicitQuestion"),
        )
        bundle = await self._load_surface_context_bundle(
            user_id=input_data["userId"],
            window_start=resolved_start,
            window_end=resolved_end,
            surface="generic",
            payload=cast(dict[str, object], review_input),
            explicit_question=self._optional_str(input_data.get("explicitQuestion")),
            safety_context=cast(SafetyContext | None, input_data.get("safetyContext")),
        )
        review_input = cast(ThresholdReviewInput, bundle["preparedPayload"])
        result = await self._core.generate_threshold_review(review_input)
        practice_session: PracticeSessionRecord | None = None
        practice = result.get("practiceRecommendation")
        if practice and input_data.get("persist", True):
            practice_session = await self._store_practice_plan(
                user_id=input_data["userId"],
                practice=practice,
                trigger={"triggerType": "threshold_review"},
            )
        workflow: ThresholdReviewWorkflowResult = {
            "result": result,
            "pendingProposals": list(result.get("memoryWritePlan", {}).get("proposals", [])),
        }
        if practice_session is not None:
            workflow["practiceSession"] = practice_session
        if input_data.get("persist", True):
            context_snapshots = await self._repository.list_context_snapshots(
                input_data["userId"],
                window_start=resolved_start,
                window_end=resolved_end,
            )
            materials = [
                item
                for item in await self._repository.list_materials(input_data["userId"])
                if (
                    resolved_start
                    <= item.get("materialDate", item.get("createdAt", ""))
                    <= resolved_end
                )
            ]
            evidence_ids = self._merge_ids(
                [
                    evidence_id
                    for threshold in result.get("thresholdProcesses", [])
                    for evidence_id in threshold.get("evidenceIds", [])
                ],
                [
                    evidence_id
                    for anchor_item in result.get("realityAnchors", [])
                    for evidence_id in anchor_item.get("evidenceIds", [])
                ],
            )
            plan = result.get("memoryWritePlan") or {}
            evidence_ids = self._merge_ids(
                evidence_ids,
                [
                    evidence_id
                    for proposal in plan.get("proposals", [])
                    for evidence_id in proposal.get("evidenceIds", [])
                ],
            )
            evidence_ids = self._merge_ids(
                evidence_ids,
                [item.get("id") for item in plan.get("evidenceItems", []) if item.get("id")],
            )
            review_record: LivingMythReviewRecord = {
                "id": create_id("living_myth_review"),
                "userId": input_data["userId"],
                "reviewType": "threshold_review",
                "status": "withheld" if result.get("withheld") else "generated",
                "windowStart": resolved_start,
                "windowEnd": resolved_end,
                "materialIds": [item["id"] for item in materials],
                "contextSnapshotIds": [item["id"] for item in context_snapshots],
                "evidenceIds": evidence_ids,
                "result": deepcopy(result),
                "proposalDecisions": self._proposal_decisions_from_memory_write_plan(
                    result.get("memoryWritePlan")
                ),
                "createdAt": now_iso(),
                "updatedAt": now_iso(),
            }
            if input_data.get("explicitQuestion"):
                review_record["explicitQuestion"] = str(input_data["explicitQuestion"])
            if result.get("memoryWritePlan"):
                review_record["memoryWritePlan"] = deepcopy(result["memoryWritePlan"])
            if practice_session is not None:
                review_record["practiceSuggestionId"] = practice_session["id"]
            workflow["review"] = await self._repository.create_living_myth_review(review_record)
        return workflow

    async def generate_living_myth_review(
        self,
        input_data: GenerateLivingMythReviewInput,
    ) -> LivingMythReviewWorkflowResult:
        anchor = input_data.get("windowEnd") or now_iso()
        default_start = self._format_datetime(self._parse_datetime(anchor) - timedelta(days=90))
        resolved_start, resolved_end = self._resolve_window(
            anchor=input_data.get("windowEnd"),
            fallback_start=input_data.get("windowStart") or default_start,
            fallback_end=input_data.get("windowEnd") or anchor,
        )
        review_input = await self._repository.build_living_myth_review_input(
            input_data["userId"],
            window_start=resolved_start,
            window_end=resolved_end,
            explicit_question=input_data.get("explicitQuestion"),
        )
        bundle = await self._load_surface_context_bundle(
            user_id=input_data["userId"],
            window_start=resolved_start,
            window_end=resolved_end,
            surface="generic",
            payload=cast(dict[str, object], review_input),
            explicit_question=self._optional_str(input_data.get("explicitQuestion")),
            safety_context=cast(SafetyContext | None, input_data.get("safetyContext")),
            sync_longitudinal=True,
        )
        review_input = cast(LivingMythReviewInput, bundle["preparedPayload"])
        result = await self._core.generate_living_myth_review(review_input)
        practice_session: PracticeSessionRecord | None = None
        practice = result.get("practiceRecommendation")
        if practice and input_data.get("persist", True):
            practice_session = await self._store_practice_plan(
                user_id=input_data["userId"],
                practice=practice,
                trigger={"triggerType": "living_myth_review"},
            )
        workflow: LivingMythReviewWorkflowResult = {
            "result": result,
            "pendingProposals": list(result.get("memoryWritePlan", {}).get("proposals", [])),
        }
        if practice_session is not None:
            workflow["practiceSession"] = practice_session
        if input_data.get("persist", True):
            context_snapshots = await self._repository.list_context_snapshots(
                input_data["userId"],
                window_start=resolved_start,
                window_end=resolved_end,
            )
            materials = [
                item
                for item in await self._repository.list_materials(input_data["userId"])
                if (
                    resolved_start
                    <= item.get("materialDate", item.get("createdAt", ""))
                    <= resolved_end
                )
            ]
            evidence_ids = [
                evidence_id
                for group in (
                    result.get("mythicQuestions", []),
                    result.get("thresholdMarkers", []),
                    result.get("complexEncounters", []),
                )
                for item in group
                for evidence_id in item.get("evidenceIds", [])
            ]
            if result.get("lifeChapter"):
                evidence_ids = self._merge_ids(
                    evidence_ids,
                    list(result["lifeChapter"].get("evidenceIds", [])),
                )
            plan = result.get("memoryWritePlan") or {}
            evidence_ids = self._merge_ids(
                evidence_ids,
                [
                    evidence_id
                    for proposal in plan.get("proposals", [])
                    for evidence_id in proposal.get("evidenceIds", [])
                ],
            )
            evidence_ids = self._merge_ids(
                evidence_ids,
                [item.get("id") for item in plan.get("evidenceItems", []) if item.get("id")],
            )
            review_record: LivingMythReviewRecord = {
                "id": create_id("living_myth_review"),
                "userId": input_data["userId"],
                "reviewType": "living_myth_review",
                "status": "withheld" if result.get("withheld") else "generated",
                "windowStart": resolved_start,
                "windowEnd": resolved_end,
                "materialIds": [item["id"] for item in materials],
                "contextSnapshotIds": [item["id"] for item in context_snapshots],
                "evidenceIds": evidence_ids,
                "result": deepcopy(result),
                "proposalDecisions": self._proposal_decisions_from_memory_write_plan(
                    result.get("memoryWritePlan")
                ),
                "createdAt": now_iso(),
                "updatedAt": now_iso(),
            }
            if input_data.get("explicitQuestion"):
                review_record["explicitQuestion"] = str(input_data["explicitQuestion"])
            if result.get("memoryWritePlan"):
                review_record["memoryWritePlan"] = deepcopy(result["memoryWritePlan"])
            if practice_session is not None:
                review_record["practiceSuggestionId"] = practice_session["id"]
            workflow["review"] = await self._repository.create_living_myth_review(review_record)
        return workflow

    async def generate_analysis_packet(
        self,
        input_data: GenerateAnalysisPacketInput,
    ) -> AnalysisPacketWorkflowResult:
        anchor = input_data.get("windowEnd") or now_iso()
        default_days = 90 if input_data.get("packetFocus") == "dream_series" else 30
        default_start = self._format_datetime(
            self._parse_datetime(anchor) - timedelta(days=default_days)
        )
        resolved_start, resolved_end = self._resolve_window(
            anchor=input_data.get("windowEnd"),
            fallback_start=input_data.get("windowStart") or default_start,
            fallback_end=input_data.get("windowEnd") or anchor,
        )
        packet_input = await self._repository.build_analysis_packet_input(
            input_data["userId"],
            window_start=resolved_start,
            window_end=resolved_end,
            packet_focus=input_data.get("packetFocus"),
            explicit_question=input_data.get("explicitQuestion"),
        )
        bundle = await self._load_surface_context_bundle(
            user_id=input_data["userId"],
            window_start=resolved_start,
            window_end=resolved_end,
            surface="analysis_packet",
            payload=cast(dict[str, object], packet_input),
            explicit_question=self._optional_str(input_data.get("explicitQuestion")),
            safety_context=cast(SafetyContext | None, input_data.get("safetyContext")),
            sync_longitudinal=True,
        )
        packet_input = cast(AnalysisPacketInput, bundle["preparedPayload"])
        result = await self._core.generate_analysis_packet(packet_input)
        workflow: AnalysisPacketWorkflowResult = {"result": result}
        if input_data.get("persist", True):
            packet_record: AnalysisPacketRecord = {
                "id": create_id("analysis_packet"),
                "userId": input_data["userId"],
                "status": "generated",
                "windowStart": resolved_start,
                "windowEnd": resolved_end,
                "packetTitle": result["packetTitle"],
                "sections": deepcopy(result["sections"]),
                "includedMaterialIds": list(result.get("includedMaterialIds", [])),
                "includedRecordRefs": deepcopy(result.get("includedRecordRefs", [])),
                "evidenceIds": list(result.get("evidenceIds", [])),
                "source": result["source"],
                "privacyClass": "approved_summary",
                "userFacingResponse": result["userFacingResponse"],
                "createdAt": now_iso(),
                "updatedAt": now_iso(),
            }
            workflow["packet"] = await self._repository.create_analysis_packet(packet_record)
        return workflow

    async def generate_practice_recommendation(
        self,
        input_data: GeneratePracticeInput,
    ) -> PracticeWorkflowResult:
        resolved_start, resolved_end = self._resolve_window(
            anchor=input_data.get("windowEnd"),
            fallback_start=input_data.get("windowStart"),
            fallback_end=input_data.get("windowEnd"),
        )
        trigger = deepcopy(input_data.get("trigger") or {"triggerType": "manual"})
        adapter_input: BuildPracticeContextInput = {
            "userId": input_data["userId"],
            "windowStart": resolved_start,
            "windowEnd": resolved_end,
            "trigger": trigger,
        }
        if input_data.get("sessionContext") is not None:
            adapter_input["sessionContext"] = normalize_session_context(
                input_data.get("sessionContext")
            )
        if input_data.get("explicitQuestion"):
            adapter_input["explicitQuestion"] = str(input_data["explicitQuestion"])
        if input_data.get("safetyContext") is not None:
            adapter_input["safetyContext"] = deepcopy(input_data["safetyContext"])
        if input_data.get("options") is not None:
            adapter_input["options"] = normalize_options(input_data["options"])
        practice_input = await self._context_adapter.build_practice_input(adapter_input)
        practice_surface: Literal["generic", "practice_followup"] = (
            "practice_followup"
            if str(trigger.get("triggerType") or "manual") == "practice_followup"
            else "generic"
        )
        bundle = await self._load_surface_context_bundle(
            user_id=input_data["userId"],
            window_start=resolved_start,
            window_end=resolved_end,
            surface=practice_surface,
            payload=cast(dict[str, object], practice_input),
            material_id=cast(Id | None, trigger.get("materialId")),
            explicit_question=self._optional_str(input_data.get("explicitQuestion")),
            safety_context=cast(SafetyContext | None, input_data.get("safetyContext")),
        )
        practice_input = cast(PracticeRecommendationInput, bundle["preparedPayload"])
        profile = cast(dict[str, object] | None, bundle["profile"])
        practice_hints = self._adaptation_engine.derive_practice_hints(profile=profile)
        practice_input["practiceHints"] = deepcopy(practice_hints)
        practice_input["adaptationHints"] = deepcopy(practice_hints)
        llm_result = await self._core.generate_practice(practice_input)
        practice_session: PracticeSessionRecord | None = None
        if input_data.get("persist", True):
            practice_session = await self._store_practice_plan(
                user_id=input_data["userId"],
                practice=llm_result["practiceRecommendation"],
                trigger=trigger,
            )
        await self._record_adaptation_signal(
            user_id=input_data["userId"],
            event_type="practice_recommended",
            signals={
                "practiceType": llm_result["practiceRecommendation"]["type"],
                "modality": llm_result["practiceRecommendation"].get("modality"),
                "templateId": llm_result["practiceRecommendation"].get("templateId"),
                "triggerType": trigger.get("triggerType", "manual"),
                "source": (
                    llm_result["llmHealth"]["source"] if llm_result.get("llmHealth") else None
                ),
            },
        )
        result: PracticeWorkflowResult = {
            "practiceRecommendation": llm_result["practiceRecommendation"],
            "userFacingResponse": llm_result["userFacingResponse"],
            "llmResult": llm_result,
        }
        if practice_session is not None:
            result["practiceSession"] = practice_session
        return result

    async def respond_practice_recommendation(
        self,
        input_data: RespondPracticeInput,
    ) -> PracticeSessionRecord:
        action = str(input_data["action"])
        if action not in {"accepted", "skipped"}:
            raise ValidationError("Practice response action must be accepted or skipped.")
        practice = await self._repository.get_practice_session(
            input_data["userId"],
            input_data["practiceSessionId"],
        )
        previous_status = str(practice["status"])
        if previous_status == action:
            return practice
        try:
            self._practice_engine.validate_transition(
                current_status=previous_status,  # type: ignore[arg-type]
                target_status=action,  # type: ignore[arg-type]
            )
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        timestamp = now_iso()
        note = str(input_data.get("note") or "").strip()
        updates: dict[str, object] = {
            "status": action,
            "updatedAt": timestamp,
        }
        if action == "accepted":
            updates["acceptedAt"] = practice.get("acceptedAt", timestamp)
            if input_data.get("activationBefore"):
                updates["activationBefore"] = input_data["activationBefore"]
        else:
            updates["skippedAt"] = practice.get("skippedAt", timestamp)
            if note:
                updates["skipReason"] = note
        updated = await self._repository.update_practice_session(
            input_data["userId"],
            input_data["practiceSessionId"],
            updates,
        )
        if note:
            await self._repository.create_integration_record(
                {
                    "id": create_id("integration"),
                    "userId": input_data["userId"],
                    "materialId": updated.get("materialId"),
                    "action": "practice_feedback",
                    "approvedProposalIds": [],
                    "rejectedProposalIds": [],
                    "suppressedHypothesisIds": [],
                    "affectedEntityIds": [updated["id"]],
                    "note": note,
                    "createdAt": timestamp,
                }
            )
        event = self._practice_engine.summarize_outcome_signal(
            practice=updated,
            previous_status=previous_status,  # type: ignore[arg-type]
            outcome=None,
            action=action,  # type: ignore[arg-type]
        )
        await self._record_adaptation_signal(
            user_id=input_data["userId"],
            event_type=event["eventType"],
            signals=event["signals"],
            success=event.get("success"),
            sample_weight=event.get("sampleWeight"),
        )
        return updated

    async def record_practice_outcome(
        self,
        *,
        user_id: Id,
        practice_session_id: Id | None,
        material_id: Id | None,
        outcome: PracticeOutcomeWritePayload,
    ) -> PracticeSessionRecord:
        timestamp = now_iso()
        previous_status: str | None = None
        should_record_adaptation = True
        should_create_integration = True
        if practice_session_id:
            existing = await self._repository.get_practice_session(user_id, practice_session_id)
            previous_status = str(existing["status"])
            if previous_status == "completed":
                if (
                    existing.get("outcome") == outcome["outcome"]
                    and existing.get("activationBefore") == outcome.get("activationBefore")
                    and existing.get("activationAfter") == outcome.get("activationAfter")
                ):
                    return existing
                should_record_adaptation = False
                should_create_integration = False
            else:
                try:
                    self._practice_engine.validate_transition(
                        current_status=previous_status,  # type: ignore[arg-type]
                        target_status="completed",
                    )
                except ValueError as exc:
                    raise ValidationError(str(exc)) from exc
            updates: dict[str, object] = {
                "status": "completed",
                "outcome": outcome["outcome"],
                "activationBefore": outcome.get("activationBefore"),
                "activationAfter": outcome.get("activationAfter"),
                "outcomeEvidenceIds": list(outcome.get("outcomeEvidenceIds", [])),
                "updatedAt": timestamp,
                "completedAt": existing.get("completedAt", timestamp),
            }
            practice = await self._repository.update_practice_session(
                user_id,
                practice_session_id,
                updates,
            )
        else:
            practice = await self._repository.create_practice_session(
                {
                    "id": create_id("practice_session"),
                    "userId": user_id,
                    "materialId": material_id,
                    "practiceType": outcome["practiceType"],
                    "target": outcome.get("target"),
                    "reason": outcome["outcome"],
                    "instructions": [],
                    "durationMinutes": 0,
                    "contraindicationsChecked": [],
                    "requiresConsent": False,
                    "status": "completed",
                    "outcome": outcome["outcome"],
                    "activationBefore": outcome.get("activationBefore"),
                    "activationAfter": outcome.get("activationAfter"),
                    "outcomeEvidenceIds": list(outcome.get("outcomeEvidenceIds", [])),
                    "source": "manual",
                    "followUpCount": 0,
                    "createdAt": timestamp,
                    "updatedAt": timestamp,
                    "completedAt": timestamp,
                }
            )
        if should_create_integration:
            await self._repository.create_integration_record(
                {
                    "id": create_id("integration"),
                    "userId": user_id,
                    "materialId": material_id or practice.get("materialId"),
                    "action": "practice_outcome",
                    "approvedProposalIds": [],
                    "rejectedProposalIds": [],
                    "suppressedHypothesisIds": [],
                    "affectedEntityIds": [practice["id"]],
                    "note": outcome["outcome"],
                    "createdAt": timestamp,
                }
            )
        if should_record_adaptation:
            event = self._practice_engine.summarize_outcome_signal(
                practice=practice,
                previous_status=previous_status,  # type: ignore[arg-type]
                outcome=outcome,
                action="completed",
            )
            await self._record_adaptation_signal(
                user_id=user_id,
                event_type=event["eventType"],
                signals=event["signals"],
                success=event.get("success"),
                sample_weight=event.get("sampleWeight"),
            )
        return practice

    async def generate_rhythmic_briefs(
        self,
        input_data: GenerateRhythmicBriefsInput,
    ) -> RhythmicBriefWorkflowResult:
        source = str(input_data.get("source") or "manual")
        if source not in {"manual", "scheduled"}:
            raise ValidationError("Rhythmic brief source must be manual or scheduled.")
        now = now_iso()
        resolved_start, resolved_end = self._resolve_window(
            anchor=input_data.get("windowEnd"),
            fallback_start=input_data.get("windowStart"),
            fallback_end=input_data.get("windowEnd"),
        )
        bundle = await self._load_surface_context_bundle(
            user_id=input_data["userId"],
            window_start=resolved_start,
            window_end=resolved_end,
            surface="rhythmic_brief",
            payload=cast(
                dict[str, object],
                await self._repository.build_circulation_summary_input(
                    input_data["userId"],
                    window_start=resolved_start,
                    window_end=resolved_end,
                ),
            ),
            include_dashboard=True,
            memory_query={},
            safety_context=cast(SafetyContext | None, input_data.get("safetyContext")),
        )
        summary_input = cast(CirculationSummaryInput, bundle["preparedPayload"])
        memory_snapshot = cast(MemoryKernelSnapshot, bundle["memorySnapshot"])
        dashboard = cast(DashboardSummary, bundle["dashboard"])
        thread_digests = cast(list[ThreadDigest], bundle["threadDigests"])
        recent_practices = cast(list[PracticeSessionRecord], bundle["recentPractices"])
        journeys = cast(list[JourneyRecord], bundle["journeys"])
        existing_briefs = cast(list[ProactiveBriefRecord], bundle["existingBriefs"])
        profile = cast(dict[str, object] | None, bundle["profile"])
        cadence_hints = self._adaptation_engine.derive_rhythm_hints(profile=profile)
        adaptation_summary = cast(UserAdaptationProfileSummary | None, bundle["adaptationSummary"])
        method_context = summary_input.get("methodContextSnapshot")
        consent_status = self._consent_status(
            method_context.get("consentPreferences", []) if method_context else [],
            "proactive_briefing",
        )
        skipped_reasons: list[str] = []
        if source == "scheduled" and consent_status != "allow":
            return {
                "briefs": [],
                "skippedReasons": ["scheduled_proactive_briefing_not_allowed"],
            }
        seeds = self._proactive_engine.build_candidate_seeds(
            user_id=input_data["userId"],
            memory_snapshot=memory_snapshot,
            dashboard=dashboard,
            method_context=method_context,
            thread_digests=thread_digests,
            recent_practices=recent_practices,
            journeys=journeys,
            existing_briefs=existing_briefs,
            adaptation_profile=adaptation_summary,
            source=source,  # type: ignore[arg-type]
            now=now,
            limit=max(1, int(input_data.get("limit", 3))),
        )
        due_seeds = self._proactive_engine.filter_due_candidates(
            seeds=seeds,
            existing_briefs=existing_briefs,
            cadence_hints=cadence_hints,
            source=source,  # type: ignore[arg-type]
            now=now,
        )
        if not due_seeds:
            result: RhythmicBriefWorkflowResult = {"briefs": []}
            if skipped_reasons:
                result["skippedReasons"] = skipped_reasons
            return result
        existing_ids = {item["id"] for item in existing_briefs}
        persisted: list[ProactiveBriefRecord] = []
        for seed in due_seeds:
            brief_input: RhythmicBriefInput = {
                "userId": input_data["userId"],
                "windowStart": resolved_start,
                "windowEnd": resolved_end,
                "source": source,
                "seed": deepcopy(seed),
                "hermesMemoryContext": deepcopy(summary_input["hermesMemoryContext"]),
            }
            if summary_input.get("lifeContextSnapshot") is not None:
                brief_input["lifeContextSnapshot"] = deepcopy(summary_input["lifeContextSnapshot"])
            if method_context is not None:
                brief_input["methodContextSnapshot"] = deepcopy(method_context)
            if summary_input.get("threadDigests"):
                brief_input["threadDigests"] = deepcopy(summary_input["threadDigests"])
            if adaptation_summary is not None:
                brief_input["adaptationProfile"] = deepcopy(adaptation_summary)
            if input_data.get("safetyContext") is not None:
                brief_input["safetyContext"] = deepcopy(input_data["safetyContext"])
            brief_result = await self._core.generate_rhythmic_brief(brief_input)
            if brief_result.get("withheld"):
                skipped_reasons.append(
                    str(
                        brief_result.get("withheldReason") or seed.get("reason") or "brief_withheld"
                    )
                )
                continue
            brief = await self._store_rhythmic_brief(
                user_id=input_data["userId"],
                source=source,
                seed=seed,
                result=brief_result,
                created_at=now,
            )
            persisted.append(brief)
            if brief["id"] in existing_ids:
                continue
            existing_ids.add(brief["id"])
            await self._record_adaptation_signal(
                user_id=input_data["userId"],
                event_type="rhythmic_brief_candidate_created",
                signals={
                    "briefType": brief["briefType"],
                    "source": brief.get("source"),
                    "triggerKey": brief.get("triggerKey"),
                },
            )
        result = {"briefs": persisted}
        if skipped_reasons:
            result["skippedReasons"] = skipped_reasons
        return result

    async def respond_rhythmic_brief(
        self,
        input_data: RespondRhythmicBriefInput,
    ) -> ProactiveBriefRecord:
        action = str(input_data["action"])
        if action not in {"shown", "dismissed", "acted_on", "deleted"}:
            raise ValidationError(
                "Rhythmic brief action must be shown, dismissed, acted_on, or deleted."
            )
        brief = await self._repository.get_proactive_brief(
            input_data["userId"],
            input_data["briefId"],
            include_deleted=action == "deleted",
        )
        current_status = str(brief["status"])
        if current_status == action:
            return brief
        try:
            self._proactive_engine.validate_transition(
                current_status=current_status,  # type: ignore[arg-type]
                target_status=action,  # type: ignore[arg-type]
            )
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        timestamp = now_iso()
        profile = await self._repository.get_adaptation_profile(input_data["userId"])
        cadence_hints = self._adaptation_engine.derive_rhythm_hints(profile=profile)
        updates: dict[str, object] = {
            "status": action,
            "updatedAt": timestamp,
        }
        if action == "shown":
            updates["shownAt"] = brief.get("shownAt", timestamp)
        elif action == "dismissed":
            updates["dismissedAt"] = brief.get("dismissedAt", timestamp)
            updates["cooldownUntil"] = self._format_datetime(
                self._parse_datetime(timestamp)
                + timedelta(hours=int(cadence_hints.get("dismissedTriggerCooldownHours", 48)))
            )
        elif action == "acted_on":
            updates["actedOnAt"] = brief.get("actedOnAt", timestamp)
            updates["cooldownUntil"] = self._format_datetime(
                self._parse_datetime(timestamp)
                + timedelta(hours=int(cadence_hints.get("actedOnTriggerCooldownHours", 96)))
            )
        else:
            updates["deletedAt"] = brief.get("deletedAt", timestamp)
        updated = await self._repository.update_proactive_brief(
            input_data["userId"],
            input_data["briefId"],
            updates,
        )
        if action == "shown":
            for journey_id in updated.get("relatedJourneyIds", []):
                await self._repository.update_journey(
                    input_data["userId"],
                    journey_id,
                    {"lastBriefedAt": timestamp, "updatedAt": timestamp},
                )
        if action != "deleted":
            await self._record_adaptation_signal(
                user_id=input_data["userId"],
                event_type=f"rhythmic_brief_{action}",
                signals={
                    "briefType": updated["briefType"],
                    "source": updated.get("source"),
                    "triggerKey": updated.get("triggerKey"),
                },
            )
        return updated

    async def list_materials(
        self,
        *,
        user_id: Id,
        filters: dict[str, object] | None = None,
    ) -> list[MaterialRecord]:
        return await self._repository.list_materials(user_id, filters)

    async def get_material(
        self,
        *,
        user_id: Id,
        material_id: Id,
        include_deleted: bool = False,
    ) -> MaterialRecord:
        return await self._repository.get_material(
            user_id,
            material_id,
            include_deleted=include_deleted,
        )

    async def get_interpretation_run(self, *, user_id: Id, run_id: Id) -> InterpretationRunRecord:
        return await self._repository.get_interpretation_run(user_id, run_id)

    async def list_interpretation_runs(
        self,
        *,
        user_id: Id,
        material_id: Id | None = None,
        limit: int = 20,
    ) -> list[InterpretationRunRecord]:
        return await self._repository.list_interpretation_runs(
            user_id, material_id=material_id, limit=limit
        )

    async def get_symbol(
        self,
        *,
        user_id: Id,
        symbol_id: Id,
        include_deleted: bool = False,
    ) -> SymbolRecord:
        return await self._repository.get_symbol(
            user_id, symbol_id, include_deleted=include_deleted
        )

    async def find_symbol_by_name(self, *, user_id: Id, canonical_name: str) -> SymbolRecord | None:
        return await self._repository.find_symbol_by_name(user_id, canonical_name)

    async def list_symbols(self, *, user_id: Id, limit: int = 50) -> list[SymbolRecord]:
        return await self._repository.list_symbols(user_id, limit=limit)

    async def build_memory_kernel_snapshot(
        self,
        *,
        user_id: Id,
        query: MemoryRetrievalQuery | None = None,
    ) -> MemoryKernelSnapshot:
        return await self._repository.build_memory_kernel_snapshot(user_id, query=query)

    async def query_graph(
        self,
        *,
        user_id: Id,
        query: GraphQuery | None = None,
    ) -> GraphQueryResult:
        return await self._repository.query_graph(user_id, query=query)

    async def get_dashboard_summary(self, *, user_id: Id) -> DashboardSummary:
        return await self._repository.get_dashboard_summary(user_id)

    def _discovery_ranking_profile(self, value: object | None) -> str:
        profile = str(value or "importance").strip() or "importance"
        if profile not in {"default", "recency", "recurrence", "importance"}:
            raise ValidationError(
                "Discovery rankingProfile must be one of default, recency, recurrence, "
                "or importance."
            )
        return profile

    def _normalize_discovery_root_ids(self, raw_ids: object | None) -> list[Id]:
        if not isinstance(raw_ids, list):
            return []
        root_ids: list[Id] = []
        for value in raw_ids:
            if not isinstance(value, str):
                continue
            candidate = value.strip()
            if candidate:
                root_ids = self._merge_ids(root_ids, [candidate])
        return root_ids[:20]

    def _derive_discovery_root_ids(
        self,
        *,
        dashboard: DashboardSummary,
        memory_snapshot: MemoryKernelSnapshot,
        method_context: MethodContextSnapshot | None = None,
    ) -> list[Id]:
        root_ids: list[Id] = []
        for record_id in self._discovery_root_ids_from_method_context(method_context):
            root_ids = self._merge_ids(root_ids, [record_id])
        for record in dashboard.get("recentMaterials", []):
            record_id = self._optional_str(record.get("id"))
            if record_id:
                root_ids = self._merge_ids(root_ids, [record_id])
        for record in dashboard.get("recurringSymbols", []):
            record_id = self._optional_str(record.get("id"))
            if record_id:
                root_ids = self._merge_ids(root_ids, [record_id])
        for record in dashboard.get("activePatterns", []):
            record_id = self._optional_str(record.get("id"))
            if record_id:
                root_ids = self._merge_ids(root_ids, [record_id])
        for item in memory_snapshot.get("items", []):
            entity_id = self._optional_str(item.get("entityId"))
            if entity_id:
                root_ids = self._merge_ids(root_ids, [entity_id])
            provenance = item.get("provenance")
            if not isinstance(provenance, dict):
                continue
            source_id = self._optional_str(provenance.get("sourceId"))
            material_id = self._optional_str(provenance.get("materialId"))
            if source_id:
                root_ids = self._merge_ids(root_ids, [source_id])
            if material_id:
                root_ids = self._merge_ids(root_ids, [material_id])
        return root_ids[:20]

    def _discovery_root_ids_from_method_context(
        self, method_context: MethodContextSnapshot | None
    ) -> list[Id]:
        if not isinstance(method_context, dict):
            return []
        root_ids: list[Id] = []
        for signal in method_context.get("longitudinalSignals", []):
            if not isinstance(signal, dict):
                continue
            root_ids = self._merge_ids(
                root_ids,
                [
                    str(item)
                    for item in signal.get("sourceEntityIds", [])
                    if isinstance(item, str) and item.strip()
                ],
            )
            root_ids = self._merge_ids(
                root_ids,
                [
                    str(item)
                    for item in signal.get("materialIds", [])
                    if isinstance(item, str) and item.strip()
                ],
            )
        for collection_name in (
            "recentBodyStates",
            "activeGoals",
            "goalTensions",
            "recentPracticeSessions",
            "activeDreamSeries",
        ):
            for item in method_context.get(collection_name, []):
                if not isinstance(item, dict):
                    continue
                record_id = self._optional_str(item.get("id"))
                if record_id:
                    root_ids = self._merge_ids(root_ids, [record_id])
        for item in method_context.get("recentDreamDynamics", []):
            if not isinstance(item, dict):
                continue
            record_id = self._optional_str(item.get("materialId"))
            if record_id:
                root_ids = self._merge_ids(root_ids, [record_id])
        method_state = method_context.get("methodState")
        if isinstance(method_state, dict):
            for field_name in (
                "grounding",
                "containment",
                "egoCapacity",
                "egoRelationTrajectory",
                "relationalField",
                "questioningPreference",
                "activeGoalTension",
                "practiceLoop",
                "typologyMethodState",
            ):
                section = method_state.get(field_name)
                if not isinstance(section, dict):
                    continue
                record_id = self._optional_str(section.get("goalTensionId"))
                if record_id:
                    root_ids = self._merge_ids(root_ids, [record_id])
                for ref in section.get("sourceRecordRefs", []):
                    if not isinstance(ref, dict):
                        continue
                    record_id = self._optional_str(ref.get("recordId"))
                    if record_id:
                        root_ids = self._merge_ids(root_ids, [record_id])
            for tendency in method_state.get("compensationTendencies", []):
                if not isinstance(tendency, dict):
                    continue
                for ref in tendency.get("sourceRecordRefs", []):
                    if not isinstance(ref, dict):
                        continue
                    record_id = self._optional_str(ref.get("recordId"))
                    if record_id:
                        root_ids = self._merge_ids(root_ids, [record_id])
        individuation_context = method_context.get("individuationContext")
        if isinstance(individuation_context, dict):
            reality_anchor = individuation_context.get("realityAnchors")
            if isinstance(reality_anchor, dict):
                record_id = self._optional_str(reality_anchor.get("id"))
                if record_id:
                    root_ids = self._merge_ids(root_ids, [record_id])
            for collection_name in (
                "thresholdProcesses",
                "relationalScenes",
                "activeOppositions",
                "emergentThirdSignals",
                "bridgeMoments",
                "projectionHypotheses",
            ):
                for item in individuation_context.get(collection_name, []):
                    if not isinstance(item, dict):
                        continue
                    record_id = self._optional_str(item.get("id"))
                    if record_id:
                        root_ids = self._merge_ids(root_ids, [record_id])
        living_myth_context = method_context.get("livingMythContext")
        if isinstance(living_myth_context, dict):
            for field_name in ("currentLifeChapter", "latestSymbolicWellbeing"):
                item = living_myth_context.get(field_name)
                if not isinstance(item, dict):
                    continue
                record_id = self._optional_str(item.get("id"))
                if record_id:
                    root_ids = self._merge_ids(root_ids, [record_id])
            for collection_name in (
                "activeMythicQuestions",
                "recentThresholdMarkers",
                "complexEncounters",
            ):
                for item in living_myth_context.get(collection_name, []):
                    if not isinstance(item, dict):
                        continue
                    record_id = self._optional_str(item.get("id"))
                    if record_id:
                        root_ids = self._merge_ids(root_ids, [record_id])
        clarification_state = method_context.get("clarificationState")
        if isinstance(clarification_state, dict):
            for collection_name in ("pendingPrompts", "recentlyUnrouted"):
                for item in clarification_state.get(collection_name, []):
                    if not isinstance(item, dict):
                        continue
                    record_id = self._optional_str(item.get("id"))
                    prompt_id = self._optional_str(item.get("promptId"))
                    material_id = self._optional_str(item.get("materialId"))
                    if record_id:
                        root_ids = self._merge_ids(root_ids, [record_id])
                    if prompt_id:
                        root_ids = self._merge_ids(root_ids, [prompt_id])
                    if material_id:
                        root_ids = self._merge_ids(root_ids, [material_id])
        return root_ids[:20]

    def _build_discovery_sections(
        self,
        *,
        dashboard: DashboardSummary,
        memory_snapshot: MemoryKernelSnapshot,
        graph: GraphQueryResult,
        method_context: MethodContextSnapshot | None,
        thread_digests: list[ThreadDigest] | None,
        max_items: int,
    ) -> list[DiscoverySection]:
        candidates = self._discovery_candidates(
            dashboard=dashboard,
            memory_snapshot=memory_snapshot,
            graph=graph,
            method_context=method_context,
            thread_digests=thread_digests,
        )
        recurring = self._build_recurring_discovery_section(
            candidates=candidates,
            max_items=max_items,
        )
        dream_body_event_links = self._build_dream_body_event_discovery_section(
            graph=graph,
            max_items=max_items,
        )
        ripe_to_revisit = self._build_revisit_discovery_section(
            candidates=candidates,
            max_items=max_items,
        )
        conscious_attitude = self._build_conscious_attitude_discovery_section(
            candidates=candidates,
            max_items=max_items,
        )
        body_states = self._build_body_states_discovery_section(
            candidates=candidates,
            max_items=max_items,
        )
        method_state = self._build_method_state_discovery_section(
            candidates=candidates,
            max_items=max_items,
        )
        journey_threads = self._build_journey_threads_discovery_section(
            candidates=candidates,
            max_items=max_items,
        )
        held_for_now = self._build_held_for_now_discovery_section(
            dashboard=dashboard,
            used_material_ids=self._discovery_material_ids_from_sections(
                [
                    recurring,
                    dream_body_event_links,
                    ripe_to_revisit,
                    conscious_attitude,
                    body_states,
                    method_state,
                    journey_threads,
                ]
            ),
            max_items=max_items,
        )
        return [
            recurring,
            dream_body_event_links,
            ripe_to_revisit,
            conscious_attitude,
            body_states,
            method_state,
            journey_threads,
            held_for_now,
        ]

    def _discovery_candidates(
        self,
        *,
        dashboard: DashboardSummary,
        memory_snapshot: MemoryKernelSnapshot,
        graph: GraphQueryResult,
        method_context: MethodContextSnapshot | None,
        thread_digests: list[ThreadDigest] | None,
    ) -> dict[str, dict[str, object]]:
        candidates: dict[str, dict[str, object]] = {}
        degree_by_node_id = self._discovery_graph_degree_map(graph)
        for symbol in dashboard.get("recurringSymbols", []):
            symbol_id = self._optional_str(symbol.get("id"))
            if not symbol_id:
                continue
            recurrence_count = int(symbol.get("recurrenceCount", 0) or 0)
            criteria = ["dashboard_recurring_symbol"]
            if recurrence_count > 0:
                criteria.append(f"symbol_recurrence_count:{recurrence_count}")
            self._add_discovery_candidate(
                candidates,
                key=f"symbol:{symbol_id}",
                label=str(symbol.get("canonicalName") or "Symbol"),
                summary=(
                    f"Recurring symbol with {recurrence_count} appearance(s)."
                    if recurrence_count > 0
                    else "Recurring symbol surfaced in the dashboard."
                ),
                criteria=criteria,
                source_kind="dashboard",
                entity_refs={"symbols": [symbol_id]},
                evidence_ids=[],
                graph_degree=degree_by_node_id.get(symbol_id, 0),
                recurrence_count=recurrence_count,
            )
        for pattern in dashboard.get("activePatterns", []):
            pattern_id = self._optional_str(pattern.get("id"))
            if not pattern_id:
                continue
            self._add_discovery_candidate(
                candidates,
                key=f"pattern:{pattern_id}",
                label=str(pattern.get("label") or "Pattern"),
                summary=self._optional_str(pattern.get("formulation"))
                or "Active pattern surfaced in the dashboard.",
                criteria=["dashboard_active_pattern"],
                source_kind="dashboard",
                entity_refs={"patterns": [pattern_id]},
                evidence_ids=[
                    str(value)
                    for value in pattern.get("evidenceIds", [])
                    if isinstance(value, str) and value
                ],
                graph_degree=degree_by_node_id.get(pattern_id, 0),
                active_pattern=True,
            )
        for item in memory_snapshot.get("items", []):
            entity_id = self._optional_str(item.get("entityId")) or self._optional_str(
                item.get("id")
            )
            if not entity_id:
                continue
            entity_type = str(item.get("entityType") or "Entity")
            importance = item.get("importance") if isinstance(item.get("importance"), dict) else {}
            provenance = item.get("provenance") if isinstance(item.get("provenance"), dict) else {}
            recurrence_count = int(importance.get("recurrenceCount", 0) or 0)
            user_confirmed = bool(importance.get("userConfirmed"))
            criteria = ["memory_kernel_match"]
            if recurrence_count > 1:
                criteria.append(f"memory_recurrence_count:{recurrence_count}")
            if user_confirmed:
                criteria.append("user_confirmed_memory")
            self._add_discovery_candidate(
                candidates,
                key=self._discovery_entity_key(entity_type=entity_type, entity_id=entity_id),
                label=str(item.get("label") or entity_type),
                summary=self._optional_str(item.get("summary"))
                or f"Approved {entity_type} surfaced in memory.",
                criteria=criteria,
                source_kind="memory_kernel",
                entity_refs=self._discovery_entity_refs(
                    entity_type=entity_type, entity_id=entity_id
                ),
                evidence_ids=[
                    str(value)
                    for value in provenance.get("evidenceIds", [])
                    if isinstance(value, str) and value
                ],
                graph_degree=degree_by_node_id.get(entity_id, 0),
                recurrence_count=recurrence_count,
                user_confirmed=user_confirmed,
            )
        self._add_method_context_discovery_candidates(
            candidates,
            method_context=method_context,
            degree_by_node_id=degree_by_node_id,
        )
        self._add_thread_digest_discovery_candidates(
            candidates,
            thread_digests=thread_digests,
            degree_by_node_id=degree_by_node_id,
        )
        return candidates

    def _add_method_context_discovery_candidates(
        self,
        candidates: dict[str, dict[str, object]],
        *,
        method_context: MethodContextSnapshot | None,
        degree_by_node_id: dict[Id, int],
    ) -> None:
        if not isinstance(method_context, dict):
            return
        conscious_attitude = method_context.get("consciousAttitude")
        if isinstance(conscious_attitude, dict):
            attitude_id = self._optional_str(conscious_attitude.get("id"))
            stance_summary = self._optional_str(conscious_attitude.get("stanceSummary"))
            if attitude_id and stance_summary:
                self._add_discovery_candidate(
                    candidates,
                    key=f"conscious_attitude:{attitude_id}",
                    label="Conscious attitude",
                    summary=stance_summary,
                    criteria=["method_context_conscious_attitude"],
                    source_kind="method_context",
                    entity_refs={"entities": [attitude_id]},
                    evidence_ids=[
                        str(value)
                        for value in conscious_attitude.get("evidenceIds", [])
                        if isinstance(value, str) and value
                    ],
                    graph_degree=degree_by_node_id.get(attitude_id, 0),
                    longitudinal_context=True,
                )
        for body_state in method_context.get("recentBodyStates", [])[:5]:
            if not isinstance(body_state, dict):
                continue
            body_state_id = self._optional_str(body_state.get("id"))
            if not body_state_id:
                continue
            sensation = str(body_state.get("sensation") or "Body state")
            body_region = self._optional_str(body_state.get("bodyRegion"))
            label = f"{sensation} ({body_region})" if body_region else sensation
            summary = (
                self._optional_str(body_state.get("tone"))
                or self._optional_str(body_state.get("activation"))
                or f"Recent body state: {sensation}."
            )
            self._add_discovery_candidate(
                candidates,
                key=f"body_state:{body_state_id}",
                label=label,
                summary=summary,
                criteria=["method_context_recent_body_state"],
                source_kind="method_context",
                entity_refs={"bodyStates": [body_state_id]},
                evidence_ids=[
                    str(value)
                    for value in body_state.get("evidenceIds", [])
                    if isinstance(value, str) and value
                ],
                graph_degree=degree_by_node_id.get(body_state_id, 0),
                longitudinal_context=True,
            )
        for signal in method_context.get("longitudinalSignals", [])[:5]:
            if not isinstance(signal, dict):
                continue
            signal_id = self._optional_str(signal.get("id"))
            signal_summary = self._optional_str(signal.get("summary"))
            if not signal_id or not signal_summary:
                continue
            source_entity_ids = [
                str(item)
                for item in signal.get("sourceEntityIds", [])
                if isinstance(item, str) and item.strip()
            ]
            material_ids = [
                str(item)
                for item in signal.get("materialIds", [])
                if isinstance(item, str) and item.strip()
            ]
            signal_type = self._optional_str(signal.get("signalType")) or "longitudinal_signal"
            strength = self._optional_str(signal.get("strength"))
            summary = signal_summary
            if strength:
                summary = f"{signal_summary} Signal strength: {strength.replace('_', ' ')}."
            entity_refs: dict[str, list[Id]] = {}
            if source_entity_ids:
                entity_refs["entities"] = source_entity_ids
            if material_ids:
                entity_refs["materials"] = material_ids
            self._add_discovery_candidate(
                candidates,
                key=f"longitudinal_signal:{signal_id}",
                label=(signal_type.replace("_", " ").title()),
                summary=summary,
                criteria=[
                    "method_context_longitudinal_signal",
                    f"longitudinal_signal:{signal_type}",
                ],
                source_kind="method_context",
                entity_refs=entity_refs,
                evidence_ids=[],
                graph_degree=max(
                    [degree_by_node_id.get(ref_id, 0) for ref_id in source_entity_ids],
                    default=0,
                ),
                longitudinal_context=True,
            )
        method_state = method_context.get("methodState")
        if isinstance(method_state, dict):
            method_state_summary = self._method_state_discovery_summary(method_state)
            if method_state_summary:
                method_state_ref_ids = self._method_state_discovery_ref_ids(method_state)
                self._add_discovery_candidate(
                    candidates,
                    key="method_state:current",
                    label="Method state",
                    summary=method_state_summary,
                    criteria=["method_context_method_state"],
                    source_kind="method_context",
                    entity_refs=(
                        {"entities": method_state_ref_ids} if method_state_ref_ids else {}
                    ),
                    evidence_ids=self._method_state_discovery_evidence_ids(method_state),
                    graph_degree=max(
                        [degree_by_node_id.get(ref_id, 0) for ref_id in method_state_ref_ids],
                        default=0,
                    ),
                    longitudinal_context=True,
                )
            relational_field = (
                method_state.get("relationalField")
                if isinstance(method_state.get("relationalField"), dict)
                else {}
            )
            relational_field_summary = self._relational_field_discovery_summary(relational_field)
            if relational_field_summary:
                relational_ref_ids = self._method_state_section_ref_ids(relational_field)
                self._add_discovery_candidate(
                    candidates,
                    key="method_state_relational_field:current",
                    label="Relational field",
                    summary=relational_field_summary,
                    criteria=["method_state_relational_field"],
                    source_kind="method_context",
                    entity_refs=({"entities": relational_ref_ids} if relational_ref_ids else {}),
                    evidence_ids=self._method_state_section_evidence_ids(relational_field),
                    graph_degree=max(
                        [degree_by_node_id.get(ref_id, 0) for ref_id in relational_ref_ids],
                        default=0,
                    ),
                    longitudinal_context=True,
                )
            questioning_preference = (
                method_state.get("questioningPreference")
                if isinstance(method_state.get("questioningPreference"), dict)
                else {}
            )
            questioning_summary = self._questioning_preference_discovery_summary(
                questioning_preference
            )
            if questioning_summary:
                questioning_ref_ids = self._method_state_section_ref_ids(questioning_preference)
                self._add_discovery_candidate(
                    candidates,
                    key="method_state_questioning_preference:current",
                    label="Questioning preference",
                    summary=questioning_summary,
                    criteria=["method_state_questioning_preference"],
                    source_kind="method_context",
                    entity_refs=({"entities": questioning_ref_ids} if questioning_ref_ids else {}),
                    evidence_ids=self._method_state_section_evidence_ids(questioning_preference),
                    graph_degree=max(
                        [degree_by_node_id.get(ref_id, 0) for ref_id in questioning_ref_ids],
                        default=0,
                    ),
                    longitudinal_context=True,
                )
            typology_state = (
                method_state.get("typologyMethodState")
                if isinstance(method_state.get("typologyMethodState"), dict)
                else {}
            )
            typology_summary = self._typology_method_state_discovery_summary(typology_state)
            if typology_summary:
                typology_ref_ids = self._method_state_section_ref_ids(typology_state)
                self._add_discovery_candidate(
                    candidates,
                    key="method_state_typology_method_state:current",
                    label="Typology method state",
                    summary=typology_summary,
                    criteria=["method_state_typology_method_state"],
                    source_kind="method_context",
                    entity_refs=({"entities": typology_ref_ids} if typology_ref_ids else {}),
                    evidence_ids=self._method_state_section_evidence_ids(typology_state),
                    graph_degree=max(
                        [degree_by_node_id.get(ref_id, 0) for ref_id in typology_ref_ids],
                        default=0,
                    ),
                    longitudinal_context=True,
                )
            active_goal_tension = (
                method_state.get("activeGoalTension")
                if isinstance(method_state.get("activeGoalTension"), dict)
                else {}
            )
            active_goal_tension_id = self._optional_str(active_goal_tension.get("goalTensionId"))
            if active_goal_tension_id:
                self._add_discovery_candidate(
                    candidates,
                    key=f"method_state_goal_tension:{active_goal_tension_id}",
                    label="Active goal tension",
                    summary=self._optional_str(active_goal_tension.get("balancingDirection"))
                    or "A current goal tension is shaping pacing and reflection.",
                    criteria=["method_state_active_goal_tension"],
                    source_kind="method_context",
                    entity_refs={"entities": [active_goal_tension_id]},
                    evidence_ids=[
                        str(value)
                        for value in active_goal_tension.get("evidenceIds", [])
                        if isinstance(value, str) and value
                    ],
                    graph_degree=degree_by_node_id.get(active_goal_tension_id, 0),
                    longitudinal_context=True,
                )
            practice_loop = (
                method_state.get("practiceLoop")
                if isinstance(method_state.get("practiceLoop"), dict)
                else {}
            )
            practice_loop_summary = self._optional_str(practice_loop.get("recentOutcomeTrend"))
            if practice_loop_summary:
                practice_loop_ref_ids = [
                    self._optional_str(ref.get("recordId"))
                    for ref in practice_loop.get("sourceRecordRefs", [])
                    if isinstance(ref, dict)
                ]
                practice_loop_ref_ids = [item for item in practice_loop_ref_ids if item]
                self._add_discovery_candidate(
                    candidates,
                    key="method_state_practice_loop:current",
                    label="Practice loop",
                    summary=(f"Practice arc: {practice_loop_summary.replace('_', ' ')}."),
                    criteria=["method_state_practice_loop"],
                    source_kind="method_context",
                    entity_refs={"entities": practice_loop_ref_ids},
                    evidence_ids=[
                        str(value)
                        for value in practice_loop.get("evidenceIds", [])
                        if isinstance(value, str) and value
                    ],
                    graph_degree=max(
                        [degree_by_node_id.get(ref_id, 0) for ref_id in practice_loop_ref_ids],
                        default=0,
                    ),
                    longitudinal_context=True,
                )
        witness_state = method_context.get("witnessState")
        if isinstance(witness_state, dict):
            witness_summary = self._witness_state_discovery_summary(witness_state)
            if witness_summary:
                self._add_discovery_candidate(
                    candidates,
                    key="witness_state:current",
                    label="Witness contract",
                    summary=witness_summary,
                    criteria=["method_context_witness_state"],
                    source_kind="method_context",
                    entity_refs={},
                    evidence_ids=(
                        self._method_state_discovery_evidence_ids(method_state)
                        if isinstance(method_state, dict)
                        else []
                    ),
                    graph_degree=0,
                    longitudinal_context=True,
                )
        for journey in method_context.get("activeJourneys", [])[:5]:
            if not isinstance(journey, dict):
                continue
            journey_id = self._optional_str(journey.get("id"))
            if not journey_id:
                continue
            self._add_discovery_candidate(
                candidates,
                key=f"journey:{journey_id}",
                label=str(journey.get("label") or "Journey thread"),
                summary=self._optional_str(journey.get("currentQuestion"))
                or self._optional_str(journey.get("description"))
                or "An active journey thread remains open in the current context.",
                criteria=["method_context_active_journey"],
                source_kind="method_context",
                entity_refs={"journeys": [journey_id]},
                evidence_ids=[],
                graph_degree=degree_by_node_id.get(journey_id, 0),
                longitudinal_context=True,
            )
        for goal in method_context.get("activeGoals", [])[:5]:
            if not isinstance(goal, dict):
                continue
            goal_id = self._optional_str(goal.get("id"))
            if not goal_id:
                continue
            label = str(goal.get("label") or "Goal")
            self._add_discovery_candidate(
                candidates,
                key=f"goal:{goal_id}",
                label=label,
                summary=self._optional_str(goal.get("description")) or f"Active goal: {label}.",
                criteria=["method_context_active_goal"],
                source_kind="method_context",
                entity_refs={"goals": [goal_id]},
                evidence_ids=[],
                graph_degree=degree_by_node_id.get(goal_id, 0),
                longitudinal_context=True,
            )
        for tension in method_context.get("goalTensions", [])[:5]:
            if not isinstance(tension, dict):
                continue
            tension_id = self._optional_str(tension.get("id"))
            if not tension_id:
                continue
            goal_ids = [
                str(item) for item in tension.get("goalIds", []) if isinstance(item, str) and item
            ]
            graph_degree = max(
                [
                    degree_by_node_id.get(tension_id, 0),
                    *[degree_by_node_id.get(item, 0) for item in goal_ids],
                ]
            )
            self._add_discovery_candidate(
                candidates,
                key=f"goal_tension:{tension_id}",
                label="Goal tension",
                summary=self._optional_str(tension.get("tensionSummary"))
                or "A live goal tension remains active in the current context.",
                criteria=["method_context_goal_tension"],
                source_kind="method_context",
                entity_refs={"entities": [tension_id], "goals": goal_ids},
                evidence_ids=[
                    str(value)
                    for value in tension.get("evidenceIds", [])
                    if isinstance(value, str) and value
                ],
                graph_degree=graph_degree,
                longitudinal_context=True,
            )
        for practice in method_context.get("recentPracticeSessions", [])[:5]:
            if not isinstance(practice, dict):
                continue
            practice_id = self._optional_str(practice.get("id"))
            if not practice_id:
                continue
            practice_type = str(practice.get("practiceType") or "Practice").replace("_", " ")
            self._add_discovery_candidate(
                candidates,
                key=f"practice_session:{practice_id}",
                label=practice_type.title(),
                summary=self._optional_str(practice.get("outcome"))
                or "Recent practice outcome remains part of the current longitudinal context.",
                criteria=["method_context_recent_practice"],
                source_kind="method_context",
                entity_refs={"practiceSessions": [practice_id]},
                evidence_ids=[],
                graph_degree=degree_by_node_id.get(practice_id, 0),
                longitudinal_context=True,
            )
        individuation_context = method_context.get("individuationContext")
        if isinstance(individuation_context, dict):
            reality_anchor = individuation_context.get("realityAnchors")
            if isinstance(reality_anchor, dict):
                anchor_id = self._optional_str(reality_anchor.get("id"))
                if anchor_id:
                    self._add_discovery_candidate(
                        candidates,
                        key=f"reality_anchor:{anchor_id}",
                        label=str(reality_anchor.get("label") or "Reality anchors"),
                        summary=self._optional_str(reality_anchor.get("anchorSummary"))
                        or self._optional_str(reality_anchor.get("summary"))
                        or "Reality anchors are part of the current containment context.",
                        criteria=["method_context_reality_anchor"],
                        source_kind="method_context",
                        entity_refs={"entities": [anchor_id]},
                        evidence_ids=[
                            str(value)
                            for value in reality_anchor.get("evidenceIds", [])
                            if isinstance(value, str) and value
                        ],
                        graph_degree=degree_by_node_id.get(anchor_id, 0),
                        longitudinal_context=True,
                    )
            for threshold in individuation_context.get("thresholdProcesses", [])[:5]:
                if not isinstance(threshold, dict):
                    continue
                threshold_id = self._optional_str(threshold.get("id"))
                if not threshold_id:
                    continue
                self._add_discovery_candidate(
                    candidates,
                    key=f"threshold_process:{threshold_id}",
                    label=str(threshold.get("label") or "Threshold process"),
                    summary=self._optional_str(threshold.get("summary"))
                    or self._optional_str(threshold.get("whatIsEnding"))
                    or "An active threshold process remains in the current window.",
                    criteria=["method_context_threshold_process"],
                    source_kind="method_context",
                    entity_refs={"entities": [threshold_id]},
                    evidence_ids=[
                        str(value)
                        for value in threshold.get("evidenceIds", [])
                        if isinstance(value, str) and value
                    ],
                    graph_degree=degree_by_node_id.get(threshold_id, 0),
                    longitudinal_context=True,
                )
            for scene in individuation_context.get("relationalScenes", [])[:5]:
                if not isinstance(scene, dict):
                    continue
                scene_id = self._optional_str(scene.get("id"))
                if not scene_id:
                    continue
                self._add_discovery_candidate(
                    candidates,
                    key=f"relational_scene:{scene_id}",
                    label=str(scene.get("label") or "Relational scene"),
                    summary=self._optional_str(scene.get("sceneSummary"))
                    or self._optional_str(scene.get("summary"))
                    or "A relational scene remains active in the current context.",
                    criteria=["method_context_relational_scene"],
                    source_kind="method_context",
                    entity_refs={"entities": [scene_id]},
                    evidence_ids=[
                        str(value)
                        for value in scene.get("evidenceIds", [])
                        if isinstance(value, str) and value
                    ],
                    graph_degree=degree_by_node_id.get(scene_id, 0),
                    longitudinal_context=True,
                )
            for collection_name, key_prefix, label, criteria in (
                (
                    "activeOppositions",
                    "active_opposition",
                    "Active opposition",
                    "method_context_active_opposition",
                ),
                (
                    "emergentThirdSignals",
                    "emergent_third",
                    "Emergent third",
                    "method_context_emergent_third",
                ),
                ("bridgeMoments", "bridge_moment", "Bridge moment", "method_context_bridge_moment"),
                (
                    "projectionHypotheses",
                    "projection_hypothesis",
                    "Projection hypothesis",
                    "method_context_projection_hypothesis",
                ),
            ):
                for item in individuation_context.get(collection_name, [])[:5]:
                    if not isinstance(item, dict):
                        continue
                    item_id = self._optional_str(item.get("id"))
                    if not item_id:
                        continue
                    self._add_discovery_candidate(
                        candidates,
                        key=f"{key_prefix}:{item_id}",
                        label=self._optional_str(item.get("label")) or label,
                        summary=self._optional_str(item.get("summary"))
                        or self._optional_str(item.get("claim"))
                        or f"{label} remains active in the current context.",
                        criteria=[criteria],
                        source_kind="method_context",
                        entity_refs={"entities": [item_id]},
                        evidence_ids=[
                            str(value)
                            for value in item.get("evidenceIds", [])
                            if isinstance(value, str) and value
                        ],
                        graph_degree=degree_by_node_id.get(item_id, 0),
                        longitudinal_context=True,
                    )
        living_myth_context = method_context.get("livingMythContext")
        if isinstance(living_myth_context, dict):
            life_chapter = living_myth_context.get("currentLifeChapter")
            if isinstance(life_chapter, dict):
                chapter_id = self._optional_str(life_chapter.get("id"))
                if chapter_id:
                    self._add_discovery_candidate(
                        candidates,
                        key=f"life_chapter:{chapter_id}",
                        label=str(
                            life_chapter.get("chapterLabel")
                            or life_chapter.get("label")
                            or "Life chapter"
                        ),
                        summary=self._optional_str(life_chapter.get("chapterSummary"))
                        or self._optional_str(life_chapter.get("summary"))
                        or "A life chapter remains active in the current longitudinal context.",
                        criteria=["living_myth_current_chapter"],
                        source_kind="method_context",
                        entity_refs={"entities": [chapter_id]},
                        evidence_ids=[
                            str(value)
                            for value in life_chapter.get("evidenceIds", [])
                            if isinstance(value, str) and value
                        ],
                        graph_degree=degree_by_node_id.get(chapter_id, 0),
                        longitudinal_context=True,
                    )
            symbolic_wellbeing = living_myth_context.get("latestSymbolicWellbeing")
            if isinstance(symbolic_wellbeing, dict):
                wellbeing_id = self._optional_str(symbolic_wellbeing.get("id"))
                if wellbeing_id:
                    self._add_discovery_candidate(
                        candidates,
                        key=f"symbolic_wellbeing:{wellbeing_id}",
                        label=str(symbolic_wellbeing.get("label") or "Symbolic wellbeing"),
                        summary=self._optional_str(symbolic_wellbeing.get("capacitySummary"))
                        or self._optional_str(symbolic_wellbeing.get("summary"))
                        or "A recent symbolic wellbeing snapshot remains active.",
                        criteria=["living_myth_symbolic_wellbeing"],
                        source_kind="method_context",
                        entity_refs={"entities": [wellbeing_id]},
                        evidence_ids=[
                            str(value)
                            for value in symbolic_wellbeing.get("evidenceIds", [])
                            if isinstance(value, str) and value
                        ],
                        graph_degree=degree_by_node_id.get(wellbeing_id, 0),
                        longitudinal_context=True,
                    )
            for collection_name, key_prefix, label, criteria in (
                (
                    "activeMythicQuestions",
                    "mythic_question",
                    "Mythic question",
                    "living_myth_active_question",
                ),
                (
                    "recentThresholdMarkers",
                    "threshold_marker",
                    "Threshold marker",
                    "living_myth_threshold_marker",
                ),
                (
                    "complexEncounters",
                    "complex_encounter",
                    "Complex encounter",
                    "living_myth_complex_encounter",
                ),
            ):
                for item in living_myth_context.get(collection_name, [])[:5]:
                    if not isinstance(item, dict):
                        continue
                    item_id = self._optional_str(item.get("id"))
                    if not item_id:
                        continue
                    self._add_discovery_candidate(
                        candidates,
                        key=f"{key_prefix}:{item_id}",
                        label=self._optional_str(item.get("label")) or label,
                        summary=self._optional_str(item.get("summary"))
                        or self._optional_str(item.get("questionText"))
                        or f"{label} remains active in the current longitudinal context.",
                        criteria=[criteria],
                        source_kind="method_context",
                        entity_refs={"entities": [item_id]},
                        evidence_ids=[
                            str(value)
                            for value in item.get("evidenceIds", [])
                            if isinstance(value, str) and value
                        ],
                        graph_degree=degree_by_node_id.get(item_id, 0),
                        longitudinal_context=True,
                    )
        clarification_state = method_context.get("clarificationState")
        if isinstance(clarification_state, dict):
            for prompt in clarification_state.get("pendingPrompts", [])[:5]:
                if not isinstance(prompt, dict):
                    continue
                prompt_id = self._optional_str(prompt.get("id"))
                if not prompt_id:
                    continue
                self._add_discovery_candidate(
                    candidates,
                    key=f"clarification_prompt:{prompt_id}",
                    label="Pending clarification",
                    summary=self._optional_str(prompt.get("questionText"))
                    or "A clarification prompt is still open in the current context.",
                    criteria=["clarification_state_pending_prompt"],
                    source_kind="method_context",
                    entity_refs={"entities": [prompt_id]},
                    evidence_ids=[],
                    graph_degree=degree_by_node_id.get(prompt_id, 0),
                    longitudinal_context=True,
                )
            for answer in clarification_state.get("recentlyUnrouted", [])[:5]:
                if not isinstance(answer, dict):
                    continue
                answer_id = self._optional_str(answer.get("id"))
                if not answer_id:
                    continue
                self._add_discovery_candidate(
                    candidates,
                    key=f"clarification_unrouted:{answer_id}",
                    label="Clarification friction",
                    summary=self._clarification_friction_discovery_summary(answer),
                    criteria=["clarification_state_recently_unrouted"],
                    source_kind="method_context",
                    entity_refs=(
                        {"materials": [material_id]}
                        if (material_id := self._optional_str(answer.get("materialId")))
                        else {}
                    ),
                    evidence_ids=[],
                    graph_degree=degree_by_node_id.get(answer_id, 0),
                    longitudinal_context=True,
                )
            question_keys = [
                str(item)
                for item in clarification_state.get("avoidRepeatQuestionKeys", [])
                if isinstance(item, str) and item.strip()
            ]
            if question_keys:
                self._add_discovery_candidate(
                    candidates,
                    key="clarification_avoid_repeat:current",
                    label="Question friction",
                    summary=(
                        f"Avoid repeating {len(question_keys)} recent clarification question(s) "
                        "until the context shifts."
                    ),
                    criteria=["clarification_state_avoid_repeat"],
                    source_kind="method_context",
                    entity_refs={},
                    evidence_ids=[],
                    graph_degree=0,
                    longitudinal_context=True,
                )

    def _add_thread_digest_discovery_candidates(
        self,
        candidates: dict[str, dict[str, object]],
        *,
        thread_digests: list[ThreadDigest] | None,
        degree_by_node_id: dict[Id, int],
    ) -> None:
        for digest in thread_digests or []:
            if not isinstance(digest, dict):
                continue
            thread_key = self._optional_str(digest.get("threadKey"))
            summary = self._optional_str(digest.get("summary"))
            if not thread_key or not summary:
                continue
            kind = self._optional_str(digest.get("kind")) or "thread"
            entity_refs = deepcopy(
                digest.get("entityRefs") if isinstance(digest.get("entityRefs"), dict) else {}
            )
            journey_ids = [
                str(value)
                for value in digest.get("journeyIds", [])
                if isinstance(value, str) and value.strip()
            ]
            if journey_ids:
                entity_refs["journeys"] = self._merge_ids(
                    cast(list[Id], entity_refs.get("journeys", [])),
                    cast(list[Id], journey_ids),
                )
            graph_degree = max(
                [
                    degree_by_node_id.get(ref_id, 0)
                    for ref_ids in entity_refs.values()
                    if isinstance(ref_ids, list)
                    for ref_id in ref_ids
                    if isinstance(ref_id, str) and ref_id.strip()
                ],
                default=0,
            )
            self._add_discovery_candidate(
                candidates,
                key=thread_key,
                label=self._thread_digest_label(digest),
                summary=summary,
                criteria=["thread_digest", f"thread_kind:{kind}"],
                source_kind="thread_digest",
                entity_refs=entity_refs,
                evidence_ids=[
                    str(value)
                    for value in digest.get("evidenceIds", [])
                    if isinstance(value, str) and value.strip()
                ],
                graph_degree=graph_degree,
                longitudinal_context=True,
            )

    def _add_discovery_candidate(
        self,
        candidates: dict[str, dict[str, object]],
        *,
        key: str,
        label: str,
        summary: str,
        criteria: list[str],
        source_kind: str,
        entity_refs: dict[str, list[Id]],
        evidence_ids: list[Id],
        graph_degree: int = 0,
        recurrence_count: int = 0,
        user_confirmed: bool = False,
        active_pattern: bool = False,
        longitudinal_context: bool = False,
    ) -> None:
        candidate = candidates.setdefault(
            key,
            {
                "label": label,
                "summary": summary,
                "criteria": [],
                "sourceKinds": [],
                "entityRefs": {},
                "evidenceIds": [],
                "graphDegree": 0,
                "recurrenceCount": 0,
                "userConfirmed": False,
                "activePattern": False,
                "longitudinalContext": False,
            },
        )
        existing_label = self._optional_str(candidate.get("label"))
        if not existing_label or existing_label.lower() in {
            "dream",
            "reflection",
            "charged_event",
            "charged event",
            "material",
        }:
            candidate["label"] = label
        existing_summary = self._optional_str(candidate.get("summary"))
        if not existing_summary:
            candidate["summary"] = summary
        candidate["criteria"] = self._merge_tags(
            list(candidate.get("criteria", [])),
            [value for value in criteria if value],
        )
        candidate["sourceKinds"] = self._merge_tags(
            list(candidate.get("sourceKinds", [])),
            [source_kind],
        )
        candidate["entityRefs"] = self._discovery_merge_entity_refs(
            candidate.get("entityRefs"),
            entity_refs,
        )
        candidate["evidenceIds"] = self._merge_ids(
            list(candidate.get("evidenceIds", [])),
            [value for value in evidence_ids if value],
        )
        candidate["graphDegree"] = max(int(candidate.get("graphDegree", 0) or 0), graph_degree)
        candidate["recurrenceCount"] = max(
            int(candidate.get("recurrenceCount", 0) or 0),
            recurrence_count,
        )
        candidate["userConfirmed"] = bool(candidate.get("userConfirmed")) or user_confirmed
        candidate["activePattern"] = bool(candidate.get("activePattern")) or active_pattern
        candidate["longitudinalContext"] = bool(candidate.get("longitudinalContext")) or bool(
            longitudinal_context
        )
        if int(candidate.get("graphDegree", 0) or 0) > 0:
            candidate["sourceKinds"] = self._merge_tags(
                list(candidate.get("sourceKinds", [])),
                ["graph"],
            )
            candidate["criteria"] = self._merge_tags(
                list(candidate.get("criteria", [])),
                [f"graph_connection_count:{int(candidate['graphDegree'])}"],
            )

    def _build_recurring_discovery_section(
        self,
        *,
        candidates: dict[str, dict[str, object]],
        max_items: int,
    ) -> DiscoverySection:
        recurring_candidates = [
            candidate
            for candidate in candidates.values()
            if bool(candidate.get("activePattern"))
            or bool(candidate.get("userConfirmed"))
            or int(candidate.get("recurrenceCount", 0) or 0) > 1
            or "dashboard_recurring_symbol" in candidate.get("criteria", [])
        ]
        items = [
            self._candidate_to_discovery_item(candidate)
            for candidate in sorted(recurring_candidates, key=self._discovery_item_sort_key)[
                :max_items
            ]
        ]
        summary = (
            "Structural recurrences surfaced from dashboard and approved memory."
            if items
            else (
                "No recurring approved symbol or pattern surfaced in this bounded discovery digest."
            )
        )
        return {
            "key": "recurring",
            "title": "Recurring",
            "summary": summary,
            "items": items,
        }

    def _build_dream_body_event_discovery_section(
        self,
        *,
        graph: GraphQueryResult,
        max_items: int,
    ) -> DiscoverySection:
        nodes_by_id = {
            str(node["id"]): node
            for node in graph.get("nodes", [])
            if isinstance(node, dict) and isinstance(node.get("id"), str)
        }
        edges = [edge for edge in graph.get("edges", []) if isinstance(edge, dict)]
        adjacency: dict[Id, set[Id]] = {}
        pair_items: list[tuple[tuple[int, int, str], DiscoveryDigestItem]] = []
        triad_items: list[tuple[tuple[int, int, str], DiscoveryDigestItem]] = []
        seen_pair_keys: set[tuple[str, str, str]] = set()
        seen_cluster_keys: set[tuple[str, ...]] = set()

        def add_material_ref(refs: dict[str, list[Id]], node_id: Id, category: str | None) -> None:
            if category == "body":
                refs["bodyStates"] = self._merge_ids(refs.get("bodyStates", []), [node_id])
                return
            refs["materials"] = self._merge_ids(refs.get("materials", []), [node_id])

        for edge in edges:
            from_node_id = self._optional_str(edge.get("fromNodeId"))
            to_node_id = self._optional_str(edge.get("toNodeId"))
            if not from_node_id or not to_node_id:
                continue
            if from_node_id not in nodes_by_id or to_node_id not in nodes_by_id:
                continue
            adjacency.setdefault(from_node_id, set()).add(to_node_id)
            adjacency.setdefault(to_node_id, set()).add(from_node_id)
            from_category = self._discovery_node_category(nodes_by_id[from_node_id])
            to_category = self._discovery_node_category(nodes_by_id[to_node_id])
            categories = sorted(
                {category for category in (from_category, to_category) if category is not None}
            )
            if len(categories) < 2:
                continue
            edge_type = str(edge.get("type") or "graph_link")
            pair_key = tuple(sorted((from_node_id, to_node_id, edge_type)))
            if pair_key in seen_pair_keys:
                continue
            seen_pair_keys.add(pair_key)
            entity_refs: dict[str, list[Id]] = {}
            add_material_ref(entity_refs, from_node_id, from_category)
            add_material_ref(entity_refs, to_node_id, to_category)
            evidence_ids = [
                str(value)
                for value in edge.get("evidenceIds", [])
                if isinstance(value, str) and value
            ]
            label = " / ".join(category.title() for category in categories) + " link"
            summary = (
                f"{self._discovery_display_label(nodes_by_id[from_node_id])} and "
                f"{self._discovery_display_label(nodes_by_id[to_node_id])} "
                f"are connected by {edge_type}."
            )
            pair_items.append(
                (
                    (-len(categories), -len(evidence_ids), label.lower()),
                    {
                        "label": label,
                        "summary": self._compact_page_text(summary, max_length=180),
                        "criteria": [
                            f"graph_edge:{edge_type}",
                            f"cross_source_categories:{'+'.join(categories)}",
                        ],
                        "sourceKinds": ["graph"],
                        "entityRefs": entity_refs,
                        "evidenceIds": evidence_ids,
                    },
                )
            )
        for node_id, node in nodes_by_id.items():
            category = self._discovery_node_category(node)
            if category is None:
                continue
            cluster_ids = {node_id}
            for neighbor_id in adjacency.get(node_id, set()):
                neighbor = nodes_by_id.get(neighbor_id)
                if neighbor is None:
                    continue
                if self._discovery_node_category(neighbor) is not None:
                    cluster_ids.add(neighbor_id)
            cluster_categories = sorted(
                {
                    cluster_category
                    for cluster_id in cluster_ids
                    for cluster_category in [self._discovery_node_category(nodes_by_id[cluster_id])]
                    if cluster_category is not None
                }
            )
            if len(cluster_categories) < 3:
                continue
            cluster_key = tuple(sorted(cluster_ids))
            if cluster_key in seen_cluster_keys:
                continue
            seen_cluster_keys.add(cluster_key)
            entity_refs: dict[str, list[Id]] = {}
            evidence_ids: list[Id] = []
            for cluster_id in cluster_key:
                add_material_ref(
                    entity_refs,
                    cluster_id,
                    self._discovery_node_category(nodes_by_id[cluster_id]),
                )
            for edge in edges:
                from_node_id = self._optional_str(edge.get("fromNodeId"))
                to_node_id = self._optional_str(edge.get("toNodeId"))
                if from_node_id not in cluster_ids or to_node_id not in cluster_ids:
                    continue
                evidence_ids = self._merge_ids(
                    evidence_ids,
                    [
                        str(value)
                        for value in edge.get("evidenceIds", [])
                        if isinstance(value, str) and value
                    ],
                )
            triad_items.append(
                (
                    (
                        -len(cluster_categories),
                        -len(evidence_ids),
                        "dream / body / event neighborhood",
                    ),
                    {
                        "label": "Dream / body / event neighborhood",
                        "summary": (
                            "Dream, body, and event nodes appear in the same bounded "
                            "graph neighborhood."
                        ),
                        "criteria": [
                            "graph_bounded_neighborhood",
                            f"cross_source_categories:{'+'.join(cluster_categories)}",
                        ],
                        "sourceKinds": ["graph"],
                        "entityRefs": entity_refs,
                        "evidenceIds": evidence_ids,
                    },
                )
            )
        items = [item for _, item in sorted(triad_items + pair_items)[:max_items]]
        summary = (
            "Bounded graph links surfaced between dream, body, and event-adjacent records."
            if items
            else "No approved dream/body/event cross-link surfaced in this bounded graph view."
        )
        return {
            "key": "dream_body_event_links",
            "title": "Dream / body / event links",
            "summary": summary,
            "items": items,
        }

    def _build_revisit_discovery_section(
        self,
        *,
        candidates: dict[str, dict[str, object]],
        max_items: int,
    ) -> DiscoverySection:
        revisit_candidates: list[dict[str, object]] = []
        for candidate in candidates.values():
            source_count = len(candidate.get("sourceKinds", []))
            qualifies = (
                source_count >= 2
                or int(candidate.get("recurrenceCount", 0) or 0) > 1
                or bool(candidate.get("userConfirmed"))
                or int(candidate.get("graphDegree", 0) or 0) > 1
                or bool(candidate.get("activePattern"))
                or bool(candidate.get("longitudinalContext"))
            )
            if not qualifies:
                continue
            prepared = deepcopy(candidate)
            if source_count >= 2:
                prepared["criteria"] = self._merge_tags(
                    list(prepared.get("criteria", [])),
                    [f"source_category_count:{source_count}"],
                )
            revisit_candidates.append(prepared)
        items = [
            self._candidate_to_discovery_item(candidate)
            for candidate in sorted(revisit_candidates, key=self._discovery_item_sort_key)[
                :max_items
            ]
        ]
        summary = (
            "These appear across multiple approved sources and may be worth revisiting."
            if items
            else "No multi-source revisit candidate surfaced in this bounded discovery digest."
        )
        return {
            "key": "ripe_to_revisit",
            "title": "Ripe to revisit",
            "summary": summary,
            "items": items,
        }

    def _build_conscious_attitude_discovery_section(
        self,
        *,
        candidates: dict[str, dict[str, object]],
        max_items: int,
    ) -> DiscoverySection:
        attitude_candidates = [
            candidate
            for candidate in candidates.values()
            if "method_context_conscious_attitude" in candidate.get("criteria", [])
        ]
        items = [
            self._candidate_to_discovery_item(candidate)
            for candidate in sorted(attitude_candidates, key=self._discovery_item_sort_key)[
                :max_items
            ]
        ]
        summary = (
            "Current conscious attitude snapshots that shape how symbolic material can be met."
            if items
            else "No conscious-attitude snapshot surfaced in this bounded discovery digest."
        )
        return {
            "key": "conscious_attitude",
            "title": "Conscious attitude",
            "summary": summary,
            "items": items,
        }

    def _build_body_states_discovery_section(
        self,
        *,
        candidates: dict[str, dict[str, object]],
        max_items: int,
    ) -> DiscoverySection:
        body_state_candidates = [
            candidate
            for candidate in candidates.values()
            if "method_context_recent_body_state" in candidate.get("criteria", [])
        ]
        items = [
            self._candidate_to_discovery_item(candidate)
            for candidate in sorted(body_state_candidates, key=self._discovery_item_sort_key)[
                :max_items
            ]
        ]
        summary = (
            "Recent body states that remain symbolically or practically relevant right now."
            if items
            else "No recent body-state signal surfaced in this bounded discovery digest."
        )
        return {
            "key": "body_states",
            "title": "Body states",
            "summary": summary,
            "items": items,
        }

    def _build_method_state_discovery_section(
        self,
        *,
        candidates: dict[str, dict[str, object]],
        max_items: int,
    ) -> DiscoverySection:
        method_state_criteria = {
            "method_context_method_state",
            "method_context_longitudinal_signal",
            "method_context_witness_state",
            "method_state_active_goal_tension",
            "method_state_practice_loop",
            "method_state_relational_field",
            "method_state_questioning_preference",
            "method_state_typology_method_state",
            "method_context_goal_tension",
            "method_context_reality_anchor",
            "method_context_threshold_process",
            "clarification_state_pending_prompt",
            "clarification_state_recently_unrouted",
            "clarification_state_avoid_repeat",
        }
        method_state_candidates = [
            candidate
            for candidate in candidates.values()
            if any(
                criterion in method_state_criteria
                for criterion in cast(list[str], candidate.get("criteria", []))
            )
        ]
        prioritized_criteria = (
            "method_context_witness_state",
            "method_context_longitudinal_signal",
            "method_state_relational_field",
            "method_state_questioning_preference",
            "method_state_typology_method_state",
            "clarification_state_recently_unrouted",
            "clarification_state_avoid_repeat",
        )
        ranked_candidates = sorted(method_state_candidates, key=self._discovery_item_sort_key)
        selected_candidates: list[dict[str, object]] = []
        selected_ids: set[int] = set()
        for prioritized_criterion in prioritized_criteria:
            candidate = next(
                (
                    item
                    for item in ranked_candidates
                    if prioritized_criterion in cast(list[str], item.get("criteria", []))
                    and id(item) not in selected_ids
                ),
                None,
            )
            if candidate is None:
                continue
            selected_candidates.append(candidate)
            selected_ids.add(id(candidate))
            if len(selected_candidates) >= max_items:
                break
        if len(selected_candidates) < max_items:
            for candidate in ranked_candidates:
                if id(candidate) in selected_ids:
                    continue
                selected_candidates.append(candidate)
                selected_ids.add(id(candidate))
                if len(selected_candidates) >= max_items:
                    break
        items = [
            self._candidate_to_discovery_item(candidate)
            for candidate in selected_candidates[:max_items]
        ]
        summary = (
            "Method state, witness pacing, and clarification friction shaping the next move."
            if items
            else "No method-state pacing signal surfaced in this bounded discovery digest."
        )
        return {
            "key": "method_state",
            "title": "Method state",
            "summary": summary,
            "items": items,
        }

    def _build_journey_threads_discovery_section(
        self,
        *,
        candidates: dict[str, dict[str, object]],
        max_items: int,
    ) -> DiscoverySection:
        journey_candidates = [
            candidate
            for candidate in candidates.values()
            if "method_context_active_journey" in candidate.get("criteria", [])
            or "thread_digest" in candidate.get("criteria", [])
        ]
        items = [
            self._candidate_to_discovery_item(candidate)
            for candidate in sorted(journey_candidates, key=self._discovery_item_sort_key)[
                :max_items
            ]
        ]
        summary = (
            "Derived threads that still organize the current symbolic field."
            if items
            else "No live thread surfaced in this bounded discovery digest."
        )
        return {
            "key": "journey_threads",
            "title": "Journey threads",
            "summary": summary,
            "items": items,
        }

    def _build_held_for_now_discovery_section(
        self,
        *,
        dashboard: DashboardSummary,
        used_material_ids: list[Id],
        max_items: int,
    ) -> DiscoverySection:
        items: list[DiscoveryDigestItem] = []
        for material in dashboard.get("recentMaterials", []):
            material_id = self._optional_str(material.get("id"))
            if not material_id or material_id in used_material_ids:
                continue
            items.append(
                {
                    "label": self._discovery_material_label(material),
                    "summary": (
                        "Recent material with no additional approved cross-link in "
                        "this bounded digest."
                    ),
                    "criteria": ["recent_material_without_cross_source_link"],
                    "sourceKinds": ["dashboard"],
                    "entityRefs": {"materials": [material_id]},
                    "evidenceIds": [],
                }
            )
            if len(items) >= max_items:
                break
        summary = (
            "Recent held material with no additional approved cross-source link in "
            "this bounded digest."
            if items
            else "No held recent material remained outside the other bounded discovery sections."
        )
        return {
            "key": "held_for_now",
            "title": "Held for now",
            "summary": summary,
            "items": items,
        }

    def _candidate_to_discovery_item(self, candidate: dict[str, object]) -> DiscoveryDigestItem:
        item: DiscoveryDigestItem = {
            "label": str(candidate.get("label") or "Discovery item"),
            "criteria": list(candidate.get("criteria", [])),
            "sourceKinds": list(candidate.get("sourceKinds", [])),
            "entityRefs": deepcopy(candidate.get("entityRefs", {})),
            "evidenceIds": list(candidate.get("evidenceIds", [])),
        }
        summary = self._optional_str(candidate.get("summary"))
        if summary:
            item["summary"] = self._compact_page_text(summary, max_length=180)
        return item

    def _discovery_item_sort_key(
        self, candidate: dict[str, object]
    ) -> tuple[int, int, int, int, int, str]:
        return (
            -int(bool(candidate.get("longitudinalContext"))),
            -len(candidate.get("sourceKinds", [])),
            -int(bool(candidate.get("activePattern"))),
            -int(bool(candidate.get("userConfirmed"))),
            -int(candidate.get("recurrenceCount", 0) or 0),
            -int(candidate.get("graphDegree", 0) or 0),
            str(candidate.get("label") or "").lower(),
        )

    def _discovery_graph_degree_map(self, graph: GraphQueryResult) -> dict[Id, int]:
        degree_by_node_id: dict[Id, int] = {}
        for edge in graph.get("edges", []):
            if not isinstance(edge, dict):
                continue
            from_node_id = self._optional_str(edge.get("fromNodeId"))
            to_node_id = self._optional_str(edge.get("toNodeId"))
            if from_node_id:
                degree_by_node_id[from_node_id] = degree_by_node_id.get(from_node_id, 0) + 1
            if to_node_id:
                degree_by_node_id[to_node_id] = degree_by_node_id.get(to_node_id, 0) + 1
        return degree_by_node_id

    def _discovery_entity_key(self, *, entity_type: str, entity_id: Id) -> str:
        if entity_type == "PersonalSymbol":
            return f"symbol:{entity_id}"
        if entity_type in {"ComplexCandidate", "Theme"}:
            return f"pattern:{entity_id}"
        if entity_type in {"MaterialEntry", "DreamEntry", "ReflectionEntry", "ChargedEventNote"}:
            return f"material:{entity_id}"
        if entity_type == "BodyState":
            return f"body_state:{entity_id}"
        if entity_type == "Journey":
            return f"journey:{entity_id}"
        if entity_type == "Goal":
            return f"goal:{entity_id}"
        if entity_type == "PracticeSession":
            return f"practice_session:{entity_id}"
        if entity_type == "InterpretationRun":
            return f"run:{entity_id}"
        return f"{entity_type.lower()}:{entity_id}"

    def _discovery_entity_refs(self, *, entity_type: str, entity_id: Id) -> dict[str, list[Id]]:
        if entity_type == "PersonalSymbol":
            return {"symbols": [entity_id]}
        if entity_type in {"ComplexCandidate", "Theme"}:
            return {"patterns": [entity_id]}
        if entity_type in {"MaterialEntry", "DreamEntry", "ReflectionEntry", "ChargedEventNote"}:
            return {"materials": [entity_id]}
        if entity_type == "BodyState":
            return {"bodyStates": [entity_id]}
        if entity_type == "Journey":
            return {"journeys": [entity_id]}
        if entity_type == "Goal":
            return {"goals": [entity_id]}
        if entity_type == "PracticeSession":
            return {"practiceSessions": [entity_id]}
        if entity_type == "InterpretationRun":
            return {"runs": [entity_id]}
        if entity_type == "EvidenceItem":
            return {"evidence": [entity_id]}
        return {"entities": [entity_id]}

    def _discovery_merge_entity_refs(
        self,
        existing: object,
        updates: dict[str, list[Id]],
    ) -> dict[str, list[Id]]:
        merged: dict[str, list[Id]] = {}
        if isinstance(existing, dict):
            for key, values in existing.items():
                if isinstance(values, list):
                    merged[str(key)] = [str(value) for value in values if isinstance(value, str)]
        for key, values in updates.items():
            merged[key] = self._merge_ids(merged.get(key, []), list(values))
        return merged

    def _discovery_material_ids_from_sections(self, sections: list[DiscoverySection]) -> list[Id]:
        material_ids: list[Id] = []
        for section in sections:
            for item in section.get("items", []):
                entity_refs = item.get("entityRefs")
                if not isinstance(entity_refs, dict):
                    continue
                values = entity_refs.get("materials")
                if not isinstance(values, list):
                    continue
                material_ids = self._merge_ids(
                    material_ids,
                    [str(value) for value in values if isinstance(value, str)],
                )
        return material_ids

    def _discovery_node_category(self, node: dict[str, object]) -> str | None:
        node_type = str(node.get("type") or "")
        metadata = node.get("metadata") if isinstance(node.get("metadata"), dict) else {}
        material_type = str(metadata.get("materialType") or "")
        if node_type == "BodyState":
            return "body"
        if node_type == "DreamEntry" or material_type == "dream":
            return "dream"
        if node_type == "ChargedEventNote" or material_type == "charged_event":
            return "event"
        return None

    def _discovery_display_label(self, node: dict[str, object]) -> str:
        label = self._optional_str(node.get("label"))
        summary = self._optional_str(node.get("summary"))
        if label and label.lower() not in {"dream", "reflection", "charged_event", "charged event"}:
            return self._compact_page_text(label, max_length=60)
        if summary:
            return self._compact_page_text(summary, max_length=60)
        return self._compact_page_text(str(node.get("type") or "record"), max_length=60)

    def _discovery_material_label(self, material: MaterialRecord) -> str:
        if material.get("title"):
            return self._compact_page_text(material["title"], max_length=60)
        if material.get("summary"):
            return self._compact_page_text(material["summary"], max_length=60)
        return f"{str(material.get('materialType') or 'material').replace('_', ' ').title()} entry"

    def _method_state_discovery_summary(self, method_state: dict[str, object]) -> str | None:
        fragments: list[str] = []
        grounding = method_state.get("grounding")
        if isinstance(grounding, dict):
            recommendation = self._optional_str(grounding.get("recommendation"))
            if recommendation:
                fragments.append(f"Grounding: {recommendation.replace('_', ' ')}.")
        containment = method_state.get("containment")
        if isinstance(containment, dict):
            status = self._optional_str(containment.get("status"))
            if status:
                fragments.append(f"Containment: {status.replace('_', ' ')}.")
        ego_capacity = method_state.get("egoCapacity")
        if isinstance(ego_capacity, dict):
            reflective_capacity = self._optional_str(ego_capacity.get("reflectiveCapacity"))
            if reflective_capacity:
                fragments.append(f"Reflective capacity: {reflective_capacity.replace('_', ' ')}.")
        relational_field = method_state.get("relationalField")
        if isinstance(relational_field, dict):
            relationship_contact = self._optional_str(relational_field.get("relationshipContact"))
            if relationship_contact:
                fragments.append(f"Relational contact: {relationship_contact.replace('_', ' ')}.")
            isolation_risk = self._optional_str(relational_field.get("isolationRisk"))
            if isolation_risk:
                fragments.append(f"Isolation risk: {isolation_risk.replace('_', ' ')}.")
        questioning_preference = method_state.get("questioningPreference")
        if isinstance(questioning_preference, dict):
            depth_pacing = self._optional_str(questioning_preference.get("depthPacing"))
            if depth_pacing:
                fragments.append(f"Question pacing: {depth_pacing.replace('_', ' ')}.")
        active_goal_tension = method_state.get("activeGoalTension")
        if isinstance(active_goal_tension, dict):
            balancing_direction = self._optional_str(active_goal_tension.get("balancingDirection"))
            if balancing_direction:
                fragments.append(balancing_direction)
        practice_loop = method_state.get("practiceLoop")
        if isinstance(practice_loop, dict):
            outcome_trend = self._optional_str(practice_loop.get("recentOutcomeTrend"))
            if outcome_trend:
                fragments.append(f"Practice trend: {outcome_trend.replace('_', ' ')}.")
        typology_state = method_state.get("typologyMethodState")
        if isinstance(typology_state, dict):
            practice_bias = self._optional_str(typology_state.get("practiceBias"))
            if practice_bias and practice_bias != "neutral":
                fragments.append(f"Typology frame: {practice_bias.replace('_', ' ')}.")
        if not fragments:
            return None
        return " ".join(fragments)

    def _method_state_section_ref_ids(self, section: dict[str, object]) -> list[Id]:
        ref_ids: list[Id] = []
        record_id = self._optional_str(section.get("goalTensionId"))
        if record_id:
            ref_ids = self._merge_ids(ref_ids, [record_id])
        for ref in section.get("sourceRecordRefs", []):
            if not isinstance(ref, dict):
                continue
            record_id = self._optional_str(ref.get("recordId"))
            if record_id:
                ref_ids = self._merge_ids(ref_ids, [record_id])
        return ref_ids

    def _method_state_section_evidence_ids(self, section: dict[str, object]) -> list[Id]:
        return [
            str(value)
            for value in section.get("evidenceIds", [])
            if isinstance(value, str) and value
        ]

    def _relational_field_discovery_summary(
        self,
        relational_field: dict[str, object],
    ) -> str | None:
        fragments: list[str] = []
        relationship_contact = self._optional_str(relational_field.get("relationshipContact"))
        if relationship_contact:
            fragments.append(f"Relational contact: {relationship_contact.replace('_', ' ')}.")
        isolation_risk = self._optional_str(relational_field.get("isolationRisk"))
        if isolation_risk:
            fragments.append(f"Isolation risk: {isolation_risk.replace('_', ' ')}.")
        support_direction = self._optional_str(relational_field.get("supportDirection"))
        if support_direction:
            fragments.append(f"Support direction: {support_direction.replace('_', ' ')}.")
        recurring_affect = [
            str(item).strip()
            for item in relational_field.get("recurringAffect", [])
            if str(item).strip()
        ]
        if recurring_affect:
            fragments.append(f"Recurring affect: {', '.join(recurring_affect[:2])}.")
        return " ".join(fragments) or None

    def _questioning_preference_discovery_summary(
        self, questioning_preference: dict[str, object]
    ) -> str | None:
        fragments: list[str] = []
        depth_pacing = self._optional_str(questioning_preference.get("depthPacing"))
        if depth_pacing:
            fragments.append(f"Question pacing: {depth_pacing.replace('_', ' ')}.")
        max_questions = questioning_preference.get("maxQuestionsPerTurn")
        if isinstance(max_questions, int) and max_questions > 0:
            fragments.append(f"Max questions per turn: {max_questions}.")
        preferred_targets = [
            str(item).replace("_", " ")
            for item in questioning_preference.get("preferredCaptureTargets", [])
            if str(item).strip()
        ]
        if preferred_targets:
            fragments.append(f"Prefer clarifications about {', '.join(preferred_targets[:2])}.")
        friction_signals = [
            str(item).replace("_", " ")
            for item in questioning_preference.get("answerFrictionSignals", [])
            if str(item).strip()
        ]
        if friction_signals:
            fragments.append(f"Friction: {friction_signals[0]}.")
        return " ".join(fragments) or None

    def _typology_method_state_discovery_summary(
        self, typology_state: dict[str, object]
    ) -> str | None:
        fragments: list[str] = []
        status = self._optional_str(typology_state.get("status"))
        if status:
            fragments.append(f"Status: {status.replace('_', ' ')}.")
        prompt_bias = self._optional_str(typology_state.get("promptBias"))
        if prompt_bias and prompt_bias != "neutral":
            fragments.append(f"Prompt bias: {prompt_bias.replace('_', ' ')}.")
        practice_bias = self._optional_str(typology_state.get("practiceBias"))
        if practice_bias and practice_bias != "neutral":
            fragments.append(f"Practice bias: {practice_bias.replace('_', ' ')}.")
        balancing_function = self._optional_str(typology_state.get("balancingFunction"))
        if balancing_function:
            fragments.append(f"Balancing function: {balancing_function}.")
        return " ".join(fragments) or None

    def _witness_state_discovery_summary(self, witness_state: dict[str, object]) -> str | None:
        stance = self._optional_str(witness_state.get("stance"))
        starting_move = self._optional_str(witness_state.get("startingMove"))
        tone = self._optional_str(witness_state.get("tone"))
        if not any((stance, starting_move, tone)):
            return None
        fragments: list[str] = []
        if stance:
            fragments.append(f"Witness stance: {stance.replace('_', ' ')}.")
        if tone:
            fragments.append(f"Tone: {tone.replace('_', ' ')}.")
        if starting_move:
            fragments.append(f"Start with {starting_move.replace('_', ' ')}.")
        return " ".join(fragments)

    def _clarification_friction_discovery_summary(self, answer: dict[str, object]) -> str:
        capture_target = (
            self._optional_str(answer.get("captureTarget")) or "clarification"
        ).replace("_", " ")
        routing_status = (
            self._optional_str(answer.get("routingStatus")) or "needs_review"
        ).replace("_", " ")
        summary = f"Recent {capture_target} clarification stayed {routing_status}."
        errors = [
            str(item).strip() for item in answer.get("validationErrors", []) if str(item).strip()
        ]
        if errors:
            summary = f"{summary} {errors[0]}"
        return summary

    def _method_state_discovery_ref_ids(self, method_state: dict[str, object]) -> list[Id]:
        ref_ids: list[Id] = []
        for field_name in (
            "grounding",
            "containment",
            "egoCapacity",
            "egoRelationTrajectory",
            "relationalField",
            "questioningPreference",
            "activeGoalTension",
            "practiceLoop",
            "typologyMethodState",
        ):
            section = method_state.get(field_name)
            if not isinstance(section, dict):
                continue
            record_id = self._optional_str(section.get("goalTensionId"))
            if record_id:
                ref_ids = self._merge_ids(ref_ids, [record_id])
            for ref in section.get("sourceRecordRefs", []):
                if not isinstance(ref, dict):
                    continue
                record_id = self._optional_str(ref.get("recordId"))
                if record_id:
                    ref_ids = self._merge_ids(ref_ids, [record_id])
        for tendency in method_state.get("compensationTendencies", []):
            if not isinstance(tendency, dict):
                continue
            for ref in tendency.get("sourceRecordRefs", []):
                if not isinstance(ref, dict):
                    continue
                record_id = self._optional_str(ref.get("recordId"))
                if record_id:
                    ref_ids = self._merge_ids(ref_ids, [record_id])
        return ref_ids

    def _method_state_discovery_evidence_ids(self, method_state: dict[str, object]) -> list[Id]:
        evidence_ids: list[Id] = []
        for field_name in (
            "grounding",
            "containment",
            "egoCapacity",
            "egoRelationTrajectory",
            "relationalField",
            "questioningPreference",
            "activeGoalTension",
            "practiceLoop",
            "typologyMethodState",
        ):
            section = method_state.get(field_name)
            if not isinstance(section, dict):
                continue
            evidence_ids = self._merge_ids(
                evidence_ids,
                [
                    str(value)
                    for value in section.get("evidenceIds", [])
                    if isinstance(value, str) and value
                ],
            )
        for tendency in method_state.get("compensationTendencies", []):
            if not isinstance(tendency, dict):
                continue
            evidence_ids = self._merge_ids(
                evidence_ids,
                [
                    str(value)
                    for value in tendency.get("evidenceIds", [])
                    if isinstance(value, str) and value
                ],
            )
        return evidence_ids

    def _render_discovery_fallback(
        self,
        *,
        sections: list[DiscoverySection],
        window_start: str,
        window_end: str,
        explicit_question: str | None,
    ) -> str:
        lines = ["Discovery digest", f"Window: {window_start} -> {window_end}"]
        if explicit_question:
            lines.append(f"Focus: {explicit_question}")
        for section in sections:
            lines.append("")
            lines.append(section["title"])
            items = section.get("items", [])
            if not items:
                lines.append(section["summary"])
                continue
            for item in items:
                summary = self._optional_str(item.get("summary"))
                if summary:
                    lines.append(f"- {item['label']} - {summary}")
                    continue
                lines.append(f"- {item['label']}")
        return "\n".join(lines)

    def _build_intake_context_packet(
        self,
        *,
        material: MaterialRecord,
        window_start: str,
        window_end: str,
        method_context: MethodContextSnapshot | None,
        thread_digests: list[ThreadDigest] | None,
        dashboard: DashboardSummary | None,
        warnings: list[str],
    ) -> IntakeContextPacket:
        items: list[IntakeContextItem] = []
        seen_keys: set[str] = set()
        for item in self._intake_items_from_method_context(
            material=material,
            method_context=method_context,
        ):
            self._add_intake_item(items, item=item, seen_keys=seen_keys)
        for item in self._intake_items_from_thread_digests(thread_digests=thread_digests):
            self._add_intake_item(items, item=item, seen_keys=seen_keys)
        for item in self._intake_items_from_dashboard(
            material=material,
            dashboard=dashboard,
        ):
            self._add_intake_item(items, item=item, seen_keys=seen_keys)
        source_counts: IntakeContextSourceCounts = {
            "recentMaterialCount": sum(
                1
                for record in (dashboard or {}).get("recentMaterials", [])
                if isinstance(record, dict)
                and self._optional_str(record.get("id"))
                and self._optional_str(record.get("id")) != material["id"]
            ),
            "recurringSymbolCount": sum(
                1
                for record in (dashboard or {}).get("recurringSymbols", [])
                if isinstance(record, dict) and self._optional_str(record.get("id"))
            ),
            "activePatternCount": sum(
                1
                for record in (dashboard or {}).get("activePatterns", [])
                if isinstance(record, dict) and self._optional_str(record.get("id"))
            ),
            "activeJourneyCount": sum(
                1
                for record in (method_context or {}).get("activeJourneys", [])
                if isinstance(record, dict) and self._optional_str(record.get("id"))
            ),
            "threadDigestCount": sum(
                1
                for record in (thread_digests or [])
                if isinstance(record, dict) and self._optional_str(record.get("threadKey"))
            ),
            "longitudinalSignalCount": sum(
                1
                for record in (method_context or {}).get("longitudinalSignals", [])
                if isinstance(record, dict) and self._optional_str(record.get("id"))
            ),
            "intakeItemCount": len(items),
            "pendingProposalCount": int((dashboard or {}).get("pendingProposalCount", 0) or 0),
        }
        packet_warnings = list(dict.fromkeys(warnings))
        return {
            "packetId": create_id("intake_context"),
            "visibility": "host_only",
            "status": "partial" if packet_warnings else "complete",
            "source": "circulatio-post-store",
            "generatedAt": now_iso(),
            "userId": material["userId"],
            "materialId": material["id"],
            "materialType": material["materialType"],
            "windowStart": window_start,
            "windowEnd": window_end,
            "anchorMaterial": self._intake_anchor_material(material),
            "hostGuidance": self._build_intake_host_guidance(
                method_context=method_context,
                item_count=len(items),
                warnings=packet_warnings,
            ),
            "items": items,
            "entityRefs": self._aggregate_intake_entity_refs(items),
            "sourceCounts": source_counts,
            "warnings": packet_warnings,
        }

    def _intake_anchor_material(self, material: MaterialRecord) -> IntakeAnchorMaterial:
        anchor: IntakeAnchorMaterial = {
            "id": material["id"],
            "materialType": material["materialType"],
            "materialDate": str(
                material.get("materialDate") or material.get("createdAt") or now_iso()
            ),
            "tags": [
                str(item) for item in material.get("tags", []) if isinstance(item, str) and item
            ],
        }
        title = self._truncate_intake_text(material.get("title"), limit=120)
        summary = self._truncate_intake_text(material.get("summary"), limit=220)
        text_preview = self._truncate_intake_text(material.get("text"), limit=220)
        if title:
            anchor["title"] = title
        if summary:
            anchor["summary"] = summary
        if text_preview:
            anchor["textPreview"] = text_preview
        return anchor

    def _intake_items_from_thread_digests(
        self,
        *,
        thread_digests: list[ThreadDigest] | None,
    ) -> list[IntakeContextItem]:
        items: list[IntakeContextItem] = []
        seen_keys: set[str] = set()
        for digest in (thread_digests or [])[:4]:
            if not isinstance(digest, dict):
                continue
            thread_key = self._optional_str(digest.get("threadKey"))
            summary = self._truncate_intake_text(digest.get("summary"), limit=180)
            if not thread_key or not summary:
                continue
            kind = self._optional_str(digest.get("kind")) or "thread"
            if kind == "coach_loop":
                continue
            entity_refs = deepcopy(
                digest.get("entityRefs") if isinstance(digest.get("entityRefs"), dict) else {}
            )
            journey_ids = [
                str(value)
                for value in digest.get("journeyIds", [])
                if isinstance(value, str) and value.strip()
            ]
            if journey_ids:
                entity_refs["journeys"] = self._merge_ids(
                    cast(list[Id], entity_refs.get("journeys", [])),
                    cast(list[Id], journey_ids),
                )
            self._add_intake_item(
                items,
                item={
                    "key": f"thread_digest:{thread_key}",
                    "kind": "thread_digest",
                    "label": self._thread_digest_label(digest),
                    "summary": summary,
                    "sourceKind": "method_context",
                    "criteria": ["thread_digest", f"thread_kind:{kind}"],
                    "entityRefs": entity_refs,
                    "evidenceIds": [
                        str(value)
                        for value in digest.get("evidenceIds", [])
                        if isinstance(value, str) and value.strip()
                    ],
                },
                seen_keys=seen_keys,
                max_items=4,
            )
        return items

    def _intake_items_from_dashboard(
        self,
        *,
        material: MaterialRecord,
        dashboard: DashboardSummary | None,
    ) -> list[IntakeContextItem]:
        if dashboard is None:
            return []
        items: list[IntakeContextItem] = []
        seen_keys: set[str] = set()
        recent_materials = [
            record
            for record in dashboard.get("recentMaterials", [])
            if isinstance(record, dict)
            and self._optional_str(record.get("id"))
            and self._optional_str(record.get("id")) != material["id"]
        ]
        for recent in recent_materials[:3]:
            recent_id = str(recent["id"])
            item: IntakeContextItem = {
                "key": f"recent_material:{recent_id}",
                "kind": "recent_material",
                "label": self._discovery_material_label(cast(MaterialRecord, recent)),
                "sourceKind": "dashboard",
                "criteria": ["dashboard_recent_material"],
                "entityRefs": {"materials": [recent_id]},
                "evidenceIds": [],
            }
            summary = self._truncate_intake_text(recent.get("summary"), limit=180) or (
                self._truncate_intake_text(recent.get("text"), limit=180)
            )
            if summary:
                item["summary"] = summary
            self._add_intake_item(items, item=item, seen_keys=seen_keys)
        for symbol in dashboard.get("recurringSymbols", [])[:3]:
            if not isinstance(symbol, dict):
                continue
            symbol_id = self._optional_str(symbol.get("id"))
            canonical_name = self._optional_str(symbol.get("canonicalName"))
            if not symbol_id or not canonical_name:
                continue
            recurrence_count = int(symbol.get("recurrenceCount", 0) or 0)
            self._add_intake_item(
                items,
                item={
                    "key": f"symbol:{symbol_id}",
                    "kind": "recurring_symbol",
                    "label": self._compact_page_text(canonical_name, max_length=60),
                    "summary": (
                        f"Recurring symbol with {recurrence_count} recorded appearance(s)."
                        if recurrence_count > 0
                        else "Recurring symbol surfaced in the dashboard."
                    ),
                    "sourceKind": "dashboard",
                    "criteria": [
                        "dashboard_recurring_symbol",
                        f"symbol_recurrence_count:{recurrence_count}",
                    ],
                    "entityRefs": {"symbols": [symbol_id]},
                    "evidenceIds": [],
                },
                seen_keys=seen_keys,
            )
        for pattern in dashboard.get("activePatterns", [])[:3]:
            if not isinstance(pattern, dict):
                continue
            pattern_id = self._optional_str(pattern.get("id"))
            label = self._optional_str(pattern.get("label"))
            if not pattern_id or not label:
                continue
            evidence_ids = [
                str(value)
                for value in pattern.get("evidenceIds", [])
                if isinstance(value, str) and value
            ]
            item = {
                "key": f"pattern:{pattern_id}",
                "kind": "active_pattern",
                "label": self._compact_page_text(label, max_length=60),
                "sourceKind": "dashboard",
                "criteria": ["dashboard_active_pattern"],
                "entityRefs": {"patterns": [pattern_id]},
                "evidenceIds": evidence_ids,
            }
            summary = self._truncate_intake_text(pattern.get("formulation"), limit=180)
            if summary:
                item["summary"] = summary
            else:
                item["summary"] = "Active pattern surfaced in the dashboard."
            self._add_intake_item(items, item=item, seen_keys=seen_keys)
        return items

    def _intake_items_from_method_context(
        self,
        *,
        material: MaterialRecord,
        method_context: MethodContextSnapshot | None,
    ) -> list[IntakeContextItem]:
        if method_context is None:
            return []
        items: list[IntakeContextItem] = []
        seen_keys: set[str] = set()
        current_material_id = material["id"]
        method_state_item_count = 0
        context_item_count = 0
        method_state = (
            method_context.get("methodState")
            if isinstance(method_context.get("methodState"), dict)
            else None
        )
        clarification_state = (
            method_context.get("clarificationState")
            if isinstance(method_context.get("clarificationState"), dict)
            else None
        )
        individuation_context = (
            method_context.get("individuationContext")
            if isinstance(method_context.get("individuationContext"), dict)
            else None
        )
        living_myth_context = (
            method_context.get("livingMythContext")
            if isinstance(method_context.get("livingMythContext"), dict)
            else None
        )

        if isinstance(individuation_context, dict):
            reality_anchor = individuation_context.get("realityAnchors")
            if isinstance(reality_anchor, dict):
                anchor_id = self._optional_str(reality_anchor.get("id"))
                if anchor_id:
                    anchor_item: IntakeContextItem = {
                        "key": f"reality_anchor:{anchor_id}",
                        "kind": "reality_anchor",
                        "label": self._compact_page_text(
                            str(reality_anchor.get("label") or "Reality anchors"),
                            max_length=60,
                        ),
                        "sourceKind": "method_context",
                        "criteria": ["method_context_reality_anchor"],
                        "entityRefs": {"entities": [anchor_id]},
                        "evidenceIds": [
                            str(value)
                            for value in reality_anchor.get("evidenceIds", [])
                            if isinstance(value, str) and value
                        ],
                    }
                    summary = self._truncate_intake_text(
                        reality_anchor.get("anchorSummary") or reality_anchor.get("summary"),
                        limit=180,
                    )
                    if summary:
                        anchor_item["summary"] = summary
                    grounding_recommendation = self._optional_str(
                        reality_anchor.get("groundingRecommendation")
                    )
                    if grounding_recommendation == "grounding_first":
                        anchor_item["caution"] = "Grounding first."
                    elif grounding_recommendation == "pace_gently":
                        anchor_item["caution"] = "Pace gently."
                    if self._add_intake_item(items, item=anchor_item, seen_keys=seen_keys):
                        context_item_count += 1

        if isinstance(method_state, dict):
            method_state_ref_ids = self._method_state_discovery_ref_ids(method_state)
            method_state_evidence_ids = self._method_state_discovery_evidence_ids(method_state)
            summary = self._method_state_discovery_summary(method_state)
            if (
                summary
                and (method_state_ref_ids or method_state_evidence_ids)
                and self._add_intake_item(
                    items,
                    item={
                        "key": "method_state:current",
                        "kind": "method_state",
                        "label": "Method state",
                        "summary": self._truncate_intake_text(summary, limit=180) or summary,
                        "sourceKind": "method_context",
                        "criteria": ["method_context_method_state"],
                        "entityRefs": {"entities": method_state_ref_ids},
                        "evidenceIds": method_state_evidence_ids,
                    },
                    seen_keys=seen_keys,
                )
            ):
                method_state_item_count += 1

        if isinstance(clarification_state, dict):
            pending_prompts = [
                prompt
                for prompt in clarification_state.get("pendingPrompts", [])
                if isinstance(prompt, dict) and self._optional_str(prompt.get("id"))
            ]
            if pending_prompts:
                prompt_ids = [str(prompt["id"]) for prompt in pending_prompts[:2]]
                first_prompt = pending_prompts[0]
                summary = self._truncate_intake_text(
                    first_prompt.get("questionText"), limit=180
                ) or (f"{len(pending_prompts)} pending clarification prompt(s).")
                self._add_intake_item(
                    items,
                    item={
                        "key": "clarification_state:pending",
                        "kind": "clarification_state",
                        "label": "Pending clarification",
                        "summary": summary,
                        "sourceKind": "method_context",
                        "criteria": ["clarification_state_pending"],
                        "entityRefs": {"entities": prompt_ids},
                        "evidenceIds": [],
                    },
                    seen_keys=seen_keys,
                )
            recently_unrouted = [
                answer
                for answer in clarification_state.get("recentlyUnrouted", [])
                if isinstance(answer, dict) and self._optional_str(answer.get("id"))
            ]
            avoid_repeat = [
                str(item)
                for item in clarification_state.get("avoidRepeatQuestionKeys", [])
                if isinstance(item, str) and item.strip()
            ]
            if recently_unrouted or avoid_repeat:
                criteria: list[str] = []
                summary_parts: list[str] = []
                entity_refs: dict[str, list[Id]] = {}
                if recently_unrouted:
                    criteria.append("clarification_state_recently_unrouted")
                    first_unrouted = recently_unrouted[0]
                    summary_parts.append(
                        self._clarification_friction_discovery_summary(first_unrouted)
                    )
                    answer_id = self._optional_str(first_unrouted.get("id"))
                    if answer_id:
                        entity_refs["entities"] = [answer_id]
                    material_id = self._optional_str(first_unrouted.get("materialId"))
                    if material_id:
                        entity_refs["materials"] = [material_id]
                if avoid_repeat:
                    criteria.append("clarification_state_avoid_repeat")
                    summary_parts.append("Avoid repeating the same clarification question.")
                self._add_intake_item(
                    items,
                    item={
                        "key": "clarification_state:pacing",
                        "kind": "clarification_state",
                        "label": "Clarification pacing",
                        "summary": self._truncate_intake_text(" ".join(summary_parts), limit=180)
                        or "Clarification pacing is active.",
                        "sourceKind": "method_context",
                        "criteria": criteria,
                        "entityRefs": entity_refs,
                        "evidenceIds": [],
                    },
                    seen_keys=seen_keys,
                )

        for body_state in method_context.get("recentBodyStates", [])[:2]:
            if not isinstance(body_state, dict):
                continue
            body_state_id = self._optional_str(body_state.get("id"))
            sensation = self._optional_str(body_state.get("sensation"))
            if not body_state_id or not sensation:
                continue
            region = self._optional_str(body_state.get("bodyRegion"))
            activation = self._optional_str(body_state.get("activation"))
            tone = self._optional_str(body_state.get("tone"))
            fragments = [f"{sensation}{f' in the {region}' if region else ''}."]
            if activation:
                fragments.append(f"Activation: {activation.replace('_', ' ')}.")
            if tone:
                fragments.append(f"Tone: {tone.replace('_', ' ')}.")
            self._add_intake_item(
                items,
                item={
                    "key": f"body_state:{body_state_id}",
                    "kind": "recent_body_state",
                    "label": self._compact_page_text(sensation, max_length=60),
                    "summary": " ".join(fragments),
                    "sourceKind": "method_context",
                    "criteria": ["method_context_recent_body_state"],
                    "entityRefs": {"bodyStates": [body_state_id]},
                    "evidenceIds": [],
                },
                seen_keys=seen_keys,
            )

        for journey in method_context.get("activeJourneys", [])[:3]:
            if not isinstance(journey, dict):
                continue
            journey_id = self._optional_str(journey.get("id"))
            label = self._optional_str(journey.get("label"))
            if not journey_id or not label:
                continue
            criteria = ["method_context_active_journey"]
            related_material_ids = [
                str(item)
                for item in journey.get("relatedMaterialIds", [])
                if isinstance(item, str) and item
            ]
            if current_material_id in related_material_ids:
                criteria.append("current_material_already_linked")
            entity_refs: dict[str, list[Id]] = {"journeys": [journey_id]}
            if related_material_ids:
                entity_refs["materials"] = related_material_ids[:5]
            related_symbol_ids = [
                str(item)
                for item in journey.get("relatedSymbolIds", [])
                if isinstance(item, str) and item
            ]
            if related_symbol_ids:
                entity_refs["symbols"] = related_symbol_ids[:5]
            related_pattern_ids = [
                str(item)
                for item in journey.get("relatedPatternIds", [])
                if isinstance(item, str) and item
            ]
            if related_pattern_ids:
                entity_refs["patterns"] = related_pattern_ids[:5]
            self._add_intake_item(
                items,
                item={
                    "key": f"journey:{journey_id}",
                    "kind": "active_journey",
                    "label": self._compact_page_text(label, max_length=60),
                    "summary": self._truncate_intake_text(
                        journey.get("currentQuestion"),
                        limit=180,
                    )
                    or "Active journey thread.",
                    "sourceKind": "method_context",
                    "criteria": criteria,
                    "entityRefs": entity_refs,
                    "evidenceIds": [],
                },
                seen_keys=seen_keys,
            )

        for series in method_context.get("activeDreamSeries", [])[:3]:
            if not isinstance(series, dict):
                continue
            series_id = self._optional_str(series.get("id"))
            label = self._optional_str(series.get("label"))
            if not series_id or not label:
                continue
            criteria = ["method_context_active_dream_series"]
            material_ids = [
                str(item)
                for item in series.get("materialIds", [])
                if isinstance(item, str) and item
            ]
            if current_material_id in material_ids:
                criteria.append("current_material_already_linked")
            summary = (
                self._truncate_intake_text(series.get("progressionSummary"), limit=180)
                or self._truncate_intake_text(series.get("egoTrajectory"), limit=180)
                or self._truncate_intake_text(series.get("compensationTrajectory"), limit=180)
                or f"Active dream series with {len(material_ids)} linked material(s)."
            )
            entity_refs = {"dreamSeries": [series_id]}
            if material_ids:
                entity_refs["materials"] = material_ids[:5]
            self._add_intake_item(
                items,
                item={
                    "key": f"dream_series:{series_id}",
                    "kind": "active_dream_series",
                    "label": self._compact_page_text(label, max_length=60),
                    "summary": summary,
                    "sourceKind": "method_context",
                    "criteria": criteria,
                    "entityRefs": entity_refs,
                    "evidenceIds": [],
                },
                seen_keys=seen_keys,
            )

        for dynamic in method_context.get("recentDreamDynamics", [])[:3]:
            if not isinstance(dynamic, dict):
                continue
            material_id = self._optional_str(dynamic.get("materialId"))
            if not material_id:
                continue
            summary = (
                self._truncate_intake_text(dynamic.get("summary"), limit=180)
                or self._truncate_intake_text(dynamic.get("dynamicSummary"), limit=180)
                or self._truncate_intake_text(dynamic.get("label"), limit=180)
                or self._truncate_intake_text(dynamic.get("motif"), limit=180)
            )
            if not summary:
                ego_stance = self._optional_str(dynamic.get("egoStance"))
                action_summary = self._optional_str(dynamic.get("actionSummary"))
                if ego_stance and action_summary:
                    summary = self._truncate_intake_text(
                        f"{ego_stance}: {action_summary}",
                        limit=180,
                    )
                elif action_summary:
                    summary = self._truncate_intake_text(action_summary, limit=180)
            if not summary:
                continue
            evidence_ids = [
                str(value)
                for value in dynamic.get("evidenceIds", [])
                if isinstance(value, str) and value
            ]
            self._add_intake_item(
                items,
                item={
                    "key": f"recent_dream_dynamic:{material_id}",
                    "kind": "recent_dream_dynamic",
                    "label": self._compact_page_text(
                        self._optional_str(dynamic.get("egoStance")) or "Dream dynamics",
                        max_length=60,
                    ),
                    "summary": summary,
                    "sourceKind": "method_context",
                    "criteria": ["method_context_recent_dream_dynamic"],
                    "entityRefs": {"materials": [material_id]},
                    "evidenceIds": evidence_ids,
                },
                seen_keys=seen_keys,
            )

        for signal in method_context.get("longitudinalSignals", [])[:3]:
            if not isinstance(signal, dict):
                continue
            signal_id = self._optional_str(signal.get("id"))
            signal_type = self._optional_str(signal.get("signalType"))
            summary = self._truncate_intake_text(signal.get("summary"), limit=180)
            if not signal_id or not signal_type or not summary:
                continue
            strength = self._optional_str(signal.get("strength"))
            if strength:
                summary = f"{summary} Strength: {strength}."
            self._add_intake_item(
                items,
                item={
                    "key": f"longitudinal_signal:{signal_id}",
                    "kind": "longitudinal_signal",
                    "label": signal_type.replace("_", " ").title(),
                    "summary": summary,
                    "sourceKind": "method_context",
                    "criteria": [
                        "method_context_longitudinal_signal",
                        f"longitudinal_signal:{signal_type}",
                    ],
                    "entityRefs": {
                        "entities": [
                            str(value)
                            for value in signal.get("sourceEntityIds", [])
                            if isinstance(value, str) and value
                        ],
                        "materials": [
                            str(value)
                            for value in signal.get("materialIds", [])
                            if isinstance(value, str) and value
                        ],
                    },
                    "evidenceIds": [],
                },
                seen_keys=seen_keys,
            )

        if isinstance(method_state, dict):
            relational_field = method_state.get("relationalField")
            if (
                method_state_item_count < 4
                and isinstance(relational_field, dict)
                and (summary := self._relational_field_discovery_summary(relational_field))
            ):
                entity_ids = self._method_state_section_ref_ids(relational_field)
                active_scene_ids = [
                    str(item)
                    for item in relational_field.get("activeSceneIds", [])
                    if isinstance(item, str) and item
                ]
                if active_scene_ids:
                    entity_ids = self._merge_ids(
                        entity_ids,
                        active_scene_ids,
                    )
                relationship_contact = self._optional_str(
                    relational_field.get("relationshipContact")
                )
                isolation_risk = self._optional_str(relational_field.get("isolationRisk"))
                recurring_affect = [
                    str(item).strip()
                    for item in relational_field.get("recurringAffect", [])
                    if str(item).strip()
                ]
                evidence_ids = self._method_state_section_evidence_ids(relational_field)
                has_relational_signal = bool(
                    entity_ids
                    or evidence_ids
                    or recurring_affect
                    or relationship_contact not in {None, "unknown"}
                    or isolation_risk not in {None, "unknown"}
                )
                if has_relational_signal and self._add_intake_item(
                    items,
                    item={
                        "key": "method_state:relational_field",
                        "kind": "method_state",
                        "label": "Relational field",
                        "summary": self._truncate_intake_text(summary, limit=180) or summary,
                        "sourceKind": "method_context",
                        "criteria": ["method_state_relational_field"],
                        "entityRefs": {"entities": entity_ids},
                        "evidenceIds": evidence_ids,
                    },
                    seen_keys=seen_keys,
                ):
                    method_state_item_count += 1
            questioning_preference = method_state.get("questioningPreference")
            if (
                method_state_item_count < 4
                and isinstance(questioning_preference, dict)
                and (
                    summary := self._questioning_preference_discovery_summary(
                        questioning_preference
                    )
                )
            ):
                if self._add_intake_item(
                    items,
                    item={
                        "key": "method_state:questioning_preference",
                        "kind": "method_state",
                        "label": "Questioning preference",
                        "summary": self._truncate_intake_text(summary, limit=180) or summary,
                        "sourceKind": "method_context",
                        "criteria": ["method_state_questioning_preference"],
                        "entityRefs": {
                            "entities": self._method_state_section_ref_ids(questioning_preference)
                        },
                        "evidenceIds": self._method_state_section_evidence_ids(
                            questioning_preference
                        ),
                    },
                    seen_keys=seen_keys,
                ):
                    method_state_item_count += 1
            active_goal_tension = method_state.get("activeGoalTension")
            if method_state_item_count < 4 and isinstance(active_goal_tension, dict):
                summary = self._truncate_intake_text(
                    active_goal_tension.get("summary")
                    or active_goal_tension.get("balancingDirection"),
                    limit=180,
                )
                if summary and self._add_intake_item(
                    items,
                    item={
                        "key": "method_state:active_goal_tension",
                        "kind": "method_state",
                        "label": "Goal tension",
                        "summary": summary,
                        "sourceKind": "method_context",
                        "criteria": ["method_state_active_goal_tension"],
                        "entityRefs": {
                            "entities": self._method_state_section_ref_ids(active_goal_tension),
                            "goals": [
                                str(item)
                                for item in active_goal_tension.get("linkedGoalIds", [])
                                if isinstance(item, str) and item
                            ][:5],
                        },
                        "evidenceIds": self._method_state_section_evidence_ids(active_goal_tension),
                    },
                    seen_keys=seen_keys,
                ):
                    method_state_item_count += 1
            practice_loop = method_state.get("practiceLoop")
            if method_state_item_count < 4 and isinstance(practice_loop, dict):
                fragments: list[str] = []
                outcome_trend = self._optional_str(practice_loop.get("recentOutcomeTrend"))
                if outcome_trend:
                    fragments.append(f"Practice trend: {outcome_trend.replace('_', ' ')}.")
                intensity = self._optional_str(practice_loop.get("recommendedIntensity"))
                if intensity:
                    fragments.append(f"Recommended intensity: {intensity.replace('_', ' ')}.")
                modalities = [
                    str(item).replace("_", " ")
                    for item in practice_loop.get("preferredModalities", [])
                    if str(item).strip()
                ]
                if modalities:
                    fragments.append(f"Preferred modalities: {', '.join(modalities[:2])}.")
                max_duration = practice_loop.get("maxDurationMinutes")
                if isinstance(max_duration, int) and max_duration > 0:
                    fragments.append(f"Max duration: {max_duration} minutes.")
                summary = " ".join(fragments)
                if summary and self._add_intake_item(
                    items,
                    item={
                        "key": "method_state:practice_loop",
                        "kind": "method_state",
                        "label": "Practice loop",
                        "summary": self._truncate_intake_text(summary, limit=180) or summary,
                        "sourceKind": "method_context",
                        "criteria": ["method_state_practice_loop"],
                        "entityRefs": {
                            "entities": self._method_state_section_ref_ids(practice_loop)
                        },
                        "evidenceIds": self._method_state_section_evidence_ids(practice_loop),
                    },
                    seen_keys=seen_keys,
                ):
                    method_state_item_count += 1
            typology_state = method_state.get("typologyMethodState")
            if (
                method_state_item_count < 4
                and isinstance(typology_state, dict)
                and (summary := self._typology_method_state_discovery_summary(typology_state))
            ):
                if self._add_intake_item(
                    items,
                    item={
                        "key": "method_state:typology",
                        "kind": "method_state",
                        "label": "Typology method state",
                        "summary": self._truncate_intake_text(summary, limit=180) or summary,
                        "sourceKind": "method_context",
                        "criteria": ["method_state_typology_method_state"],
                        "entityRefs": {
                            "entities": self._merge_ids(
                                self._method_state_section_ref_ids(typology_state),
                                [
                                    str(item)
                                    for item in typology_state.get("activeLensIds", [])
                                    if isinstance(item, str) and item
                                ],
                            )
                        },
                        "evidenceIds": self._method_state_section_evidence_ids(typology_state),
                    },
                    seen_keys=seen_keys,
                ):
                    method_state_item_count += 1

        if isinstance(individuation_context, dict):
            for threshold in individuation_context.get("thresholdProcesses", [])[:3]:
                if context_item_count >= 3 or not isinstance(threshold, dict):
                    break
                threshold_id = self._optional_str(threshold.get("id"))
                label = self._optional_str(threshold.get("label"))
                summary = self._truncate_intake_text(
                    threshold.get("summary") or threshold.get("whatIsEnding"),
                    limit=180,
                )
                if not threshold_id or not label or not summary:
                    continue
                if self._add_intake_item(
                    items,
                    item={
                        "key": f"threshold_process:{threshold_id}",
                        "kind": "threshold_process",
                        "label": self._compact_page_text(label, max_length=60),
                        "summary": summary,
                        "sourceKind": "method_context",
                        "criteria": ["method_context_threshold_process"],
                        "entityRefs": {"entities": [threshold_id]},
                        "evidenceIds": [
                            str(value)
                            for value in threshold.get("evidenceIds", [])
                            if isinstance(value, str) and value
                        ],
                    },
                    seen_keys=seen_keys,
                ):
                    context_item_count += 1
            for scene in individuation_context.get("relationalScenes", [])[:3]:
                if context_item_count >= 3 or not isinstance(scene, dict):
                    break
                scene_id = self._optional_str(scene.get("id"))
                label = self._optional_str(scene.get("label"))
                summary = self._truncate_intake_text(
                    scene.get("sceneSummary") or scene.get("summary"),
                    limit=180,
                )
                if not scene_id or not label or not summary:
                    continue
                if self._add_intake_item(
                    items,
                    item={
                        "key": f"relational_scene:{scene_id}",
                        "kind": "relational_scene",
                        "label": self._compact_page_text(label, max_length=60),
                        "summary": summary,
                        "sourceKind": "method_context",
                        "criteria": ["method_context_relational_scene"],
                        "entityRefs": {"entities": [scene_id]},
                        "evidenceIds": [
                            str(value)
                            for value in scene.get("evidenceIds", [])
                            if isinstance(value, str) and value
                        ],
                    },
                    seen_keys=seen_keys,
                ):
                    context_item_count += 1

        if isinstance(living_myth_context, dict):
            symbolic_wellbeing = living_myth_context.get("latestSymbolicWellbeing")
            if context_item_count < 3 and isinstance(symbolic_wellbeing, dict):
                wellbeing_id = self._optional_str(symbolic_wellbeing.get("id"))
                label = self._optional_str(symbolic_wellbeing.get("label"))
                summary = self._truncate_intake_text(
                    symbolic_wellbeing.get("capacitySummary") or symbolic_wellbeing.get("summary"),
                    limit=180,
                )
                if (
                    wellbeing_id
                    and label
                    and summary
                    and self._add_intake_item(
                        items,
                        item={
                            "key": f"living_myth_wellbeing:{wellbeing_id}",
                            "kind": "living_myth_context",
                            "label": self._compact_page_text(label, max_length=60),
                            "summary": summary,
                            "sourceKind": "method_context",
                            "criteria": ["living_myth_symbolic_wellbeing"],
                            "entityRefs": {"entities": [wellbeing_id]},
                            "evidenceIds": [
                                str(value)
                                for value in symbolic_wellbeing.get("evidenceIds", [])
                                if isinstance(value, str) and value
                            ],
                        },
                        seen_keys=seen_keys,
                    )
                ):
                    context_item_count += 1
            current_life_chapter = living_myth_context.get("currentLifeChapter")
            if context_item_count < 3 and isinstance(current_life_chapter, dict):
                chapter_id = self._optional_str(current_life_chapter.get("id"))
                label = self._optional_str(
                    current_life_chapter.get("chapterLabel") or current_life_chapter.get("label")
                )
                summary = self._truncate_intake_text(
                    current_life_chapter.get("chapterSummary")
                    or current_life_chapter.get("summary"),
                    limit=180,
                )
                if (
                    chapter_id
                    and label
                    and summary
                    and self._add_intake_item(
                        items,
                        item={
                            "key": f"living_myth_chapter:{chapter_id}",
                            "kind": "living_myth_context",
                            "label": self._compact_page_text(label, max_length=60),
                            "summary": summary,
                            "sourceKind": "method_context",
                            "criteria": ["living_myth_current_chapter"],
                            "entityRefs": {"entities": [chapter_id]},
                            "evidenceIds": [
                                str(value)
                                for value in current_life_chapter.get("evidenceIds", [])
                                if isinstance(value, str) and value
                            ],
                        },
                        seen_keys=seen_keys,
                    )
                ):
                    context_item_count += 1
            for question in living_myth_context.get("activeMythicQuestions", [])[:3]:
                if context_item_count >= 3 or not isinstance(question, dict):
                    break
                question_id = self._optional_str(question.get("id"))
                label = self._optional_str(question.get("label"))
                summary = self._truncate_intake_text(
                    question.get("questionText") or question.get("summary"),
                    limit=180,
                )
                if not question_id or not label or not summary:
                    continue
                if self._add_intake_item(
                    items,
                    item={
                        "key": f"living_myth_question:{question_id}",
                        "kind": "living_myth_context",
                        "label": self._compact_page_text(label, max_length=60),
                        "summary": summary,
                        "sourceKind": "method_context",
                        "criteria": ["living_myth_active_question"],
                        "entityRefs": {"entities": [question_id]},
                        "evidenceIds": [
                            str(value)
                            for value in question.get("evidenceIds", [])
                            if isinstance(value, str) and value
                        ],
                    },
                    seen_keys=seen_keys,
                ):
                    context_item_count += 1
        return items

    def _build_intake_host_guidance(
        self,
        *,
        method_context: MethodContextSnapshot | None,
        item_count: int,
        warnings: list[str],
    ) -> IntakeHostGuidance:
        mention_recommendation = "acknowledge_only"
        followup_question_style = "none"
        max_questions = 1
        reasons = ["store_hold_first", "auto_interpretation_disabled"]
        method_state = (
            method_context.get("methodState")
            if isinstance((method_context or {}).get("methodState"), dict)
            else None
        )
        clarification_state = (
            method_context.get("clarificationState")
            if isinstance((method_context or {}).get("clarificationState"), dict)
            else None
        )
        coach_state = (
            method_context.get("coachState")
            if isinstance((method_context or {}).get("coachState"), dict)
            else None
        )
        if method_context is not None:
            reasons.append("method_context_available")
        grounding_recommendation = None
        if isinstance(method_state, dict):
            grounding = method_state.get("grounding")
            if isinstance(grounding, dict):
                grounding_recommendation = self._optional_str(grounding.get("recommendation"))
        if grounding_recommendation is None:
            individuation_context = (
                method_context.get("individuationContext")
                if isinstance((method_context or {}).get("individuationContext"), dict)
                else None
            )
            if isinstance(individuation_context, dict):
                reality_anchor = individuation_context.get("realityAnchors")
                if isinstance(reality_anchor, dict):
                    grounding_recommendation = self._optional_str(
                        reality_anchor.get("groundingRecommendation")
                    )
        if grounding_recommendation == "grounding_first" or (
            isinstance(coach_state, dict)
            and isinstance(coach_state.get("globalConstraints"), dict)
            and self._optional_str(coach_state["globalConstraints"].get("depthLevel"))
            == "grounding_only"
        ):
            mention_recommendation = "grounding_first_hold_context"
            followup_question_style = "grounding_orienting"
            reasons.append("grounding_first")
        elif isinstance(clarification_state, dict) and (
            clarification_state.get("pendingPrompts")
            or clarification_state.get("avoidRepeatQuestionKeys")
            or clarification_state.get("recentlyUnrouted")
        ):
            mention_recommendation = "ask_one_clarification_only_if_user_invites"
            followup_question_style = "clarify_before_depth"
            reasons.append("clarification_state_present")
        elif item_count > 0:
            mention_recommendation = "context_available_hold_first"
            followup_question_style = "single_gentle_question"
            reasons.append("context_items_available")
        questioning_preference = (
            method_state.get("questioningPreference")
            if isinstance(method_state, dict)
            and isinstance(method_state.get("questioningPreference"), dict)
            else None
        )
        if isinstance(questioning_preference, dict):
            preferred_styles = [
                str(item)
                for item in questioning_preference.get("preferredQuestionStyles", [])
                if isinstance(item, str) and item
            ]
            if (
                followup_question_style == "single_gentle_question"
                and "choice_based" in preferred_styles
            ):
                followup_question_style = "user_choice"
                reasons.append("questioning_preference_choice_based")
        if isinstance(coach_state, dict):
            global_constraints = (
                coach_state.get("globalConstraints")
                if isinstance(coach_state.get("globalConstraints"), dict)
                else None
            )
            if isinstance(global_constraints, dict):
                constrained_max_questions = global_constraints.get("maxQuestionsPerTurn")
                if isinstance(constrained_max_questions, int) and constrained_max_questions < 1:
                    max_questions = 0
                    followup_question_style = "none"
                    reasons.append("questions_blocked")
        if warnings:
            reasons.append("partial_context")
        return {
            "holdFirst": True,
            "allowAutoInterpretation": False,
            "maxQuestions": max_questions,
            "mentionRecommendation": cast(
                Literal[
                    "acknowledge_only",
                    "context_available_hold_first",
                    "grounding_first_hold_context",
                    "ask_one_clarification_only_if_user_invites",
                ],
                mention_recommendation,
            ),
            "followupQuestionStyle": cast(
                Literal[
                    "none",
                    "single_gentle_question",
                    "grounding_orienting",
                    "clarify_before_depth",
                    "user_choice",
                ],
                followup_question_style,
            ),
            "reasons": list(dict.fromkeys(reasons)),
        }

    def _aggregate_intake_entity_refs(
        self,
        items: list[IntakeContextItem],
    ) -> dict[str, list[Id]]:
        entity_refs: dict[str, list[Id]] = {}
        for item in items:
            for entity_type, ref_ids in item.get("entityRefs", {}).items():
                if not isinstance(ref_ids, list):
                    continue
                normalized_ids = [
                    str(value) for value in ref_ids if isinstance(value, str) and value
                ]
                if not normalized_ids:
                    continue
                entity_refs[entity_type] = self._merge_ids(
                    entity_refs.get(entity_type, []),
                    normalized_ids,
                )
        return entity_refs

    def _add_intake_item(
        self,
        items: list[IntakeContextItem],
        *,
        item: IntakeContextItem,
        seen_keys: set[str],
        max_items: int = 12,
    ) -> bool:
        if len(items) >= max_items or item["key"] in seen_keys:
            return False
        seen_keys.add(item["key"])
        items.append(item)
        return True

    def _truncate_intake_text(self, value: object, *, limit: int = 220) -> str | None:
        if value is None:
            return None
        text = " ".join(str(value).split())
        if not text:
            return None
        if len(text) <= limit:
            return text
        return text[: limit - 3].rstrip() + "..."

    async def _build_ephemeral_circulation_summary(
        self,
        *,
        user_id: Id,
        window_start: str,
        window_end: str,
        explicit_question: str | None = None,
        surface: Literal["alive_today", "journey_page"] = "alive_today",
    ) -> tuple[CirculationSummaryInput, CirculationSummaryResult]:
        bundle = await self._load_surface_context_bundle(
            user_id=user_id,
            window_start=window_start,
            window_end=window_end,
            include_dashboard=True,
            surface=surface,
            explicit_question=explicit_question,
        )
        summary_input = cast(CirculationSummaryInput, bundle["preparedPayload"])
        return summary_input, await self._core.generate_circulation_summary(summary_input)

    def _build_journey_alive_surface(
        self,
        summary: CirculationSummaryResult,
    ) -> JourneyAliveTodaySurface:
        return {
            "summaryId": summary["summaryId"],
            "title": "Alive today",
            "response": self._compact_page_text(summary["userFacingResponse"], max_length=480),
            "activeThemes": [str(item) for item in summary.get("activeThemes", [])][:5],
            "recurringSymbolIds": [
                item["id"] for item in summary.get("recurringSymbols", [])[:5] if item.get("id")
            ],
        }

    def _build_journey_weekly_surface(
        self,
        *,
        weekly_reviews: list[WeeklyReviewRecord],
        existing_briefs: list[ProactiveBriefRecord],
        due_seeds: list[dict[str, object]],
        window_start: str,
        window_end: str,
    ) -> JourneyWeeklySurface:
        for review in weekly_reviews:
            if self._same_iso_week(review.get("windowEnd"), window_end):
                return {
                    "kind": "latest_review",
                    "title": "Weekly reflection",
                    "summary": self._compact_page_text(
                        review.get("result", {}).get("userFacingResponse")
                        or "A weekly reflection is already available for this week.",
                        max_length=320,
                    ),
                    "reviewId": review["id"],
                    "windowStart": window_start,
                    "windowEnd": window_end,
                    "actions": [
                        self._journey_action(
                            label="Open review",
                            kind="entity",
                            entity_type="WeeklyReview",
                            entity_id=review["id"],
                            write_intent="read",
                            requires_explicit_user_action=True,
                        )
                    ],
                }
        for brief in existing_briefs:
            if brief.get("briefType") != "weekly" or brief.get("status") not in {
                "candidate",
                "shown",
            }:
                continue
            return {
                "kind": "review_invitation_active",
                "title": "Weekly reflection",
                "summary": self._compact_page_text(
                    brief.get("summary") or "A weekly reflection invitation is active.",
                    max_length=320,
                ),
                "briefId": brief["id"],
                "windowStart": window_start,
                "windowEnd": window_end,
                "actions": self._brief_actions(brief),
            }
        for seed in due_seeds:
            if str(seed.get("briefType") or "") != "weekly":
                continue
            return {
                "kind": "review_due",
                "title": "Weekly review is available",
                "summary": self._compact_page_text(
                    "A weekly reflection surface is available for this page.",
                    max_length=320,
                ),
                "windowStart": window_start,
                "windowEnd": window_end,
                "actions": [
                    self._journey_action(
                        label="Generate weekly review",
                        kind="tool",
                        operation="circulatio.review.weekly",
                        payload={"windowStart": window_start, "windowEnd": window_end},
                        write_intent="write",
                        requires_explicit_user_action=True,
                    )
                ],
            }
        return {
            "kind": "review_due",
            "title": "Weekly review is available",
            "summary": self._compact_page_text(
                "A weekly reflection surface is available for this page.",
                max_length=320,
            ),
            "windowStart": window_start,
            "windowEnd": window_end,
            "actions": [
                self._journey_action(
                    label="Generate weekly review",
                    kind="tool",
                    operation="circulatio.review.weekly",
                    payload={"windowStart": window_start, "windowEnd": window_end},
                    write_intent="write",
                    requires_explicit_user_action=True,
                )
            ],
        }

    def _build_journey_rhythmic_invitations(
        self,
        *,
        existing_briefs: list[ProactiveBriefRecord],
        due_seeds: list[dict[str, object]],
        max_invitations: int,
        window_start: str,
        window_end: str,
    ) -> list[JourneyInvitationPreview]:
        previews: list[JourneyInvitationPreview] = []
        represented_trigger_keys: set[str] = set()
        active_briefs = sorted(
            [
                brief
                for brief in existing_briefs
                if brief.get("briefType") != "weekly"
                and brief.get("status") in {"candidate", "shown"}
            ],
            key=lambda item: item.get("updatedAt", item.get("createdAt", "")),
            reverse=True,
        )
        for brief in active_briefs:
            trigger_key = self._optional_str(brief.get("triggerKey"))
            if trigger_key:
                represented_trigger_keys.add(trigger_key)
            previews.append(
                {
                    "kind": "active_brief",
                    "title": str(brief.get("title") or "Invitation"),
                    "summary": self._compact_page_text(
                        str(brief.get("summary") or ""),
                        max_length=280,
                    ),
                    "briefType": str(brief.get("briefType") or "daily"),
                    "briefId": brief["id"],
                    "triggerKey": trigger_key,
                    "status": str(brief.get("status") or ""),
                    "suggestedAction": self._optional_str(brief.get("suggestedAction")),
                    "relatedJourneyIds": list(brief.get("relatedJourneyIds", [])),
                    "relatedMaterialIds": list(brief.get("relatedMaterialIds", [])),
                    "relatedSymbolIds": list(brief.get("relatedSymbolIds", [])),
                    "relatedPracticeSessionIds": list(brief.get("relatedPracticeSessionIds", [])),
                    "actions": self._brief_actions(brief),
                }
            )
        for seed in due_seeds:
            if str(seed.get("briefType") or "") == "weekly":
                continue
            trigger_key = str(seed.get("triggerKey") or "")
            if trigger_key in represented_trigger_keys:
                continue
            represented_trigger_keys.add(trigger_key)
            previews.append(
                {
                    "kind": "due_seed_preview",
                    "title": str(seed.get("titleHint") or "Invitation"),
                    "summary": self._compact_page_text(
                        str(seed.get("summaryHint") or "A gentle invitation is available."),
                        max_length=280,
                    ),
                    "briefType": str(seed.get("briefType") or "daily"),
                    "triggerKey": trigger_key,
                    "suggestedAction": self._optional_str(seed.get("suggestedActionHint")),
                    "relatedJourneyIds": list(seed.get("relatedJourneyIds", [])),
                    "relatedMaterialIds": list(seed.get("relatedMaterialIds", [])),
                    "relatedSymbolIds": list(seed.get("relatedSymbolIds", [])),
                    "relatedPracticeSessionIds": list(seed.get("relatedPracticeSessionIds", [])),
                    "actions": [
                        self._journey_action(
                            label="Create invitation card",
                            kind="tool",
                            operation="circulatio.briefs.generate",
                            payload={
                                "source": "manual",
                                "limit": 1,
                                "windowStart": window_start,
                                "windowEnd": window_end,
                            },
                            write_intent="write",
                            requires_explicit_user_action=True,
                        )
                    ],
                }
            )
        return previews[:max_invitations]

    def _build_journey_practice_container(
        self,
        *,
        recent_practices: list[PracticeSessionRecord],
        practice_suggestion: PracticePlan | None,
        window_start: str,
        window_end: str,
        now: str,
    ) -> JourneyPracticeContainer:
        now_dt = self._parse_datetime(now)
        due_practices = sorted(
            [
                practice
                for practice in recent_practices
                if practice.get("status") in {"recommended", "accepted"}
                and practice.get("nextFollowUpDueAt")
                and self._parse_datetime(practice["nextFollowUpDueAt"]) <= now_dt
            ],
            key=lambda item: (
                item.get("nextFollowUpDueAt", ""),
                item.get("updatedAt", item.get("createdAt", "")),
            ),
            reverse=True,
        )
        if due_practices:
            practice = due_practices[0]
            actions = [
                self._journey_action(
                    label="Open practice card",
                    kind="entity",
                    entity_type="PracticeSession",
                    entity_id=practice["id"],
                    write_intent="read",
                    requires_explicit_user_action=True,
                )
            ]
            if practice.get("status") == "recommended":
                actions.extend(self._practice_response_actions(practice["id"]))
            return {
                "kind": "practice_follow_up",
                "title": "Practice follow-up",
                "summary": self._compact_page_text(
                    str(practice.get("followUpPrompt") or practice.get("reason") or ""),
                    max_length=320,
                ),
                "practiceSessionId": practice["id"],
                "status": str(practice.get("status") or ""),
                "actions": actions,
            }
        recommended = sorted(
            [practice for practice in recent_practices if practice.get("status") == "recommended"],
            key=lambda item: item.get("updatedAt", item.get("createdAt", "")),
            reverse=True,
        )
        if recommended:
            practice = recommended[0]
            return {
                "kind": "recommended_session",
                "title": "Practice",
                "summary": self._compact_page_text(
                    self._practice_summary(practice),
                    max_length=320,
                ),
                "practiceSessionId": practice["id"],
                "status": str(practice.get("status") or ""),
                "actions": self._practice_response_actions(practice["id"]),
            }
        if practice_suggestion:
            return {
                "kind": "suggested_container",
                "title": "Practice",
                "summary": self._compact_page_text(
                    self._practice_plan_summary(practice_suggestion),
                    max_length=320,
                ),
                "practiceRecommendation": deepcopy(practice_suggestion),
                "actions": [
                    self._journey_action(
                        label="Create practice card",
                        kind="tool",
                        operation="circulatio.practice.generate",
                        payload={
                            "windowStart": window_start,
                            "windowEnd": window_end,
                            "trigger": {
                                "triggerType": "manual",
                                "reason": "journey_page",
                            },
                        },
                        write_intent="write",
                        requires_explicit_user_action=True,
                    )
                ],
            }
        return {
            "kind": "quiet",
            "title": "Practice",
            "summary": "No practice container is open for this page.",
            "actions": [],
        }

    def _build_journey_analysis_packet_preview(
        self,
        *,
        summary: CirculationSummaryResult,
        summary_input: CirculationSummaryInput,
        recent_practices: list[PracticeSessionRecord],
        window_start: str,
        window_end: str,
    ) -> JourneyAnalysisPacketPreview:
        sections: list[JourneyAnalysisPacketSection] = []
        symbols = summary.get("recurringSymbols", [])[:5]
        if symbols:
            sections.append(
                {
                    "sectionType": "symbol_field",
                    "title": "Symbol field",
                    "items": [
                        {
                            "label": str(item.get("canonicalName") or item.get("id") or "symbol"),
                            "summary": self._compact_page_text(
                                f"{item.get('category', 'symbol')} field",
                                max_length=160,
                            ),
                            "entityType": "symbol",
                            "entityId": item.get("id"),
                            "source": "alive_today",
                        }
                        for item in symbols
                    ],
                }
            )
        life_links = summary.get("notableLifeContextLinks", [])[:5]
        if life_links:
            sections.append(
                {
                    "sectionType": "life_context",
                    "title": "Life context",
                    "items": [
                        {
                            "label": str(
                                item.get("stateSnapshotField")
                                or item.get("lifeEventRefId")
                                or "Life context"
                            ),
                            "summary": self._compact_page_text(
                                str(item.get("summary") or ""),
                                max_length=220,
                            ),
                            "source": "alive_today",
                        }
                        for item in life_links
                    ],
                }
            )
        method_context = summary_input.get("methodContextSnapshot") or {}
        method_items: list[JourneyAnalysisPacketItem] = []
        conscious_attitude = method_context.get("consciousAttitude")
        if isinstance(conscious_attitude, dict) and conscious_attitude.get("stanceSummary"):
            method_items.append(
                {
                    "label": "Conscious attitude",
                    "summary": self._compact_page_text(
                        str(conscious_attitude.get("stanceSummary") or ""),
                        max_length=220,
                    ),
                    "entityType": "ConsciousAttitude",
                    "entityId": conscious_attitude.get("id"),
                    "source": "method_context",
                }
            )
        for body_state in method_context.get("recentBodyStates", [])[:2]:
            label = str(body_state.get("sensation") or "Body state")
            region = self._optional_str(body_state.get("bodyRegion"))
            if region:
                label = f"{label} ({region})"
            method_items.append(
                {
                    "label": label,
                    "summary": self._compact_page_text(
                        str(body_state.get("activation") or ""),
                        max_length=160,
                    ),
                    "entityType": "BodyState",
                    "entityId": body_state.get("id"),
                    "source": "method_context",
                }
            )
        for goal in method_context.get("activeGoals", [])[:2]:
            method_items.append(
                {
                    "label": str(goal.get("label") or "Goal"),
                    "summary": self._compact_page_text(
                        str(goal.get("description") or goal.get("status") or ""),
                        max_length=160,
                    ),
                    "entityType": "Goal",
                    "entityId": goal.get("id"),
                    "source": "method_context",
                }
            )
        for series in method_context.get("activeDreamSeries", [])[:1]:
            method_items.append(
                {
                    "label": str(series.get("label") or "Dream series"),
                    "summary": self._compact_page_text(
                        str(series.get("progressionSummary") or series.get("status") or ""),
                        max_length=160,
                    ),
                    "entityType": "DreamSeries",
                    "entityId": series.get("id"),
                    "source": "method_context",
                }
            )
        if method_items:
            sections.append(
                {
                    "sectionType": "method_context",
                    "title": "Method context",
                    "items": method_items[:5],
                }
            )
        thread_digests = [
            item
            for item in summary_input.get("threadDigests", [])
            if isinstance(item, dict) and self._optional_str(item.get("threadKey"))
        ]
        if thread_digests:
            sections.append(
                {
                    "sectionType": "journey_threads",
                    "title": "Live threads",
                    "items": [
                        {
                            "label": self._thread_digest_label(cast(ThreadDigest, item)),
                            "summary": self._compact_page_text(
                                str(item.get("summary") or ""),
                                max_length=220,
                            ),
                            "entityType": str(item.get("kind") or "Thread")
                            .replace("_", " ")
                            .title(),
                            "entityId": (
                                item.get("sourceRecordRefs", [{}])[0].get("recordId")
                                if isinstance(item.get("sourceRecordRefs"), list)
                                and item.get("sourceRecordRefs")
                                and isinstance(item["sourceRecordRefs"][0], dict)
                                else None
                            ),
                            "source": "thread_digest",
                        }
                        for item in thread_digests[:5]
                    ],
                }
            )
        practice_items = []
        for practice in recent_practices[:5]:
            practice_items.append(
                {
                    "label": self._practice_label(practice),
                    "summary": self._compact_page_text(
                        str(
                            practice.get("outcome")
                            or practice.get("followUpPrompt")
                            or practice.get("reason")
                            or ""
                        ),
                        max_length=220,
                    ),
                    "entityType": "PracticeSession",
                    "entityId": practice.get("id"),
                    "source": "practice",
                }
            )
        if practice_items:
            sections.append(
                {
                    "sectionType": "practice_context",
                    "title": "Practice context",
                    "items": practice_items[:5],
                }
            )
        return {
            "status": "preview",
            "bounded": True,
            "windowStart": window_start,
            "windowEnd": window_end,
            "sections": sections[:5],
        }

    def _journey_card(
        self,
        *,
        section: str,
        title: str,
        body: str,
        actions: list[JourneyPageAction],
        status: str | None = None,
        entity_refs: dict[str, list[Id]] | None = None,
        payload: dict[str, object] | None = None,
    ) -> JourneyPageCard:
        card: JourneyPageCard = {
            "id": create_id("journey_card"),
            "section": section,  # type: ignore[typeddict-item]
            "title": title,
            "body": self._compact_page_text(body, max_length=480),
            "actions": deepcopy(actions),
        }
        if status:
            card["status"] = status
        if entity_refs:
            card["entityRefs"] = deepcopy(entity_refs)
        if payload:
            card["payload"] = deepcopy(payload)
        return card

    def _journey_action(
        self,
        *,
        label: str,
        kind: str,
        write_intent: str,
        requires_explicit_user_action: bool,
        operation: str | None = None,
        command: str | None = None,
        payload: dict[str, object] | None = None,
        entity_type: str | None = None,
        entity_id: Id | None = None,
    ) -> JourneyPageAction:
        action: JourneyPageAction = {
            "label": label,
            "kind": kind,  # type: ignore[typeddict-item]
            "writeIntent": write_intent,  # type: ignore[typeddict-item]
            "requiresExplicitUserAction": requires_explicit_user_action,
        }
        if operation:
            action["operation"] = operation
        if command:
            action["command"] = command
        if payload:
            action["payload"] = deepcopy(payload)
        if entity_type:
            action["entityType"] = entity_type
        if entity_id:
            action["entityId"] = entity_id
        return action

    def _render_journey_page_fallback(
        self,
        *,
        cards: list[JourneyPageCard],
        window_start: str,
        window_end: str,
    ) -> str:
        lines = ["Journey page", f"Window: {window_start} -> {window_end}"]
        for card in cards:
            lines.append("")
            lines.append(f"{card['title']}:")
            if card["section"] == "rhythmic_invitations":
                lines.append(card["body"])
            else:
                lines.append(self._compact_page_text(card["body"], max_length=320))
            action_labels = [action["label"] for action in card.get("actions", [])[:3]]
            if action_labels:
                lines.append("Actions: " + ", ".join(action_labels))
        return "\n".join(lines)

    def _render_invitation_body(
        self,
        invitations: list[JourneyInvitationPreview],
    ) -> str:
        if not invitations:
            return "No rhythmic invitation surface is open for this page."
        return "\n".join(
            f"- {item['title']}: {self._compact_page_text(item['summary'], max_length=180)}"
            for item in invitations[:3]
        )

    def _card_actions_from_invitations(
        self,
        invitations: list[JourneyInvitationPreview],
    ) -> list[JourneyPageAction]:
        actions: list[JourneyPageAction] = []
        seen: set[tuple[str, str]] = set()
        for invitation in invitations:
            for action in invitation.get("actions", []):
                key = (
                    str(action.get("label") or ""),
                    str(action.get("entityId") or action.get("operation") or ""),
                )
                if key in seen:
                    continue
                seen.add(key)
                actions.append(deepcopy(action))
        return actions[:6]

    def _render_analysis_preview_body(
        self,
        preview: JourneyAnalysisPacketPreview,
    ) -> str:
        titles = [section["title"].lower() for section in preview.get("sections", [])]
        if not titles:
            return "A bounded analysis preview is quiet for this page."
        return "Existing " + ", ".join(titles) + " are available as a bounded preview."

    def _practice_response_actions(self, practice_session_id: Id) -> list[JourneyPageAction]:
        return [
            self._journey_action(
                label="Accept",
                kind="tool",
                operation="circulatio.practice.respond",
                payload={"practiceSessionId": practice_session_id, "action": "accepted"},
                write_intent="write",
                requires_explicit_user_action=True,
            ),
            self._journey_action(
                label="Skip",
                kind="tool",
                operation="circulatio.practice.respond",
                payload={"practiceSessionId": practice_session_id, "action": "skipped"},
                write_intent="write",
                requires_explicit_user_action=True,
            ),
        ]

    def _brief_actions(self, brief: ProactiveBriefRecord) -> list[JourneyPageAction]:
        actions: list[JourneyPageAction] = []
        brief_id = brief["id"]
        if brief.get("status") == "candidate":
            actions.append(
                self._journey_action(
                    label="Show",
                    kind="tool",
                    operation="circulatio.briefs.respond",
                    payload={"briefId": brief_id, "action": "shown"},
                    write_intent="write",
                    requires_explicit_user_action=True,
                )
            )
        actions.append(
            self._journey_action(
                label="Dismiss",
                kind="tool",
                operation="circulatio.briefs.respond",
                payload={"briefId": brief_id, "action": "dismissed"},
                write_intent="write",
                requires_explicit_user_action=True,
            )
        )
        actions.append(
            self._journey_action(
                label="Mark done",
                kind="tool",
                operation="circulatio.briefs.respond",
                payload={"briefId": brief_id, "action": "acted_on"},
                write_intent="write",
                requires_explicit_user_action=True,
            )
        )
        return actions

    def _practice_summary(self, practice: PracticeSessionRecord) -> str:
        duration = practice.get("durationMinutes")
        prefix = self._practice_label(practice)
        if duration:
            prefix = f"{prefix}, {duration} min"
        reason = self._optional_str(practice.get("reason")) or "A practice card is available."
        return f"{prefix}. {reason}"

    def _practice_plan_summary(self, practice: PracticePlan) -> str:
        duration = practice.get("durationMinutes")
        prefix = str(practice.get("type") or "practice").replace("_", " ").title()
        if duration:
            prefix = f"{prefix}, {duration} min"
        reason = self._optional_str(practice.get("reason")) or "A practice container is available."
        return f"{prefix}. {reason}"

    def _practice_label(self, practice: PracticeSessionRecord) -> str:
        return str(practice.get("practiceType") or "practice").replace("_", " ").title()

    def _compact_page_text(self, value: object, *, max_length: int) -> str:
        text = " ".join(str(value or "").split())
        if len(text) <= max_length:
            return text
        return text[: max_length - 3].rstrip() + "..."

    def _same_iso_week(self, left: object | None, right: object | None) -> bool:
        if left is None or right is None:
            return False
        left_week = self._parse_datetime(str(left)).isocalendar()[:2]
        right_week = self._parse_datetime(str(right)).isocalendar()[:2]
        return left_week == right_week

    def _optional_str(self, value: object | None) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def _validate_cultural_frame_type(self, value: object | None) -> str:
        frame_type = self._optional_str(value) or "chosen"
        if frame_type not in {"alchemical", "mythic", "religious", "literary", "family", "chosen"}:
            raise ValidationError(f"Unsupported cultural frame type: {frame_type}")
        return frame_type

    def _validate_cultural_frame_status(self, value: object | None) -> str:
        status = self._optional_str(value) or "enabled"
        if status not in {"enabled", "disabled", "deleted"}:
            raise ValidationError(f"Unsupported cultural frame status: {status}")
        return status

    def _normalize_cultural_frame_use_list(self, value: object | None) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValidationError("Cultural frame uses must be a list of strings.")
        return list(dict.fromkeys(str(item).strip() for item in value if str(item).strip()))

    async def _ensure_clarification_prompt_for_run(
        self,
        *,
        user_id: Id,
        material: MaterialRecord,
        run_id: Id,
        interpretation: InterpretationResult,
    ) -> list[ClarificationPromptRecord]:
        plan = interpretation.get("clarificationPlan")
        if not isinstance(plan, dict):
            return []
        question_text = self._optional_str(plan.get("questionText"))
        if not question_text:
            return []
        question_key = self._optional_str(
            plan.get("questionKey")
        ) or self._clarification_question_key(question_text)
        existing = await self._repository.list_clarification_prompts(
            user_id,
            run_id=run_id,
            limit=20,
        )
        for item in existing:
            if question_key and item.get("questionKey") == question_key:
                return [item]
            if item.get("questionText") == question_text and item.get("status") == "pending":
                return [item]
        if question_key:
            recent_prompts = await self._repository.list_clarification_prompts(
                user_id,
                limit=50,
            )
            for item in recent_prompts:
                if item.get("status") == "deleted":
                    continue
                if item.get("questionKey") != question_key:
                    continue
                existing_material_id = self._optional_str(item.get("materialId"))
                if existing_material_id not in {None, material["id"]}:
                    continue
                if item.get("status") == "pending":
                    return [item]
                return []
        timestamp = now_iso()
        routing_hints = (
            deepcopy(plan.get("routingHints")) if isinstance(plan.get("routingHints"), dict) else {}
        )
        anchor_refs = plan.get("anchorRefs")
        if isinstance(anchor_refs, dict) and anchor_refs:
            routing_hints["anchorRefs"] = deepcopy(anchor_refs)
        record: ClarificationPromptRecord = {
            "id": create_id("clarification_prompt"),
            "userId": user_id,
            "materialId": material["id"],
            "runId": run_id,
            "questionText": question_text,
            "questionKey": question_key,
            "intent": str(plan.get("intent") or "other"),
            "captureTarget": str(plan.get("captureTarget") or "answer_only"),
            "expectedAnswerKind": str(plan.get("expectedAnswerKind") or "free_text"),
            "status": "pending",
            "privacyClass": str(material.get("privacyClass") or "session_only"),
            "createdAt": timestamp,
            "updatedAt": timestamp,
        }
        if isinstance(plan.get("answerSlots"), dict) and plan["answerSlots"]:
            record["answerSlots"] = deepcopy(plan["answerSlots"])
        if routing_hints:
            record["routingHints"] = routing_hints
        supporting_refs = [
            str(item) for item in plan.get("supportingRefs", []) if str(item).strip()
        ]
        if supporting_refs:
            record["supportingRefs"] = supporting_refs[:8]
        created = await self._repository.create_clarification_prompt(record)
        await self._record_adaptation_signal(
            user_id=user_id,
            event_type="clarification_prompt_created",
            signals={
                "intent": created["intent"],
                "captureTarget": created["captureTarget"],
                "expectedAnswerKind": created["expectedAnswerKind"],
            },
        )
        return [created]

    async def _clarification_window(
        self,
        *,
        user_id: Id,
        prompt: ClarificationPromptRecord | None,
        answer: ClarificationAnswerRecord,
    ) -> tuple[str, str]:
        run_id = self._optional_str(answer.get("runId")) or (
            self._optional_str(prompt.get("runId")) if prompt else None
        )
        if run_id:
            run = await self._repository.get_interpretation_run(user_id, run_id)
            snapshot_id = self._optional_str(run.get("inputSnapshotId"))
            if snapshot_id:
                snapshot = await self._repository.get_context_snapshot(user_id, snapshot_id)
                return (
                    str(snapshot.get("windowStart") or snapshot.get("createdAt") or now_iso()),
                    str(snapshot.get("windowEnd") or snapshot.get("createdAt") or now_iso()),
                )
        material_id = self._optional_str(answer.get("materialId")) or (
            self._optional_str(prompt.get("materialId")) if prompt else None
        )
        anchor = None
        if material_id:
            material = await self._repository.get_material(user_id, material_id)
            anchor = str(material.get("materialDate") or material.get("createdAt") or now_iso())
        return self._resolve_window(anchor=anchor)

    async def _route_clarification_answer(
        self,
        *,
        user_id: Id,
        prompt: ClarificationPromptRecord | None,
        answer: ClarificationAnswerRecord,
        capture_target: ClarificationCaptureTarget,
        payload: dict[str, object],
    ) -> tuple[list[dict[str, str]], dict[str, object]]:
        routed_record: dict[str, object]
        record_type: str
        material_id = self._optional_str(answer.get("materialId")) or (
            self._optional_str(prompt.get("materialId")) if prompt else None
        )
        run_id = self._optional_str(answer.get("runId")) or (
            self._optional_str(prompt.get("runId")) if prompt else None
        )
        routing_hints = (
            deepcopy(prompt.get("routingHints"))
            if prompt is not None and isinstance(prompt.get("routingHints"), dict)
            else {}
        )
        if capture_target == "body_state":
            sensation = self._optional_str(payload.get("sensation"))
            if not sensation:
                raise ValidationError("Body-state clarification answers require payload.sensation.")
            result = await self.store_body_state(
                {
                    "userId": user_id,
                    "sensation": sensation,
                    "observedAt": self._optional_str(payload.get("observedAt")) or now_iso(),
                    "bodyRegion": self._optional_str(payload.get("bodyRegion")),
                    "activation": payload.get("activation"),
                    "tone": self._optional_str(payload.get("tone")),
                    "temporalContext": self._optional_str(payload.get("temporalContext")),
                    "linkedGoalIds": list(payload.get("linkedGoalIds", [])),
                    "linkedMaterialIds": [material_id] if material_id else [],
                    "privacyClass": answer.get("privacyClass", "session_only"),
                    "evidenceIds": [],
                }
            )
            routed_record = result["bodyState"]
            record_type = "BodyState"
        elif capture_target == "conscious_attitude":
            stance_summary = self._optional_str(payload.get("stanceSummary"))
            if not stance_summary:
                raise ValidationError(
                    "Conscious-attitude clarification answers require payload.stanceSummary."
                )
            window_start, window_end = await self._clarification_window(
                user_id=user_id,
                prompt=prompt,
                answer=answer,
            )
            routed_record = await self.capture_conscious_attitude(
                {
                    "userId": user_id,
                    "windowStart": window_start,
                    "windowEnd": window_end,
                    "stanceSummary": stance_summary,
                    "activeValues": list(payload.get("activeValues", [])),
                    "activeConflicts": list(payload.get("activeConflicts", [])),
                    "avoidedThemes": list(payload.get("avoidedThemes", [])),
                    "emotionalTone": self._optional_str(payload.get("emotionalTone")),
                    "egoPosition": self._optional_str(payload.get("egoPosition")),
                    "confidence": self._optional_str(payload.get("confidence")) or "medium",
                    "relatedMaterialIds": [material_id] if material_id else [],
                    "relatedGoalIds": list(payload.get("relatedGoalIds", [])),
                    "privacyClass": answer.get("privacyClass", "session_only"),
                    "source": "reflection",
                    "status": "candidate",
                    "evidenceIds": [],
                }
            )
            record_type = "ConsciousAttitudeSnapshot"
        elif capture_target == "personal_amplification":
            canonical_name = self._optional_str(payload.get("canonicalName")) or self._optional_str(
                routing_hints.get("canonicalName")
            )
            surface_text = self._optional_str(payload.get("surfaceText")) or self._optional_str(
                routing_hints.get("surfaceText")
            )
            if not canonical_name or not surface_text:
                raise ValidationError(
                    "Personal amplification clarification answers require "
                    "canonicalName and surfaceText."
                )
            routed_record = await self.answer_amplification_prompt(
                {
                    "userId": user_id,
                    "promptId": self._optional_str(routing_hints.get("amplificationPromptId")),
                    "materialId": material_id,
                    "runId": run_id,
                    "symbolId": self._optional_str(payload.get("symbolId"))
                    or self._optional_str(routing_hints.get("symbolId")),
                    "canonicalName": canonical_name,
                    "surfaceText": surface_text,
                    "associationText": self._optional_str(payload.get("associationText"))
                    or answer["answerText"],
                    "feelingTone": self._optional_str(payload.get("feelingTone")),
                    "bodySensations": list(payload.get("bodySensations", [])),
                    "memoryRefs": list(payload.get("memoryRefs", [])),
                    "privacyClass": answer.get("privacyClass", "user_private"),
                    "evidenceIds": [],
                }
            )
            record_type = "PersonalAmplification"
        elif capture_target == "consent_preference":
            scope = self._optional_str(payload.get("scope"))
            status = self._optional_str(payload.get("status"))
            if not scope or not status:
                raise ValidationError("Consent clarification answers require scope and status.")
            routed_record = await self.set_consent_preference(
                {
                    "userId": user_id,
                    "scope": scope,
                    "status": status,
                    "note": self._optional_str(payload.get("note")) or answer["answerText"],
                    "source": "clarification_answer",
                }
            )
            record_type = "ConsentPreference"
        elif capture_target == "goal":
            label = self._optional_str(payload.get("label"))
            if not label:
                raise ValidationError("Goal clarification answers require payload.label.")
            routed_record = await self.upsert_goal(
                {
                    "userId": user_id,
                    "goalId": self._optional_str(payload.get("goalId")),
                    "label": label,
                    "description": self._optional_str(payload.get("description")),
                    "status": self._optional_str(payload.get("status")) or "active",
                    "valueTags": list(payload.get("valueTags", [])),
                    "linkedMaterialIds": [material_id] if material_id else [],
                    "linkedSymbolIds": list(payload.get("linkedSymbolIds", [])),
                    "evidenceIds": [],
                }
            )
            record_type = "Goal"
        elif capture_target == "goal_tension":
            tension_summary = self._optional_str(payload.get("tensionSummary"))
            goal_ids = list(payload.get("goalIds", []))
            if not tension_summary or not goal_ids:
                raise ValidationError(
                    "Goal-tension clarification answers require tensionSummary and goalIds."
                )
            routed_record = await self.upsert_goal_tension(
                {
                    "userId": user_id,
                    "tensionId": self._optional_str(payload.get("tensionId")),
                    "goalIds": goal_ids,
                    "tensionSummary": tension_summary,
                    "polarityLabels": list(payload.get("polarityLabels", [])),
                    "status": self._optional_str(payload.get("status")) or "candidate",
                    "evidenceIds": [],
                }
            )
            record_type = "GoalTension"
        elif capture_target == "reality_anchors":
            routed_record = await self.capture_reality_anchors(
                {
                    "userId": user_id,
                    **deepcopy(payload),
                    "relatedMaterialIds": self._merge_ids(
                        list(payload.get("relatedMaterialIds", [])),
                        [material_id] if material_id else [],
                    ),
                    "privacyClass": answer.get("privacyClass", "user_private"),
                    "evidenceIds": [],
                }
            )
            record_type = "RealityAnchorSummary"
        elif capture_target == "threshold_process":
            routed_record = await self.upsert_threshold_process(
                {
                    "userId": user_id,
                    **deepcopy(payload),
                    "relatedMaterialIds": self._merge_ids(
                        list(payload.get("relatedMaterialIds", [])),
                        [material_id] if material_id else [],
                    ),
                    "privacyClass": answer.get("privacyClass", "user_private"),
                    "evidenceIds": [],
                }
            )
            record_type = "ThresholdProcess"
        elif capture_target == "relational_scene":
            routed_record = await self.record_relational_scene(
                {
                    "userId": user_id,
                    **deepcopy(payload),
                    "relatedMaterialIds": self._merge_ids(
                        list(payload.get("relatedMaterialIds", [])),
                        [material_id] if material_id else [],
                    ),
                    "privacyClass": answer.get("privacyClass", "user_private"),
                    "evidenceIds": [],
                }
            )
            record_type = "RelationalScene"
        elif capture_target == "inner_outer_correspondence":
            routed_record = await self.record_inner_outer_correspondence(
                {
                    "userId": user_id,
                    **deepcopy(payload),
                    "privacyClass": answer.get("privacyClass", "user_private"),
                    "evidenceIds": [],
                }
            )
            record_type = "InnerOuterCorrespondence"
        elif capture_target == "numinous_encounter":
            routed_record = await self.record_numinous_encounter(
                {
                    "userId": user_id,
                    **deepcopy(payload),
                    "relatedMaterialIds": self._merge_ids(
                        list(payload.get("relatedMaterialIds", [])),
                        [material_id] if material_id else [],
                    ),
                    "privacyClass": answer.get("privacyClass", "user_private"),
                    "evidenceIds": [],
                }
            )
            record_type = "NuminousEncounter"
        elif capture_target == "aesthetic_resonance":
            routed_record = await self.record_aesthetic_resonance(
                {
                    "userId": user_id,
                    **deepcopy(payload),
                    "relatedMaterialIds": self._merge_ids(
                        list(payload.get("relatedMaterialIds", [])),
                        [material_id] if material_id else [],
                    ),
                    "privacyClass": answer.get("privacyClass", "user_private"),
                    "evidenceIds": [],
                }
            )
            record_type = "AestheticResonance"
        elif capture_target == "interpretation_preference":
            preferences = {
                key: deepcopy(payload[key])
                for key in ("depthPreference", "modalityBias")
                if key in payload
            }
            if not preferences:
                raise ValidationError(
                    "Interpretation-preference clarification answers require depthPreference "
                    "or modalityBias."
                )
            routed_record = await self.set_adaptation_preferences(
                user_id=user_id,
                scope="interpretation",
                preferences=preferences,
            )
            record_type = "AdaptationProfile"
        elif capture_target == "typology_feedback":
            routed_record = await self._store_typology_feedback_record(
                user_id=user_id,
                payload=payload,
                material_id=material_id,
            )
            record_type = "TypologyLens"
        else:
            raise ValidationError(f"Clarification target '{capture_target}' is not routable yet.")
        return ([{"recordType": record_type, "id": str(routed_record["id"])}], routed_record)

    def _clarification_method_state_targets(
        self, capture_target: ClarificationCaptureTarget
    ) -> list[MethodStateCaptureTargetKind]:
        mapping: dict[ClarificationCaptureTarget, MethodStateCaptureTargetKind] = {
            "body_state": "body_state",
            "conscious_attitude": "conscious_attitude",
            "goal": "goal",
            "goal_tension": "goal_tension",
            "personal_amplification": "personal_amplification",
            "reality_anchors": "reality_anchors",
            "threshold_process": "threshold_process",
            "relational_scene": "relational_scene",
            "inner_outer_correspondence": "inner_outer_correspondence",
            "numinous_encounter": "numinous_encounter",
            "aesthetic_resonance": "aesthetic_resonance",
            "consent_preference": "consent_preference",
            "typology_feedback": "typology_lens",
        }
        target = mapping.get(capture_target)
        return [target] if target is not None else []

    async def _clarification_method_state_anchor_refs(
        self,
        *,
        user_id: Id,
        prompt: ClarificationPromptRecord | None,
        answer: ClarificationAnswerRecord,
    ) -> dict[str, object]:
        anchor_refs: dict[str, object] = {}
        routing_hints = (
            deepcopy(prompt.get("routingHints"))
            if prompt is not None and isinstance(prompt.get("routingHints"), dict)
            else {}
        )
        hinted_anchor_refs = routing_hints.get("anchorRefs")
        if isinstance(hinted_anchor_refs, dict):
            anchor_refs.update(deepcopy(hinted_anchor_refs))
        material_id = self._optional_str(answer.get("materialId")) or (
            self._optional_str(prompt.get("materialId")) if prompt else None
        )
        if material_id and "materialId" not in anchor_refs:
            anchor_refs["materialId"] = material_id
        run_id = self._optional_str(answer.get("runId")) or (
            self._optional_str(prompt.get("runId")) if prompt else None
        )
        if run_id and "runId" not in anchor_refs:
            anchor_refs["runId"] = run_id
        if run_id and "clarificationRefKey" not in anchor_refs:
            try:
                run = await self._repository.get_interpretation_run(user_id, run_id)
            except EntityNotFoundError:
                run = None
            intent = (
                run.get("result", {}).get("clarificationIntent") if isinstance(run, dict) else None
            )
            if isinstance(intent, dict):
                ref_key = self._optional_str(intent.get("refKey"))
                if ref_key:
                    anchor_refs["clarificationRefKey"] = ref_key
        return anchor_refs

    async def _clarification_routed_record_from_entity_ref(
        self,
        *,
        user_id: Id,
        entity_type: str,
        entity_id: Id,
    ) -> dict[str, object] | None:
        try:
            if entity_type == "PersonalAmplification":
                return await self._repository.get_personal_amplification(user_id, entity_id)
            if entity_type == "BodyState":
                return await self._repository.get_body_state(user_id, entity_id)
            if entity_type == "ConsciousAttitude":
                return await self._repository.get_conscious_attitude_snapshot(user_id, entity_id)
            if entity_type == "Goal":
                return await self._repository.get_goal(user_id, entity_id)
            if entity_type == "GoalTension":
                return await self._repository.get_goal_tension(user_id, entity_id)
            if entity_type == "PracticeSession":
                return await self._repository.get_practice_session(user_id, entity_id)
            if entity_type == "ConsentPreference":
                preferences = await self._repository.list_consent_preferences(user_id, limit=50)
                return next(
                    (
                        item
                        for item in preferences
                        if str(item.get("id") or "").strip() == entity_id
                    ),
                    None,
                )
            if entity_type in {
                "RealityAnchorSummary",
                "ThresholdProcess",
                "RelationalScene",
                "InnerOuterCorrespondence",
                "NuminousEncounter",
                "AestheticResonance",
            }:
                return await self._repository.get_individuation_record(user_id, entity_id)
            if entity_type == "TypologyLens":
                return await self._repository.get_typology_lens(user_id, entity_id)
            if entity_type == "DreamEntry":
                return await self._repository.get_material(user_id, entity_id)
            if entity_type == "AdaptationProfile":
                profile = await self._repository.get_adaptation_profile(user_id)
                if isinstance(profile, dict) and str(profile.get("id") or "").strip() == entity_id:
                    return profile
        except EntityNotFoundError:
            return None
        return None

    async def _route_clarification_answer_from_text(
        self,
        *,
        user_id: Id,
        prompt: ClarificationPromptRecord | None,
        answer: ClarificationAnswerRecord,
        capture_target: ClarificationCaptureTarget,
    ) -> tuple[list[dict[str, str]], dict[str, object] | None, list[str]] | None:
        if self._method_state_llm is None:
            return None
        expected_targets = self._clarification_method_state_targets(capture_target)
        if not expected_targets:
            return None
        anchor_refs = await self._clarification_method_state_anchor_refs(
            user_id=user_id,
            prompt=prompt,
            answer=answer,
        )
        if not self._method_state_has_anchor(anchor_refs):
            return None
        try:
            workflow = await self.process_method_state_response(
                {
                    "userId": user_id,
                    "idempotencyKey": f"clarification_answer:{answer['id']}",
                    "source": "clarifying_answer",
                    "responseText": answer["answerText"],
                    "observedAt": str(
                        answer.get("updatedAt") or answer.get("createdAt") or now_iso()
                    ),
                    "anchorRefs": anchor_refs,
                    "expectedTargets": expected_targets,
                    "privacyClass": answer.get("privacyClass", "session_only"),
                }
            )
        except ValidationError as exc:
            return ([], None, [str(exc)])
        created_record_refs = [
            {
                "recordType": str(item.get("entityType") or ""),
                "id": str(item.get("entityId") or ""),
            }
            for item in workflow.get("appliedEntityRefs", [])
            if isinstance(item, dict) and item.get("entityType") and item.get("entityId")
        ]
        routed_record = None
        if created_record_refs:
            routed_record = await self._clarification_routed_record_from_entity_ref(
                user_id=user_id,
                entity_type=created_record_refs[0]["recordType"],
                entity_id=created_record_refs[0]["id"],
            )
            return (created_record_refs, routed_record, [])
        warnings = [str(item) for item in workflow.get("warnings", []) if str(item).strip()] or [
            "Free-text clarification answer could not be routed into a typed durable capture."
        ]
        return ([], None, warnings)

    async def _store_typology_feedback_record(
        self,
        *,
        user_id: Id,
        payload: dict[str, object],
        material_id: Id | None,
    ) -> TypologyLensRecord:
        allowed_roles = {"dominant", "auxiliary", "tertiary", "inferior", "compensation_link"}
        allowed_functions = {"thinking", "feeling", "sensation", "intuition"}
        allowed_statuses = {"candidate", "user_refined", "disconfirmed"}
        lens_id = self._optional_str(payload.get("lensId"))
        existing: TypologyLensRecord | None = None
        if lens_id:
            existing = await self._repository.get_typology_lens(user_id, lens_id)
        claim = self._optional_str(payload.get("claim"))
        if existing is None and claim:
            existing = next(
                (
                    item
                    for item in await self._repository.list_typology_lenses(
                        user_id, include_deleted=False, limit=50
                    )
                    if str(item.get("claim") or "").strip().lower() == claim.lower()
                ),
                None,
            )
        role = self._optional_str(payload.get("role")) or (
            self._optional_str(existing.get("role")) if existing else None
        )
        function = self._optional_str(payload.get("function")) or (
            self._optional_str(existing.get("function")) if existing else None
        )
        claim = claim or (self._optional_str(existing.get("claim")) if existing else None)
        user_test_prompt = self._optional_str(payload.get("userTestPrompt")) or (
            self._optional_str(existing.get("userTestPrompt")) if existing else None
        )
        if (
            role not in allowed_roles
            or function not in allowed_functions
            or not claim
            or not user_test_prompt
        ):
            raise ValidationError(
                "Typology-feedback clarification answers require valid role, function, claim, "
                "and userTestPrompt fields."
            )
        confidence = self._optional_str(payload.get("confidence")) or (
            self._optional_str(existing.get("confidence")) if existing else "low"
        )
        if confidence == "high":
            confidence = "medium"
        if confidence not in {"low", "medium"}:
            raise ValidationError("Typology feedback confidence must be low or medium.")
        status = self._optional_str(payload.get("status")) or (
            self._optional_str(existing.get("status")) if existing else "user_refined"
        )
        if status not in allowed_statuses:
            raise ValidationError(
                "Typology feedback status must be candidate, user_refined, or disconfirmed."
            )
        linked_material_ids = self._merge_ids(
            list(existing.get("linkedMaterialIds", [])) if existing else [],
            [material_id] if material_id else [],
        )
        linked_material_ids = self._merge_ids(
            linked_material_ids,
            [str(item) for item in payload.get("linkedMaterialIds", []) if str(item).strip()],
        )
        counterevidence_ids = self._merge_ids(
            list(existing.get("counterevidenceIds", [])) if existing else [],
            [str(item) for item in payload.get("counterevidenceIds", []) if str(item).strip()],
        )
        now = now_iso()
        role_value = cast(
            Literal["dominant", "auxiliary", "tertiary", "inferior", "compensation_link"],
            role,
        )
        function_value = cast(
            Literal["thinking", "feeling", "sensation", "intuition"],
            function,
        )
        confidence_value = cast(Literal["low", "medium"], confidence)
        status_value = cast(Literal["candidate", "user_refined", "disconfirmed"], status)
        if existing is not None:
            return await self._repository.update_typology_lens(
                user_id,
                existing["id"],
                {
                    "role": role_value,
                    "function": function_value,
                    "claim": claim,
                    "confidence": confidence_value,
                    "status": status_value,
                    "counterevidenceIds": counterevidence_ids,
                    "userTestPrompt": user_test_prompt,
                    "linkedMaterialIds": linked_material_ids,
                    "updatedAt": now,
                    "lastSeen": now,
                },
            )
        return await self._repository.create_typology_lens(
            {
                "id": create_id("typology_lens"),
                "userId": user_id,
                "role": role_value,
                "function": function_value,
                "claim": claim,
                "confidence": confidence_value,
                "status": status_value,
                "evidenceIds": [],
                "counterevidenceIds": counterevidence_ids,
                "userTestPrompt": user_test_prompt,
                "linkedMaterialIds": linked_material_ids,
                "createdAt": now,
                "updatedAt": now,
                "lastSeen": now,
            }
        )

    def _clarification_question_key(self, question_text: str) -> str:
        compact = re.sub(r"[^a-z0-9]+", "_", question_text.lower()).strip("_")
        return compact[:80] or create_id("clarification_key")

    def _method_state_has_anchor(self, anchor_refs: dict[str, object]) -> bool:
        return any(str(value).strip() for value in anchor_refs.values() if value is not None)

    async def _resolve_clarification_prompt_for_method_state_response(
        self,
        *,
        user_id: Id,
        anchor_refs: dict[str, object],
        anchors: dict[str, object],
    ) -> ClarificationPromptRecord | None:
        prompt_id = self._optional_str(anchor_refs.get("promptId"))
        if prompt_id:
            try:
                return await self._repository.get_clarification_prompt(user_id, prompt_id)
            except EntityNotFoundError:
                pass
        run = anchors.get("run")
        run_id = self._optional_str(anchor_refs.get("runId"))
        if not run_id and isinstance(run, dict):
            run_id = self._optional_str(run.get("id"))
        if not run_id:
            return None
        prompts = await self._repository.list_clarification_prompts(
            user_id,
            run_id=run_id,
            limit=20,
        )
        if not prompts:
            return None
        ref_keys: list[str] = []
        explicit_ref_key = self._optional_str(anchor_refs.get("clarificationRefKey"))
        if explicit_ref_key:
            ref_keys.append(explicit_ref_key)
        if isinstance(run, dict):
            intent = run.get("result", {}).get("clarificationIntent")
            if isinstance(intent, dict):
                run_ref_key = self._optional_str(intent.get("refKey"))
                if run_ref_key and run_ref_key not in ref_keys:
                    ref_keys.append(run_ref_key)
        for ref_key in ref_keys:
            matches = [
                item for item in prompts if self._clarification_prompt_matches_ref_key(item, ref_key)
            ]
            preferred = self._prefer_clarification_prompt(matches)
            if preferred is not None:
                return preferred
        if len(prompts) == 1:
            return prompts[0]
        return self._prefer_clarification_prompt(prompts)

    def _clarification_prompt_matches_ref_key(
        self,
        prompt: ClarificationPromptRecord,
        ref_key: str,
    ) -> bool:
        if self._optional_str(prompt.get("questionKey")) == ref_key:
            return True
        routing_hints = prompt.get("routingHints")
        if not isinstance(routing_hints, dict):
            return False
        anchor_refs = routing_hints.get("anchorRefs")
        if not isinstance(anchor_refs, dict):
            return False
        return self._optional_str(anchor_refs.get("clarificationRefKey")) == ref_key

    def _prefer_clarification_prompt(
        self,
        prompts: list[ClarificationPromptRecord],
    ) -> ClarificationPromptRecord | None:
        for prompt in prompts:
            if self._optional_str(prompt.get("status")) == "pending":
                return prompt
        return prompts[0] if prompts else None

    def _is_context_only_fallback_clarification(
        self,
        *,
        anchors: dict[str, object],
        prompt: ClarificationPromptRecord | None,
        expected_targets: list[MethodStateCaptureTargetKind],
    ) -> bool:
        del expected_targets
        if prompt is not None and self._optional_str(prompt.get("captureTarget")) == "answer_only":
            return True
        routing_hints = prompt.get("routingHints") if prompt is not None else None
        if isinstance(routing_hints, dict):
            if self._optional_str(routing_hints.get("source")) == "fallback_collaborative_opening":
                return True
            if (
                self._optional_str(routing_hints.get("continuationMode"))
                == "interpretation_context_only"
            ):
                return True
        run = anchors.get("run")
        if not isinstance(run, dict):
            return False
        result = run.get("result")
        if not isinstance(result, dict):
            return False
        llm_health = result.get("llmInterpretationHealth")
        if isinstance(llm_health, dict) and self._optional_str(llm_health.get("source")) == "fallback":
            return True
        depth_engine_health = result.get("depthEngineHealth")
        if isinstance(depth_engine_health, dict) and (
            self._optional_str(depth_engine_health.get("source")) == "fallback"
        ):
            return True
        clarification_intent = result.get("clarificationIntent")
        if not isinstance(clarification_intent, dict):
            return False
        return self._optional_str(clarification_intent.get("refKey")) in {
            "clarify_dream_primary_image",
            "clarify_primary_image",
        }

    async def _record_clarification_answer_from_method_state(
        self,
        *,
        user_id: Id,
        prompt: ClarificationPromptRecord | None,
        response_text: str,
        response_material: MaterialRecord,
        anchor_refs: dict[str, object],
        applied_entity_refs: list[MethodStateAppliedEntityRef],
        pending_proposals: list[MemoryWriteProposal],
        warnings: list[str],
        privacy_class: str,
        capture_target: ClarificationCaptureTarget,
    ) -> ClarificationAnswerRecord | None:
        if prompt is None:
            return None
        routing_status = "routed" if applied_entity_refs else "needs_review" if pending_proposals else "unrouted"
        created_record_refs = [
            {
                "recordType": str(item.get("entityType") or ""),
                "id": str(item.get("entityId") or ""),
            }
            for item in applied_entity_refs
            if str(item.get("entityType") or "").strip()
            and str(item.get("entityId") or "").strip()
        ]
        existing_answer_id = self._optional_str(prompt.get("answerRecordId"))
        prompt_status = "answered" if routing_status == "routed" else "answered_unrouted"
        if existing_answer_id:
            existing_answer = await self._repository.get_clarification_answer(user_id, existing_answer_id)
            if str(existing_answer.get("answerText") or "").strip() != response_text:
                warnings.append("clarification_prompt_already_answered")
                return existing_answer
            prompt_updates: dict[str, object] = {}
            if self._optional_str(prompt.get("status")) == "pending":
                prompt_updates.update(
                    {
                        "status": prompt_status,
                        "answerRecordId": existing_answer["id"],
                        "answeredAt": str(
                            existing_answer.get("updatedAt")
                            or existing_answer.get("createdAt")
                            or now_iso()
                        ),
                        "updatedAt": str(
                            existing_answer.get("updatedAt")
                            or existing_answer.get("createdAt")
                            or now_iso()
                        ),
                    }
                )
            if self._optional_str(prompt.get("captureTarget")) != capture_target:
                prompt_updates["captureTarget"] = capture_target
            if prompt_updates:
                await self._repository.update_clarification_prompt(
                    user_id,
                    prompt["id"],
                    cast(dict[str, object], prompt_updates),
                )
            return existing_answer
        timestamp = now_iso()
        answer_record: ClarificationAnswerRecord = {
            "id": create_id("clarification_answer"),
            "userId": user_id,
            "promptId": prompt["id"],
            "answerText": response_text,
            "captureTarget": capture_target,
            "routingStatus": routing_status,
            "createdRecordRefs": created_record_refs,
            "privacyClass": privacy_class,
            "createdAt": timestamp,
            "updatedAt": timestamp,
        }
        material_id = self._optional_str(prompt.get("materialId")) or self._optional_str(
            anchor_refs.get("materialId")
        )
        if material_id:
            answer_record["materialId"] = material_id
        else:
            answer_record["materialId"] = response_material["id"]
        run_id = self._optional_str(prompt.get("runId")) or self._optional_str(anchor_refs.get("runId"))
        if run_id:
            answer_record["runId"] = run_id
        validation_errors = [str(item) for item in warnings if str(item).strip()]
        if validation_errors:
            answer_record["validationErrors"] = validation_errors
        stored_answer = await self._repository.create_clarification_answer(answer_record)
        await self._repository.update_clarification_prompt(
            user_id,
            prompt["id"],
            {
                "captureTarget": capture_target,
                "status": prompt_status,
                "answerRecordId": stored_answer["id"],
                "answeredAt": stored_answer["updatedAt"],
                "updatedAt": stored_answer["updatedAt"],
            },
        )
        await self._record_adaptation_signal(
            user_id=user_id,
            event_type="clarification_answered"
            if routing_status == "routed"
            else "clarification_unrouted",
            signals={
                "intent": prompt.get("intent") or "other",
                "captureTarget": capture_target,
                "expectedAnswerKind": prompt.get("expectedAnswerKind") or "free_text",
                "routingStatus": routing_status,
            },
        )
        return stored_answer

    async def _materialize_method_state_result(
        self,
        capture_run: MethodStateCaptureRunRecord,
    ) -> MethodStateWorkflowResult:
        response_material = await self._repository.get_material(
            capture_run["userId"],
            capture_run["responseMaterialId"],
        )
        evidence_items = [
            await self._repository.get_evidence_item(capture_run["userId"], evidence_id)
            for evidence_id in capture_run.get("evidenceIds", [])
        ]
        plan = capture_run.get("memoryWritePlan", {"proposals": []})
        return {
            "captureRun": capture_run,
            "responseMaterial": response_material,
            "evidence": evidence_items,
            "appliedEntityRefs": deepcopy(capture_run.get("appliedEntityRefs", [])),
            "pendingProposals": deepcopy(plan.get("proposals", [])),
            "followUpPrompts": [
                str(item)
                for item in capture_run.get("extractionResult", {}).get("followUpPrompts", [])
                if str(item).strip()
            ],
            "withheldCandidates": deepcopy(
                capture_run.get("extractionResult", {}).get("withheldCandidates", [])
            ),
            "warnings": [
                str(item)
                for item in capture_run.get("extractionResult", {}).get("routingWarnings", [])
                if str(item).strip()
            ],
        }

    async def _load_method_state_anchors(
        self,
        *,
        user_id: Id,
        anchor_refs: dict[str, object],
    ) -> dict[str, object]:
        anchors: dict[str, object] = {}
        if anchor_refs.get("materialId"):
            anchors["material"] = await self._repository.get_material(
                user_id, str(anchor_refs["materialId"])
            )
        if anchor_refs.get("runId"):
            run = await self._repository.get_interpretation_run(user_id, str(anchor_refs["runId"]))
            anchors["run"] = run
            if anchor_refs.get("clarificationRefKey"):
                intent = run.get("result", {}).get("clarificationIntent")
                if not isinstance(intent, dict) or str(intent.get("refKey") or "") != str(
                    anchor_refs["clarificationRefKey"]
                ):
                    raise ValidationError("clarificationRefKey does not match the anchored run.")
                anchors["clarificationIntent"] = deepcopy(intent)
            if "material" not in anchors:
                anchors["material"] = await self._repository.get_material(
                    user_id, run["materialId"]
                )
        if anchor_refs.get("promptId"):
            anchors["prompt"] = await self._repository.get_amplification_prompt(
                user_id,
                str(anchor_refs["promptId"]),
            )
        if anchor_refs.get("practiceSessionId"):
            anchors["practiceSession"] = await self._repository.get_practice_session(
                user_id,
                str(anchor_refs["practiceSessionId"]),
            )
        if anchor_refs.get("goalId"):
            anchors["goal"] = await self._repository.get_goal(user_id, str(anchor_refs["goalId"]))
        return anchors

    def _resolve_expected_capture_targets(
        self,
        *,
        source: str,
        expected_targets: list[MethodStateCaptureTargetKind],
        anchors: dict[str, object],
    ) -> list[MethodStateCaptureTargetKind]:
        resolved: list[MethodStateCaptureTargetKind] = list(expected_targets)
        prompt = anchors.get("prompt")
        if isinstance(prompt, dict):
            resolved.append("personal_amplification")
        clarification_intent = anchors.get("clarificationIntent")
        if isinstance(clarification_intent, dict):
            for item in clarification_intent.get("expectedTargets", []):
                if isinstance(item, str):
                    resolved.append(item)  # type: ignore[arg-type]
        source_defaults: dict[str, list[MethodStateCaptureTargetKind]] = {
            "body_note": ["body_state"],
            "practice_feedback": ["practice_outcome", "practice_preference"],
            "goal_feedback": ["goal", "goal_tension"],
            "relational_scene": ["relational_scene"],
            "dream_dynamics": ["dream_dynamics", "body_state"],
            "amplification_answer": ["personal_amplification"],
            "consent_update": ["consent_preference"],
        }
        resolved.extend(source_defaults.get(source, []))
        deduped: list[MethodStateCaptureTargetKind] = []
        for item in resolved:
            if item not in deduped:
                deduped.append(item)
        return deduped

    def _method_state_anchor_summary(self, anchors: dict[str, object]) -> str | None:
        prompt = anchors.get("prompt")
        if isinstance(prompt, dict):
            return self._optional_str(prompt.get("promptText"))
        run = anchors.get("run")
        if isinstance(run, dict):
            return self._optional_str(run.get("result", {}).get("userFacingResponse"))
        return None

    def _method_state_evidence_text(
        self,
        *,
        response_text: str,
        span: dict[str, object],
    ) -> str:
        quote = str(span.get("quote") or "").strip()
        if quote and quote in response_text:
            return quote
        summary = str(span.get("summary") or "").strip()
        if summary:
            return summary
        return self._compact_page_text(response_text, max_length=200)

    async def _create_method_state_evidence(
        self,
        *,
        user_id: Id,
        response_material_id: Id,
        response_text: str,
        observed_at: str,
        privacy_class: str,
        spans: object,
    ) -> list[EvidenceItem]:
        if not isinstance(spans, list):
            return []
        items: list[EvidenceItem] = []
        for span in spans:
            if not isinstance(span, dict):
                continue
            items.append(
                {
                    "id": create_id("evidence"),
                    "type": "method_state_response",
                    "sourceId": response_material_id,
                    "quoteOrSummary": self._method_state_evidence_text(
                        response_text=response_text,
                        span=span,
                    ),
                    "timestamp": observed_at,
                    "privacyClass": privacy_class,
                    "reliability": "high"
                    if str(span.get("quote") or "").strip() in response_text
                    else "medium",
                }
            )
        if not items:
            return []
        return await self._repository.store_evidence_items(user_id, items)

    def _method_state_requires_proposal(self, target_kind: str) -> bool:
        return target_kind in {
            "projection_hypothesis",
            "inner_outer_correspondence",
            "typology_lens",
            "living_myth_question",
        }

    def _method_state_candidate_withheld_reason(
        self,
        *,
        candidate: MethodStateCaptureCandidate,
        consent_preferences: list[dict[str, object]],
        safety_context: SafetyContext | None,
        runtime_policy: dict[str, object] | None,
    ) -> str | None:
        target_kind = str(candidate.get("targetKind") or "").strip()
        policy = runtime_policy if isinstance(runtime_policy, dict) else {}
        if (
            policy.get("depthLevel") == "grounding_only"
            and target_kind in _METHOD_STATE_GROUNDING_ONLY_BLOCKED_TARGETS
        ):
            return f"method_state_policy_grounding_only:{target_kind}"
        for blocked_move in policy.get("blockedMoves", []):
            move = str(blocked_move).strip()
            if target_kind in _METHOD_STATE_POLICY_TARGETS_BY_BLOCKED_MOVE.get(move, ()):
                return f"method_state_policy_blocked_move:{move}"
        consent_scopes = [
            str(item) for item in candidate.get("consentScopes", []) if str(item).strip()
        ]
        for scope in consent_scopes:
            if self._consent_status(consent_preferences, scope) not in {None, "allow"}:
                return f"consent_required:{scope}"
        if (
            safety_context
            and safety_context.get("userReportedActivation") == "overwhelming"
            and candidate.get("targetKind")
            in {
                "projection_hypothesis",
                "inner_outer_correspondence",
                "typology_lens",
                "living_myth_question",
                "threshold_process",
                "numinous_encounter",
            }
        ):
            return "grounding_only_withheld"
        return None

    def _method_state_candidate_to_proposal(
        self,
        *,
        candidate: MethodStateCaptureCandidate,
        evidence_ids: list[Id],
    ) -> MemoryWriteProposal | None:
        target_kind = str(candidate.get("targetKind") or "")
        action_by_target = {
            "projection_hypothesis": ("upsert_projection_hypothesis", "ProjectionHypothesis"),
            "inner_outer_correspondence": (
                "upsert_inner_outer_correspondence",
                "InnerOuterCorrespondence",
            ),
            "typology_lens": ("store_typology_lens", "TypologyLens"),
            "living_myth_question": ("upsert_mythic_question", "MythicQuestion"),
            "threshold_process": ("upsert_threshold_process", "ThresholdProcess"),
            "numinous_encounter": ("create_numinous_encounter", "NuminousEncounter"),
            "aesthetic_resonance": ("create_aesthetic_resonance", "AestheticResonance"),
            "relational_scene": ("upsert_relational_scene", "RelationalScene"),
        }
        mapping = action_by_target.get(target_kind)
        if mapping is None:
            return None
        action, entity_type = mapping
        payload = deepcopy(candidate.get("payload", {}))
        if target_kind == "typology_lens":
            payload["confidence"] = (
                "medium"
                if payload.get("confidence") == "high"
                else str(payload.get("confidence") or "low")
            )
            payload.setdefault("status", "candidate")
            payload["evidenceIds"] = list(evidence_ids)
        return {
            "id": create_id("proposal"),
            "action": action,
            "entityType": entity_type,
            "payload": payload,
            "evidenceIds": list(evidence_ids),
            "reason": str(candidate.get("reason") or "Method-state connector proposal."),
            "requiresUserApproval": True,
            "status": "pending_user_approval",
        }

    async def _apply_method_state_candidate(
        self,
        *,
        user_id: Id,
        source: str,
        response_material: MaterialRecord,
        observed_at: str,
        expected_targets: list[MethodStateCaptureTargetKind],
        anchors: dict[str, object],
        candidate: MethodStateCaptureCandidate,
        evidence_ids_by_ref: dict[str, Id],
        consent_preferences: list[dict[str, object]],
        safety_context: SafetyContext | None,
        runtime_policy: dict[str, object] | None,
        window_start: str,
        window_end: str,
    ) -> dict[str, object]:
        target_kind = str(candidate.get("targetKind") or "")
        application = str(candidate.get("application") or "ignore")
        if target_kind not in expected_targets and source != "freeform_followup":
            return {
                "withheld": {
                    "targetKind": target_kind,
                    "reason": "unexpected_target_for_anchor",
                }
            }
        if application in {"ignore", "needs_clarification", "withheld"}:
            return {
                "withheld": {
                    "targetKind": target_kind,
                    "reason": str(candidate.get("reason") or application),
                }
            }
        withheld_reason = self._method_state_candidate_withheld_reason(
            candidate=candidate,
            consent_preferences=consent_preferences,
            safety_context=safety_context,
            runtime_policy=runtime_policy,
        )
        if withheld_reason:
            return {
                "withheld": {
                    "targetKind": target_kind,
                    "reason": withheld_reason,
                }
            }
        evidence_ids = [
            evidence_ids_by_ref[ref]
            for ref in candidate.get("supportingEvidenceRefs", [])
            if ref in evidence_ids_by_ref
        ]
        if self._method_state_requires_proposal(target_kind) or application == "approval_proposal":
            proposal = self._method_state_candidate_to_proposal(
                candidate=candidate,
                evidence_ids=evidence_ids,
            )
            if proposal is None:
                return {"warning": f"unsupported_method_state_proposal:{target_kind}"}
            return {"proposal": proposal}
        payload = deepcopy(candidate.get("payload", {}))
        if target_kind == "body_state":
            if not str(payload.get("sensation") or "").strip():
                return {"warning": "body_state_missing_sensation"}
            stored = await self.store_body_state(
                {
                    "userId": user_id,
                    "sensation": str(payload.get("sensation") or "").strip(),
                    "observedAt": str(payload.get("observedAt") or observed_at),
                    "bodyRegion": self._optional_str(payload.get("bodyRegion")),
                    "activation": payload.get("activation"),
                    "tone": self._optional_str(payload.get("tone")),
                    "temporalContext": self._optional_str(payload.get("temporalContext")),
                    "linkedMaterialIds": self._merge_ids(
                        [response_material["id"]],
                        list(payload.get("linkedMaterialIds", [])),
                    ),
                    "linkedGoalIds": list(payload.get("linkedGoalIds", [])),
                    "evidenceIds": evidence_ids,
                    "privacyClass": response_material.get("privacyClass", "user_private"),
                }
            )
            return {
                "appliedEntityRef": {
                    "entityType": "BodyState",
                    "entityId": stored["bodyState"]["id"],
                }
            }
        if target_kind == "personal_amplification":
            prompt = anchors.get("prompt") if isinstance(anchors.get("prompt"), dict) else {}
            canonical_name = str(
                payload.get("canonicalName") or prompt.get("canonicalName") or ""
            ).strip()
            surface_text = str(
                payload.get("surfaceText") or prompt.get("surfaceText") or ""
            ).strip()
            association_text = str(payload.get("associationText") or "").strip()
            if not canonical_name or not surface_text or not association_text:
                return {"warning": "personal_amplification_missing_required_fields"}
            created = await self.answer_amplification_prompt(
                {
                    "userId": user_id,
                    "promptId": prompt.get("id"),
                    "materialId": response_material["id"],
                    "runId": anchors.get("run", {}).get("id")
                    if isinstance(anchors.get("run"), dict)
                    else None,
                    "symbolId": payload.get("symbolId") or prompt.get("symbolId"),
                    "canonicalName": canonical_name,
                    "surfaceText": surface_text,
                    "associationText": association_text,
                    "feelingTone": self._optional_str(payload.get("feelingTone")),
                    "bodySensations": list(payload.get("bodySensations", [])),
                    "memoryRefs": list(payload.get("memoryRefs", [])),
                    "evidenceIds": evidence_ids,
                    "privacyClass": response_material.get("privacyClass", "user_private"),
                }
            )
            return {
                "appliedEntityRef": {
                    "entityType": "PersonalAmplification",
                    "entityId": created["id"],
                }
            }
        if target_kind == "conscious_attitude":
            stance_summary = str(payload.get("stanceSummary") or "").strip()
            if not stance_summary:
                return {"warning": "conscious_attitude_missing_stance_summary"}
            created = await self.capture_conscious_attitude(
                {
                    "userId": user_id,
                    "windowStart": window_start,
                    "windowEnd": window_end,
                    "stanceSummary": stance_summary,
                    "activeValues": list(payload.get("activeValues", [])),
                    "activeConflicts": list(payload.get("activeConflicts", [])),
                    "avoidedThemes": list(payload.get("avoidedThemes", [])),
                    "emotionalTone": self._optional_str(payload.get("emotionalTone")),
                    "egoPosition": self._optional_str(payload.get("egoPosition")),
                    "confidence": str(
                        payload.get("confidence") or candidate.get("confidence") or "low"
                    ),
                    "relatedMaterialIds": [response_material["id"]],
                    "relatedGoalIds": list(payload.get("relatedGoalIds", [])),
                    "evidenceIds": evidence_ids,
                    "source": "reflection",
                    "status": "candidate" if application == "candidate_write" else "user_confirmed",
                    "privacyClass": response_material.get("privacyClass", "user_private"),
                }
            )
            return {
                "appliedEntityRef": {
                    "entityType": "ConsciousAttitude",
                    "entityId": created["id"],
                }
            }
        if target_kind == "goal":
            label = str(payload.get("label") or "").strip()
            if not label:
                return {"warning": "goal_missing_label"}
            anchored_goal = anchors.get("goal") if isinstance(anchors.get("goal"), dict) else {}
            goal = await self.upsert_goal(
                {
                    "userId": user_id,
                    "goalId": payload.get("goalId") or anchored_goal.get("id"),
                    "label": label,
                    "description": self._optional_str(payload.get("description")),
                    "status": str(payload.get("status") or "active"),
                    "valueTags": list(payload.get("valueTags", [])),
                    "linkedMaterialIds": [response_material["id"]],
                    "linkedSymbolIds": list(payload.get("linkedSymbolIds", [])),
                    "evidenceIds": evidence_ids,
                }
            )
            return {"appliedEntityRef": {"entityType": "Goal", "entityId": goal["id"]}}
        if target_kind == "goal_tension":
            goal_ids = [str(item) for item in payload.get("goalIds", []) if str(item).strip()]
            if not goal_ids or not str(payload.get("tensionSummary") or "").strip():
                return {"warning": "goal_tension_missing_required_fields"}
            tension = await self.upsert_goal_tension(
                {
                    "userId": user_id,
                    "tensionId": payload.get("tensionId"),
                    "goalIds": goal_ids,
                    "tensionSummary": str(payload.get("tensionSummary") or "").strip(),
                    "polarityLabels": list(payload.get("polarityLabels", [])),
                    "evidenceIds": evidence_ids,
                    "status": "candidate"
                    if application == "candidate_write"
                    else str(payload.get("status") or "active"),
                }
            )
            return {
                "appliedEntityRef": {
                    "entityType": "GoalTension",
                    "entityId": tension["id"],
                }
            }
        if target_kind == "practice_outcome":
            practice_session = (
                anchors.get("practiceSession")
                if isinstance(anchors.get("practiceSession"), dict)
                else {}
            )
            practice_type = str(
                payload.get("practiceType") or practice_session.get("practiceType") or ""
            ).strip()
            outcome_text = str(payload.get("outcome") or "").strip()
            if not practice_type or not outcome_text:
                return {"warning": "practice_outcome_missing_required_fields"}
            practice = await self.record_practice_outcome(
                user_id=user_id,
                practice_session_id=practice_session.get("id"),
                material_id=response_material["id"],
                outcome={
                    "practiceType": practice_type,
                    "target": self._optional_str(
                        payload.get("target") or practice_session.get("target")
                    ),
                    "outcome": outcome_text,
                    "activationBefore": payload.get("activationBefore"),
                    "activationAfter": payload.get("activationAfter"),
                    "outcomeEvidenceIds": evidence_ids,
                },
            )
            return {
                "appliedEntityRef": {
                    "entityType": "PracticeSession",
                    "entityId": practice["id"],
                }
            }
        if target_kind == "practice_preference":
            preferences = {
                key: deepcopy(payload[key])
                for key in ("preferredModalities", "avoidedModalities", "maxDurationMinutes")
                if key in payload
            }
            if not preferences:
                return {"warning": "practice_preference_missing_required_fields"}
            try:
                profile = await self.set_adaptation_preferences(
                    user_id=user_id,
                    scope="practice",
                    preferences=preferences,
                )
            except ValidationError:
                return {"warning": "practice_preference_invalid_payload"}
            return {
                "appliedEntityRef": {
                    "entityType": "AdaptationProfile",
                    "entityId": profile["id"],
                }
            }
        if target_kind == "reality_anchors":
            summary = str(payload.get("summary") or "").strip()
            anchor_summary = str(payload.get("anchorSummary") or "").strip()
            if not summary or not anchor_summary:
                return {"warning": "reality_anchors_missing_required_fields"}
            record = await self.capture_reality_anchors(
                {
                    "userId": user_id,
                    "summary": summary,
                    "anchorSummary": anchor_summary,
                    "workDailyLifeContinuity": str(
                        payload.get("workDailyLifeContinuity") or "unknown"
                    ),
                    "sleepBodyRegulation": str(payload.get("sleepBodyRegulation") or "unknown"),
                    "relationshipContact": str(payload.get("relationshipContact") or "unknown"),
                    "reflectiveCapacity": str(payload.get("reflectiveCapacity") or "unknown"),
                    "groundingRecommendation": str(
                        payload.get("groundingRecommendation") or "pace_gently"
                    ),
                    "reasons": list(payload.get("reasons", [])),
                    "relatedMaterialIds": self._merge_ids(
                        [response_material["id"]],
                        list(payload.get("relatedMaterialIds", [])),
                    ),
                    "relatedSymbolIds": list(payload.get("relatedSymbolIds", [])),
                    "relatedGoalIds": list(payload.get("relatedGoalIds", [])),
                    "evidenceIds": evidence_ids,
                    "privacyClass": response_material.get("privacyClass", "user_private"),
                }
            )
            return {
                "appliedEntityRef": {
                    "entityType": "RealityAnchorSummary",
                    "entityId": record["id"],
                }
            }
        if target_kind == "threshold_process":
            threshold_name = str(payload.get("thresholdName") or "").strip()
            summary = str(payload.get("summary") or "").strip()
            if not threshold_name or not summary:
                return {"warning": "threshold_process_missing_required_fields"}
            normalized_key = str(payload.get("normalizedThresholdKey") or "").strip()
            if not normalized_key:
                normalized_key = re.sub(r"[^a-z0-9]+", "-", threshold_name.lower()).strip("-")
            if not normalized_key:
                return {"warning": "threshold_process_missing_required_fields"}
            record = await self.upsert_threshold_process(
                {
                    "userId": user_id,
                    "thresholdId": payload.get("thresholdId"),
                    "label": self._optional_str(payload.get("label")),
                    "summary": summary,
                    "thresholdName": threshold_name,
                    "phase": str(payload.get("phase") or "unknown"),
                    "whatIsEnding": str(payload.get("whatIsEnding") or "").strip(),
                    "notYetBegun": str(payload.get("notYetBegun") or "").strip(),
                    "bodyCarrying": self._optional_str(payload.get("bodyCarrying")),
                    "groundingStatus": str(payload.get("groundingStatus") or "unknown"),
                    "symbolicLens": self._optional_str(payload.get("symbolicLens")),
                    "invitationReadiness": str(payload.get("invitationReadiness") or "ask"),
                    "normalizedThresholdKey": normalized_key,
                    "relatedMaterialIds": self._merge_ids(
                        [response_material["id"]],
                        list(payload.get("relatedMaterialIds", [])),
                    ),
                    "relatedSymbolIds": list(payload.get("relatedSymbolIds", [])),
                    "relatedGoalIds": list(payload.get("relatedGoalIds", [])),
                    "relatedDreamSeriesIds": list(payload.get("relatedDreamSeriesIds", [])),
                    "evidenceIds": evidence_ids,
                    "privacyClass": response_material.get("privacyClass", "user_private"),
                }
            )
            return {
                "appliedEntityRef": {
                    "entityType": "ThresholdProcess",
                    "entityId": record["id"],
                }
            }
        if target_kind == "relational_scene":
            summary = str(payload.get("summary") or "").strip()
            scene_summary = str(payload.get("sceneSummary") or "").strip()
            normalized_key = str(payload.get("normalizedSceneKey") or "").strip()
            if not summary or not scene_summary or not normalized_key:
                return {"warning": "relational_scene_missing_required_fields"}
            scene = await self.record_relational_scene(
                {
                    "userId": user_id,
                    "summary": summary,
                    "sceneSummary": scene_summary,
                    "normalizedSceneKey": normalized_key,
                    "chargedRoles": list(payload.get("chargedRoles", [])),
                    "recurringAffect": list(payload.get("recurringAffect", [])),
                    "recurrenceContexts": list(payload.get("recurrenceContexts", [])),
                    "relatedMaterialIds": [response_material["id"]],
                    "relatedGoalIds": list(payload.get("relatedGoalIds", [])),
                    "evidenceIds": evidence_ids,
                    "privacyClass": response_material.get("privacyClass", "user_private"),
                }
            )
            return {
                "appliedEntityRef": {
                    "entityType": "RelationalScene",
                    "entityId": scene["id"],
                }
            }
        if target_kind == "consent_preference":
            scope = str(payload.get("scope") or "").strip()
            status = str(payload.get("status") or "").strip()
            if not scope or not status:
                return {"warning": "consent_preference_missing_required_fields"}
            preference = await self.set_consent_preference(
                {
                    "userId": user_id,
                    "scope": scope,
                    "status": status,
                    "note": self._optional_str(
                        payload.get("note") or response_material.get("summary")
                    ),
                    "source": "response_followup",
                }
            )
            return {
                "appliedEntityRef": {
                    "entityType": "ConsentPreference",
                    "entityId": preference["id"],
                }
            }
        if target_kind == "dream_dynamics":
            material = (
                anchors.get("material") if isinstance(anchors.get("material"), dict) else None
            )
            if material is None or material.get("materialType") != "dream":
                return {"warning": "dream_dynamics_requires_dream_anchor"}
            updated_material = await self._append_dream_dynamics_observation(
                material=material,
                observed_at=observed_at,
                payload=payload,
                evidence_ids=evidence_ids,
                source=source,
            )
            return {
                "appliedEntityRef": {
                    "entityType": "DreamEntry",
                    "entityId": updated_material["id"],
                }
            }
        if target_kind == "numinous_encounter":
            summary = str(payload.get("summary") or "").strip()
            interpretation_constraint = str(payload.get("interpretationConstraint") or "").strip()
            if not summary or not interpretation_constraint:
                return {"warning": "numinous_encounter_missing_required_fields"}
            record = await self.record_numinous_encounter(
                {
                    "userId": user_id,
                    "summary": summary,
                    "encounterMedium": str(payload.get("encounterMedium") or "unknown"),
                    "affectTone": str(payload.get("affectTone") or "").strip(),
                    "containmentNeed": str(payload.get("containmentNeed") or "ordinary_reflection"),
                    "interpretationConstraint": interpretation_constraint,
                    "relatedMaterialIds": [response_material["id"]],
                    "relatedSymbolIds": list(payload.get("relatedSymbolIds", [])),
                    "evidenceIds": evidence_ids,
                    "privacyClass": response_material.get("privacyClass", "user_private"),
                }
            )
            return {
                "appliedEntityRef": {
                    "entityType": "NuminousEncounter",
                    "entityId": record["id"],
                }
            }
        if target_kind == "aesthetic_resonance":
            summary = str(payload.get("summary") or "").strip()
            resonance_summary = str(payload.get("resonanceSummary") or "").strip()
            if not summary or not resonance_summary:
                return {"warning": "aesthetic_resonance_missing_required_fields"}
            record = await self.record_aesthetic_resonance(
                {
                    "userId": user_id,
                    "summary": summary,
                    "medium": str(payload.get("medium") or "unknown"),
                    "objectDescription": str(payload.get("objectDescription") or "").strip(),
                    "resonanceSummary": resonance_summary,
                    "feelingTone": self._optional_str(payload.get("feelingTone")),
                    "bodySensations": list(payload.get("bodySensations", [])),
                    "relatedMaterialIds": [response_material["id"]],
                    "relatedSymbolIds": list(payload.get("relatedSymbolIds", [])),
                    "evidenceIds": evidence_ids,
                    "privacyClass": response_material.get("privacyClass", "user_private"),
                }
            )
            return {
                "appliedEntityRef": {
                    "entityType": "AestheticResonance",
                    "entityId": record["id"],
                }
            }
        return {"warning": f"unsupported_method_state_target:{target_kind}"}

    async def _append_dream_dynamics_observation(
        self,
        *,
        material: MaterialRecord,
        observed_at: str,
        payload: dict[str, object],
        evidence_ids: list[Id],
        source: str,
    ) -> MaterialRecord:
        dream_structure = deepcopy(material.get("dreamStructure", {}))
        dynamics = [deepcopy(item) for item in dream_structure.get("methodDynamics", [])]
        dynamics.insert(
            0,
            {
                "id": create_id("dream_dynamics"),
                "source": "clarifying_answer" if source == "clarifying_answer" else "user_reported",
                "observedAt": observed_at,
                "egoStance": str(payload.get("egoStance") or "").strip(),
                "actionSummary": str(payload.get("actionSummary") or "").strip(),
                "affectBefore": str(payload.get("affectBefore") or "").strip(),
                "affectAfter": str(payload.get("affectAfter") or "").strip(),
                "bodySensations": list(payload.get("bodySensations", [])),
                "lysisSummary": str(payload.get("lysisSummary") or "").strip(),
                "relationalStance": str(payload.get("relationalStance") or "").strip(),
                "evidenceIds": list(evidence_ids),
                "createdAt": now_iso(),
            },
        )
        dream_structure["methodDynamics"] = dynamics[:20]
        return await self._repository.update_material(
            material["userId"],
            material["id"],
            {
                "dreamStructure": dream_structure,
                "updatedAt": now_iso(),
            },
        )

    async def _ensure_amplification_prompts_for_run(
        self,
        *,
        user_id: Id,
        material_id: Id,
        run_id: Id,
        interpretation: InterpretationResult,
    ) -> list[AmplificationPromptRecord]:
        summaries = interpretation.get("amplificationPrompts", [])
        if not summaries:
            return []
        existing = await self._repository.list_amplification_prompts(
            user_id,
            run_id=run_id,
            limit=100,
        )
        existing_ids = {item["id"] for item in existing}
        mention_symbol_ids = {
            item["id"]: item.get("symbolId")
            for item in interpretation.get("symbolMentions", [])
            if item.get("symbolId")
        }
        created: list[AmplificationPromptRecord] = []
        timestamp = now_iso()
        for summary in summaries:
            if summary["id"] in existing_ids:
                continue
            record: AmplificationPromptRecord = {
                "id": summary["id"],
                "userId": user_id,
                "materialId": material_id,
                "runId": run_id,
                "canonicalName": summary["canonicalName"],
                "surfaceText": summary["surfaceText"],
                "promptText": summary["promptText"],
                "reason": summary["reason"],
                "status": str(summary.get("status") or "pending"),
                "createdAt": summary.get("createdAt", timestamp),
                "updatedAt": timestamp,
            }
            if summary.get("symbolMentionId"):
                record["symbolMentionId"] = summary["symbolMentionId"]
                symbol_id = mention_symbol_ids.get(summary["symbolMentionId"])
                if symbol_id:
                    record["symbolId"] = symbol_id
            created.append(await self._repository.create_amplification_prompt(record))
        return created

    async def _record_adaptation_signal(
        self,
        *,
        user_id: Id,
        event_type: str,
        signals: dict[str, object],
        success: bool | None = None,
        sample_weight: int | None = None,
    ) -> None:
        current = await self._repository.get_adaptation_profile(user_id)
        profile = self._adaptation_engine.ensure_profile(user_id=user_id, current=current)
        event: AdaptationSignalEvent = {
            "eventType": event_type,
            "timestamp": now_iso(),
            "signals": deepcopy(signals),
        }
        if success is not None:
            event["success"] = success
        if sample_weight is not None:
            event["sampleWeight"] = sample_weight
        updated = self._adaptation_engine.record_event(profile=profile, event=event)
        await self._persist_adaptation_profile(user_id=user_id, current=current, updated=updated)

    async def _persist_adaptation_profile(
        self,
        *,
        user_id: Id,
        current: dict[str, object] | None,
        updated: dict[str, object],
    ) -> None:
        if current is None:
            await self._repository.upsert_adaptation_profile(user_id, updated)
            return
        await self._repository.update_adaptation_profile(
            user_id,
            str(current["id"]),
            {
                "explicitPreferences": deepcopy(updated.get("explicitPreferences", {})),
                "learnedSignals": deepcopy(updated.get("learnedSignals", {})),
                "sampleCounts": deepcopy(updated.get("sampleCounts", {})),
                "updatedAt": str(updated["updatedAt"]),
                "status": str(updated.get("status", "active")),
            },
        )

    def _validate_interpretation_feedback(
        self, feedback: InterpretationInteractionFeedback
    ) -> None:
        allowed = {
            "too_much",
            "too_vague",
            "too_abstract",
            "good_level",
            "helpful",
            "not_helpful",
        }
        if feedback not in allowed:
            raise ValidationError(f"Invalid interpretation feedback: {feedback}")

    def _validate_practice_feedback(self, feedback: PracticeInteractionFeedback) -> None:
        allowed = {
            "good_fit",
            "not_for_me",
            "too_intense",
            "too_long",
            "helpful",
            "not_helpful",
        }
        if feedback not in allowed:
            raise ValidationError(f"Invalid practice feedback: {feedback}")

    async def _build_material_input(
        self,
        *,
        material: MaterialRecord,
        session_context: SessionContext | None,
        life_context_snapshot: LifeContextSnapshot | None,
        life_os_window: dict[str, str] | None,
        user_associations: list[UserAssociationInput] | None,
        explicit_question: str | None,
        cultural_origins: list[dict[str, object]] | None,
        safety_context: SafetyContext | None,
        options: InterpretationOptions | None,
    ) -> MaterialInterpretationInput:
        text = self._material_text(material)
        normalized_options = normalize_options(options)
        adapter_input: BuildContextInput = {
            "userId": material["userId"],
            "materialId": material["id"],
            "materialType": material["materialType"],
            "materialText": text,
            "materialDate": material.get("materialDate", material.get("createdAt", now_iso())),
            "sessionContext": session_context or normalize_session_context(None),
            "options": normalized_options,
        }
        if life_os_window:
            adapter_input["lifeOsWindow"] = life_os_window
        if life_context_snapshot is not None:
            adapter_input["lifeContextSnapshot"] = deepcopy(life_context_snapshot)
        if user_associations:
            adapter_input["userAssociations"] = deepcopy(user_associations)
        if explicit_question:
            adapter_input["explicitQuestion"] = explicit_question
        if safety_context:
            adapter_input["safetyContext"] = deepcopy(safety_context)
        if cultural_origins:
            adapter_input["culturalOrigins"] = deepcopy(cultural_origins)
        material_input = await self._context_adapter.build_material_input(adapter_input)
        material_input["materialId"] = material["id"]
        material_input["materialText"] = text
        material_input["materialDate"] = material.get(
            "materialDate", material.get("createdAt", now_iso())
        )
        material_input["sessionContext"] = normalize_session_context(
            session_context or material_input.get("sessionContext")
        )
        material_input["options"] = normalized_options
        if user_associations:
            material_input["userAssociations"] = deepcopy(user_associations)
        if explicit_question:
            material_input["explicitQuestion"] = explicit_question
        if cultural_origins:
            material_input["culturalOrigins"] = deepcopy(cultural_origins)
        if safety_context:
            material_input["safetyContext"] = deepcopy(safety_context)
        adaptation_profile = await self._repository.get_adaptation_profile(material["userId"])
        communication_hints = self._adaptation_engine.derive_communication_hints(
            profile=adaptation_profile
        )
        interpretation_hints = self._adaptation_engine.derive_interpretation_hints(
            profile=adaptation_profile
        )
        practice_hints = self._adaptation_engine.derive_practice_hints(profile=adaptation_profile)
        material_input["communicationHints"] = deepcopy(communication_hints)
        material_input["interpretationHints"] = deepcopy(interpretation_hints)
        material_input["practiceHints"] = deepcopy(practice_hints)
        if self._trusted_amplification_sources:
            material_input["trustedAmplificationSources"] = deepcopy(
                self._trusted_amplification_sources
            )
        window_start, window_end = self._resolve_window(
            anchor=material.get("materialDate", material.get("createdAt")),
            fallback_start=life_context_snapshot.get("windowStart")
            if life_context_snapshot
            else None,
            fallback_end=life_context_snapshot.get("windowEnd") if life_context_snapshot else None,
            life_os_window=life_os_window,
        )
        method_context = await self._repository.build_method_context_snapshot_from_records(
            material["userId"],
            window_start=window_start,
            window_end=window_end,
            material_id=material["id"],
        )
        if method_context is not None:
            coach_runtime = await self._load_coach_runtime_inputs(user_id=material["userId"])
            material_input["methodContextSnapshot"] = deepcopy(
                self._enrich_method_context_snapshot(
                    method_context,
                    window_start=window_start,
                    window_end=window_end,
                    surface="generic",
                    existing_briefs=cast(
                        list[ProactiveBriefRecord], coach_runtime["existingBriefs"]
                    ),
                    recent_practices=cast(
                        list[PracticeSessionRecord], coach_runtime["recentPractices"]
                    ),
                    journeys=cast(list[JourneyRecord], coach_runtime["journeys"]),
                    adaptation_profile=cast(
                        UserAdaptationProfileSummary | None, coach_runtime["adaptationSummary"]
                    ),
                    safety_context=safety_context,
                )
            )
        return material_input

    async def _store_context_snapshot(
        self,
        *,
        material: MaterialRecord,
        material_input: MaterialInterpretationInput,
    ) -> ContextSnapshot | None:
        session_context = material_input.get("sessionContext")
        life_snapshot = material_input.get("lifeContextSnapshot")
        method_snapshot = material_input.get("methodContextSnapshot")
        if not session_context and not life_snapshot and not method_snapshot:
            return None
        if session_context and not self._session_context_has_content(session_context):
            session_context = None
        if session_context is None and life_snapshot is None and method_snapshot is None:
            return None
        source = "current-conversation"
        if life_snapshot is not None:
            source = life_snapshot["source"]
        elif session_context is not None:
            source = session_context["source"]
        snapshot: ContextSnapshot = {
            "id": create_id("context_snapshot"),
            "userId": material["userId"],
            "source": source,
            "relatedMaterialIds": [material["id"]],
            "createdAt": now_iso(),
            "privacyClass": "approved_summary",
            "status": "active",
        }
        if session_context is not None:
            snapshot["sessionContext"] = deepcopy(session_context)
            snapshot["summary"] = "; ".join(session_context.get("currentStateNotes", [])[:2])
        if life_snapshot is not None:
            snapshot["lifeContextSnapshot"] = deepcopy(life_snapshot)
            snapshot["windowStart"] = life_snapshot.get("windowStart")
            snapshot["windowEnd"] = life_snapshot.get("windowEnd")
            if not snapshot.get("summary"):
                snapshot["summary"] = life_snapshot.get("focusSummary") or life_snapshot.get(
                    "moodSummary"
                )
        method_snapshot = material_input.get("methodContextSnapshot")
        if method_snapshot is not None:
            snapshot["methodContextSnapshot"] = deepcopy(method_snapshot)
            snapshot["windowStart"] = snapshot.get("windowStart") or method_snapshot.get(
                "windowStart"
            )
            snapshot["windowEnd"] = snapshot.get("windowEnd") or method_snapshot.get("windowEnd")
            if not snapshot.get("summary"):
                snapshot["summary"] = self._method_snapshot_summary(method_snapshot)
        return await self._repository.create_context_snapshot(snapshot)

    async def _store_practice_recommendation(
        self,
        *,
        user_id: Id,
        material_id: Id,
        interpretation: InterpretationResult,
    ) -> PracticeSessionRecord | None:
        practice = interpretation.get("practiceRecommendation")
        if practice is None:
            return None
        return await self._store_practice_plan(
            user_id=user_id,
            practice=practice,
            trigger={
                "triggerType": "interpretation",
                "materialId": material_id,
                "runId": interpretation["runId"],
            },
        )

    async def _store_review_practice(
        self,
        *,
        user_id: Id,
        result: dict[str, object],
    ) -> PracticeSessionRecord | None:
        practice = result.get("practiceSuggestion")
        if not practice:
            return None
        return await self._store_practice_plan(
            user_id=user_id,
            practice=deepcopy(practice),
            trigger={"triggerType": "weekly_review"},
        )

    async def _store_practice_plan(
        self,
        *,
        user_id: Id,
        practice: PracticePlan,
        trigger: dict[str, object],
    ) -> PracticeSessionRecord:
        timestamp = now_iso()
        plan = deepcopy(practice)
        defaults = self._practice_engine.derive_lifecycle_defaults(
            practice=plan,
            created_at=timestamp,
            trigger=trigger,  # type: ignore[arg-type]
        )
        record: PracticeSessionRecord = {
            "id": str(plan.get("id") or create_id("practice_session")),
            "userId": user_id,
            "practiceType": plan["type"],
            "target": plan.get("target"),
            "reason": plan["reason"],
            "instructions": deepcopy(plan["instructions"]),
            "durationMinutes": plan["durationMinutes"],
            "contraindicationsChecked": deepcopy(plan["contraindicationsChecked"]),
            "requiresConsent": plan["requiresConsent"],
            "templateId": plan.get("templateId"),
            "modality": plan.get("modality"),
            "intensity": plan.get("intensity"),
            "script": deepcopy(plan.get("script", [])),
            "followUpPrompt": plan.get("followUpPrompt"),
            "adaptationSignals": {"adaptationNotes": deepcopy(plan.get("adaptationNotes", []))},
            "status": "recommended",
            "source": defaults["source"],  # type: ignore[typeddict-item]
            "followUpCount": int(defaults.get("followUpCount", 0)),
            "createdAt": timestamp,
            "updatedAt": timestamp,
        }
        if trigger.get("materialId"):
            record["materialId"] = str(trigger["materialId"])
        if trigger.get("runId"):
            record["runId"] = str(trigger["runId"])
        if defaults.get("nextFollowUpDueAt"):
            record["nextFollowUpDueAt"] = str(defaults["nextFollowUpDueAt"])
        if defaults.get("relatedBriefId"):
            record["relatedBriefId"] = str(defaults["relatedBriefId"])
        coach_loop_key = str(plan.get("coachLoopKey") or "").strip()
        if coach_loop_key:
            record["coachLoopKey"] = coach_loop_key
        coach_loop_kind = str(plan.get("coachLoopKind") or "").strip()
        if coach_loop_kind:
            record["coachLoopKind"] = cast(CoachLoopKind, coach_loop_kind)
        coach_move_kind = str(plan.get("coachMoveKind") or "").strip()
        if coach_move_kind:
            record["coachMoveKind"] = cast(CoachMoveKind, coach_move_kind)
        resource_invitation = plan.get("resourceInvitation")
        if isinstance(resource_invitation, dict):
            record["resourceInvitation"] = cast(
                ResourceInvitationSummary,
                deepcopy(resource_invitation),
            )
        resource_invitation_id = str(plan.get("resourceInvitationId") or "").strip()
        if not resource_invitation_id and isinstance(resource_invitation, dict):
            resource_invitation_id = str(resource_invitation.get("id") or "").strip()
        if resource_invitation_id:
            record["resourceInvitationId"] = resource_invitation_id
        related_resource_ids_value = plan.get("relatedResourceIds")
        related_resource_ids = (
            [str(item) for item in related_resource_ids_value if str(item).strip()]
            if isinstance(related_resource_ids_value, list)
            else []
        )
        if not related_resource_ids and isinstance(resource_invitation, dict):
            resource = resource_invitation.get("resource")
            if isinstance(resource, dict) and str(resource.get("id") or "").strip():
                related_resource_ids = [str(resource["id"])]
        if related_resource_ids:
            record["relatedResourceIds"] = cast(list[Id], related_resource_ids)
        return await self._repository.create_practice_session(record)

    async def _store_rhythmic_brief(
        self,
        *,
        user_id: Id,
        source: str,
        seed: dict[str, object],
        result: dict[str, object],
        created_at: str,
    ) -> ProactiveBriefRecord:
        expires_at = self._format_datetime(self._parse_datetime(created_at) + timedelta(days=7))
        record: ProactiveBriefRecord = {
            "id": create_id("proactive_brief"),
            "userId": user_id,
            "briefType": str(seed["briefType"]),
            "status": "candidate",
            "title": str(result["title"]),
            "summary": str(result["summary"]),
            "suggestedAction": str(result.get("suggestedAction") or ""),
            "triggerKey": str(seed["triggerKey"]),
            "source": source,  # type: ignore[typeddict-item]
            "priority": int(seed.get("priority", 0)),
            "renderedResponse": str(result["userFacingResponse"]),
            "expiresAt": expires_at,
            "relatedJourneyIds": list(seed.get("relatedJourneyIds", [])),
            "relatedMaterialIds": list(seed.get("relatedMaterialIds", [])),
            "relatedSymbolIds": list(seed.get("relatedSymbolIds", [])),
            "relatedPracticeSessionIds": list(seed.get("relatedPracticeSessionIds", [])),
            "evidenceIds": list(seed.get("evidenceIds", [])),
            "createdAt": created_at,
            "updatedAt": created_at,
        }
        coach_loop_key = str(seed.get("coachLoopKey") or "").strip()
        if coach_loop_key:
            record["coachLoopKey"] = coach_loop_key
        coach_loop_kind = str(seed.get("coachLoopKind") or "").strip()
        if coach_loop_kind:
            record["coachLoopKind"] = cast(CoachLoopKind, coach_loop_kind)
        coach_move_kind = str(seed.get("coachMoveKind") or "").strip()
        if coach_move_kind:
            record["coachMoveKind"] = cast(CoachMoveKind, coach_move_kind)
        if isinstance(seed.get("capture"), dict):
            record["capture"] = cast(CoachCaptureContract, deepcopy(seed["capture"]))
        resource_invitation = result.get("resourceInvitation")
        if not isinstance(resource_invitation, dict):
            resource_invitation = seed.get("resourceInvitation")
        if isinstance(resource_invitation, dict):
            record["resourceInvitation"] = cast(
                ResourceInvitationSummary,
                deepcopy(resource_invitation),
            )
        related_resource_ids = [
            str(item) for item in seed.get("relatedResourceIds", []) if str(item).strip()
        ]
        if not related_resource_ids and isinstance(resource_invitation, dict):
            resource = resource_invitation.get("resource")
            if isinstance(resource, dict) and str(resource.get("id") or "").strip():
                related_resource_ids = [str(resource["id"])]
        if related_resource_ids:
            record["relatedResourceIds"] = cast(list[Id], related_resource_ids)
        return await self._repository.create_proactive_brief(record)

    async def _store_interpretation_run(
        self,
        *,
        material: MaterialRecord,
        material_input: MaterialInterpretationInput,
        interpretation: InterpretationResult,
        context_snapshot: ContextSnapshot | None,
        practice_session: PracticeSessionRecord | None,
    ) -> InterpretationRunRecord:
        run: InterpretationRunRecord = {
            "id": interpretation["runId"],
            "userId": material["userId"],
            "materialId": material["id"],
            "materialType": material["materialType"],
            "createdAt": now_iso(),
            "status": "blocked_by_safety"
            if interpretation["safetyDisposition"]["status"] != "clear"
            else "completed",
            "options": deepcopy(material_input.get("options", {})),
            "safetyDisposition": deepcopy(interpretation["safetyDisposition"]),
            "result": deepcopy(interpretation),
            "evidenceIds": [item["id"] for item in interpretation["evidence"]],
            "hypothesisIds": [item["id"] for item in interpretation["hypotheses"]],
            "proposalDecisions": self._proposal_decisions_from_plan(interpretation),
        }
        if context_snapshot is not None:
            run["inputSnapshotId"] = context_snapshot["id"]
        if practice_session is not None:
            run["practiceRecommendationId"] = practice_session["id"]
        return await self._repository.store_interpretation_run(run)

    def _proposal_decisions_from_plan(
        self, interpretation: InterpretationResult
    ) -> list[ProposalDecisionRecord]:
        return self._proposal_decisions_from_memory_write_plan(
            interpretation.get("memoryWritePlan")
        )

    def _proposal_decisions_from_memory_write_plan(
        self,
        memory_write_plan: dict[str, object] | None,
    ) -> list[ProposalDecisionRecord]:
        if not memory_write_plan:
            return []
        proposals = memory_write_plan.get("proposals", [])
        if not isinstance(proposals, list):
            return []
        return [
            {
                "proposalId": proposal["id"],
                "action": proposal["action"],
                "entityType": proposal["entityType"],
                "status": "pending",
            }
            for proposal in proposals
            if isinstance(proposal, dict) and proposal.get("id")
        ]

    def _proposal_records(
        self, run: InterpretationRunRecord, proposal_ids: list[Id]
    ) -> list[dict[str, object]]:
        return self._proposal_records_from_memory_write_plan(
            memory_write_plan=run["result"].get("memoryWritePlan"),
            proposal_ids=proposal_ids,
            owner_label="run",
            owner_id=run["id"],
        )

    def _review_proposal_records(
        self,
        review: LivingMythReviewRecord,
        proposal_ids: list[Id],
    ) -> list[dict[str, object]]:
        return self._proposal_records_from_memory_write_plan(
            memory_write_plan=review.get("memoryWritePlan"),
            proposal_ids=proposal_ids,
            owner_label="living myth review",
            owner_id=review["id"],
        )

    def _proposal_records_from_memory_write_plan(
        self,
        *,
        memory_write_plan: dict[str, object] | None,
        proposal_ids: list[Id],
        owner_label: str,
        owner_id: Id,
    ) -> list[dict[str, object]]:
        if not memory_write_plan:
            raise ValidationError(f"{owner_label.title()} {owner_id} has no memory write plan.")
        proposals = memory_write_plan.get("proposals", [])
        if not isinstance(proposals, list):
            raise ValidationError(f"{owner_label.title()} {owner_id} has no proposals.")
        plan_proposals = {
            proposal["id"]: proposal
            for proposal in proposals
            if isinstance(proposal, dict) and proposal.get("id")
        }
        missing = [proposal_id for proposal_id in proposal_ids if proposal_id not in plan_proposals]
        if missing:
            raise ValidationError(f"Unknown proposal ids for {owner_label} {owner_id}: {missing}")
        return [deepcopy(plan_proposals[proposal_id]) for proposal_id in proposal_ids]

    def _decision_status(self, run: InterpretationRunRecord, proposal_id: Id) -> str:
        return self._decision_status_from_records(run.get("proposalDecisions", []), proposal_id)

    def _review_decision_status(self, review: LivingMythReviewRecord, proposal_id: Id) -> str:
        return self._decision_status_from_records(review.get("proposalDecisions", []), proposal_id)

    def _decision_status_from_records(
        self,
        decisions: list[ProposalDecisionRecord],
        proposal_id: Id,
    ) -> str:
        for decision in decisions:
            if decision["proposalId"] == proposal_id:
                return decision["status"]
        return "pending"

    def _assert_proposal_transition(
        self,
        run: InterpretationRunRecord,
        proposal_id: Id,
        target_status: str,
    ) -> None:
        self._assert_transition_from_decisions(
            run.get("proposalDecisions", []),
            proposal_id,
            target_status,
        )

    def _assert_review_proposal_transition(
        self,
        review: LivingMythReviewRecord,
        proposal_id: Id,
        target_status: str,
    ) -> None:
        self._assert_transition_from_decisions(
            review.get("proposalDecisions", []),
            proposal_id,
            target_status,
        )

    def _assert_transition_from_decisions(
        self,
        decisions: list[ProposalDecisionRecord],
        proposal_id: Id,
        target_status: str,
    ) -> None:
        current_status = self._decision_status_from_records(decisions, proposal_id)
        if current_status == "pending":
            return
        if current_status == target_status:
            raise ValidationError(f"Proposal {proposal_id} is already {current_status}.")
        raise ValidationError(
            f"Proposal {proposal_id} cannot transition from {current_status} to {target_status}."
        )

    def _merge_proposal_decisions(
        self,
        existing: list[ProposalDecisionRecord],
        updates: list[ProposalDecisionRecord],
    ) -> list[ProposalDecisionRecord]:
        by_id = {item["proposalId"]: deepcopy(item) for item in existing}
        for update in updates:
            merged = by_id.get(update["proposalId"], {})
            merged.update(deepcopy(update))
            by_id[update["proposalId"]] = merged
        return list(by_id.values())

    def _hydrate_feedback_keys(
        self,
        interpretation: InterpretationResult,
        feedback_by_hypothesis_id: dict[Id, FeedbackValue],
    ) -> dict[Id, FeedbackValue]:
        hypotheses = {item["id"]: item for item in interpretation["hypotheses"]}
        missing = [
            hypothesis_id
            for hypothesis_id in feedback_by_hypothesis_id
            if hypothesis_id not in hypotheses
        ]
        if missing:
            raise ValidationError(f"Unknown hypothesis ids: {missing}")
        hydrated: dict[Id, FeedbackValue] = {}
        for hypothesis_id, feedback in feedback_by_hypothesis_id.items():
            hypothesis = hypotheses[hypothesis_id]
            hydrated[hypothesis_id] = {
                **deepcopy(feedback),
                "normalizedClaimKey": feedback.get(
                    "normalizedClaimKey", hypothesis["normalizedClaimKey"]
                ),
                "claimDomain": feedback.get("claimDomain", hypothesis["hypothesisType"]),
            }
        return hydrated

    async def _load_materials(self, user_id: Id, material_ids: list[Id]) -> list[MaterialRecord]:
        materials: list[MaterialRecord] = []
        for material_id in material_ids:
            try:
                materials.append(
                    await self._repository.get_material(user_id, material_id, include_deleted=True)
                )
            except EntityNotFoundError:
                continue
        return materials

    def _material_text(self, material: MaterialRecord) -> str:
        text = material.get("text") or material.get("summary")
        if not text:
            raise ValidationError(f"Material {material['id']} has no text or summary to interpret")
        if material["materialType"] != "dream":
            return text
        dream_structure = material.get("dreamStructure") or {}
        sections = [
            f"Exposition: {dream_structure['exposition']}"
            for key in ("exposition",)
            if dream_structure.get(key)
        ]
        sections.extend(
            f"{label}: {dream_structure[key]}"
            for key, label in (("peripetia", "Peripetia"), ("lysis", "Lysis"))
            if dream_structure.get(key)
        )
        if not sections:
            return text
        return f"{text}\n\nDream structure:\n" + "\n".join(sections)

    def _merge_ids(self, existing: list[Id], new_items: list[Id]) -> list[Id]:
        result = list(existing)
        for item in new_items:
            if item not in result:
                result.append(item)
        return result

    def _merge_tags(self, existing: list[str], new_items: list[str]) -> list[str]:
        result = list(existing)
        for item in new_items:
            if item not in result:
                result.append(item)
        return result

    def _normalize_id_list(self, raw_ids: object | None) -> list[Id]:
        if not isinstance(raw_ids, list):
            return []
        result: list[Id] = []
        for item in raw_ids:
            text = str(item).strip()
            if text and text not in result:
                result.append(text)
        return result

    def _apply_journey_link_update(
        self,
        existing: list[Id],
        add_ids: list[Id],
        remove_ids: list[Id],
    ) -> list[Id]:
        remove_set = set(remove_ids)
        merged = self._merge_ids(existing, add_ids)
        return [item for item in merged if item not in remove_set]

    def _journey_link_update_requested(
        self,
        input_data: dict[str, object],
        *,
        add_key: str,
        remove_key: str,
    ) -> bool:
        return bool(input_data.get(add_key) or input_data.get(remove_key))

    def _validate_journey_status(self, status: str, *, allow_deleted: bool) -> str:
        valid = {"active", "paused", "completed", "archived"}
        if allow_deleted:
            valid.add("deleted")
        normalized = status.strip().lower()
        if normalized not in valid:
            raise ValidationError(f"Unsupported journey status: {status}")
        return normalized

    async def _resolve_journey_reference(
        self,
        *,
        user_id: Id,
        journey_id: object | None,
        journey_label: object | None,
        include_deleted: bool = False,
    ) -> JourneyRecord:
        resolved_journey_id = self._optional_str(journey_id)
        resolved_journey_label = self._optional_str(journey_label)
        if resolved_journey_id:
            journey = await self._repository.get_journey(
                user_id,
                resolved_journey_id,
                include_deleted=include_deleted,
            )
            if resolved_journey_label is None:
                return journey
            if not self._journey_label_matches(
                str(journey.get("label") or ""),
                resolved_journey_label,
            ):
                raise ValidationError("journeyId and journeyLabel refer to different journeys")
            return journey
        if resolved_journey_label is None:
            raise ValidationError("journeyId or journeyLabel is required")
        return await self._resolve_journey_by_label(
            user_id=user_id,
            journey_label=resolved_journey_label,
            include_deleted=include_deleted,
        )

    async def _resolve_journey_by_label(
        self,
        *,
        user_id: Id,
        journey_label: str,
        include_deleted: bool,
    ) -> JourneyRecord:
        journeys = await self._repository.list_journeys(
            user_id,
            include_deleted=include_deleted,
            limit=500,
        )
        exact_matches = [
            item for item in journeys if str(item.get("label") or "").strip() == journey_label
        ]
        if len(exact_matches) == 1:
            return exact_matches[0]
        if len(exact_matches) > 1:
            raise ConflictError(self._journey_label_ambiguity_message(journey_label, exact_matches))
        normalized_matches = [
            item
            for item in journeys
            if self._journey_label_matches(str(item.get("label") or ""), journey_label)
        ]
        if not normalized_matches:
            raise EntityNotFoundError(f'Journey not found for label "{journey_label}".')
        if len(normalized_matches) > 1:
            raise ConflictError(
                self._journey_label_ambiguity_message(journey_label, normalized_matches)
            )
        return normalized_matches[0]

    def _journey_label_matches(self, left: str, right: str) -> bool:
        return self._normalize_journey_label(left) == self._normalize_journey_label(right)

    def _normalize_journey_label(self, value: str) -> str:
        collapsed = re.sub(r"\s+", " ", value.replace("-", " ").replace("_", " ").strip())
        return collapsed.lower()

    def _journey_label_ambiguity_message(
        self,
        journey_label: str,
        journeys: list[JourneyRecord],
    ) -> str:
        preview = ", ".join(
            f"{item.get('label', 'Journey')} [{item.get('id', 'unknown')}]" for item in journeys[:5]
        )
        suffix = " ..." if len(journeys) > 5 else ""
        return f'Ambiguous journey label "{journey_label}". Matches: {preview}{suffix}'

    async def _validate_journey_material_ids(
        self,
        user_id: Id,
        raw_ids: object | None,
    ) -> list[Id]:
        ids = self._normalize_id_list(raw_ids)
        for item_id in ids:
            try:
                await self._repository.get_material(user_id, item_id)
            except EntityNotFoundError as exc:
                raise ValidationError(f"Unknown material id for journey: {item_id}") from exc
        return ids

    async def _validate_journey_symbol_ids(
        self,
        user_id: Id,
        raw_ids: object | None,
    ) -> list[Id]:
        ids = self._normalize_id_list(raw_ids)
        for item_id in ids:
            try:
                await self._repository.get_symbol(user_id, item_id)
            except EntityNotFoundError as exc:
                raise ValidationError(f"Unknown symbol id for journey: {item_id}") from exc
        return ids

    async def _validate_journey_pattern_ids(
        self,
        user_id: Id,
        raw_ids: object | None,
    ) -> list[Id]:
        ids = self._normalize_id_list(raw_ids)
        for item_id in ids:
            try:
                await self._repository.get_pattern(user_id, item_id)
            except EntityNotFoundError as exc:
                raise ValidationError(f"Unknown pattern id for journey: {item_id}") from exc
        return ids

    async def _validate_journey_dream_series_ids(
        self,
        user_id: Id,
        raw_ids: object | None,
    ) -> list[Id]:
        ids = self._normalize_id_list(raw_ids)
        for item_id in ids:
            try:
                await self._repository.get_dream_series(user_id, item_id)
            except EntityNotFoundError as exc:
                raise ValidationError(f"Unknown dream series id for journey: {item_id}") from exc
        return ids

    async def _validate_journey_goal_ids(
        self,
        user_id: Id,
        raw_ids: object | None,
    ) -> list[Id]:
        ids = self._normalize_id_list(raw_ids)
        for item_id in ids:
            try:
                await self._repository.get_goal(user_id, item_id)
            except EntityNotFoundError as exc:
                raise ValidationError(f"Unknown goal id for journey: {item_id}") from exc
        return ids

    async def _find_individuation_record_by_detail(
        self,
        *,
        user_id: Id,
        record_type: str,
        detail_key: str,
        detail_value: str,
    ) -> IndividuationRecord | None:
        for item in await self._repository.list_individuation_records(
            user_id,
            record_types=[record_type],
            limit=200,
        ):
            details = item.get("details", {})
            if not isinstance(details, dict):
                continue
            if str(details.get(detail_key, "")).strip().lower() == detail_value.strip().lower():
                return item
        return None

    def _consent_status(
        self,
        consent_preferences: list[dict[str, object]],
        scope: str,
    ) -> str | None:
        for item in reversed(consent_preferences):
            if str(item.get("scope") or "") == scope:
                status = str(item.get("status") or "").strip()
                if status:
                    return status
        return None

    def _session_context_has_content(self, session_context: SessionContext) -> bool:
        return any(
            session_context.get(field)
            for field in ("contextNotes", "recentEventNotes", "currentStateNotes")
        )

    def _method_snapshot_summary(self, snapshot: dict[str, object]) -> str | None:
        conscious = snapshot.get("consciousAttitude")
        if isinstance(conscious, dict) and conscious.get("stanceSummary"):
            return str(conscious["stanceSummary"])
        body_states = snapshot.get("recentBodyStates")
        if isinstance(body_states, list) and body_states:
            first = body_states[0]
            if isinstance(first, dict):
                region = f" in the {first['bodyRegion']}" if first.get("bodyRegion") else ""
                return f"Recent body note: {first.get('sensation', 'sensation')}{region}"
        goals = snapshot.get("activeGoals")
        if isinstance(goals, list) and goals:
            first = goals[0]
            if isinstance(first, dict) and first.get("label"):
                return f"Active goal: {first['label']}"
        return None

    def _resolve_window(
        self,
        *,
        anchor: str | None,
        fallback_start: str | None = None,
        fallback_end: str | None = None,
        life_os_window: dict[str, str] | None = None,
    ) -> tuple[str, str]:
        if life_os_window:
            return life_os_window["start"], life_os_window["end"]
        if fallback_start and fallback_end:
            return fallback_start, fallback_end
        days = int(getattr(self._context_adapter, "_default_life_context_window_days", 7))
        anchor_dt = self._parse_datetime(anchor)
        return (
            self._format_datetime(anchor_dt - timedelta(days=days)),
            self._format_datetime(anchor_dt),
        )

    def _parse_datetime(self, value: str | None) -> datetime:
        if not value:
            return datetime.now(UTC)
        candidate = value.strip()
        if candidate.endswith("Z"):
            candidate = candidate[:-1] + "+00:00"
        parsed = datetime.fromisoformat(candidate)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)

    def _format_datetime(self, value: datetime) -> str:
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
