from __future__ import annotations

from typing import Literal, NotRequired, Required, TypedDict

from ..application.circulatio_service import CirculatioService
from ..domain.errors import EntityNotFoundError
from ..domain.graph import GraphNodeType
from ..domain.individuation import IndividuationRecord
from ..domain.integration import IntegrationRecord
from ..domain.interpretations import InterpretationRunRecord
from ..domain.living_myth import AnalysisPacketRecord, LivingMythReviewRecord
from ..domain.materials import MaterialRecord
from ..domain.patterns import PatternRecord
from ..domain.practices import PracticeSessionRecord
from ..domain.presentation import (
    PresentationCostEstimate,
    PresentationRenderRequest,
    PresentationRitualPlan,
)
from ..domain.proactive import ProactiveBriefRecord
from ..domain.reviews import WeeklyReviewRecord
from ..domain.symbols import SymbolHistoryEntry, SymbolRecord
from ..domain.types import (
    AnalysisPacketResult,
    FeedbackValue,
    Id,
    InterpretationResult,
    MemoryWriteProposal,
    PracticePlan,
)


class HermesCommandResult(TypedDict, total=False):
    command: Required[str]
    userId: Required[Id]
    status: Required[Literal["ok", "blocked", "not_found", "error"]]
    message: Required[str]
    material: NotRequired[MaterialRecord]
    run: NotRequired[InterpretationRunRecord]
    interpretation: NotRequired[InterpretationResult]
    review: NotRequired[WeeklyReviewRecord]
    livingMythReview: NotRequired[LivingMythReviewRecord]
    analysisPacket: NotRequired[AnalysisPacketRecord]
    analysisPacketResult: NotRequired[AnalysisPacketResult]
    individuationRecord: NotRequired[IndividuationRecord]
    practiceSession: NotRequired[PracticeSessionRecord]
    practiceRecommendation: NotRequired[PracticePlan]
    ritualPlan: NotRequired[PresentationRitualPlan]
    costEstimate: NotRequired[PresentationCostEstimate]
    renderRequest: NotRequired[PresentationRenderRequest]
    warnings: NotRequired[list[str]]
    continuity: NotRequired[dict[str, object]]
    brief: NotRequired[ProactiveBriefRecord]
    briefs: NotRequired[list[ProactiveBriefRecord]]
    symbols: NotRequired[list[SymbolRecord]]
    patterns: NotRequired[list[PatternRecord]]
    integration: NotRequired[IntegrationRecord]
    pendingProposals: NotRequired[list[MemoryWriteProposal]]
    symbolHistory: NotRequired[list[SymbolHistoryEntry]]
    linkedMaterials: NotRequired[list[MaterialRecord]]
    affectedEntityIds: NotRequired[list[Id]]


