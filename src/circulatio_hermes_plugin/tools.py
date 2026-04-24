from __future__ import annotations

import json
from copy import deepcopy

from circulatio.hermes.agent_bridge_contracts import BridgeOperation

from .commands import _boot_failure_response, build_tool_request
from .runtime import get_runtime

_TOOL_METADATA_KEYS = {
    "args",
    "command",
    "command_args",
    "messageId",
    "message_id",
    "platform",
    "profile",
    "profile_name",
    "raw_args",
    "sessionId",
    "session_id",
    "source_platform",
    "tool_call_id",
    "user_args",
    "user_id",
    "userId",
}


def _tool_payload(
    arguments: dict[str, object] | None, kwargs: dict[str, object]
) -> dict[str, object]:
    payload = deepcopy(arguments or {})
    for key, value in kwargs.items():
        if key in _TOOL_METADATA_KEYS or key in payload:
            continue
        payload[key] = deepcopy(value)
    return payload


async def _dispatch_tool(
    *,
    operation: BridgeOperation,
    tool_name: str,
    arguments: dict[str, object] | None,
    kwargs: dict[str, object],
) -> str:
    payload = _tool_payload(arguments, kwargs)
    request = build_tool_request(
        operation=operation,
        payload=payload,
        tool_name=tool_name,
        kwargs=kwargs,
    )
    try:
        response = await get_runtime(request["source"].get("profile")).bridge.dispatch(request)
    except Exception as exc:
        response = _boot_failure_response(request=request, exc=exc)
    return json.dumps(response, sort_keys=True, ensure_ascii=False)


async def _dispatch_material_store_tool(
    *,
    tool_name: str,
    material_type: str,
    arguments: dict[str, object] | None,
    kwargs: dict[str, object],
) -> str:
    payload = deepcopy(arguments or {})
    payload["materialType"] = material_type
    return await _dispatch_tool(
        operation="circulatio.material.store",
        tool_name=tool_name,
        arguments=payload,
        kwargs=kwargs,
    )


async def store_dream_tool(arguments: dict[str, object] | None = None, **kwargs: object) -> str:
    return await _dispatch_material_store_tool(
        tool_name="circulatio_store_dream",
        material_type="dream",
        arguments=arguments,
        kwargs=kwargs,
    )


async def store_event_tool(arguments: dict[str, object] | None = None, **kwargs: object) -> str:
    return await _dispatch_material_store_tool(
        tool_name="circulatio_store_event",
        material_type="charged_event",
        arguments=arguments,
        kwargs=kwargs,
    )


async def store_reflection_tool(
    arguments: dict[str, object] | None = None, **kwargs: object
) -> str:
    return await _dispatch_material_store_tool(
        tool_name="circulatio_store_reflection",
        material_type="reflection",
        arguments=arguments,
        kwargs=kwargs,
    )


async def store_symbolic_note_tool(
    arguments: dict[str, object] | None = None, **kwargs: object
) -> str:
    return await _dispatch_material_store_tool(
        tool_name="circulatio_store_symbolic_note",
        material_type="symbolic_motif",
        arguments=arguments,
        kwargs=kwargs,
    )


async def store_body_state_tool(
    arguments: dict[str, object] | None = None, **kwargs: object
) -> str:
    return await _dispatch_tool(
        operation="circulatio.body.store",
        tool_name="circulatio_store_body_state",
        arguments=arguments,
        kwargs=kwargs,
    )


async def alive_today_tool(arguments: dict[str, object] | None = None, **kwargs: object) -> str:
    return await _dispatch_tool(
        operation="circulatio.summary.alive_today",
        tool_name="circulatio_alive_today",
        arguments=arguments,
        kwargs=kwargs,
    )


async def query_graph_tool(arguments: dict[str, object] | None = None, **kwargs: object) -> str:
    return await _dispatch_tool(
        operation="circulatio.graph.query",
        tool_name="circulatio_query_graph",
        arguments=arguments,
        kwargs=kwargs,
    )


async def memory_kernel_tool(arguments: dict[str, object] | None = None, **kwargs: object) -> str:
    return await _dispatch_tool(
        operation="circulatio.memory.kernel",
        tool_name="circulatio_memory_kernel",
        arguments=arguments,
        kwargs=kwargs,
    )


async def dashboard_summary_tool(
    arguments: dict[str, object] | None = None, **kwargs: object
) -> str:
    return await _dispatch_tool(
        operation="circulatio.dashboard.summary",
        tool_name="circulatio_dashboard_summary",
        arguments=arguments,
        kwargs=kwargs,
    )


async def discovery_tool(arguments: dict[str, object] | None = None, **kwargs: object) -> str:
    return await _dispatch_tool(
        operation="circulatio.discovery",
        tool_name="circulatio_discovery",
        arguments=arguments,
        kwargs=kwargs,
    )


