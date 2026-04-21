from __future__ import annotations

import re
from copy import deepcopy
from datetime import UTC, datetime, timedelta

from ..adapters.context_adapter import BuildContextInput, BuildPracticeContextInput, ContextAdapter
from ..core.adaptation_engine import AdaptationEngine
from ..core.circulatio_core import CirculatioCore
from ..core.practice_engine import PracticeEngine
from ..core.proactive_engine import ProactiveEngine
from ..domain.adaptation import AdaptationSignalEvent
from ..domain.amplifications import AmplificationPromptRecord, PersonalAmplificationRecord
from ..domain.conscious_attitude import ConsciousAttitudeSnapshotRecord
from ..domain.context import ContextSnapshot
from ..domain.culture import CulturalFrameRecord
from ..domain.errors import ConflictError, EntityNotFoundError, ValidationError
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
    CirculationSummaryInput,
    CirculationSummaryResult,
    FeedbackValue,
    Id,
    InterpretationOptions,
    InterpretationResult,
    LifeContextSnapshot,
    MaterialInterpretationInput,
    MethodContextSnapshot,
    PracticeOutcomeWritePayload,
    PracticePlan,
    RhythmicBriefInput,
    SafetyContext,
    SessionContext,
    UserAssociationInput,
)
from ..repositories.circulatio_repository import CirculatioRepository
from .workflow_types import (
    AliveTodayResult,
    AnalysisPacketWorkflowResult,
    AnswerAmplificationPromptInput,
    CaptureConsciousAttitudeInput,
    CaptureRealityAnchorsInput,
    CreateAndInterpretMaterialInput,
    CreateBodyStateInput,
    CreateJourneyInput,
    CreateMaterialInput,
    GenerateAnalysisPacketInput,
    GenerateJourneyPageInput,
    GenerateLivingMythReviewInput,
    GeneratePracticeInput,
    GenerateRhythmicBriefsInput,
    GenerateThresholdReviewInput,
    GetJourneyInput,
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
    PatternHistoryResult,
    PracticeWorkflowResult,
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
    SymbolHistoryResult,
    ThresholdReviewWorkflowResult,
    UpdateJourneyInput,
    UpsertGoalInput,
    UpsertGoalTensionInput,
    UpsertThresholdProcessInput,
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
    ) -> None:
        self._repository = repository
        self._core = core
        self._context_adapter = context_adapter or ContextAdapter(repository)
        self._adaptation_engine = adaptation_engine or AdaptationEngine()
        self._practice_engine = practice_engine or PracticeEngine()
        self._proactive_engine = proactive_engine or ProactiveEngine()

    @property
    def repository(self) -> CirculatioRepository:
        return self._repository

    async def store_material(self, input_data: CreateMaterialInput) -> MaterialRecord:
        payload = deepcopy(input_data)
        payload.setdefault("source", "hermes_ui")
        return await self.create_material(payload)

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
        linked_material_ids: list[Id] = []
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
            "evidenceIds": [],
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
            "evidenceIds": [],
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
            "source": "user_reported",
            "status": "active",
            "windowStart": input_data["windowStart"],
            "windowEnd": input_data["windowEnd"],
            "stanceSummary": stance_summary,
            "activeValues": list(input_data.get("activeValues", [])),
            "activeConflicts": list(input_data.get("activeConflicts", [])),
            "avoidedThemes": list(input_data.get("avoidedThemes", [])),
            "confidence": str(input_data.get("confidence") or "low"),
            "evidenceIds": [],
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
        if snapshot is not None:
            return snapshot
        return {
            "windowStart": window_start,
            "windowEnd": window_end,
            "source": "circulatio-backend",
        }

    async def set_cultural_frame(
        self,
        input_data: SetCulturalFrameInput,
    ) -> CulturalFrameRecord:
        timestamp = now_iso()
        frame_type = str(input_data.get("type") or "chosen")
        status = str(input_data.get("status") or "enabled")
        if input_data.get("culturalFrameId"):
            record = await self._repository.update_cultural_frame(
                input_data["userId"],
                input_data["culturalFrameId"],
                {
                    "label": input_data["label"],
                    "frameType": frame_type,
                    "allowedUses": list(input_data.get("allowedUses", [])),
                    "avoidUses": list(input_data.get("avoidUses", [])),
                    "notes": input_data.get("notes"),
                    "status": status,
                    "updatedAt": timestamp,
                },
            )
        else:
            record = await self._repository.create_cultural_frame(
                {
                    "id": create_id("cultural_frame"),
                    "userId": input_data["userId"],
                    "label": input_data["label"],
                    "frameType": frame_type,
                    "allowedUses": list(input_data.get("allowedUses", [])),
                    "avoidUses": list(input_data.get("avoidUses", [])),
                    "notes": input_data.get("notes"),
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
            "evidenceIds": [],
            "relatedMaterialIds": list(input_data.get("relatedMaterialIds", [])),
            "relatedSymbolIds": list(input_data.get("relatedSymbolIds", [])),
            "relatedGoalIds": list(input_data.get("relatedGoalIds", [])),
            "relatedDreamSeriesIds": [],
            "relatedJourneyIds": [],
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
                "evidenceIds": [],
                "relatedMaterialIds": list(input_data.get("relatedMaterialIds", [])),
                "relatedSymbolIds": list(input_data.get("relatedSymbolIds", [])),
                "relatedGoalIds": list(input_data.get("relatedGoalIds", [])),
                "relatedDreamSeriesIds": list(input_data.get("relatedDreamSeriesIds", [])),
                "relatedJourneyIds": [],
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
                "evidenceIds": [],
                "relatedMaterialIds": list(input_data.get("relatedMaterialIds", [])),
                "relatedSymbolIds": [],
                "relatedGoalIds": list(input_data.get("relatedGoalIds", [])),
                "relatedDreamSeriesIds": [],
                "relatedJourneyIds": [],
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
                "evidenceIds": [],
                "relatedMaterialIds": [],
                "relatedSymbolIds": list(input_data.get("symbolIds", [])),
                "relatedGoalIds": [],
                "relatedDreamSeriesIds": [],
                "relatedJourneyIds": [],
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
                    "relatedSymbolIds": self._merge_ids(
                        list(existing.get("relatedSymbolIds", [])),
                        list(input_data.get("symbolIds", [])),
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
            "evidenceIds": [],
            "relatedMaterialIds": list(input_data.get("relatedMaterialIds", [])),
            "relatedSymbolIds": list(input_data.get("relatedSymbolIds", [])),
            "relatedGoalIds": [],
            "relatedDreamSeriesIds": [],
            "relatedJourneyIds": [],
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
            "evidenceIds": [],
            "relatedMaterialIds": list(input_data.get("relatedMaterialIds", [])),
            "relatedSymbolIds": list(input_data.get("relatedSymbolIds", [])),
            "relatedGoalIds": [],
            "relatedDreamSeriesIds": [],
            "relatedJourneyIds": [],
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
        summary_input = await self._repository.build_circulation_summary_input(
            user_id,
            window_start=window_start,
            window_end=window_end,
        )
        result = await self._core.generate_circulation_summary(summary_input)
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
        generated_at = now_iso()
        seeds = self._proactive_engine.build_candidate_seeds(
            user_id=input_data["userId"],
            memory_snapshot=memory_snapshot,
            dashboard=dashboard,
            method_context=method_context,
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
                journeys=journeys,
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
        if input_data.get("safetyContext") is not None:
            review_input = deepcopy(review_input)
            review_input["safetyContext"] = deepcopy(input_data["safetyContext"])
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
        if input_data.get("safetyContext") is not None:
            review_input = deepcopy(review_input)
            review_input["safetyContext"] = deepcopy(input_data["safetyContext"])
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
        if input_data.get("safetyContext") is not None:
            packet_input = deepcopy(packet_input)
            packet_input["safetyContext"] = deepcopy(input_data["safetyContext"])
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
        profile = await self._repository.get_adaptation_profile(input_data["userId"])
        adaptation_hints = self._adaptation_engine.derive_practice_hints(profile=profile)
        practice_input = deepcopy(practice_input)
        practice_input["adaptationHints"] = deepcopy(adaptation_hints)
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
        summary_input = await self._repository.build_circulation_summary_input(
            input_data["userId"],
            window_start=resolved_start,
            window_end=resolved_end,
        )
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
        memory_snapshot = await self._repository.build_memory_kernel_snapshot(input_data["userId"])
        dashboard = await self._repository.get_dashboard_summary(user_id=input_data["userId"])
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
        seeds = self._proactive_engine.build_candidate_seeds(
            user_id=input_data["userId"],
            memory_snapshot=memory_snapshot,
            dashboard=dashboard,
            method_context=method_context,
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

    async def _build_ephemeral_circulation_summary(
        self,
        *,
        user_id: Id,
        window_start: str,
        window_end: str,
        explicit_question: str | None = None,
    ) -> tuple[CirculationSummaryInput, CirculationSummaryResult]:
        summary_input = await self._repository.build_circulation_summary_input(
            user_id,
            window_start=window_start,
            window_end=window_end,
        )
        if explicit_question:
            summary_input = deepcopy(summary_input)
            summary_input["explicitQuestion"] = explicit_question
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
            "kind": "quiet",
            "title": "Weekly reflection",
            "summary": "No weekly reflection surface is open for this page.",
            "windowStart": window_start,
            "windowEnd": window_end,
            "actions": [],
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
        journeys: list[dict[str, object]],
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
        active_journeys = [item for item in journeys if item.get("status") == "active"][:5]
        if active_journeys:
            sections.append(
                {
                    "sectionType": "journey_threads",
                    "title": "Journey threads",
                    "items": [
                        {
                            "label": str(item.get("label") or "Journey"),
                            "summary": self._compact_page_text(
                                str(item.get("currentQuestion") or ""),
                                max_length=220,
                            ),
                            "entityType": "Journey",
                            "entityId": item.get("id"),
                            "source": "journey",
                        }
                        for item in active_journeys
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
        if current is None:
            await self._repository.upsert_adaptation_profile(user_id, updated)
            return
        await self._repository.update_adaptation_profile(
            user_id,
            current["id"],
            {
                "explicitPreferences": deepcopy(updated.get("explicitPreferences", {})),
                "learnedSignals": deepcopy(updated.get("learnedSignals", {})),
                "sampleCounts": deepcopy(updated.get("sampleCounts", {})),
                "updatedAt": updated["updatedAt"],
                "status": str(updated.get("status", "active")),
            },
        )

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
            material_input["methodContextSnapshot"] = deepcopy(method_context)
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
        return await self._repository.create_proactive_brief(
            {
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
        )

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