class HermesCirculationCommandRouter:
    def __init__(self, service: CirculatioService) -> None:
        self._service = service

    async def dream(self, *, user_id: Id, text: str, **kwargs: object) -> HermesCommandResult:
        workflow = await self._service.create_and_interpret_material(
            {"userId": user_id, "materialType": "dream", "text": text, **kwargs}
        )
        return self._workflow_result("/circulation dream", user_id, workflow)

    async def reflect(self, *, user_id: Id, text: str, **kwargs: object) -> HermesCommandResult:
        workflow = await self._service.create_and_interpret_material(
            {"userId": user_id, "materialType": "reflection", "text": text, **kwargs}
        )
        return self._workflow_result("/circulation reflect", user_id, workflow)

    async def event(self, *, user_id: Id, text: str, **kwargs: object) -> HermesCommandResult:
        workflow = await self._service.create_and_interpret_material(
            {"userId": user_id, "materialType": "charged_event", "text": text, **kwargs}
        )
        return self._workflow_result("/circulation event", user_id, workflow)

    async def review_week(
        self,
        *,
        user_id: Id,
        window_start: str,
        window_end: str,
    ) -> HermesCommandResult:
        review = await self._service.generate_weekly_review(
            user_id=user_id,
            window_start=window_start,
            window_end=window_end,
        )
        return {
            "command": "/circulation review week",
            "userId": user_id,
            "status": "ok",
            "message": review["result"]["userFacingResponse"],
            "review": review,
            "affectedEntityIds": [review["id"]],
        }

    async def threshold_review(
        self,
        *,
        user_id: Id,
        payload: dict[str, object],
    ) -> HermesCommandResult:
        workflow = await self._service.generate_threshold_review({"userId": user_id, **payload})
        affected = []
        if workflow.get("review") is not None:
            affected.append(workflow["review"]["id"])
        if workflow.get("practiceSession") is not None:
            affected.append(workflow["practiceSession"]["id"])
        return {
            "command": "/circulation review threshold",
            "userId": user_id,
            "status": "ok",
            "message": workflow["result"]["userFacingResponse"],
            "livingMythReview": workflow.get("review"),
            "practiceRecommendation": workflow["result"].get("practiceRecommendation"),
            "practiceSession": workflow.get("practiceSession"),
            "pendingProposals": workflow.get("pendingProposals", []),
            "affectedEntityIds": affected,
        }

    async def living_myth_review(
        self,
        *,
        user_id: Id,
        payload: dict[str, object],
    ) -> HermesCommandResult:
        workflow = await self._service.generate_living_myth_review({"userId": user_id, **payload})
        affected = []
        if workflow.get("review") is not None:
            affected.append(workflow["review"]["id"])
        if workflow.get("practiceSession") is not None:
            affected.append(workflow["practiceSession"]["id"])
        return {
            "command": "/circulation review living-myth",
            "userId": user_id,
            "status": "ok",
            "message": workflow["result"]["userFacingResponse"],
            "livingMythReview": workflow.get("review"),
            "practiceRecommendation": workflow["result"].get("practiceRecommendation"),
            "practiceSession": workflow.get("practiceSession"),
            "pendingProposals": workflow.get("pendingProposals", []),
            "affectedEntityIds": affected,
        }

    async def analysis_packet(
        self,
        *,
        user_id: Id,
        payload: dict[str, object],
    ) -> HermesCommandResult:
        workflow = await self._service.generate_analysis_packet({"userId": user_id, **payload})
        affected = [workflow["packet"]["id"]] if workflow.get("packet") is not None else []
        return {
            "command": "/circulation packet",
            "userId": user_id,
            "status": "ok",
            "message": workflow["result"]["userFacingResponse"],
            "analysisPacket": workflow.get("packet"),
            "analysisPacketResult": workflow["result"],
            "affectedEntityIds": affected,
        }

    async def practice(
        self,
        *,
        user_id: Id,
        payload: dict[str, object],
    ) -> HermesCommandResult:
        workflow = await self._service.generate_practice_recommendation(
            {"userId": user_id, **payload}
        )
        affected = [workflow["practiceSession"]["id"]] if workflow.get("practiceSession") else []
        return {
            "command": "/circulation practice",
            "userId": user_id,
            "status": "ok",
            "message": workflow["userFacingResponse"],
            "practiceRecommendation": workflow["practiceRecommendation"],
            "practiceSession": workflow.get("practiceSession"),
            "affectedEntityIds": affected,
        }

    async def plan_ritual(
        self,
        *,
        user_id: Id,
        payload: dict[str, object],
    ) -> HermesCommandResult:
        workflow = await self._service.plan_ritual({"userId": user_id, **payload})
        plan = workflow["plan"]
        return {
            "command": "/circulation ritual plan",
            "userId": user_id,
            "status": "ok",
            "message": (
                "Prepared a ritual plan. "
                "Render it through the Hermes Rituals artifact renderer."
            ),
            "ritualPlan": plan,
            "costEstimate": workflow["costEstimate"],
            "renderRequest": workflow["renderRequest"],
            "warnings": workflow.get("warnings", []),
            "continuity": workflow.get("continuity"),
            "affectedEntityIds": [],
        }

    async def respond_practice(
        self,
        *,
        user_id: Id,
        payload: dict[str, object],
    ) -> HermesCommandResult:
        result = await self._service.respond_practice_recommendation({"userId": user_id, **payload})
        action = str(payload["action"])
        practice = result["practiceSession"]
        return {
            "command": f"/circulation practice {'accept' if action == 'accepted' else 'skip'}",
            "userId": user_id,
            "status": "ok",
            "message": "Practice accepted." if action == "accepted" else "Practice skipped.",
            "practiceSession": practice,
            "continuity": result.get("continuity"),
            "affectedEntityIds": [practice["id"]],
        }

    async def brief(
        self,
        *,
        user_id: Id,
        payload: dict[str, object],
    ) -> HermesCommandResult:
        workflow = await self._service.generate_rhythmic_briefs({"userId": user_id, **payload})
        briefs = workflow["briefs"]
        message = (
            str(briefs[0].get("renderedResponse"))
            if briefs
            else "No rhythmic brief candidates are due right now."
        )
        return {
            "command": "/circulation brief",
            "userId": user_id,
            "status": "ok",
            "message": message,
            "briefs": briefs,
            "affectedEntityIds": [item["id"] for item in briefs],
        }

    async def respond_brief(
        self,
        *,
        user_id: Id,
        payload: dict[str, object],
    ) -> HermesCommandResult:
        record = await self._service.respond_rhythmic_brief({"userId": user_id, **payload})
        action = str(payload["action"])
        message_map = {
            "shown": "Brief marked shown.",
            "dismissed": "Brief dismissed for now.",
            "acted_on": "Brief marked acted on.",
            "deleted": "Brief deleted.",
        }
        return {
            "command": f"/circulation brief {action}",
            "userId": user_id,
            "status": "ok",
            "message": message_map.get(action, "Brief updated."),
            "brief": record,
            "affectedEntityIds": [record["id"]],
        }

    async def witness_state(
        self,
        *,
        user_id: Id,
        window_start: str,
        window_end: str,
        material_id: Id | None = None,
    ) -> HermesCommandResult:
        snapshot = await self._service.get_witness_state(
            user_id=user_id,
            window_start=window_start,
            window_end=window_end,
            material_id=material_id,
        )
        return {
            "command": "/circulation witness",
            "userId": user_id,
            "status": "ok",
            "message": "Loaded current witness state.",
            "affectedEntityIds": [material_id] if material_id else [],
            "interpretation": {"userFacingResponse": "Loaded current witness state."},
            "pendingProposals": [],
            "symbols": [],
            "run": {
                "id": "witness_state",
                "userId": user_id,
                "materialId": material_id or "",
                "materialType": "reflection",
                "createdAt": "",
                "status": "completed",
                "result": {"witnessState": snapshot},
                "evidenceIds": [],
                "hypothesisIds": [],
                "proposalDecisions": [],
            },
        }

    async def answer_amplification(
        self,
        *,
        user_id: Id,
        payload: dict[str, object],
    ) -> HermesCommandResult:
        record = await self._service.answer_amplification_prompt({"userId": user_id, **payload})
        return {
            "command": "/circulation amplify",
            "userId": user_id,
            "status": "ok",
            "message": "Stored personal amplification.",
            "affectedEntityIds": [record["id"]],
        }

    async def capture_conscious_attitude(
        self,
        *,
        user_id: Id,
        payload: dict[str, object],
    ) -> HermesCommandResult:
        record = await self._service.capture_conscious_attitude({"userId": user_id, **payload})
        return {
            "command": "/circulation attitude",
            "userId": user_id,
            "status": "ok",
            "message": "Captured conscious attitude.",
            "affectedEntityIds": [record["id"]],
        }

    async def capture_reality_anchors(
        self,
        *,
        user_id: Id,
        payload: dict[str, object],
    ) -> HermesCommandResult:
        record = await self._service.capture_reality_anchors({"userId": user_id, **payload})
        return {
            "command": "/circulation anchors",
            "userId": user_id,
            "status": "ok",
            "message": "Captured reality anchors.",
            "individuationRecord": record,
            "affectedEntityIds": [record["id"]],
        }

    async def upsert_threshold_process(
        self,
        *,
        user_id: Id,
        payload: dict[str, object],
    ) -> HermesCommandResult:
        record = await self._service.upsert_threshold_process({"userId": user_id, **payload})
        return {
            "command": "/circulation threshold",
            "userId": user_id,
            "status": "ok",
            "message": "Updated threshold process.",
            "individuationRecord": record,
            "affectedEntityIds": [record["id"]],
        }

    async def record_relational_scene(
        self,
        *,
        user_id: Id,
        payload: dict[str, object],
    ) -> HermesCommandResult:
        record = await self._service.record_relational_scene({"userId": user_id, **payload})
        return {
            "command": "/circulation relational-scene",
            "userId": user_id,
            "status": "ok",
            "message": "Recorded relational scene.",
            "individuationRecord": record,
            "affectedEntityIds": [record["id"]],
        }

    async def record_inner_outer_correspondence(
        self,
        *,
        user_id: Id,
        payload: dict[str, object],
    ) -> HermesCommandResult:
        record = await self._service.record_inner_outer_correspondence(
            {"userId": user_id, **payload}
        )
        return {
            "command": "/circulation correspondence",
            "userId": user_id,
            "status": "ok",
            "message": "Recorded inner / outer correspondence.",
            "individuationRecord": record,
            "affectedEntityIds": [record["id"]],
        }

    async def record_numinous_encounter(
        self,
        *,
        user_id: Id,
        payload: dict[str, object],
    ) -> HermesCommandResult:
        record = await self._service.record_numinous_encounter({"userId": user_id, **payload})
        return {
            "command": "/circulation numinous",
            "userId": user_id,
            "status": "ok",
            "message": "Recorded numinous encounter.",
            "individuationRecord": record,
            "affectedEntityIds": [record["id"]],
        }

    async def record_aesthetic_resonance(
        self,
        *,
        user_id: Id,
        payload: dict[str, object],
    ) -> HermesCommandResult:
        record = await self._service.record_aesthetic_resonance({"userId": user_id, **payload})
        return {
            "command": "/circulation resonance",
            "userId": user_id,
            "status": "ok",
            "message": "Recorded aesthetic resonance.",
            "individuationRecord": record,
            "affectedEntityIds": [record["id"]],
        }

    async def set_consent(
        self,
        *,
        user_id: Id,
        payload: dict[str, object],
    ) -> HermesCommandResult:
        record = await self._service.set_consent_preference({"userId": user_id, **payload})
        return {
            "command": "/circulation consent",
            "userId": user_id,
            "status": "ok",
            "message": "Updated consent preference.",
            "affectedEntityIds": [record["id"]],
        }

    async def upsert_goal(self, *, user_id: Id, payload: dict[str, object]) -> HermesCommandResult:
        record = await self._service.upsert_goal({"userId": user_id, **payload})
        return {
            "command": "/circulation goal",
            "userId": user_id,
            "status": "ok",
            "message": "Updated goal record.",
            "affectedEntityIds": [record["id"]],
        }

    async def upsert_goal_tension(
        self, *, user_id: Id, payload: dict[str, object]
    ) -> HermesCommandResult:
        record = await self._service.upsert_goal_tension({"userId": user_id, **payload})
        return {
            "command": "/circulation goal-tension",
            "userId": user_id,
            "status": "ok",
            "message": "Updated goal tension.",
            "affectedEntityIds": [record["id"]],
        }

    async def set_cultural_frame(
        self, *, user_id: Id, payload: dict[str, object]
    ) -> HermesCommandResult:
        record = await self._service.set_cultural_frame({"userId": user_id, **payload})
        return {
            "command": "/circulation culture",
            "userId": user_id,
            "status": "ok",
            "message": "Updated cultural frame.",
            "affectedEntityIds": [record["id"]],
        }

    async def symbols(
        self,
        *,
        user_id: Id,
        symbol_id: Id | None = None,
        symbol_name: str | None = None,
        include_history: bool = False,
        limit: int = 20,
    ) -> HermesCommandResult:
        if symbol_id or symbol_name:
            symbol = None
            if symbol_id:
                try:
                    symbol = await self._service.get_symbol(user_id=user_id, symbol_id=symbol_id)
                except EntityNotFoundError:
                    symbol = None
            elif symbol_name:
                symbol = await self._service.find_symbol_by_name(
                    user_id=user_id, canonical_name=symbol_name
                )
            if symbol is None:
                return {
                    "command": "/circulation symbols",
                    "userId": user_id,
                    "status": "not_found",
                    "message": "No matching symbol was found.",
                }
            if include_history:
                history = await self._service.get_symbol_history(
                    user_id=user_id, symbol_id=symbol["id"], limit=limit
                )
                return {
                    "command": "/circulation symbols",
                    "userId": user_id,
                    "status": "ok",
                    "message": f"Loaded history for {symbol['canonicalName']}.",
                    "symbols": [history["symbol"]],
                    "symbolHistory": history["history"],
                    "linkedMaterials": history["linkedMaterials"],
                    "affectedEntityIds": [symbol["id"]],
                }
            return {
                "command": "/circulation symbols",
                "userId": user_id,
                "status": "ok",
                "message": f"Loaded symbol {symbol['canonicalName']}.",
                "symbols": [symbol],
                "affectedEntityIds": [symbol["id"]],
            }
        symbols = await self._service.list_symbols(user_id=user_id, limit=limit)
        return {
            "command": "/circulation symbols",
            "userId": user_id,
            "status": "ok",
            "message": f"Loaded {len(symbols)} symbol record(s).",
            "symbols": symbols,
            "affectedEntityIds": [item["id"] for item in symbols],
        }

    async def approve(
        self,
        *,
        user_id: Id,
        run_id: Id,
        proposal_ids: list[Id],
        note: str | None = None,
    ) -> HermesCommandResult:
        integration = await self._service.approve_proposals(
            user_id=user_id,
            run_id=run_id,
            proposal_ids=proposal_ids,
            integration_note=note,
        )
        return {
            "command": "/circulation approve",
            "userId": user_id,
            "status": "ok",
            "message": "Approved proposals were applied to Circulatio memory.",
            "integration": integration,
            "affectedEntityIds": integration["affectedEntityIds"],
        }

    async def reject(
        self,
        *,
        user_id: Id,
        run_id: Id,
        proposal_ids: list[Id] | None = None,
        feedback_by_hypothesis_id: dict[Id, FeedbackValue] | None = None,
        reason: str | None = None,
    ) -> HermesCommandResult:
        if proposal_ids:
            integration = await self._service.reject_proposals(
                user_id=user_id,
                run_id=run_id,
                proposal_ids=proposal_ids,
                reason=reason,
            )
        elif feedback_by_hypothesis_id:
            integration = await self._service.reject_hypotheses(
                user_id=user_id,
                run_id=run_id,
                feedback_by_hypothesis_id=feedback_by_hypothesis_id,
            )
        else:
            return {
                "command": "/circulation reject",
                "userId": user_id,
                "status": "error",
                "message": "Provide proposal ids or hypothesis feedback.",
            }
        return {
            "command": "/circulation reject",
            "userId": user_id,
            "status": "ok",
            "message": "Rejection was recorded.",
            "integration": integration,
            "affectedEntityIds": integration["affectedEntityIds"],
        }

    async def revise(
        self,
        *,
        user_id: Id,
        entity_type: GraphNodeType,
        entity_id: Id,
        revision_note: str,
        replacement: dict[str, object] | None = None,
    ) -> HermesCommandResult:
        integration = await self._service.revise_entity(
            user_id=user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            revision_note=revision_note,
            replacement=replacement,
        )
        return {
            "command": "/circulation revise",
            "userId": user_id,
            "status": "ok",
            "message": "Revision was recorded.",
            "integration": integration,
            "affectedEntityIds": integration["affectedEntityIds"],
        }

    async def delete(
        self,
        *,
        user_id: Id,
        entity_type: GraphNodeType,
        entity_id: Id,
        mode: Literal["tombstone", "erase"] = "tombstone",
        reason: str | None = None,
    ) -> HermesCommandResult:
        integration = await self._service.delete_entity(
            user_id=user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            mode=mode,
            reason=reason,
        )
        return {
            "command": "/circulation delete",
            "userId": user_id,
            "status": "ok",
            "message": "Deletion was recorded.",
            "integration": integration,
            "affectedEntityIds": integration["affectedEntityIds"],
        }

    def _workflow_result(
        self,
        command: str,
        user_id: Id,
        workflow: dict[str, object],
    ) -> HermesCommandResult:
        interpretation = workflow["interpretation"]
        status = "blocked" if interpretation["safetyDisposition"]["status"] != "clear" else "ok"
        return {
            "command": command,
            "userId": user_id,
            "status": status,
            "message": interpretation["userFacingResponse"],
            "material": workflow["material"],
            "run": workflow["run"],
            "interpretation": interpretation,
            "pendingProposals": workflow["pendingProposals"],
            "affectedEntityIds": [workflow["material"]["id"], workflow["run"]["id"]],
        }