async def journey_page_tool(arguments: dict[str, object] | None = None, **kwargs: object) -> str:
    return await _dispatch_tool(
        operation="circulatio.journey.page",
        tool_name="circulatio_journey_page",
        arguments=arguments,
        kwargs=kwargs,
    )


async def create_journey_tool(arguments: dict[str, object] | None = None, **kwargs: object) -> str:
    return await _dispatch_tool(
        operation="circulatio.journeys.create",
        tool_name="circulatio_create_journey",
        arguments=arguments,
        kwargs=kwargs,
    )


async def list_journeys_tool(arguments: dict[str, object] | None = None, **kwargs: object) -> str:
    return await _dispatch_tool(
        operation="circulatio.journeys.list",
        tool_name="circulatio_list_journeys",
        arguments=arguments,
        kwargs=kwargs,
    )


async def get_journey_tool(arguments: dict[str, object] | None = None, **kwargs: object) -> str:
    return await _dispatch_tool(
        operation="circulatio.journeys.get",
        tool_name="circulatio_get_journey",
        arguments=arguments,
        kwargs=kwargs,
    )


async def update_journey_tool(arguments: dict[str, object] | None = None, **kwargs: object) -> str:
    return await _dispatch_tool(
        operation="circulatio.journeys.update",
        tool_name="circulatio_update_journey",
        arguments=arguments,
        kwargs=kwargs,
    )


async def set_journey_status_tool(
    arguments: dict[str, object] | None = None, **kwargs: object
) -> str:
    return await _dispatch_tool(
        operation="circulatio.journeys.set_status",
        tool_name="circulatio_set_journey_status",
        arguments=arguments,
        kwargs=kwargs,
    )


async def list_materials_tool(arguments: dict[str, object] | None = None, **kwargs: object) -> str:
    return await _dispatch_tool(
        operation="circulatio.material.list",
        tool_name="circulatio_list_materials",
        arguments=arguments,
        kwargs=kwargs,
    )


async def get_material_tool(arguments: dict[str, object] | None = None, **kwargs: object) -> str:
    return await _dispatch_tool(
        operation="circulatio.material.get",
        tool_name="circulatio_get_material",
        arguments=arguments,
        kwargs=kwargs,
    )


async def interpret_material_tool(
    arguments: dict[str, object] | None = None, **kwargs: object
) -> str:
    return await _dispatch_tool(
        operation="circulatio.material.interpret",
        tool_name="circulatio_interpret_material",
        arguments=arguments,
        kwargs=kwargs,
    )


async def list_pending_tool(arguments: dict[str, object] | None = None, **kwargs: object) -> str:
    return await _dispatch_tool(
        operation="circulatio.proposals.list_pending",
        tool_name="circulatio_list_pending",
        arguments=arguments,
        kwargs=kwargs,
    )


async def approve_proposals_tool(
    arguments: dict[str, object] | None = None, **kwargs: object
) -> str:
    return await _dispatch_tool(
        operation="circulatio.proposals.approve",
        tool_name="circulatio_approve_proposals",
        arguments=arguments,
        kwargs=kwargs,
    )


async def reject_proposals_tool(
    arguments: dict[str, object] | None = None, **kwargs: object
) -> str:
    return await _dispatch_tool(
        operation="circulatio.proposals.reject",
        tool_name="circulatio_reject_proposals",
        arguments=arguments,
        kwargs=kwargs,
    )


async def reject_hypotheses_tool(
    arguments: dict[str, object] | None = None, **kwargs: object
) -> str:
    return await _dispatch_tool(
        operation="circulatio.hypotheses.reject",
        tool_name="circulatio_reject_hypotheses",
        arguments=arguments,
        kwargs=kwargs,
    )


async def revise_entity_tool(arguments: dict[str, object] | None = None, **kwargs: object) -> str:
    return await _dispatch_tool(
        operation="circulatio.entity.revise",
        tool_name="circulatio_revise_entity",
        arguments=arguments,
        kwargs=kwargs,
    )


async def delete_entity_tool(arguments: dict[str, object] | None = None, **kwargs: object) -> str:
    return await _dispatch_tool(
        operation="circulatio.entity.delete",
        tool_name="circulatio_delete_entity",
        arguments=arguments,
        kwargs=kwargs,
    )


async def symbols_list_tool(arguments: dict[str, object] | None = None, **kwargs: object) -> str:
    return await _dispatch_tool(
        operation="circulatio.symbols.list",
        tool_name="circulatio_symbols_list",
        arguments=arguments,
        kwargs=kwargs,
    )


async def symbol_get_tool(arguments: dict[str, object] | None = None, **kwargs: object) -> str:
    return await _dispatch_tool(
        operation="circulatio.symbols.get",
        tool_name="circulatio_symbol_get",
        arguments=arguments,
        kwargs=kwargs,
    )


