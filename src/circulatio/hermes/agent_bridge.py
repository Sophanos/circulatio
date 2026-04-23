from __future__ import annotations

import asyncio
import hashlib
import json
from copy import deepcopy
from typing import cast

from ..application.circulatio_service import CirculatioService
from ..domain.errors import (
    CirculatioError,
    ConflictError,
    EntityDeletedError,
    EntityNotFoundError,
    PersistenceError,
    ProfileStorageConflictError,
    ProfileStorageCorruptionError,
    ValidationError,
)
from ..domain.ids import create_id
from ..domain.interpretations import InterpretationRunRecord
from ..domain.living_myth import LivingMythReviewRecord
from ..domain.method_state import MethodStateCaptureRunRecord
from ..domain.types import Id
from .agent_bridge_contracts import (
    BridgeError,
    BridgePendingProposal,
    BridgeRequestEnvelope,
    BridgeResponseEnvelope,
    BridgeStatus,
)
from .command_router import HermesCirculationCommandRouter, HermesCommandResult
from .idempotency import IdempotencyStore
from .proposal_alias_index import ProposalAliasIndex


class CirculatioAgentBridge:
    def __init__(
        self,
        *,
        router: HermesCirculationCommandRouter,
        service: CirculatioService,
        idempotency_store: IdempotencyStore,
        proposal_alias_index: ProposalAliasIndex,
    ) -> None:
        self._router = router
        self._service = service
        self._idempotency_store = idempotency_store
        self._proposal_alias_index = proposal_alias_index

    async def dispatch(self, request: BridgeRequestEnvelope) -> BridgeResponseEnvelope:
        validation_error = self._validate_request(request)
        if validation_error is not None:
            return validation_error
        request_hash = self._request_hash(request)
        try:
            begin_result = await self._idempotency_store.begin(
                request["idempotencyKey"], request_hash
            )
        except Exception:
            return self._response(
                request=request,
                status="retryable_error",
                message=(
                    "Circulatio could not access idempotency storage before starting the request."
                ),
                errors=[
                    self._error(
                        "idempotency_unavailable",
                        (
                            "Circulatio could not reserve the idempotency key. "
                            "Retry only if you are certain the earlier request "
                            "did not complete."
                        ),
                        retryable=True,
                    )
                ],
            )
        begin_status = begin_result["status"]
        if begin_status == "conflict":
            return self._response(
                request=request,
                status="conflict",
                message=("The idempotency key was reused for a different Circulatio request."),
                errors=[
                    self._error(
                        "idempotency_conflict",
                        (
                            "The same idempotency key cannot be reused for a "
                            "different request payload."
                        ),
                        retryable=False,
                    )
                ],
            )
        if begin_status == "in_flight":
            replayed = await self._await_in_flight_response(
                request=request,
                request_hash=request_hash,
            )
            if replayed is not None:
                return replayed
            return self._response(
                request=request,
                status="conflict",
                message=(
                    "An identical Circulatio request is already running. "
                    "Wait for that result instead of calling the tool again in the same turn."
                ),
                result={"inFlight": True},
                errors=[
                    self._error(
                        "request_in_flight",
                        (
                            "An identical request is already in flight. Wait "
                            "for that result instead of retrying immediately."
                        ),
                        retryable=False,
                    )
                ],
            )
        if begin_status == "stale_started":
            return self._response(
                request=request,
                status="retryable_error",
                message=(
                    "A previous matching Circulatio request was interrupted "
                    "before its replay response was saved."
                ),
                errors=[
                    self._error(
                        "idempotency_incomplete",
                        (
                            "A previous matching request was interrupted "
                            "before its replay response was saved."
                        ),
                        retryable=False,
                    )
                ],
            )
        if begin_status == "replay":
            stored = begin_result.get("stored")
            if stored is None or stored.response is None:
                return self._response(
                    request=request,
                    status="retryable_error",
                    message="The idempotent request exists but no response was cached.",
                    errors=[
                        self._error(
                            "idempotency_missing_response",
                            "Retry later.",
                            retryable=True,
                        )
                    ],
                )
            return self._replay_response(request=request, cached_response=stored.response)
        try:
            response = await self._dispatch_started_request(request)
        except Exception as exc:
            response = self._exception_response(request, exc)
            try:
                await self._idempotency_store.fail(request["idempotencyKey"], response)
            except Exception:
                response = self._append_error(
                    response,
                    code="idempotency_failure_cache_write_failed",
                    message=(
                        "The request failed and Circulatio could not cache that "
                        "failure for safe replay."
                    ),
                    retryable=True,
                    suffix=" Replay safety information could not be saved.",
                )
            return response
        response = self._sanitize_response_for_host(request=request, response=response)
        try:
            await self._idempotency_store.complete(request["idempotencyKey"], response)
        except Exception:
            response = self._append_error(
                response,
                code="idempotency_cache_write_failed",
                message=(
                    "The operation completed, but Circulatio could not save "
                    "the replay cache for this idempotency key."
                ),
                retryable=True,
                suffix=" Replay caching failed, so retry cautiously.",
            )
        return response

    async def _await_in_flight_response(
        self,
        *,
        request: BridgeRequestEnvelope,
        request_hash: str,
        timeout_seconds: float = 20.0,
    ) -> BridgeResponseEnvelope | None:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout_seconds
        delay_seconds = 0.05
        while loop.time() < deadline:
            await asyncio.sleep(delay_seconds)
            stored = await self._idempotency_store.get(request["idempotencyKey"])
            if stored is None or stored.request_hash != request_hash:
                return None
            if stored.status == "started":
                delay_seconds = min(delay_seconds * 2, 0.5)
                continue
            if stored.response is None:
                return None
            return self._replay_response(request=request, cached_response=stored.response)
        return None

    def _replay_response(
        self,
        *,
        request: BridgeRequestEnvelope,
        cached_response: BridgeResponseEnvelope,
    ) -> BridgeResponseEnvelope:
        replayed = deepcopy(cached_response)
        replayed["requestId"] = request["requestId"]
        replayed["idempotencyKey"] = request["idempotencyKey"]
        replayed["replayed"] = True
        return self._sanitize_response_for_host(request=request, response=replayed)

    async def _dispatch_started_request(
        self, request: BridgeRequestEnvelope
    ) -> BridgeResponseEnvelope:
        operation = request["operation"]
        if operation == "circulatio.material.store":
            return await self.store_material(request)
        if operation == "circulatio.material.get":
            return await self.get_material(request)
        if operation == "circulatio.material.list":
            return await self.list_materials(request)
        if operation == "circulatio.body.store":
            return await self.store_body_state(request)
        if operation == "circulatio.material.interpret":
            return await self.interpret_material(request)
        if operation == "circulatio.review.threshold":
            return await self.generate_threshold_review(request)
        if operation == "circulatio.review.living_myth":
            return await self.generate_living_myth_review(request)
        if operation == "circulatio.packet.analysis":
            return await self.generate_analysis_packet(request)
        if operation == "circulatio.practice.generate":
            return await self.generate_practice(request)
        if operation == "circulatio.practice.respond":
            return await self.respond_practice(request)
        if operation == "circulatio.feedback.interpretation":
            return await self.record_interpretation_feedback(request)
        if operation == "circulatio.feedback.practice":
            return await self.record_practice_feedback(request)
        if operation == "circulatio.briefs.generate":
            return await self.generate_briefs(request)
        if operation == "circulatio.briefs.respond":
            return await self.respond_brief(request)
        if operation == "circulatio.method_state.respond":
            return await self.process_method_state_response(request)
        if operation == "circulatio.proposals.approve":
            return await self.approve_proposals(request)
        if operation == "circulatio.proposals.reject":
            return await self.reject_proposals(request)
        if operation == "circulatio.proposals.list_pending":
            return await self.list_pending_proposals(request)
        if operation == "circulatio.review.proposals.approve":
            return await self.approve_review_proposals(request)
        if operation == "circulatio.review.proposals.reject":
            return await self.reject_review_proposals(request)
        if operation == "circulatio.review.proposals.list_pending":
            return await self.list_pending_review_proposals(request)
        if operation == "circulatio.entity.revise":
            return await self.revise_entity(request)
        if operation == "circulatio.entity.delete":
            return await self.delete_entity(request)
        if operation == "circulatio.graph.query":
            return await self.query_graph(request)
        if operation == "circulatio.memory.kernel":
            return await self.memory_kernel(request)
        if operation == "circulatio.dashboard.summary":
            return await self.dashboard_summary(request)
        if operation == "circulatio.discovery":
            return await self.discovery(request)
        if operation == "circulatio.summary.alive_today":
            return await self.alive_today(request)
        if operation == "circulatio.journey.page":
            return await self.journey_page(request)
        if operation == "circulatio.journeys.create":
            return await self.create_journey(request)
        if operation == "circulatio.journeys.list":
            return await self.list_journeys(request)
        if operation == "circulatio.journeys.get":
            return await self.get_journey(request)
        if operation == "circulatio.journeys.update":
            return await self.update_journey(request)
        if operation == "circulatio.journeys.set_status":
            return await self.set_journey_status(request)
        if operation == "circulatio.journey.experiment.start":
            return await self.start_journey_experiment(request)
        if operation == "circulatio.journey.experiment.respond":
            return await self.respond_journey_experiment(request)
        if operation == "circulatio.journey.experiment.list":
            return await self.list_journey_experiments(request)
        if operation == "circulatio.journey.experiment.get":
            return await self.get_journey_experiment(request)
        if operation == "circulatio.review.weekly":
            return await self.weekly_review(request)
        if operation == "circulatio.witness.state":
            return await self.get_witness_state(request)
        if operation == "circulatio.conscious_attitude.capture":
            return await self.capture_conscious_attitude(request)
        if operation == "circulatio.individuation.reality_anchors.capture":
            return await self.capture_reality_anchors(request)
        if operation == "circulatio.individuation.threshold_process.upsert":
            return await self.upsert_threshold_process(request)
        if operation == "circulatio.individuation.relational_scene.capture":
            return await self.record_relational_scene(request)
        if operation == "circulatio.individuation.inner_outer_correspondence.capture":
            return await self.record_inner_outer_correspondence(request)
        if operation == "circulatio.individuation.numinous_encounter.capture":
            return await self.record_numinous_encounter(request)
        if operation == "circulatio.individuation.aesthetic_resonance.capture":
            return await self.record_aesthetic_resonance(request)
        if operation == "circulatio.consent.set":
            return await self.set_consent_preference(request)
        if operation == "circulatio.amplification.answer":
            return await self.answer_amplification_prompt(request)
        if operation == "circulatio.goals.upsert":
            return await self.upsert_goal(request)
        if operation == "circulatio.goal_tensions.upsert":
            return await self.upsert_goal_tension(request)
        if operation == "circulatio.culture.frame.set":
            return await self.set_cultural_frame(request)
        if operation in {
            "circulatio.symbols.list",
            "circulatio.symbols.get",
            "circulatio.symbols.history",
        }:
            return await self.list_symbols(request)
        if operation == "circulatio.hypotheses.reject":
            return await self.reject_hypotheses(request)
        raise ValidationError(f"Unsupported Circulatio bridge operation: {operation}")

    async def store_material(self, request: BridgeRequestEnvelope) -> BridgeResponseEnvelope:
        payload = request["payload"]
        material_type = str(payload["materialType"])
        material_input: dict[str, object] = {
            "userId": request["userId"],
            "materialType": material_type,
            **self._store_material_kwargs(payload),
        }
        text = self._optional_string(payload.get("text"))
        if text is not None:
            material_input["text"] = text
        stored = await self._service.store_material_with_intake_context(material_input)  # type: ignore[arg-type]
        material = stored["material"]
        intake_context = stored["intakeContext"]
        continuity_summary = self._continuity_summary(
            cast(dict[str, object] | None, stored.get("continuity"))
        )
        if material_type == "reflection":
            message = "Held your reflection. Want to explore what comes up?"
        elif material_type == "charged_event":
            message = "Held this charged event. Want to stay with it for a moment?"
        elif material_type == "dream":
            message = "Held your dream. If you want, we can open it together."
        elif material_type == "symbolic_motif":
            message = "Held your symbolic note. We can return to it when you want."
        else:
            message = (
                f"Held your {material_type.replace('_', ' ')}. "
                "If you'd like to explore it now, just say so — otherwise it "
                "will stay here for when you return."
            )
        return self._response(
            request=request,
            status="ok",
            message=message,
            result={
                "materialId": material["id"],
                "materialType": material["materialType"],
                "material": deepcopy(material),
                "intakeContext": deepcopy(intake_context),
                **(
                    {"continuitySummary": continuity_summary}
                    if continuity_summary is not None
                    else {}
                ),
            },
            affected_entity_ids=[material["id"]],
        )

    async def get_material(self, request: BridgeRequestEnvelope) -> BridgeResponseEnvelope:
        payload = request["payload"]
        material_id = self._optional_string(payload.get("materialId"))
        if material_id is None:
            raise ValidationError("materialId is required.")
        material = await self._service.get_material(
            user_id=request["userId"],
            material_id=material_id,
            include_deleted=bool(payload.get("includeDeleted", False)),
        )
        return self._response(
            request=request,
            status="ok",
            message=f"Loaded stored {material['materialType'].replace('_', ' ')}.",
            result={
                "materialId": material["id"],
                "materialType": material["materialType"],
                "material": deepcopy(material),
            },
            affected_entity_ids=[material["id"]],
        )

    async def list_materials(self, request: BridgeRequestEnvelope) -> BridgeResponseEnvelope:
        materials = await self._service.list_materials(
            user_id=request["userId"],
            filters=self._material_list_filters(request["payload"]),
        )
        message = "No materials matched." if not materials else f"Found {len(materials)} materials."
        return self._response(
            request=request,
            status="ok",
            message=message,
            result={
                "materials": deepcopy(materials),
                "materialCount": len(materials),
            },
            affected_entity_ids=[item["id"] for item in materials],
        )

    async def store_body_state(self, request: BridgeRequestEnvelope) -> BridgeResponseEnvelope:
        payload = request["payload"]
        stored = await self._service.store_body_state(
            {
                "userId": request["userId"],
                "sensation": str(payload["sensation"]),
                **self._store_body_state_kwargs(payload),
            }
        )
        affected = [stored["bodyState"]["id"]]
        result: dict[str, object] = {
            "bodyStateId": stored["bodyState"]["id"],
        }
        if stored.get("noteMaterial") is not None:
            note_material = stored["noteMaterial"]
            affected.append(note_material["id"])
            result["noteMaterialId"] = note_material["id"]
        return self._response(
            request=request,
            status="ok",
            message=(
                "Held your body state. If it feels right, we can notice it together, "
                "or simply let it be recorded."
            ),
            result=result,
            affected_entity_ids=affected,
        )

    async def interpret_material(self, request: BridgeRequestEnvelope) -> BridgeResponseEnvelope:
        payload = request["payload"]
        material_id = self._optional_string(payload.get("materialId"))
        if material_id is not None:
            workflow = await self._service.interpret_existing_material(
                user_id=request["userId"],
                material_id=material_id,
                **self._interpret_existing_material_kwargs(payload),
            )
        else:
            kwargs = self._material_kwargs(payload)
            material_type = self._optional_string(payload.get("materialType"))
            text = self._optional_string(payload.get("text"))
            if not material_type or not text:
                raise ValidationError("Provide materialId, or provide both materialType and text.")
            workflow = await self._service.create_and_interpret_material(
                {
                    "userId": request["userId"],
                    "materialType": material_type,  # type: ignore[typeddict-item]
                    "text": text,
                    **kwargs,
                }
            )
        run = workflow["run"]
        pending: list[BridgePendingProposal] = []
        if run is not None:
            await self._proposal_alias_index.record_run(
                user_id=request["userId"],
                session_id=request["source"].get("sessionId"),
                run_id=run["id"],
                proposals=workflow["pendingProposals"],
            )
            stored_run = await self._service.get_interpretation_run(
                user_id=request["userId"], run_id=run["id"]
            )
            pending = await self._pending_proposals(
                user_id=request["userId"],
                session_id=request["source"].get("sessionId"),
                run=stored_run,
            )
        interpretation = workflow["interpretation"]
        continuation_state = self._interpretation_continuation_state(
            material_id=workflow["material"]["id"],
            run_id=run["id"],
            interpretation=interpretation,
        )
        result = {
            "materialId": workflow["material"]["id"],
            "runId": run["id"],
            "safetyStatus": interpretation["safetyDisposition"]["status"],
            "llmInterpretationHealth": self._public_interpretation_health(
                interpretation.get("llmInterpretationHealth")
            ),
            "clarifyingQuestion": interpretation.get("clarifyingQuestion"),
            "depthEngineHealth": self._public_interpretation_health(
                interpretation.get("depthEngineHealth")
            ),
            "methodGate": deepcopy(interpretation.get("methodGate")),
        }
        if continuation_state is not None:
            result["continuationState"] = continuation_state
        return self._response(
            request=request,
            status="blocked" if interpretation["safetyDisposition"]["status"] != "clear" else "ok",
            message=interpretation["userFacingResponse"],
            result=result,
            pending_proposals=pending,
            affected_entity_ids=[workflow["material"]["id"], run["id"]],
        )

    async def process_method_state_response(
        self, request: BridgeRequestEnvelope
    ) -> BridgeResponseEnvelope:
        payload = request["payload"]
        workflow = await self._service.process_method_state_response(
            {
                "userId": request["userId"],
                "idempotencyKey": request["idempotencyKey"],
                "source": str(payload.get("source") or ""),
                "responseText": str(payload.get("responseText") or ""),
                **self._method_state_kwargs(payload),
            }
        )
        capture_run = workflow["captureRun"]
        pending: list[BridgePendingProposal] = []
        if workflow["pendingProposals"]:
            await self._proposal_alias_index.record_capture_run(
                user_id=request["userId"],
                session_id=request["source"].get("sessionId"),
                capture_run_id=capture_run["id"],
                proposals=workflow["pendingProposals"],
            )
            pending = await self._pending_capture_proposals(
                user_id=request["userId"],
                session_id=request["source"].get("sessionId"),
                capture_run=capture_run,
            )
        continuation_state = self._method_state_continuation_state(
            source=str(payload.get("source") or ""),
            workflow=workflow,
        )
        message = "Method-state response was processed without durable capture."
        if continuation_state["kind"] in {"context_answer_recorded", "provider_unavailable"}:
            message = "I've kept that with the material."
        elif workflow["pendingProposals"]:
            message = (
                "Method-state response was processed; approval-gated proposals remain pending."
            )
        elif workflow["appliedEntityRefs"]:
            message = "Method-state response was processed and durable method state was updated."
        elif workflow["followUpPrompts"]:
            message = str(workflow["followUpPrompts"][0])
        affected_entity_ids = [workflow["responseMaterial"]["id"], capture_run["id"]]
        affected_entity_ids.extend(
            str(item.get("entityId") or "")
            for item in workflow["appliedEntityRefs"]
            if str(item.get("entityId") or "").strip()
        )
        return self._response(
            request=request,
            status="ok",
            message=message,
            result={
                "captureRunId": capture_run["id"],
                "responseMaterialId": workflow["responseMaterial"]["id"],
                "evidenceIds": [item["id"] for item in workflow["evidence"]],
                "appliedEntityRefs": deepcopy(workflow["appliedEntityRefs"]),
                "followUpPrompts": deepcopy(workflow["followUpPrompts"]),
                "withheldCandidates": deepcopy(workflow["withheldCandidates"]),
                "warnings": deepcopy(workflow["warnings"]),
                "continuationState": continuation_state,
            },
            pending_proposals=pending,
            affected_entity_ids=list(dict.fromkeys(affected_entity_ids)),
        )

    async def generate_practice(self, request: BridgeRequestEnvelope) -> BridgeResponseEnvelope:
        command_result = await self._router.practice(
            user_id=request["userId"],
            payload=deepcopy(request["payload"]),
        )
        result: dict[str, object] = {
            "command": command_result["command"],
            "userFacingResponse": command_result["message"],
        }
        practice_recommendation = command_result.get("practiceRecommendation")
        if isinstance(practice_recommendation, dict):
            result["practiceRecommendation"] = deepcopy(practice_recommendation)
        practice_session = command_result.get("practiceSession")
        if isinstance(practice_session, dict):
            result["practiceSessionId"] = practice_session["id"]
            result["practiceSession"] = deepcopy(practice_session)
        return self._response(
            request=request,
            status=self._bridge_status_for_command(command_result),
            message=command_result["message"],
            result=result,
            affected_entity_ids=command_result.get("affectedEntityIds", []),
        )

    async def generate_threshold_review(
        self, request: BridgeRequestEnvelope
    ) -> BridgeResponseEnvelope:
        command_result = await self._router.threshold_review(
            user_id=request["userId"],
            payload=deepcopy(request["payload"]),
        )
        result: dict[str, object] = {"command": command_result["command"]}
        review = command_result.get("livingMythReview")
        pending: list[BridgePendingProposal] = []
        if isinstance(review, dict):
            result["reviewId"] = review["id"]
            if review.get("windowStart"):
                result["windowStart"] = review["windowStart"]
            if review.get("windowEnd"):
                result["windowEnd"] = review["windowEnd"]
            if review.get("result", {}).get("practiceRecommendation"):
                result["practiceRecommendation"] = deepcopy(
                    review["result"]["practiceRecommendation"]
                )
            if review.get("memoryWritePlan"):
                await self._proposal_alias_index.record_review(
                    user_id=request["userId"],
                    session_id=request["source"].get("sessionId"),
                    review_id=review["id"],
                    proposals=review["memoryWritePlan"].get("proposals", []),
                )
                pending = await self._pending_review_proposals(
                    user_id=request["userId"],
                    session_id=request["source"].get("sessionId"),
                    review=review,
                )
        practice_session = command_result.get("practiceSession")
        if isinstance(practice_session, dict):
            result["practiceSessionId"] = practice_session["id"]
            result["practiceSession"] = deepcopy(practice_session)
        return self._response(
            request=request,
            status=self._bridge_status_for_command(command_result),
            message=self._review_message(
                kind="threshold_review",
                message=command_result["message"],
                review_result=review.get("result") if isinstance(review, dict) else None,
            ),
            result=result,
            pending_proposals=pending,
            affected_entity_ids=command_result.get("affectedEntityIds", []),
        )

    async def generate_living_myth_review(
        self, request: BridgeRequestEnvelope
    ) -> BridgeResponseEnvelope:
        command_result = await self._router.living_myth_review(
            user_id=request["userId"],
            payload=deepcopy(request["payload"]),
        )
        result: dict[str, object] = {"command": command_result["command"]}
        review = command_result.get("livingMythReview")
        pending: list[BridgePendingProposal] = []
        if isinstance(review, dict):
            result["reviewId"] = review["id"]
            if review.get("windowStart"):
                result["windowStart"] = review["windowStart"]
            if review.get("windowEnd"):
                result["windowEnd"] = review["windowEnd"]
            if review.get("result", {}).get("practiceRecommendation"):
                result["practiceRecommendation"] = deepcopy(
                    review["result"]["practiceRecommendation"]
                )
            if review.get("memoryWritePlan"):
                await self._proposal_alias_index.record_review(
                    user_id=request["userId"],
                    session_id=request["source"].get("sessionId"),
                    review_id=review["id"],
                    proposals=review["memoryWritePlan"].get("proposals", []),
                )
                pending = await self._pending_review_proposals(
                    user_id=request["userId"],
                    session_id=request["source"].get("sessionId"),
                    review=review,
                )
        practice_session = command_result.get("practiceSession")
        if isinstance(practice_session, dict):
            result["practiceSessionId"] = practice_session["id"]
            result["practiceSession"] = deepcopy(practice_session)
        return self._response(
            request=request,
            status=self._bridge_status_for_command(command_result),
            message=self._review_message(
                kind="living_myth_review",
                message=command_result["message"],
                review_result=review.get("result") if isinstance(review, dict) else None,
            ),
            result=result,
            pending_proposals=pending,
            affected_entity_ids=command_result.get("affectedEntityIds", []),
        )

    async def generate_analysis_packet(
        self, request: BridgeRequestEnvelope
    ) -> BridgeResponseEnvelope:
        command_result = await self._router.analysis_packet(
            user_id=request["userId"],
            payload=deepcopy(request["payload"]),
        )
        result: dict[str, object] = {"command": command_result["command"]}
        packet_result = command_result.get("analysisPacketResult")
        packet = (
            deepcopy(packet_result)
            if isinstance(packet_result, dict)
            else deepcopy(command_result.get("analysisPacket"))
        )
        packet_record = command_result.get("analysisPacket")
        if (
            isinstance(packet, dict)
            and isinstance(packet_record, dict)
            and "packetId" not in packet
        ):
            packet_id = self._optional_string(packet_record.get("id"))
            if packet_id:
                packet["packetId"] = packet_id
        if isinstance(packet, dict):
            result["analysisPacket"] = packet
        return self._response(
            request=request,
            status=self._bridge_status_for_command(command_result),
            message=self._analysis_packet_message(command_result["message"], packet),
            result=result,
        )

    async def respond_practice(self, request: BridgeRequestEnvelope) -> BridgeResponseEnvelope:
        command_result = await self._router.respond_practice(
            user_id=request["userId"],
            payload=deepcopy(request["payload"]),
        )
        result: dict[str, object] = {"command": command_result["command"]}
        practice_session = command_result.get("practiceSession")
        if isinstance(practice_session, dict):
            result["practiceSessionId"] = practice_session["id"]
            result["practiceSession"] = deepcopy(practice_session)
            result["status"] = practice_session["status"]
        return self._response(
            request=request,
            status=self._bridge_status_for_command(command_result),
            message=command_result["message"],
            result=result,
            affected_entity_ids=command_result.get("affectedEntityIds", []),
        )

    async def record_interpretation_feedback(
        self, request: BridgeRequestEnvelope
    ) -> BridgeResponseEnvelope:
        payload = request["payload"]
        run_id = self._optional_string(payload.get("runId"))
        feedback = self._optional_string(payload.get("feedback"))
        if run_id is None:
            raise ValidationError("runId is required.")
        if feedback is None:
            raise ValidationError("feedback is required.")
        record = await self._service.record_interpretation_feedback(
            user_id=request["userId"],
            run_id=run_id,
            feedback=feedback,
            note=self._optional_string(payload.get("note")),
            locale=self._optional_string(payload.get("locale")),
        )
        return self._response(
            request=request,
            status="ok",
            message="Recorded interpretation feedback.",
            result={
                "feedbackId": record["id"],
                "runId": record["targetId"],
                "feedback": record["feedback"],
                "domain": record["domain"],
                "locale": record.get("locale"),
            },
            affected_entity_ids=[record["id"]],
        )

    async def record_practice_feedback(
        self, request: BridgeRequestEnvelope
    ) -> BridgeResponseEnvelope:
        payload = request["payload"]
        practice_session_id = self._optional_string(payload.get("practiceSessionId"))
        feedback = self._optional_string(payload.get("feedback"))
        if practice_session_id is None:
            recent_practice = await self._service.resolve_recent_practice_session_for_feedback(
                user_id=request["userId"]
            )
            if recent_practice is not None:
                practice_session_id = str(recent_practice["id"])
            else:
                raise ValidationError("practiceSessionId is required.")
        if feedback is None:
            raise ValidationError("feedback is required.")
        record = await self._service.record_practice_feedback(
            user_id=request["userId"],
            practice_session_id=practice_session_id,
            feedback=feedback,
            note=self._optional_string(payload.get("note")),
            locale=self._optional_string(payload.get("locale")),
        )
        return self._response(
            request=request,
            status="ok",
            message="Recorded practice feedback.",
            result={
                "feedbackId": record["id"],
                "practiceSessionId": record["targetId"],
                "feedback": record["feedback"],
                "domain": record["domain"],
                "locale": record.get("locale"),
            },
            affected_entity_ids=[record["id"]],
        )

    async def generate_briefs(self, request: BridgeRequestEnvelope) -> BridgeResponseEnvelope:
        command_result = await self._router.brief(
            user_id=request["userId"],
            payload=deepcopy(request["payload"]),
        )
        briefs = [deepcopy(item) for item in command_result.get("briefs", [])]
        return self._response(
            request=request,
            status=self._bridge_status_for_command(command_result),
            message=command_result["message"],
            result={
                "command": command_result["command"],
                "briefs": briefs,
                "briefIds": [item["id"] for item in briefs],
            },
            affected_entity_ids=command_result.get("affectedEntityIds", []),
        )

    async def respond_brief(self, request: BridgeRequestEnvelope) -> BridgeResponseEnvelope:
        command_result = await self._router.respond_brief(
            user_id=request["userId"],
            payload=deepcopy(request["payload"]),
        )
        result: dict[str, object] = {"command": command_result["command"]}
        brief = command_result.get("brief")
        if isinstance(brief, dict):
            result["briefId"] = brief["id"]
            result["brief"] = deepcopy(brief)
            result["status"] = brief["status"]
        return self._response(
            request=request,
            status=self._bridge_status_for_command(command_result),
            message=command_result["message"],
            result=result,
            affected_entity_ids=command_result.get("affectedEntityIds", []),
        )

    async def approve_proposals(self, request: BridgeRequestEnvelope) -> BridgeResponseEnvelope:
        payload = request["payload"]
        capture_run_id = self._optional_string(payload.get("captureRunId"))
        if capture_run_id is not None:
            capture_run = await self._service.get_method_state_capture_run(
                user_id=request["userId"],
                capture_run_id=capture_run_id,
            )
            plan = capture_run.get("memoryWritePlan") or {"proposals": []}
            pending_ids = self._pending_capture_proposal_ids(capture_run)
            await self._proposal_alias_index.record_capture_run(
                user_id=request["userId"],
                session_id=request["source"].get("sessionId"),
                capture_run_id=capture_run_id,
                proposals=plan.get("proposals", []),
            )
            proposal_ids = await self._proposal_alias_index.resolve_capture_proposal_refs(
                user_id=request["userId"],
                session_id=request["source"].get("sessionId"),
                capture_run_id=capture_run_id,
                proposal_refs=[str(item) for item in payload.get("proposalRefs", [])],
                pending_proposal_ids=pending_ids,
            )
            updated_capture_run = await self._service.approve_method_state_capture_proposals(
                user_id=request["userId"],
                capture_run_id=capture_run_id,
                proposal_ids=proposal_ids,
                integration_note=self._optional_string(payload.get("note")),
            )
            return self._response(
                request=request,
                status="ok",
                message=(
                    "Approved method-state capture proposals were applied to Circulatio memory."
                ),
                result={
                    "captureRunId": capture_run_id,
                    "approvedProposalIds": proposal_ids,
                },
                pending_proposals=await self._pending_capture_proposals(
                    user_id=request["userId"],
                    session_id=request["source"].get("sessionId"),
                    capture_run=updated_capture_run,
                ),
                affected_entity_ids=[capture_run_id],
            )
        run_id = await self._resolve_run_id(
            request=request, run_ref=str(payload.get("runRef") or payload.get("runId") or "last")
        )
        run = await self._service.get_interpretation_run(user_id=request["userId"], run_id=run_id)
        pending_ids = self._pending_proposal_ids(run)
        await self._proposal_alias_index.record_run(
            user_id=request["userId"],
            session_id=request["source"].get("sessionId"),
            run_id=run_id,
            proposals=run["result"]["memoryWritePlan"]["proposals"],
        )
        proposal_ids = await self._proposal_alias_index.resolve_proposal_refs(
            user_id=request["userId"],
            session_id=request["source"].get("sessionId"),
            run_id=run_id,
            proposal_refs=[str(item) for item in payload.get("proposalRefs", [])],
            pending_proposal_ids=pending_ids,
        )
        command_result = await self._router.approve(
            user_id=request["userId"],
            run_id=run_id,
            proposal_ids=proposal_ids,
            note=self._optional_string(payload.get("note")),
        )
        updated_run = await self._service.get_interpretation_run(
            user_id=request["userId"], run_id=run_id
        )
        return self._response(
            request=request,
            status=self._bridge_status_for_command(command_result),
            message=command_result["message"],
            result={
                "command": command_result["command"],
                "runId": run_id,
                "integrationId": command_result.get("integration", {}).get("id"),
                "approvedProposalIds": proposal_ids,
            },
            pending_proposals=await self._pending_proposals(
                user_id=request["userId"],
                session_id=request["source"].get("sessionId"),
                run=updated_run,
            ),
            affected_entity_ids=command_result.get("affectedEntityIds", []),
        )

    async def reject_proposals(self, request: BridgeRequestEnvelope) -> BridgeResponseEnvelope:
        payload = request["payload"]
        capture_run_id = self._optional_string(payload.get("captureRunId"))
        if capture_run_id is not None:
            capture_run = await self._service.get_method_state_capture_run(
                user_id=request["userId"],
                capture_run_id=capture_run_id,
            )
            plan = capture_run.get("memoryWritePlan") or {"proposals": []}
            pending_ids = self._pending_capture_proposal_ids(capture_run)
            await self._proposal_alias_index.record_capture_run(
                user_id=request["userId"],
                session_id=request["source"].get("sessionId"),
                capture_run_id=capture_run_id,
                proposals=plan.get("proposals", []),
            )
            proposal_ids = await self._proposal_alias_index.resolve_capture_proposal_refs(
                user_id=request["userId"],
                session_id=request["source"].get("sessionId"),
                capture_run_id=capture_run_id,
                proposal_refs=[str(item) for item in payload.get("proposalRefs", [])],
                pending_proposal_ids=pending_ids,
            )
            updated_capture_run = await self._service.reject_method_state_capture_proposals(
                user_id=request["userId"],
                capture_run_id=capture_run_id,
                proposal_ids=proposal_ids,
                reason=self._optional_string(payload.get("reason")),
            )
            return self._response(
                request=request,
                status="ok",
                message="Method-state capture proposal rejection was recorded.",
                result={
                    "captureRunId": capture_run_id,
                    "rejectedProposalIds": proposal_ids,
                },
                pending_proposals=await self._pending_capture_proposals(
                    user_id=request["userId"],
                    session_id=request["source"].get("sessionId"),
                    capture_run=updated_capture_run,
                ),
                affected_entity_ids=[capture_run_id],
            )
        run_id = await self._resolve_run_id(
            request=request, run_ref=str(payload.get("runRef") or payload.get("runId") or "last")
        )
        run = await self._service.get_interpretation_run(user_id=request["userId"], run_id=run_id)
        pending_ids = self._pending_proposal_ids(run)
        await self._proposal_alias_index.record_run(
            user_id=request["userId"],
            session_id=request["source"].get("sessionId"),
            run_id=run_id,
            proposals=run["result"]["memoryWritePlan"]["proposals"],
        )
        proposal_ids = await self._proposal_alias_index.resolve_proposal_refs(
            user_id=request["userId"],
            session_id=request["source"].get("sessionId"),
            run_id=run_id,
            proposal_refs=[str(item) for item in payload.get("proposalRefs", [])],
            pending_proposal_ids=pending_ids,
        )
        command_result = await self._router.reject(
            user_id=request["userId"],
            run_id=run_id,
            proposal_ids=proposal_ids,
            reason=self._optional_string(payload.get("reason")),
        )
        updated_run = await self._service.get_interpretation_run(
            user_id=request["userId"], run_id=run_id
        )
        return self._response(
            request=request,
            status=self._bridge_status_for_command(command_result),
            message=command_result["message"],
            result={
                "command": command_result["command"],
                "runId": run_id,
                "integrationId": command_result.get("integration", {}).get("id"),
                "rejectedProposalIds": proposal_ids,
            },
            pending_proposals=await self._pending_proposals(
                user_id=request["userId"],
                session_id=request["source"].get("sessionId"),
                run=updated_run,
            ),
            affected_entity_ids=command_result.get("affectedEntityIds", []),
        )

    async def list_pending_proposals(
        self, request: BridgeRequestEnvelope
    ) -> BridgeResponseEnvelope:
        payload = request["payload"]
        capture_run_id = self._optional_string(payload.get("captureRunId"))
        if capture_run_id is not None:
            capture_run = await self._service.get_method_state_capture_run(
                user_id=request["userId"],
                capture_run_id=capture_run_id,
            )
            pending = await self._pending_capture_proposals(
                user_id=request["userId"],
                session_id=request["source"].get("sessionId"),
                capture_run=capture_run,
            )
            return self._response(
                request=request,
                status="ok",
                message=self._pending_proposals_message(
                    count=len(pending), capture_run=True, review=False
                ),
                result={},
                pending_proposals=pending,
            )
        run_id = await self._resolve_run_id(
            request=request, run_ref=str(payload.get("runRef") or payload.get("runId") or "last")
        )
        run = await self._service.get_interpretation_run(user_id=request["userId"], run_id=run_id)
        pending = await self._pending_proposals(
            user_id=request["userId"],
            session_id=request["source"].get("sessionId"),
            run=run,
        )
        return self._response(
            request=request,
            status="ok",
            message=self._pending_proposals_message(
                count=len(pending), capture_run=False, review=False
            ),
            result={},
            pending_proposals=pending,
        )

    async def approve_review_proposals(
        self, request: BridgeRequestEnvelope
    ) -> BridgeResponseEnvelope:
        payload = request["payload"]
        review_id = await self._resolve_review_id(
            request=request,
            review_ref=self._optional_string(payload.get("reviewId")),
        )
        review = await self._service.repository.get_living_myth_review(request["userId"], review_id)
        pending_ids = self._pending_review_proposal_ids(review)
        plan = review.get("memoryWritePlan") or {"proposals": []}
        await self._proposal_alias_index.record_review(
            user_id=request["userId"],
            session_id=request["source"].get("sessionId"),
            review_id=review_id,
            proposals=plan.get("proposals", []),
        )
        proposal_ids = await self._proposal_alias_index.resolve_review_proposal_refs(
            user_id=request["userId"],
            session_id=request["source"].get("sessionId"),
            review_id=review_id,
            proposal_refs=[str(item) for item in payload.get("proposalRefs", [])],
            pending_proposal_ids=pending_ids,
        )
        updated_review = await self._service.approve_living_myth_review_proposals(
            user_id=request["userId"],
            review_id=review_id,
            proposal_ids=proposal_ids,
        )
        return self._response(
            request=request,
            status="ok",
            message="Approved living myth review proposals were applied to Circulatio memory.",
            result={
                "reviewId": review_id,
                "approvedProposalIds": proposal_ids,
            },
            pending_proposals=await self._pending_review_proposals(
                user_id=request["userId"],
                session_id=request["source"].get("sessionId"),
                review=updated_review,
            ),
            affected_entity_ids=[review_id],
        )

    async def reject_review_proposals(
        self, request: BridgeRequestEnvelope
    ) -> BridgeResponseEnvelope:
        payload = request["payload"]
        review_id = await self._resolve_review_id(
            request=request,
            review_ref=self._optional_string(payload.get("reviewId")),
        )
        review = await self._service.repository.get_living_myth_review(request["userId"], review_id)
        pending_ids = self._pending_review_proposal_ids(review)
        plan = review.get("memoryWritePlan") or {"proposals": []}
        await self._proposal_alias_index.record_review(
            user_id=request["userId"],
            session_id=request["source"].get("sessionId"),
            review_id=review_id,
            proposals=plan.get("proposals", []),
        )
        proposal_ids = await self._proposal_alias_index.resolve_review_proposal_refs(
            user_id=request["userId"],
            session_id=request["source"].get("sessionId"),
            review_id=review_id,
            proposal_refs=[str(item) for item in payload.get("proposalRefs", [])],
            pending_proposal_ids=pending_ids,
        )
        updated_review = await self._service.reject_living_myth_review_proposals(
            user_id=request["userId"],
            review_id=review_id,
            proposal_ids=proposal_ids,
            reason=self._optional_string(payload.get("reason")),
        )
        return self._response(
            request=request,
            status="ok",
            message="Living myth review proposal rejection was recorded.",
            result={
                "reviewId": review_id,
                "rejectedProposalIds": proposal_ids,
            },
            pending_proposals=await self._pending_review_proposals(
                user_id=request["userId"],
                session_id=request["source"].get("sessionId"),
                review=updated_review,
            ),
            affected_entity_ids=[review_id],
        )

    async def list_pending_review_proposals(
        self, request: BridgeRequestEnvelope
    ) -> BridgeResponseEnvelope:
        review_id = await self._resolve_review_id(
            request=request,
            review_ref=self._optional_string(request["payload"].get("reviewId")),
        )
        review = await self._service.repository.get_living_myth_review(request["userId"], review_id)
        pending = await self._pending_review_proposals(
            user_id=request["userId"],
            session_id=request["source"].get("sessionId"),
            review=review,
        )
        return self._response(
            request=request,
            status="ok",
            message=self._pending_proposals_message(
                count=len(pending), capture_run=False, review=True
            ),
            result={"reviewId": review_id},
            pending_proposals=pending,
        )

    async def reject_hypotheses(self, request: BridgeRequestEnvelope) -> BridgeResponseEnvelope:
        payload = request["payload"]
        run_id = str(payload["runId"])
        feedback = payload.get("feedbackByHypothesisId")
        if not isinstance(feedback, dict) or not feedback:
            raise ValidationError("feedbackByHypothesisId is required for hypothesis rejection.")
        command_result = await self._router.reject(
            user_id=request["userId"],
            run_id=run_id,
            feedback_by_hypothesis_id=deepcopy(feedback),
            reason=self._optional_string(payload.get("reason")),
        )
        return self._response(
            request=request,
            status=self._bridge_status_for_command(command_result),
            message=command_result["message"],
            result={
                "command": command_result["command"],
                "runId": run_id,
                "integrationId": command_result.get("integration", {}).get("id"),
            },
            affected_entity_ids=command_result.get("affectedEntityIds", []),
        )

    async def revise_entity(self, request: BridgeRequestEnvelope) -> BridgeResponseEnvelope:
        payload = request["payload"]
        command_result = await self._router.revise(
            user_id=request["userId"],
            entity_type=str(payload["entityType"]),
            entity_id=str(payload["entityId"]),
            revision_note=str(payload["revisionNote"]),
            replacement=deepcopy(payload.get("replacement")),
        )
        return self._response(
            request=request,
            status=self._bridge_status_for_command(command_result),
            message=command_result["message"],
            result={
                "command": command_result["command"],
                "integrationId": command_result.get("integration", {}).get("id"),
            },
            affected_entity_ids=command_result.get("affectedEntityIds", []),
        )

    async def delete_entity(self, request: BridgeRequestEnvelope) -> BridgeResponseEnvelope:
        payload = request["payload"]
        command_result = await self._router.delete(
            user_id=request["userId"],
            entity_type=str(payload["entityType"]),
            entity_id=str(payload["entityId"]),
            mode=str(payload.get("mode", "tombstone")),
            reason=self._optional_string(payload.get("reason")),
        )
        return self._response(
            request=request,
            status=self._bridge_status_for_command(command_result),
            message=command_result["message"],
            result={
                "command": command_result["command"],
                "integrationId": command_result.get("integration", {}).get("id"),
            },
            affected_entity_ids=command_result.get("affectedEntityIds", []),
        )

    async def query_graph(self, request: BridgeRequestEnvelope) -> BridgeResponseEnvelope:
        graph = await self._service.query_graph(
            user_id=request["userId"],
            query=self._graph_query_kwargs(request["payload"]),
        )
        return self._response(
            request=request,
            status="ok",
            message="Loaded Circulatio graph view.",
            result={
                "graph": deepcopy(graph),
                "nodeCount": len(graph["nodes"]),
                "edgeCount": len(graph["edges"]),
            },
        )

    async def memory_kernel(self, request: BridgeRequestEnvelope) -> BridgeResponseEnvelope:
        snapshot = await self._service.build_memory_kernel_snapshot(
            user_id=request["userId"],
            query=self._memory_kernel_query_kwargs(request["payload"]),
        )
        return self._response(
            request=request,
            status="ok",
            message="Loaded Circulatio memory kernel snapshot.",
            result={
                "memoryKernel": deepcopy(snapshot),
                "itemCount": len(snapshot["items"]),
            },
        )

    async def dashboard_summary(self, request: BridgeRequestEnvelope) -> BridgeResponseEnvelope:
        summary = await self._service.get_dashboard_summary(user_id=request["userId"])
        return self._response(
            request=request,
            status="ok",
            message="Loaded Circulatio dashboard summary.",
            result={
                "dashboardSummary": deepcopy(summary),
                "recentMaterialCount": len(summary["recentMaterials"]),
                "recurringSymbolCount": len(summary["recurringSymbols"]),
                "activePatternCount": len(summary["activePatterns"]),
                "pendingProposalCount": summary["pendingProposalCount"],
            },
        )

    async def weekly_review(self, request: BridgeRequestEnvelope) -> BridgeResponseEnvelope:
        payload = request["payload"]
        command_result = await self._router.review_week(
            user_id=request["userId"],
            window_start=str(payload["windowStart"]),
            window_end=str(payload["windowEnd"]),
        )
        review = command_result.get("review")
        result: dict[str, object] = {
            "command": command_result["command"],
            "windowStart": payload["windowStart"],
            "windowEnd": payload["windowEnd"],
        }
        if isinstance(review, dict):
            result["reviewId"] = review["id"]
        return self._response(
            request=request,
            status=self._bridge_status_for_command(command_result),
            message=self._review_message(
                kind="weekly_review",
                message=command_result["message"],
                review_result=review.get("result") if isinstance(review, dict) else None,
            ),
            result=result,
        )

    async def discovery(self, request: BridgeRequestEnvelope) -> BridgeResponseEnvelope:
        payload = request["payload"]
        discovery = await self._service.generate_discovery(
            {
                "userId": request["userId"],
                **{
                    key: deepcopy(value)
                    for key, value in payload.items()
                    if key
                    in {
                        "windowStart",
                        "windowEnd",
                        "explicitQuestion",
                        "textQuery",
                        "rootNodeIds",
                        "memoryNamespaces",
                        "rankingProfile",
                        "maxItems",
                        "analyticLens",
                    }
                },
            }
        )
        return self._response(
            request=request,
            status="ok",
            message=discovery["fallbackText"],
            result={
                "discoveryId": discovery["discoveryId"],
                "windowStart": discovery["windowStart"],
                "windowEnd": discovery["windowEnd"],
                "sectionCount": len(discovery["sections"]),
                "sourceCounts": deepcopy(discovery["sourceCounts"]),
                "discovery": deepcopy(discovery),
            },
        )

    async def get_witness_state(self, request: BridgeRequestEnvelope) -> BridgeResponseEnvelope:
        payload = request["payload"]
        snapshot = await self._service.get_witness_state(
            user_id=request["userId"],
            window_start=str(payload["windowStart"]),
            window_end=str(payload["windowEnd"]),
            material_id=self._optional_string(payload.get("materialId")),
        )
        return self._response(
            request=request,
            status="ok",
            message="Loaded a compact witness-state overview for this window.",
            result={
                "windowStart": snapshot["windowStart"],
                "windowEnd": snapshot["windowEnd"],
                "witnessStateSummary": self._witness_state_summary(snapshot),
            },
        )

    async def capture_conscious_attitude(
        self, request: BridgeRequestEnvelope
    ) -> BridgeResponseEnvelope:
        payload = request["payload"]
        record = await self._service.capture_conscious_attitude(
            {
                "userId": request["userId"],
                "windowStart": str(payload["windowStart"]),
                "windowEnd": str(payload["windowEnd"]),
                "stanceSummary": str(payload["stanceSummary"]),
                **{
                    key: deepcopy(value)
                    for key, value in payload.items()
                    if key
                    in {
                        "activeValues",
                        "activeConflicts",
                        "avoidedThemes",
                        "emotionalTone",
                        "egoPosition",
                        "confidence",
                        "relatedMaterialIds",
                        "relatedGoalIds",
                        "privacyClass",
                    }
                },
            }
        )
        return self._response(
            request=request,
            status="ok",
            message="Captured conscious attitude.",
            result={
                "consciousAttitudeId": record["id"],
                "windowStart": record["windowStart"],
                "windowEnd": record["windowEnd"],
            },
            affected_entity_ids=[record["id"]],
        )

    async def capture_reality_anchors(
        self, request: BridgeRequestEnvelope
    ) -> BridgeResponseEnvelope:
        command_result = await self._router.capture_reality_anchors(
            user_id=request["userId"],
            payload=deepcopy(request["payload"]),
        )
        record = command_result.get("individuationRecord") or {}
        return self._response(
            request=request,
            status=self._bridge_status_for_command(command_result),
            message=command_result["message"],
            result=self._individuation_record_result(record),
            affected_entity_ids=command_result.get("affectedEntityIds", []),
        )

    async def upsert_threshold_process(
        self, request: BridgeRequestEnvelope
    ) -> BridgeResponseEnvelope:
        command_result = await self._router.upsert_threshold_process(
            user_id=request["userId"],
            payload=deepcopy(request["payload"]),
        )
        record = command_result.get("individuationRecord") or {}
        return self._response(
            request=request,
            status=self._bridge_status_for_command(command_result),
            message=command_result["message"],
            result=self._individuation_record_result(record),
            affected_entity_ids=command_result.get("affectedEntityIds", []),
        )

    async def record_relational_scene(
        self, request: BridgeRequestEnvelope
    ) -> BridgeResponseEnvelope:
        command_result = await self._router.record_relational_scene(
            user_id=request["userId"],
            payload=deepcopy(request["payload"]),
        )
        record = command_result.get("individuationRecord") or {}
        return self._response(
            request=request,
            status=self._bridge_status_for_command(command_result),
            message=command_result["message"],
            result=self._individuation_record_result(record),
            affected_entity_ids=command_result.get("affectedEntityIds", []),
        )

    async def record_inner_outer_correspondence(
        self, request: BridgeRequestEnvelope
    ) -> BridgeResponseEnvelope:
        command_result = await self._router.record_inner_outer_correspondence(
            user_id=request["userId"],
            payload=deepcopy(request["payload"]),
        )
        record = command_result.get("individuationRecord") or {}
        return self._response(
            request=request,
            status=self._bridge_status_for_command(command_result),
            message=command_result["message"],
            result=self._individuation_record_result(record),
            affected_entity_ids=command_result.get("affectedEntityIds", []),
        )

    async def record_numinous_encounter(
        self, request: BridgeRequestEnvelope
    ) -> BridgeResponseEnvelope:
        command_result = await self._router.record_numinous_encounter(
            user_id=request["userId"],
            payload=deepcopy(request["payload"]),
        )
        record = command_result.get("individuationRecord") or {}
        return self._response(
            request=request,
            status=self._bridge_status_for_command(command_result),
            message=command_result["message"],
            result=self._individuation_record_result(record),
            affected_entity_ids=command_result.get("affectedEntityIds", []),
        )

    async def record_aesthetic_resonance(
        self, request: BridgeRequestEnvelope
    ) -> BridgeResponseEnvelope:
        command_result = await self._router.record_aesthetic_resonance(
            user_id=request["userId"],
            payload=deepcopy(request["payload"]),
        )
        record = command_result.get("individuationRecord") or {}
        return self._response(
            request=request,
            status=self._bridge_status_for_command(command_result),
            message=command_result["message"],
            result=self._individuation_record_result(record),
            affected_entity_ids=command_result.get("affectedEntityIds", []),
        )

    async def set_consent_preference(
        self, request: BridgeRequestEnvelope
    ) -> BridgeResponseEnvelope:
        payload = request["payload"]
        record = await self._service.set_consent_preference(
            {
                "userId": request["userId"],
                "scope": str(payload["scope"]),
                "status": str(payload["status"]),
                "note": self._optional_string(payload.get("note")),
                "source": self._optional_string(payload.get("source")),
            }
        )
        return self._response(
            request=request,
            status="ok",
            message="Updated consent preference.",
            result={
                "consentPreferenceId": record["id"],
                "scope": record["scope"],
                "status": record["status"],
            },
            affected_entity_ids=[record["id"]],
        )

    async def answer_amplification_prompt(
        self, request: BridgeRequestEnvelope
    ) -> BridgeResponseEnvelope:
        payload = request["payload"]
        record = await self._service.answer_amplification_prompt(
            {
                "userId": request["userId"],
                **{key: deepcopy(value) for key, value in payload.items()},
            }
        )
        return self._response(
            request=request,
            status="ok",
            message="Stored personal amplification.",
            result={
                "personalAmplificationId": record["id"],
                "promptId": record.get("promptId"),
                "canonicalName": record["canonicalName"],
            },
            affected_entity_ids=[record["id"]],
        )

    async def upsert_goal(self, request: BridgeRequestEnvelope) -> BridgeResponseEnvelope:
        record = await self._service.upsert_goal(
            {
                "userId": request["userId"],
                **{key: deepcopy(value) for key, value in request["payload"].items()},
            }
        )
        return self._response(
            request=request,
            status="ok",
            message="Updated goal record.",
            result={"goalId": record["id"], "status": record["status"]},
            affected_entity_ids=[record["id"]],
        )

    async def upsert_goal_tension(self, request: BridgeRequestEnvelope) -> BridgeResponseEnvelope:
        record = await self._service.upsert_goal_tension(
            {
                "userId": request["userId"],
                **{key: deepcopy(value) for key, value in request["payload"].items()},
            }
        )
        return self._response(
            request=request,
            status="ok",
            message="Updated goal tension.",
            result={"goalTensionId": record["id"], "status": record["status"]},
            affected_entity_ids=[record["id"]],
        )

    async def set_cultural_frame(self, request: BridgeRequestEnvelope) -> BridgeResponseEnvelope:
        record = await self._service.set_cultural_frame(
            {
                "userId": request["userId"],
                **{key: deepcopy(value) for key, value in request["payload"].items()},
            }
        )
        return self._response(
            request=request,
            status="ok",
            message="Updated cultural frame.",
            result={"culturalFrameId": record["id"], "status": record["status"]},
            affected_entity_ids=[record["id"]],
        )

    async def alive_today(self, request: BridgeRequestEnvelope) -> BridgeResponseEnvelope:
        payload = request["payload"]
        workflow = await self._service.generate_alive_today(
            user_id=request["userId"],
            window_start=self._optional_string(payload.get("windowStart")),
            window_end=self._optional_string(payload.get("windowEnd")),
            explicit_question=self._optional_string(payload.get("explicitQuestion")),
        )
        summary = workflow["summary"]
        continuity_summary = self._continuity_summary(
            cast(dict[str, object] | None, workflow.get("continuity"))
        )
        message = str(summary["userFacingResponse"])
        follow_up_question = self._optional_string(summary.get("followUpQuestion"))
        suggested_action = self._optional_string(summary.get("suggestedAction"))
        if follow_up_question and follow_up_question not in message and len(message) < 160:
            message = f"{message} {follow_up_question}"
        result: dict[str, object] = {
            "summaryId": summary["summaryId"],
            "windowStart": summary["windowStart"],
            "windowEnd": summary["windowEnd"],
        }
        if follow_up_question:
            result["followUpQuestion"] = follow_up_question
        if suggested_action:
            result["suggestedAction"] = suggested_action
        if continuity_summary is not None:
            result["continuitySummary"] = continuity_summary
        return self._response(
            request=request,
            status="ok",
            message=message,
            result=result,
        )

    async def journey_page(self, request: BridgeRequestEnvelope) -> BridgeResponseEnvelope:
        payload = request["payload"]
        page = await self._service.generate_journey_page(
            {
                "userId": request["userId"],
                **{
                    key: deepcopy(value)
                    for key, value in payload.items()
                    if key
                    in {
                        "windowStart",
                        "windowEnd",
                        "explicitQuestion",
                        "maxInvitations",
                        "includeAnalysisPacket",
                    }
                },
            }
        )
        continuity_summary = self._continuity_summary(
            cast(dict[str, object] | None, page.get("continuity"))
        )
        return self._response(
            request=request,
            status="ok",
            message="Loaded a compact journey overview for the requested window.",
            result={
                "journeyPage": page,
                "windowStart": page["windowStart"],
                "windowEnd": page["windowEnd"],
                "journeyPageSummary": self._journey_page_summary(page),
                **(
                    {"continuitySummary": continuity_summary}
                    if continuity_summary is not None
                    else {}
                ),
            },
        )

    async def create_journey(self, request: BridgeRequestEnvelope) -> BridgeResponseEnvelope:
        payload = request["payload"]
        journey = await self._service.create_journey(
            {
                "userId": request["userId"],
                **{
                    key: deepcopy(value)
                    for key, value in payload.items()
                    if key
                    in {
                        "label",
                        "currentQuestion",
                        "relatedMaterialIds",
                        "relatedSymbolIds",
                        "relatedPatternIds",
                        "relatedDreamSeriesIds",
                        "relatedGoalIds",
                        "nextReviewDueAt",
                        "status",
                    }
                },
            }
        )
        return self._response(
            request=request,
            status="ok",
            message=f'Opened journey "{journey["label"]}".',
            result={
                "journeyId": journey["id"],
                "journey": deepcopy(journey),
            },
            affected_entity_ids=[journey["id"]],
        )

    async def list_journeys(self, request: BridgeRequestEnvelope) -> BridgeResponseEnvelope:
        payload = request["payload"]
        journeys = await self._service.list_journeys(
            {
                "userId": request["userId"],
                **{
                    key: deepcopy(value)
                    for key, value in payload.items()
                    if key in {"statuses", "includeDeleted", "limit"}
                },
            }
        )
        message = "No journeys matched." if not journeys else f"Found {len(journeys)} journeys."
        return self._response(
            request=request,
            status="ok",
            message=message,
            result={
                "journeys": [self._journey_summary(item) for item in journeys],
                "journeyCount": len(journeys),
            },
            affected_entity_ids=[item["id"] for item in journeys],
        )

    async def get_journey(self, request: BridgeRequestEnvelope) -> BridgeResponseEnvelope:
        payload = request["payload"]
        journey = await self._service.get_journey(
            {
                "userId": request["userId"],
                **self._journey_reference_payload(payload),
                **{
                    key: deepcopy(value)
                    for key, value in payload.items()
                    if key == "includeDeleted"
                },
            }
        )
        return self._response(
            request=request,
            status="ok",
            message=f'Loaded journey "{journey["label"]}".',
            result={
                "journey": self._journey_summary(journey),
            },
        )

    async def update_journey(self, request: BridgeRequestEnvelope) -> BridgeResponseEnvelope:
        payload = request["payload"]
        journey = await self._service.update_journey(
            {
                "userId": request["userId"],
                **self._journey_reference_payload(payload),
                **{
                    key: deepcopy(value)
                    for key, value in payload.items()
                    if key
                    in {
                        "label",
                        "currentQuestion",
                        "addRelatedMaterialIds",
                        "removeRelatedMaterialIds",
                        "addRelatedSymbolIds",
                        "removeRelatedSymbolIds",
                        "addRelatedPatternIds",
                        "removeRelatedPatternIds",
                        "addRelatedDreamSeriesIds",
                        "removeRelatedDreamSeriesIds",
                        "addRelatedGoalIds",
                        "removeRelatedGoalIds",
                        "nextReviewDueAt",
                    }
                },
            }
        )
        return self._response(
            request=request,
            status="ok",
            message=f'Updated journey "{journey["label"]}".',
            result={
                "journeyId": journey["id"],
                "journey": deepcopy(journey),
            },
            affected_entity_ids=[journey["id"]],
        )

    async def set_journey_status(self, request: BridgeRequestEnvelope) -> BridgeResponseEnvelope:
        payload = request["payload"]
        status = self._optional_string(payload.get("status"))
        if not status:
            raise ValidationError("status is required.")
        journey = await self._service.set_journey_status(
            {
                "userId": request["userId"],
                **self._journey_reference_payload(payload),
                "status": status,  # type: ignore[typeddict-item]
            }
        )
        return self._response(
            request=request,
            status="ok",
            message=f'Set journey "{journey["label"]}" to {journey["status"]}.',
            result={
                "journeyId": journey["id"],
                "journey": deepcopy(journey),
            },
            affected_entity_ids=[journey["id"]],
        )

    async def start_journey_experiment(
        self, request: BridgeRequestEnvelope
    ) -> BridgeResponseEnvelope:
        payload = request["payload"]
        experiment = await self._service.start_journey_experiment(
            {
                "userId": request["userId"],
                **{
                    key: deepcopy(value)
                    for key, value in payload.items()
                    if key
                    in {
                        "briefId",
                        "journeyId",
                        "journeyLabel",
                        "surface",
                        "windowStart",
                        "windowEnd",
                        "source",
                        "title",
                        "summary",
                        "bodyFirst",
                        "preferredMoveKind",
                        "currentQuestion",
                        "suggestedActionText",
                    }
                },
            }
        )
        return self._response(
            request=request,
            status="ok",
            message="Started current tending for this journey.",
            result={
                "experimentId": experiment["id"],
                "journeyExperiment": self._journey_experiment_summary(experiment),
            },
            affected_entity_ids=[experiment["id"], cast(Id, experiment["journeyId"])],
        )

    async def respond_journey_experiment(
        self, request: BridgeRequestEnvelope
    ) -> BridgeResponseEnvelope:
        payload = request["payload"]
        action = self._optional_string(payload.get("action"))
        experiment_id = self._optional_string(payload.get("experimentId"))
        if not action or not experiment_id:
            raise ValidationError("experimentId and action are required.")
        experiment = await self._service.respond_journey_experiment(
            {
                "userId": request["userId"],
                "experimentId": experiment_id,
                "action": action,  # type: ignore[typeddict-item]
                **{
                    key: deepcopy(value)
                    for key, value in payload.items()
                    if key == "nextCheckInDueAt"
                },
            }
        )
        return self._response(
            request=request,
            status="ok",
            message=f'Updated current tending via "{action}".',
            result={
                "experimentId": experiment["id"],
                "journeyExperiment": self._journey_experiment_summary(experiment),
            },
            affected_entity_ids=[experiment["id"], cast(Id, experiment["journeyId"])],
        )

    async def list_journey_experiments(
        self, request: BridgeRequestEnvelope
    ) -> BridgeResponseEnvelope:
        payload = request["payload"]
        experiments = await self._service.list_journey_experiments(
            {
                "userId": request["userId"],
                **{
                    key: deepcopy(value)
                    for key, value in payload.items()
                    if key in {"journeyId", "journeyLabel", "statuses", "includeDeleted", "limit"}
                },
            }
        )
        count = len(experiments)
        return self._response(
            request=request,
            status="ok",
            message=(
                "No journey-tending frames matched."
                if count == 0
                else f"Found {count} journey-tending frame{'s' if count != 1 else ''}."
            ),
            result={
                "journeyExperiments": [
                    self._journey_experiment_summary(item) for item in experiments
                ],
                "experimentCount": count,
            },
            affected_entity_ids=[item["id"] for item in experiments],
        )

    async def get_journey_experiment(
        self, request: BridgeRequestEnvelope
    ) -> BridgeResponseEnvelope:
        payload = request["payload"]
        experiment_id = self._optional_string(payload.get("experimentId"))
        if not experiment_id:
            raise ValidationError("experimentId is required.")
        experiment = await self._service.get_journey_experiment(
            {
                "userId": request["userId"],
                "experimentId": experiment_id,
                **{
                    key: deepcopy(value)
                    for key, value in payload.items()
                    if key == "includeDeleted"
                },
            }
        )
        return self._response(
            request=request,
            status="ok",
            message="Loaded current tending.",
            result={
                "experimentId": experiment["id"],
                "journeyExperiment": self._journey_experiment_summary(experiment),
            },
            affected_entity_ids=[experiment["id"]],
        )

    async def list_symbols(self, request: BridgeRequestEnvelope) -> BridgeResponseEnvelope:
        payload = request["payload"]
        include_history = bool(
            payload.get("includeHistory", False)
            or request["operation"] == "circulatio.symbols.history"
        )
        command_result = await self._router.symbols(
            user_id=request["userId"],
            symbol_id=self._optional_string(payload.get("symbolId")),
            symbol_name=self._optional_string(payload.get("symbolName")),
            include_history=include_history,
        )
        symbols = [deepcopy(item) for item in command_result.get("symbols", [])]
        result: dict[str, object] = {"command": command_result["command"], "symbols": symbols}
        if len(symbols) == 1:
            result["symbolId"] = symbols[0]["id"]
        if command_result.get("symbolHistory"):
            result["history"] = deepcopy(command_result["symbolHistory"])
        if command_result.get("linkedMaterials"):
            result["linkedMaterials"] = deepcopy(command_result["linkedMaterials"])
        return self._response(
            request=request,
            status=self._bridge_status_for_command(command_result),
            message=command_result["message"],
            result=result,
            affected_entity_ids=command_result.get("affectedEntityIds", []),
        )

    async def _resolve_run_id(self, *, request: BridgeRequestEnvelope, run_ref: str) -> Id:
        try:
            return await self._proposal_alias_index.resolve_run_ref(
                user_id=request["userId"],
                session_id=request["source"].get("sessionId"),
                run_ref=run_ref,
            )
        except EntityNotFoundError:
            if run_ref != "last":
                raise
            runs = await self._service.list_interpretation_runs(user_id=request["userId"], limit=1)
            if not runs:
                raise
            await self._proposal_alias_index.record_run(
                user_id=request["userId"],
                session_id=request["source"].get("sessionId"),
                run_id=runs[0]["id"],
                proposals=runs[0]["result"]["memoryWritePlan"]["proposals"],
            )
            return runs[0]["id"]

    async def _pending_proposals(
        self,
        *,
        user_id: Id,
        session_id: str | None,
        run: InterpretationRunRecord,
    ) -> list[BridgePendingProposal]:
        pending_ids = self._pending_proposal_ids(run)
        if not pending_ids:
            return []
        await self._proposal_alias_index.record_run(
            user_id=user_id,
            session_id=session_id,
            run_id=run["id"],
            proposals=run["result"]["memoryWritePlan"]["proposals"],
        )
        aliases = await self._proposal_alias_index.list_pending_aliases(
            user_id=user_id,
            session_id=session_id,
            run_id=run["id"],
            pending_proposal_ids=pending_ids,
        )
        alias_by_id = {proposal_id: alias for alias, proposal_id in aliases}
        pending: list[BridgePendingProposal] = []
        for proposal in run["result"]["memoryWritePlan"]["proposals"]:
            proposal_id = proposal["id"]
            if proposal_id not in pending_ids:
                continue
            pending.append(
                {
                    "alias": alias_by_id.get(proposal_id, proposal_id),
                    "id": proposal_id,
                    "action": proposal["action"],
                    "entityType": proposal["entityType"],
                    "reason": proposal["reason"],
                    "evidenceIds": list(proposal["evidenceIds"]),
                    "payload": deepcopy(proposal["payload"]),
                    "sourceKind": "interpretation_run",
                    "sourceId": run["id"],
                }
            )
        return pending

    async def _pending_review_proposals(
        self,
        *,
        user_id: Id,
        session_id: str | None,
        review: LivingMythReviewRecord,
    ) -> list[BridgePendingProposal]:
        pending_ids = self._pending_review_proposal_ids(review)
        if not pending_ids:
            return []
        plan = review.get("memoryWritePlan") or {"proposals": []}
        await self._proposal_alias_index.record_review(
            user_id=user_id,
            session_id=session_id,
            review_id=review["id"],
            proposals=plan.get("proposals", []),
        )
        aliases = await self._proposal_alias_index.list_review_pending_aliases(
            user_id=user_id,
            session_id=session_id,
            review_id=review["id"],
            pending_proposal_ids=pending_ids,
        )
        alias_by_id = {proposal_id: alias for alias, proposal_id in aliases}
        pending: list[BridgePendingProposal] = []
        for proposal in plan.get("proposals", []):
            proposal_id = proposal["id"]
            if proposal_id not in pending_ids:
                continue
            pending.append(
                {
                    "alias": alias_by_id.get(proposal_id, proposal_id),
                    "id": proposal_id,
                    "action": proposal["action"],
                    "entityType": proposal["entityType"],
                    "reason": proposal["reason"],
                    "evidenceIds": list(proposal["evidenceIds"]),
                    "payload": deepcopy(proposal["payload"]),
                    "sourceKind": "living_myth_review",
                    "sourceId": review["id"],
                }
            )
        return pending

    async def _pending_capture_proposals(
        self,
        *,
        user_id: Id,
        session_id: str | None,
        capture_run: MethodStateCaptureRunRecord,
    ) -> list[BridgePendingProposal]:
        pending_ids = self._pending_capture_proposal_ids(capture_run)
        if not pending_ids:
            return []
        plan = capture_run.get("memoryWritePlan") or {"proposals": []}
        await self._proposal_alias_index.record_capture_run(
            user_id=user_id,
            session_id=session_id,
            capture_run_id=capture_run["id"],
            proposals=plan.get("proposals", []),
        )
        aliases = await self._proposal_alias_index.list_capture_pending_aliases(
            user_id=user_id,
            session_id=session_id,
            capture_run_id=capture_run["id"],
            pending_proposal_ids=pending_ids,
        )
        alias_by_id = {proposal_id: alias for alias, proposal_id in aliases}
        pending: list[BridgePendingProposal] = []
        for proposal in plan.get("proposals", []):
            proposal_id = proposal["id"]
            if proposal_id not in pending_ids:
                continue
            pending.append(
                {
                    "alias": alias_by_id.get(proposal_id, proposal_id),
                    "id": proposal_id,
                    "action": proposal["action"],
                    "entityType": proposal["entityType"],
                    "reason": proposal["reason"],
                    "evidenceIds": list(proposal["evidenceIds"]),
                    "payload": deepcopy(proposal["payload"]),
                    "sourceKind": "method_state_capture",
                    "sourceId": capture_run["id"],
                }
            )
        return pending

    def _pending_proposal_ids(self, run: InterpretationRunRecord) -> list[Id]:
        decisions = {
            decision["proposalId"]: decision["status"]
            for decision in run.get("proposalDecisions", [])
        }
        return [
            proposal["id"]
            for proposal in run["result"]["memoryWritePlan"]["proposals"]
            if decisions.get(proposal["id"], "pending") == "pending"
        ]

    def _pending_capture_proposal_ids(self, capture_run: MethodStateCaptureRunRecord) -> list[Id]:
        plan = capture_run.get("memoryWritePlan") or {"proposals": []}
        decisions = {
            decision["proposalId"]: decision["status"]
            for decision in capture_run.get("proposalDecisions", [])
        }
        return [
            proposal["id"]
            for proposal in plan.get("proposals", [])
            if decisions.get(proposal["id"], "pending") == "pending"
        ]

    def _pending_review_proposal_ids(self, review: LivingMythReviewRecord) -> list[Id]:
        plan = review.get("memoryWritePlan") or {"proposals": []}
        decisions = {
            decision["proposalId"]: decision["status"]
            for decision in review.get("proposalDecisions", [])
        }
        return [
            proposal["id"]
            for proposal in plan.get("proposals", [])
            if decisions.get(proposal["id"], "pending") == "pending"
        ]

    def _material_kwargs(self, payload: dict[str, object]) -> dict[str, object]:
        allowed_keys = {
            "materialDate",
            "privacyClass",
            "sessionContext",
            "lifeContextSnapshot",
            "lifeOsWindow",
            "userAssociations",
            "explicitQuestion",
            "culturalOrigins",
            "safetyContext",
            "options",
            "source",
            "title",
            "summary",
            "tags",
            "dreamStructure",
        }
        return {key: deepcopy(value) for key, value in payload.items() if key in allowed_keys}

    def _interpret_existing_material_kwargs(self, payload: dict[str, object]) -> dict[str, object]:
        key_map = {
            "sessionContext": "session_context",
            "lifeContextSnapshot": "life_context_snapshot",
            "lifeOsWindow": "life_os_window",
            "userAssociations": "user_associations",
            "explicitQuestion": "explicit_question",
            "culturalOrigins": "cultural_origins",
            "safetyContext": "safety_context",
            "options": "options",
            "dreamStructure": "dream_structure",
        }
        return {
            target_key: deepcopy(payload[source_key])
            for source_key, target_key in key_map.items()
            if source_key in payload
        }

    def _store_material_kwargs(self, payload: dict[str, object]) -> dict[str, object]:
        allowed_keys = {
            "materialDate",
            "privacyClass",
            "source",
            "title",
            "summary",
            "tags",
            "dreamStructure",
        }
        return {key: deepcopy(value) for key, value in payload.items() if key in allowed_keys}

    def _store_body_state_kwargs(self, payload: dict[str, object]) -> dict[str, object]:
        allowed_keys = {
            "observedAt",
            "bodyRegion",
            "activation",
            "tone",
            "temporalContext",
            "linkedGoalIds",
            "privacyClass",
            "noteText",
        }
        return {key: deepcopy(value) for key, value in payload.items() if key in allowed_keys}

    def _method_state_kwargs(self, payload: dict[str, object]) -> dict[str, object]:
        allowed_keys = {
            "observedAt",
            "anchorRefs",
            "expectedTargets",
            "privacyClass",
            "sessionContext",
            "lifeContextSnapshot",
            "safetyContext",
            "options",
        }
        return {key: deepcopy(value) for key, value in payload.items() if key in allowed_keys}

    def _material_list_filters(self, payload: dict[str, object]) -> dict[str, object] | None:
        allowed_keys = {"materialTypes", "statuses", "tags", "includeDeleted", "limit"}
        filters = {key: deepcopy(value) for key, value in payload.items() if key in allowed_keys}
        return filters or None

    def _graph_query_kwargs(self, payload: dict[str, object]) -> dict[str, object]:
        allowed_keys = {
            "rootNodeIds",
            "nodeTypes",
            "edgeTypes",
            "maxDepth",
            "direction",
            "includeEvidence",
            "limit",
        }
        return {key: deepcopy(value) for key, value in payload.items() if key in allowed_keys}

    def _memory_kernel_query_kwargs(self, payload: dict[str, object]) -> dict[str, object]:
        allowed_keys = {
            "namespaces",
            "relatedEntityIds",
            "windowStart",
            "windowEnd",
            "privacyClasses",
            "textQuery",
            "rankingProfile",
            "limit",
        }
        return {key: deepcopy(value) for key, value in payload.items() if key in allowed_keys}

    async def _resolve_review_id(
        self,
        *,
        request: BridgeRequestEnvelope,
        review_ref: str | None,
    ) -> Id:
        if review_ref is not None:
            return review_ref
        reviews = await self._service.repository.list_living_myth_reviews(
            request["userId"],
            limit=1,
        )
        if not reviews:
            raise EntityNotFoundError("No recent living-myth or threshold review was found.")
        return reviews[0]["id"]

    def _bridge_status_for_command(self, result: HermesCommandResult) -> BridgeStatus:
        mapping: dict[str, BridgeStatus] = {
            "ok": "ok",
            "blocked": "blocked",
            "not_found": "not_found",
            "error": "error",
        }
        return mapping[result["status"]]

    def _interpretation_continuation_state(
        self,
        *,
        material_id: Id,
        run_id: Id,
        interpretation: dict[str, object],
    ) -> dict[str, object] | None:
        clarifying_question = self._optional_string(interpretation.get("clarifyingQuestion"))
        method_gate = interpretation.get("methodGate")
        method_gate_waiting = isinstance(method_gate, dict) and (
            any(str(item).strip() for item in method_gate.get("missingPrerequisites", []))
            or any(str(item).strip() for item in method_gate.get("requiredPrompts", []))
            or self._optional_string(method_gate.get("depthLevel"))
            in {
                "grounding_only",
                "observations_only",
                "personal_amplification_needed",
                "cautious_pattern_note",
            }
        )
        if not clarifying_question and not method_gate_waiting:
            return None
        reason = "clarifying_question" if clarifying_question else "method_gate"
        llm_health = interpretation.get("llmInterpretationHealth")
        depth_engine_health = interpretation.get("depthEngineHealth")
        if (
            isinstance(llm_health, dict)
            and self._optional_string(llm_health.get("source")) == "fallback"
        ) or (
            isinstance(depth_engine_health, dict)
            and self._optional_string(depth_engine_health.get("source")) == "fallback"
        ):
            reason = "fallback_collaborative_opening"
        anchor_refs: dict[str, object] = {"materialId": material_id, "runId": run_id}
        expected_targets: list[str] = []
        storage_policy = "await_new_input"
        clarification_intent = interpretation.get("clarificationIntent")
        if isinstance(clarification_intent, dict):
            ref_key = self._optional_string(clarification_intent.get("refKey"))
            if ref_key:
                anchor_refs["clarificationRefKey"] = ref_key
            expected_targets = [
                str(item)
                for item in clarification_intent.get("expectedTargets", [])
                if str(item).strip()
            ]
            storage_policy = (
                self._optional_string(clarification_intent.get("storagePolicy")) or storage_policy
            )
        return {
            "kind": "waiting_for_follow_up",
            "reason": reason,
            "anchorRefs": anchor_refs,
            "expectedTargets": expected_targets,
            "storagePolicy": storage_policy,
            "doNotRetryInterpretMaterialWithUnchangedMaterial": True,
            "nextTool": "circulatio_method_state_respond",
        }

    def _method_state_continuation_state(
        self,
        *,
        source: str,
        workflow: dict[str, object],
    ) -> dict[str, object]:
        warnings = {str(item) for item in workflow.get("warnings", []) if str(item).strip()}
        provider_unavailable = bool(
            warnings
            & {
                "method_state_routing_timeout",
                "method_state_routing_provider_failed",
                "method_state_routing_contract_failed",
            }
        )
        if provider_unavailable:
            kind = "provider_unavailable"
        elif workflow.get("pendingProposals"):
            kind = "proposal_pending"
        elif workflow.get("appliedEntityRefs"):
            kind = "capture_completed"
        elif source == "clarifying_answer":
            kind = "context_answer_recorded"
        else:
            kind = "no_capture"
        return {
            "kind": kind,
            "doNotRetryInterpretMaterialWithUnchangedMaterial": True,
            "nextAction": "await_user_input",
        }

    def _journey_page_summary(self, page: dict[str, object]) -> dict[str, object]:
        summary: dict[str, object] = {
            "title": self._optional_string(page.get("title")) or "Journey overview",
            "windowStart": page.get("windowStart"),
            "windowEnd": page.get("windowEnd"),
        }
        alive_today = page.get("aliveToday")
        if isinstance(alive_today, dict):
            response = self._optional_string(alive_today.get("response"))
            if response:
                summary["aliveToday"] = response
        weekly_surface = page.get("weeklySurface")
        if isinstance(weekly_surface, dict):
            weekly_summary = self._optional_string(weekly_surface.get("summary"))
            if weekly_summary:
                summary["weeklyReflection"] = weekly_summary
        invitations = page.get("rhythmicInvitations")
        if isinstance(invitations, list) and invitations:
            summary["rhythmicInvitationCount"] = len(invitations)
        practice_container = page.get("practiceContainer")
        if isinstance(practice_container, dict):
            practice_summary = self._optional_string(practice_container.get("summary"))
            if practice_summary:
                summary["practiceFollowUp"] = self._plain_practice_follow_up(practice_summary)
        analysis_packet = page.get("analysisPacket")
        if isinstance(analysis_packet, dict):
            sections = analysis_packet.get("sections")
            if isinstance(sections, list) and sections:
                summary["analysisPreviewSections"] = [
                    self._journey_section_label(str(item.get("title") or "Section"))
                    for item in sections[:4]
                    if isinstance(item, dict) and str(item.get("title") or "").strip()
                ]
        return summary

    def _continuity_summary(
        self,
        continuity: dict[str, object] | None,
        *,
        max_threads: int = 5,
    ) -> dict[str, object] | None:
        if not isinstance(continuity, dict):
            return None
        summary: dict[str, object] = {}
        for key in ("generatedAt", "windowStart", "windowEnd"):
            value = self._optional_string(continuity.get(key))
            if value is not None:
                summary[key] = value
        thread_digests = [
            item for item in continuity.get("threadDigests", []) if isinstance(item, dict)
        ]
        summary["threadCount"] = len(thread_digests)
        threads: list[dict[str, object]] = []
        for digest in thread_digests[: max(max_threads, 0)]:
            compact: dict[str, object] = {}
            for key in ("threadKey", "kind", "status", "summary", "lastTouchedAt"):
                value = self._optional_string(digest.get(key))
                if value is not None:
                    compact[key] = value
            surface_readiness = digest.get("surfaceReadiness")
            if isinstance(surface_readiness, dict):
                compact["surfaceReadiness"] = deepcopy(surface_readiness)
            journey_ids = [
                value
                for value in (
                    self._optional_string(item) for item in digest.get("journeyIds", [])[:3]
                )
                if value is not None
            ]
            if journey_ids:
                compact["journeyIds"] = journey_ids
            if compact:
                threads.append(compact)
        summary["threads"] = threads
        method_context = continuity.get("methodContextSnapshot")
        if isinstance(method_context, dict):
            witness_state = method_context.get("witnessState")
            if isinstance(witness_state, dict):
                witness_summary = self._witness_state_summary(witness_state)
                max_questions = witness_state.get("maxQuestionsPerTurn")
                if isinstance(max_questions, int):
                    witness_summary["maxQuestionsPerTurn"] = max_questions
                reasons = witness_state.get("reasons")
                if isinstance(reasons, list):
                    visible_reasons = [str(item).strip() for item in reasons if str(item).strip()]
                    if visible_reasons:
                        witness_summary["reasons"] = visible_reasons[:3]
                if witness_summary:
                    summary["witnessState"] = witness_summary
            coach_state = method_context.get("coachState")
            selected_move = (
                coach_state.get("selectedMove") if isinstance(coach_state, dict) else None
            )
            if isinstance(selected_move, dict):
                selected_summary: dict[str, object] = {}
                loop_key = self._optional_string(selected_move.get("loopKey"))
                if loop_key:
                    selected_summary["loopKey"] = loop_key
                kind = self._optional_string(selected_move.get("kind"))
                if kind:
                    selected_summary["kind"] = kind
                title = self._optional_string(selected_move.get("titleHint"))
                if title:
                    selected_summary["title"] = title
                selected_move_summary = self._optional_string(selected_move.get("summaryHint"))
                if selected_move_summary:
                    selected_summary["summary"] = selected_move_summary
                if selected_summary:
                    summary["selectedCoachMove"] = selected_summary
        return summary

    def _journey_summary(self, journey: dict[str, object]) -> dict[str, object]:
        summary: dict[str, object] = {
            "label": self._optional_string(journey.get("label")) or "Journey",
        }
        journey_id = self._optional_string(journey.get("id"))
        if journey_id:
            summary["id"] = journey_id
        status = self._optional_string(journey.get("status"))
        if status:
            summary["status"] = status
        current_question = self._optional_string(journey.get("currentQuestion"))
        if current_question:
            summary["currentQuestion"] = current_question
        next_review_due_at = self._optional_string(journey.get("nextReviewDueAt"))
        if next_review_due_at:
            summary["nextReviewDueAt"] = next_review_due_at
        return summary

    def _journey_experiment_summary(self, experiment: dict[str, object]) -> dict[str, object]:
        summary: dict[str, object] = {
            "title": self._optional_string(experiment.get("title")) or "Current tending",
            "summary": self._optional_string(experiment.get("summary"))
            or "A current tending frame is active.",
        }
        for key in ("id", "journeyId", "status", "source", "preferredMoveKind", "currentQuestion"):
            value = self._optional_string(experiment.get(key))
            if value is not None:
                summary[key] = value
        if "bodyFirst" in experiment:
            summary["bodyFirst"] = bool(experiment.get("bodyFirst"))
        for key in ("relatedPracticeSessionIds", "relatedBriefIds"):
            values = [
                item
                for item in (self._optional_string(value) for value in experiment.get(key, []))
                if item is not None
            ]
            if values:
                summary[key] = values
        updated_at = self._optional_string(experiment.get("updatedAt"))
        if updated_at is not None:
            summary["updatedAt"] = updated_at
        return summary

    def _journey_section_label(self, title: str) -> str:
        mapping = {
            "Life context": "Alltag und Umfeld",
            "Method context": "Innere Haltung",
            "Live threads": "Lebendige Fäden",
            "Practice context": "Praxis",
        }
        return mapping.get(title, title)

    def _plain_practice_follow_up(self, summary: str) -> str:
        if "interpretation model is unavailable" in summary.lower():
            return "Bleib vorerst nah am Material und in deinen eigenen Worten."
        return summary

    def _material_summary(self, material: dict[str, object]) -> dict[str, object]:
        summary: dict[str, object] = {
            "materialType": str(material.get("materialType") or "material"),
        }
        material_id = self._optional_string(material.get("id"))
        if material_id:
            summary["id"] = material_id
        title = self._optional_string(material.get("title"))
        if title:
            summary["title"] = title
        text = self._optional_string(material.get("text"))
        if text:
            summary["text"] = text
        material_summary = self._optional_string(material.get("summary"))
        if material_summary:
            summary["summary"] = material_summary
        material_date = self._optional_string(material.get("materialDate"))
        if material_date:
            summary["materialDate"] = material_date
        tags = material.get("tags")
        if isinstance(tags, list):
            visible_tags = [str(item).strip() for item in tags if str(item).strip()]
            if visible_tags:
                summary["tags"] = visible_tags[:5]
        return summary

    def _analysis_packet_host_result(self, packet: object) -> dict[str, object]:
        if not isinstance(packet, dict):
            return {}
        summary: dict[str, object] = {}
        packet_id = self._optional_string(packet.get("packetId"))
        if packet_id:
            summary["packetId"] = packet_id
        packet_title = self._optional_string(packet.get("packetTitle"))
        if packet_title:
            summary["packetTitle"] = packet_title
        sections = packet.get("sections")
        if isinstance(sections, list):
            preview_sections: list[dict[str, object]] = []
            for section in sections[:4]:
                if not isinstance(section, dict):
                    continue
                title = self._optional_string(section.get("title")) or "Section"
                preview: dict[str, object] = {"title": title}
                item_lines: list[str] = []
                items = section.get("items")
                if isinstance(items, list):
                    for item in items[:3]:
                        if not isinstance(item, dict):
                            continue
                        label = self._optional_string(item.get("label"))
                        item_summary = self._optional_string(item.get("summary"))
                        if label and item_summary:
                            item_lines.append(f"{label}: {item_summary}")
                        elif item_summary:
                            item_lines.append(item_summary)
                        elif label:
                            item_lines.append(label)
                if item_lines:
                    preview["items"] = item_lines
                else:
                    purpose = self._optional_string(section.get("purpose"))
                    if purpose:
                        preview["summary"] = purpose
                preview_sections.append(preview)
            if preview_sections:
                summary["sectionPreview"] = preview_sections
        function_dynamics = packet.get("functionDynamics")
        if isinstance(function_dynamics, dict):
            function_summary: dict[str, object] = {}
            status = self._optional_string(function_dynamics.get("status"))
            if status:
                function_summary["status"] = status
            summary_text = self._optional_string(function_dynamics.get("summary"))
            if summary_text:
                function_summary["summary"] = summary_text
            for source_key, target_key in (
                ("foregroundFunctions", "foregroundFunctions"),
                ("compensatoryFunctions", "compensatoryFunctions"),
                ("backgroundFunctions", "backgroundFunctions"),
            ):
                values = function_dynamics.get(source_key)
                if isinstance(values, list):
                    visible = [str(item).strip() for item in values if str(item).strip()]
                    if visible:
                        function_summary[target_key] = visible[:4]
            if function_summary:
                summary["functionDynamics"] = function_summary
            if status in {"signals_only", "insufficient_evidence"}:
                summary["replyPlan"] = "bounded_discovery_same_window"
                summary["recoveryHint"] = (
                    "Use a single bounded discovery read in the same window before making a "
                    "stronger typology claim."
                )
        if (
            "replyPlan" not in summary
            and self._optional_string(packet.get("source")) == "bounded_fallback"
        ):
            summary["replyPlan"] = "bounded_discovery_same_window"
        if "recoveryHint" not in summary:
            recovery_hint = self._optional_string(packet.get("recoveryHint"))
            if recovery_hint:
                summary["recoveryHint"] = recovery_hint
        if summary.get("functionDynamics"):
            summary["replyStyle"] = "tentative_typology"
            summary["maxSentences"] = 5
        return summary

    def _witness_state_summary(self, snapshot: dict[str, object]) -> dict[str, object]:
        summary: dict[str, object] = {}
        stance = self._optional_string(snapshot.get("stance"))
        if stance:
            summary["stance"] = stance.replace("_", " ")
        tone = self._optional_string(snapshot.get("tone"))
        if tone:
            summary["tone"] = tone
        reasons = snapshot.get("reasons")
        if isinstance(reasons, list):
            visible_reasons = [str(item).strip() for item in reasons if str(item).strip()]
            if visible_reasons:
                summary["focus"] = visible_reasons[:2]
        return summary

    def _review_message(
        self,
        *,
        kind: str,
        message: str,
        review_result: object,
    ) -> str:
        fallback_messages = {
            "weekly_review": (
                "A quieter weekly reflection is available for this window. "
                "Stay close to the material that is already here."
            ),
            "threshold_review": (
                "A threshold reflection is not available for this window right now. "
                "Offer a plain weekly reflection or a concise evidence summary "
                "instead, without speculating about why."
            ),
            "living_myth_review": (
                "A living-myth reflection is not available right now. "
                "We can stay with the material that is already here instead."
            ),
        }
        if isinstance(review_result, dict):
            llm_health = review_result.get("llmHealth")
            source = (
                self._optional_string(llm_health.get("source"))
                if isinstance(llm_health, dict)
                else None
            )
            if source == "fallback":
                return fallback_messages.get(kind, message)
            return message
        lowered = message.lower()
        if (
            "model path" not in lowered
            and "speicherkonflikt" not in lowered
            and "storage conflict" not in lowered
        ):
            return message
        return fallback_messages.get(kind, message)

    def _analysis_packet_message(self, message: str, packet: object) -> str:
        if isinstance(packet, dict):
            function_dynamics = (
                packet.get("functionDynamics")
                if isinstance(packet.get("functionDynamics"), dict)
                else {}
            )
            function_status = self._optional_string(function_dynamics.get("status"))
            if function_status == "readable":
                return (
                    "Use the returned function-dynamics summary for a brief tentative typology "
                    "answer."
                )
            if function_status in {"signals_only", "insufficient_evidence"}:
                return (
                    "Make one same-window recovery read for this typology request, then answer "
                    "briefly."
                )
        if (
            isinstance(packet, dict)
            and self._optional_string(packet.get("source")) == "bounded_fallback"
        ):
            return (
                "Make one same-window recovery read for this typology request, then answer briefly."
            )
        if "bounded packet" in message.lower():
            return (
                "Make one same-window recovery read for this typology request, then answer briefly."
            )
        return message

    def _pending_proposals_message(self, *, count: int, capture_run: bool, review: bool) -> str:
        if count == 0:
            if review:
                return "There are no approval-gated review suggestions waiting right now."
            if capture_run:
                return "There are no approval-gated follow-up suggestions waiting right now."
            return "There are no approval-gated suggestions waiting right now."
        if review:
            return (
                f"There {'is' if count == 1 else 'are'} {count} approval-gated "
                f"review suggestion{'s' if count != 1 else ''} waiting."
            )
        if capture_run:
            return (
                f"There {'is' if count == 1 else 'are'} {count} approval-gated "
                f"follow-up suggestion{'s' if count != 1 else ''} waiting."
            )
        return (
            f"There {'is' if count == 1 else 'are'} {count} approval-gated "
            f"suggestion{'s' if count != 1 else ''} waiting."
        )

    def _sanitize_response_for_host(
        self,
        *,
        request: BridgeRequestEnvelope,
        response: BridgeResponseEnvelope,
    ) -> BridgeResponseEnvelope:
        sanitized = deepcopy(response)
        operation = request["operation"]
        result = sanitized.get("result", {})
        if not isinstance(result, dict):
            result = {}
            sanitized["result"] = result
        if operation == "circulatio.material.list":
            materials = result.get("materials")
            if isinstance(materials, list):
                sanitized["result"] = {
                    "materials": [
                        self._material_summary(item) for item in materials if isinstance(item, dict)
                    ],
                    "materialCount": result.get("materialCount", len(materials)),
                }
                sanitized["affectedEntityIds"] = []
            return sanitized
        if operation == "circulatio.journey.page":
            page = result.get("journeyPage")
            continuity = (
                page.get("continuity") if isinstance(page, dict) else result.get("continuity")
            )
            continuity_summary = result.get("continuitySummary")
            if not isinstance(continuity_summary, dict):
                continuity_summary = self._continuity_summary(
                    cast(dict[str, object] | None, continuity)
                )
            if isinstance(page, dict) or "journeyPageSummary" in result:
                sanitized["message"] = "Loaded a compact journey overview for the requested window."
                sanitized_result: dict[str, object] = {
                    "windowStart": (
                        page.get("windowStart")
                        if isinstance(page, dict)
                        else result.get("windowStart")
                    ),
                    "windowEnd": (
                        page.get("windowEnd") if isinstance(page, dict) else result.get("windowEnd")
                    ),
                    "journeyPageSummary": (
                        self._journey_page_summary(page)
                        if isinstance(page, dict)
                        else result.get("journeyPageSummary")
                    ),
                }
                if isinstance(page, dict):
                    sanitized_result["journeyPage"] = page
                if isinstance(continuity_summary, dict):
                    sanitized_result["continuitySummary"] = continuity_summary
                sanitized["result"] = sanitized_result
                sanitized["affectedEntityIds"] = []
            return sanitized
        if operation == "circulatio.journeys.get":
            journey = result.get("journey")
            if isinstance(journey, dict):
                sanitized["result"] = {"journey": self._journey_summary(journey)}
                sanitized["affectedEntityIds"] = []
            return sanitized
        if operation == "circulatio.journeys.list":
            journeys = result.get("journeys")
            if isinstance(journeys, list):
                sanitized["result"] = {
                    "journeys": [
                        self._journey_summary(item) for item in journeys if isinstance(item, dict)
                    ],
                    "journeyCount": result.get("journeyCount", len(journeys)),
                }
                sanitized["affectedEntityIds"] = []
            return sanitized
        if operation in {
            "circulatio.journey.experiment.start",
            "circulatio.journey.experiment.respond",
            "circulatio.journey.experiment.get",
        }:
            experiment = result.get("journeyExperiment")
            if isinstance(experiment, dict):
                sanitized["result"] = {
                    "experimentId": experiment.get("id", result.get("experimentId")),
                    "journeyExperiment": self._journey_experiment_summary(experiment),
                }
                sanitized["affectedEntityIds"] = []
            return sanitized
        if operation == "circulatio.journey.experiment.list":
            experiments = result.get("journeyExperiments")
            if isinstance(experiments, list):
                sanitized["result"] = {
                    "journeyExperiments": [
                        self._journey_experiment_summary(item)
                        for item in experiments
                        if isinstance(item, dict)
                    ],
                    "experimentCount": result.get("experimentCount", len(experiments)),
                }
                sanitized["affectedEntityIds"] = []
            return sanitized
        if operation == "circulatio.witness.state":
            snapshot = result.get("witnessState")
            if isinstance(snapshot, dict):
                sanitized["message"] = "Loaded a compact witness-state overview for this window."
                sanitized["result"] = {
                    "windowStart": snapshot.get("windowStart"),
                    "windowEnd": snapshot.get("windowEnd"),
                    "witnessStateSummary": self._witness_state_summary(snapshot),
                }
            return sanitized
        if operation == "circulatio.review.weekly":
            sanitized["message"] = self._review_message(
                kind="weekly_review",
                message=sanitized.get("message", ""),
                review_result=None,
            )
            sanitized["affectedEntityIds"] = []
            return sanitized
        if operation == "circulatio.review.threshold":
            sanitized["message"] = self._review_message(
                kind="threshold_review",
                message=sanitized.get("message", ""),
                review_result=None,
            )
            sanitized["affectedEntityIds"] = []
            return sanitized
        if operation == "circulatio.review.living_myth":
            sanitized["message"] = self._review_message(
                kind="living_myth_review",
                message=sanitized.get("message", ""),
                review_result=None,
            )
            sanitized["affectedEntityIds"] = []
            return sanitized
        if operation == "circulatio.packet.analysis":
            packet = result.get("analysisPacket")
            sanitized["message"] = self._analysis_packet_message(
                sanitized.get("message", ""),
                packet,
            )
            sanitized["result"] = self._analysis_packet_host_result(packet)
            sanitized["affectedEntityIds"] = []
            return sanitized
        if operation == "circulatio.material.interpret":
            sanitized_result: dict[str, object] = {}
            for key in (
                "materialId",
                "runId",
                "safetyStatus",
                "llmInterpretationHealth",
                "clarifyingQuestion",
                "depthEngineHealth",
                "methodGate",
                "continuationState",
            ):
                if key in result:
                    sanitized_result[key] = deepcopy(result[key])
            sanitized["result"] = sanitized_result
            sanitized["affectedEntityIds"] = []
            return sanitized
        if operation == "circulatio.proposals.list_pending":
            pending = sanitized.get("pendingProposals", [])
            sanitized["message"] = self._pending_proposals_message(
                count=len(pending) if isinstance(pending, list) else 0,
                capture_run=bool(result.get("captureRunId")),
                review=False,
            )
            sanitized["result"] = {}
            return sanitized
        if operation == "circulatio.review.proposals.list_pending":
            pending = sanitized.get("pendingProposals", [])
            sanitized["message"] = self._pending_proposals_message(
                count=len(pending) if isinstance(pending, list) else 0,
                capture_run=False,
                review=True,
            )
            sanitized["result"] = {}
            return sanitized
        return sanitized

    def _validate_request(self, request: BridgeRequestEnvelope) -> BridgeResponseEnvelope | None:
        if not request.get("idempotencyKey"):
            return self._response(
                request=request,
                status="validation_error",
                message="An idempotency key is required for Circulatio bridge operations.",
                errors=[
                    self._error(
                        "missing_idempotency_key",
                        "An idempotency key is required.",
                        retryable=False,
                    )
                ],
            )
        if not request.get("requestId"):
            return self._response(
                request=request,
                status="validation_error",
                message="A request id is required for Circulatio bridge operations.",
                errors=[
                    self._error("missing_request_id", "A request id is required.", retryable=False)
                ],
            )
        if not request.get("userId"):
            return self._response(
                request=request,
                status="validation_error",
                message="A user id is required for Circulatio bridge operations.",
                errors=[self._error("missing_user_id", "A user id is required.", retryable=False)],
            )
        payload = request.get("payload")
        if not isinstance(payload, dict):
            return self._response(
                request=request,
                status="validation_error",
                message="Circulatio bridge payloads must be JSON objects.",
                errors=[
                    self._error(
                        "invalid_payload", "The request payload must be an object.", retryable=False
                    )
                ],
            )
        source = request.get("source")
        if not isinstance(source, dict):
            return self._response(
                request=request,
                status="validation_error",
                message="Circulatio bridge source metadata is required.",
                errors=[
                    self._error(
                        "invalid_source", "The request source must be an object.", retryable=False
                    )
                ],
            )
        return None

    def _response(
        self,
        *,
        request: BridgeRequestEnvelope,
        status: BridgeStatus,
        message: str,
        result: dict[str, object] | None = None,
        pending_proposals: list[BridgePendingProposal] | None = None,
        affected_entity_ids: list[Id] | None = None,
        errors: list[BridgeError] | None = None,
    ) -> BridgeResponseEnvelope:
        return {
            "requestId": str(request.get("requestId") or create_id("bridge_req")),
            "idempotencyKey": str(request.get("idempotencyKey") or ""),
            "replayed": False,
            "status": status,
            "message": message,
            "result": result or {},
            "pendingProposals": pending_proposals or [],
            "affectedEntityIds": affected_entity_ids or [],
            "errors": errors or [],
        }

    def _exception_response(
        self, request: BridgeRequestEnvelope, exc: Exception
    ) -> BridgeResponseEnvelope:
        if isinstance(exc, ValidationError):
            return self._response(
                request=request,
                status="validation_error",
                message=str(exc),
                errors=[self._error("validation_error", str(exc), retryable=False)],
            )
        if isinstance(exc, (EntityNotFoundError, EntityDeletedError)):
            return self._response(
                request=request,
                status="not_found",
                message=str(exc),
                errors=[self._error("not_found", str(exc), retryable=False)],
            )
        if isinstance(exc, ProfileStorageConflictError):
            return self._response(
                request=request,
                status="conflict",
                message="This reflection is not available right now. Please try again shortly.",
                errors=[
                    self._error(
                        "profile_storage_conflict",
                        "This reflection is not available right now.",
                        retryable=False,
                    )
                ],
            )
        if isinstance(exc, ProfileStorageCorruptionError):
            return self._response(
                request=request,
                status="error",
                message="This reflection could not be completed right now.",
                errors=[
                    self._error(
                        "profile_storage_corruption",
                        "This reflection could not be completed right now.",
                        retryable=False,
                    )
                ],
            )
        if isinstance(exc, PersistenceError):
            code = "profile_storage_unavailable" if exc.retryable else "profile_storage_error"
            status: BridgeStatus = "retryable_error" if exc.retryable else "error"
            return self._response(
                request=request,
                status=status,
                message="Circulatio could not complete this request right now.",
                errors=[
                    self._error(
                        code,
                        "Circulatio could not complete this request right now.",
                        retryable=exc.retryable,
                    )
                ],
            )
        if isinstance(exc, ConflictError):
            message = str(exc)
            return self._response(
                request=request,
                status="conflict",
                message=message,
                errors=[
                    self._error(
                        "conflict",
                        message,
                        retryable=False,
                    )
                ],
            )
        if isinstance(exc, CirculatioError):
            return self._response(
                request=request,
                status="error",
                message="Circulatio could not complete this request right now.",
                errors=[
                    self._error(
                        "circulatio_error",
                        "Circulatio could not complete this request right now.",
                        retryable=False,
                    )
                ],
            )
        return self._response(
            request=request,
            status="error",
            message="Circulatio encountered an unexpected error.",
            errors=[
                self._error(
                    "unexpected_error",
                    f"{type(exc).__name__}: {exc}",
                    retryable=False,
                )
            ],
        )

    def _append_error(
        self,
        response: BridgeResponseEnvelope,
        *,
        code: str,
        message: str,
        retryable: bool,
        suffix: str,
    ) -> BridgeResponseEnvelope:
        updated = deepcopy(response)
        updated["errors"] = [
            *updated.get("errors", []),
            self._error(code, message, retryable=retryable),
        ]
        if suffix and suffix not in updated["message"]:
            updated["message"] = f"{updated['message']}{suffix}".strip()
        return updated

    def _error(self, code: str, message: str, *, retryable: bool) -> BridgeError:
        return {"code": code, "message": message, "retryable": retryable}

    def _request_hash(self, request: BridgeRequestEnvelope) -> str:
        payload = {
            "operation": request["operation"],
            "userId": request["userId"],
            "payload": request["payload"],
        }
        encoded = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), default=self._json_default
        )
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    def _json_default(self, value: object) -> object:
        if isinstance(value, set):
            return sorted(value)
        return str(value)

    def _optional_string(self, value: object | None) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def _public_interpretation_health(self, value: object) -> dict[str, object] | None:
        if not isinstance(value, dict):
            return None
        status = self._optional_string(value.get("status"))
        source = self._optional_string(value.get("source"))
        reason = self._optional_string(value.get("reason"))
        if status is None and source is None and reason is None:
            return None
        result: dict[str, object] = {}
        if status is not None:
            result["status"] = status
        if source is not None:
            result["source"] = source
        if reason is not None:
            result["reason"] = reason
        return result

    def _journey_reference_payload(self, payload: dict[str, object]) -> dict[str, str]:
        journey_id = self._optional_string(payload.get("journeyId"))
        journey_label = self._optional_string(payload.get("journeyLabel"))
        if not journey_id and not journey_label:
            raise ValidationError("journeyId or journeyLabel is required.")
        result: dict[str, str] = {}
        if journey_id is not None:
            result["journeyId"] = journey_id
        if journey_label is not None:
            result["journeyLabel"] = journey_label
        return result

    def _individuation_record_result(self, record: dict[str, object]) -> dict[str, object]:
        return {
            "individuationRecordId": record.get("id"),
            "recordType": record.get("recordType"),
        }