async def symbol_history_tool(arguments: dict[str, object] | None = None, **kwargs: object) -> str:
    payload = deepcopy(arguments or {})
    payload["includeHistory"] = True
    return await _dispatch_tool(
        operation="circulatio.symbols.history",
        tool_name="circulatio_symbol_history",
        arguments=payload,
        kwargs=kwargs,
    )


async def weekly_review_tool(arguments: dict[str, object] | None = None, **kwargs: object) -> str:
    return await _dispatch_tool(
        operation="circulatio.review.weekly",
        tool_name="circulatio_weekly_review",
        arguments=arguments,
        kwargs=kwargs,
    )


async def threshold_review_tool(
    arguments: dict[str, object] | None = None, **kwargs: object
) -> str:
    return await _dispatch_tool(
        operation="circulatio.review.threshold",
        tool_name="circulatio_threshold_review",
        arguments=arguments,
        kwargs=kwargs,
    )


async def living_myth_review_tool(
    arguments: dict[str, object] | None = None, **kwargs: object
) -> str:
    return await _dispatch_tool(
        operation="circulatio.review.living_myth",
        tool_name="circulatio_living_myth_review",
        arguments=arguments,
        kwargs=kwargs,
    )


async def analysis_packet_tool(arguments: dict[str, object] | None = None, **kwargs: object) -> str:
    return await _dispatch_tool(
        operation="circulatio.packet.analysis",
        tool_name="circulatio_analysis_packet",
        arguments=arguments,
        kwargs=kwargs,
    )


async def plan_ritual_tool(arguments: dict[str, object] | None = None, **kwargs: object) -> str:
    return await _dispatch_tool(
        operation="circulatio.presentation.plan_ritual",
        tool_name="circulatio_plan_ritual",
        arguments=arguments,
        kwargs=kwargs,
    )


async def record_ritual_completion_tool(
    arguments: dict[str, object] | None = None, **kwargs: object
) -> str:
    payload = _tool_payload(arguments, kwargs)
    if (
        not str(payload.get("idempotencyKey") or "").strip()
        and str(payload.get("completionId") or "").strip()
    ):
        payload["idempotencyKey"] = str(payload["completionId"])
    return await _dispatch_tool(
        operation="circulatio.presentation.record_ritual_completion",
        tool_name="circulatio_record_ritual_completion",
        arguments=payload,
        kwargs={},
    )


async def list_pending_review_proposals_tool(
    arguments: dict[str, object] | None = None, **kwargs: object
) -> str:
    return await _dispatch_tool(
        operation="circulatio.review.proposals.list_pending",
        tool_name="circulatio_list_pending_review_proposals",
        arguments=arguments,
        kwargs=kwargs,
    )


async def approve_review_proposals_tool(
    arguments: dict[str, object] | None = None, **kwargs: object
) -> str:
    return await _dispatch_tool(
        operation="circulatio.review.proposals.approve",
        tool_name="circulatio_approve_review_proposals",
        arguments=arguments,
        kwargs=kwargs,
    )


async def reject_review_proposals_tool(
    arguments: dict[str, object] | None = None, **kwargs: object
) -> str:
    return await _dispatch_tool(
        operation="circulatio.review.proposals.reject",
        tool_name="circulatio_reject_review_proposals",
        arguments=arguments,
        kwargs=kwargs,
    )


async def witness_state_tool(arguments: dict[str, object] | None = None, **kwargs: object) -> str:
    return await _dispatch_tool(
        operation="circulatio.witness.state",
        tool_name="circulatio_witness_state",
        arguments=arguments,
        kwargs=kwargs,
    )


async def capture_conscious_attitude_tool(
    arguments: dict[str, object] | None = None, **kwargs: object
) -> str:
    return await _dispatch_tool(
        operation="circulatio.conscious_attitude.capture",
        tool_name="circulatio_capture_conscious_attitude",
        arguments=arguments,
        kwargs=kwargs,
    )


async def capture_reality_anchors_tool(
    arguments: dict[str, object] | None = None, **kwargs: object
) -> str:
    return await _dispatch_tool(
        operation="circulatio.individuation.reality_anchors.capture",
        tool_name="circulatio_capture_reality_anchors",
        arguments=arguments,
        kwargs=kwargs,
    )


async def upsert_threshold_process_tool(
    arguments: dict[str, object] | None = None, **kwargs: object
) -> str:
    return await _dispatch_tool(
        operation="circulatio.individuation.threshold_process.upsert",
        tool_name="circulatio_upsert_threshold_process",
        arguments=arguments,
        kwargs=kwargs,
    )


async def record_relational_scene_tool(
    arguments: dict[str, object] | None = None, **kwargs: object
) -> str:
    return await _dispatch_tool(
        operation="circulatio.individuation.relational_scene.capture",
        tool_name="circulatio_record_relational_scene",
        arguments=arguments,
        kwargs=kwargs,
    )


async def record_inner_outer_correspondence_tool(
    arguments: dict[str, object] | None = None, **kwargs: object
) -> str:
    return await _dispatch_tool(
        operation="circulatio.individuation.inner_outer_correspondence.capture",
        tool_name="circulatio_record_inner_outer_correspondence",
        arguments=arguments,
        kwargs=kwargs,
    )


async def record_numinous_encounter_tool(
    arguments: dict[str, object] | None = None, **kwargs: object
) -> str:
    return await _dispatch_tool(
        operation="circulatio.individuation.numinous_encounter.capture",
        tool_name="circulatio_record_numinous_encounter",
        arguments=arguments,
        kwargs=kwargs,
    )


async def record_aesthetic_resonance_tool(
    arguments: dict[str, object] | None = None, **kwargs: object
) -> str:
    return await _dispatch_tool(
        operation="circulatio.individuation.aesthetic_resonance.capture",
        tool_name="circulatio_record_aesthetic_resonance",
        arguments=arguments,
        kwargs=kwargs,
    )


async def set_consent_tool(arguments: dict[str, object] | None = None, **kwargs: object) -> str:
    return await _dispatch_tool(
        operation="circulatio.consent.set",
        tool_name="circulatio_set_consent",
        arguments=arguments,
        kwargs=kwargs,
    )


async def answer_amplification_tool(
    arguments: dict[str, object] | None = None, **kwargs: object
) -> str:
    return await _dispatch_tool(
        operation="circulatio.amplification.answer",
        tool_name="circulatio_answer_amplification",
        arguments=arguments,
        kwargs=kwargs,
    )


async def method_state_respond_tool(
    arguments: dict[str, object] | None = None, **kwargs: object
) -> str:
    return await _dispatch_tool(
        operation="circulatio.method_state.respond",
        tool_name="circulatio_method_state_respond",
        arguments=arguments,
        kwargs=kwargs,
    )


async def upsert_goal_tool(arguments: dict[str, object] | None = None, **kwargs: object) -> str:
    return await _dispatch_tool(
        operation="circulatio.goals.upsert",
        tool_name="circulatio_upsert_goal",
        arguments=arguments,
        kwargs=kwargs,
    )


async def upsert_goal_tension_tool(
    arguments: dict[str, object] | None = None, **kwargs: object
) -> str:
    return await _dispatch_tool(
        operation="circulatio.goal_tensions.upsert",
        tool_name="circulatio_upsert_goal_tension",
        arguments=arguments,
        kwargs=kwargs,
    )


async def set_cultural_frame_tool(
    arguments: dict[str, object] | None = None, **kwargs: object
) -> str:
    return await _dispatch_tool(
        operation="circulatio.culture.frame.set",
        tool_name="circulatio_set_cultural_frame",
        arguments=arguments,
        kwargs=kwargs,
    )


async def generate_practice_recommendation_tool(
    arguments: dict[str, object] | None = None, **kwargs: object
) -> str:
    return await _dispatch_tool(
        operation="circulatio.practice.generate",
        tool_name="circulatio_generate_practice_recommendation",
        arguments=arguments,
        kwargs=kwargs,
    )


async def respond_practice_recommendation_tool(
    arguments: dict[str, object] | None = None, **kwargs: object
) -> str:
    return await _dispatch_tool(
        operation="circulatio.practice.respond",
        tool_name="circulatio_respond_practice_recommendation",
        arguments=arguments,
        kwargs=kwargs,
    )


async def record_interpretation_feedback_tool(
    arguments: dict[str, object] | None = None, **kwargs: object
) -> str:
    return await _dispatch_tool(
        operation="circulatio.feedback.interpretation",
        tool_name="circulatio_record_interpretation_feedback",
        arguments=arguments,
        kwargs=kwargs,
    )


async def record_practice_feedback_tool(
    arguments: dict[str, object] | None = None, **kwargs: object
) -> str:
    return await _dispatch_tool(
        operation="circulatio.feedback.practice",
        tool_name="circulatio_record_practice_feedback",
        arguments=arguments,
        kwargs=kwargs,
    )


async def generate_rhythmic_briefs_tool(
    arguments: dict[str, object] | None = None, **kwargs: object
) -> str:
    return await _dispatch_tool(
        operation="circulatio.briefs.generate",
        tool_name="circulatio_generate_rhythmic_briefs",
        arguments=arguments,
        kwargs=kwargs,
    )


async def respond_rhythmic_brief_tool(
    arguments: dict[str, object] | None = None, **kwargs: object
) -> str:
    return await _dispatch_tool(
        operation="circulatio.briefs.respond",
        tool_name="circulatio_respond_rhythmic_brief",
        arguments=arguments,
        kwargs=kwargs,
    )
