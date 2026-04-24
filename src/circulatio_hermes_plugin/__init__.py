from __future__ import annotations

from pathlib import Path
from typing import Any

from circulatio.hermes.boot_validation import PluginBootError, raise_for_invalid_plugin_assets

from .commands import handle_circulation_sync
from .schemas import TOOL_SCHEMAS
from .tools import (
    alive_today_tool,
    analysis_packet_tool,
    answer_amplification_tool,
    approve_proposals_tool,
    approve_review_proposals_tool,
    capture_conscious_attitude_tool,
    capture_reality_anchors_tool,
    create_journey_tool,
    dashboard_summary_tool,
    delete_entity_tool,
    discovery_tool,
    generate_practice_recommendation_tool,
    generate_rhythmic_briefs_tool,
    get_journey_tool,
    get_material_tool,
    interpret_material_tool,
    journey_page_tool,
    list_journeys_tool,
    list_materials_tool,
    list_pending_review_proposals_tool,
    list_pending_tool,
    living_myth_review_tool,
    memory_kernel_tool,
    method_state_respond_tool,
    plan_ritual_tool,
    query_graph_tool,
    record_aesthetic_resonance_tool,
    record_inner_outer_correspondence_tool,
    record_interpretation_feedback_tool,
    record_numinous_encounter_tool,
    record_practice_feedback_tool,
    record_relational_scene_tool,
    reject_hypotheses_tool,
    reject_proposals_tool,
    reject_review_proposals_tool,
    respond_practice_recommendation_tool,
    respond_rhythmic_brief_tool,
    revise_entity_tool,
    set_consent_tool,
    set_cultural_frame_tool,
    set_journey_status_tool,
    store_body_state_tool,
    store_dream_tool,
    store_event_tool,
    store_reflection_tool,
    store_symbolic_note_tool,
    symbol_get_tool,
    symbol_history_tool,
    symbols_list_tool,
    threshold_review_tool,
    update_journey_tool,
    upsert_goal_tension_tool,
    upsert_goal_tool,
    upsert_threshold_process_tool,
    weekly_review_tool,
    witness_state_tool,
)

_SKILL_PATH = Path(__file__).resolve().parent / "skills" / "circulation" / "SKILL.md"
_TOOL_HANDLERS = {
    "circulatio_store_dream": store_dream_tool,
    "circulatio_store_event": store_event_tool,
    "circulatio_store_reflection": store_reflection_tool,
    "circulatio_store_symbolic_note": store_symbolic_note_tool,
    "circulatio_store_body_state": store_body_state_tool,
    "circulatio_alive_today": alive_today_tool,
    "circulatio_query_graph": query_graph_tool,
    "circulatio_memory_kernel": memory_kernel_tool,
    "circulatio_dashboard_summary": dashboard_summary_tool,
    "circulatio_discovery": discovery_tool,
    "circulatio_journey_page": journey_page_tool,
    "circulatio_create_journey": create_journey_tool,
    "circulatio_list_journeys": list_journeys_tool,
    "circulatio_get_journey": get_journey_tool,
    "circulatio_update_journey": update_journey_tool,
    "circulatio_set_journey_status": set_journey_status_tool,
    "circulatio_list_materials": list_materials_tool,
    "circulatio_get_material": get_material_tool,
    "circulatio_interpret_material": interpret_material_tool,
    "circulatio_list_pending": list_pending_tool,
    "circulatio_approve_proposals": approve_proposals_tool,
    "circulatio_reject_proposals": reject_proposals_tool,
    "circulatio_list_pending_review_proposals": list_pending_review_proposals_tool,
    "circulatio_approve_review_proposals": approve_review_proposals_tool,
    "circulatio_reject_review_proposals": reject_review_proposals_tool,
    "circulatio_reject_hypotheses": reject_hypotheses_tool,
    "circulatio_revise_entity": revise_entity_tool,
    "circulatio_delete_entity": delete_entity_tool,
    "circulatio_symbols_list": symbols_list_tool,
    "circulatio_symbol_get": symbol_get_tool,
    "circulatio_symbol_history": symbol_history_tool,
    "circulatio_weekly_review": weekly_review_tool,
    "circulatio_threshold_review": threshold_review_tool,
    "circulatio_living_myth_review": living_myth_review_tool,
    "circulatio_analysis_packet": analysis_packet_tool,
    "circulatio_plan_ritual": plan_ritual_tool,
    "circulatio_witness_state": witness_state_tool,
    "circulatio_capture_conscious_attitude": capture_conscious_attitude_tool,
    "circulatio_capture_reality_anchors": capture_reality_anchors_tool,
    "circulatio_upsert_threshold_process": upsert_threshold_process_tool,
    "circulatio_record_relational_scene": record_relational_scene_tool,
    "circulatio_record_inner_outer_correspondence": record_inner_outer_correspondence_tool,
    "circulatio_record_numinous_encounter": record_numinous_encounter_tool,
    "circulatio_record_aesthetic_resonance": record_aesthetic_resonance_tool,
    "circulatio_set_consent": set_consent_tool,
    "circulatio_answer_amplification": answer_amplification_tool,
    "circulatio_method_state_respond": method_state_respond_tool,
    "circulatio_upsert_goal": upsert_goal_tool,
    "circulatio_upsert_goal_tension": upsert_goal_tension_tool,
    "circulatio_set_cultural_frame": set_cultural_frame_tool,
    "circulatio_generate_practice_recommendation": generate_practice_recommendation_tool,
    "circulatio_respond_practice_recommendation": respond_practice_recommendation_tool,
    "circulatio_record_interpretation_feedback": record_interpretation_feedback_tool,
    "circulatio_record_practice_feedback": record_practice_feedback_tool,
    "circulatio_generate_rhythmic_briefs": generate_rhythmic_briefs_tool,
    "circulatio_respond_rhythmic_brief": respond_rhythmic_brief_tool,
}


def register(ctx: Any) -> None:
    _register_command(ctx)
    _register_tools(ctx)
    _register_skill(ctx)


def _register_command(ctx: Any) -> None:
    if not hasattr(ctx, "register_command"):
        return
    try:
        ctx.register_command(
            "circulation",
            handler=handle_circulation_sync,
            description=(
                "Store symbolic material, interpret it deliberately, and "
                "manage approval-gated Circulatio memory."
            ),
        )
    except TypeError:
        ctx.register_command(
            "circulation",
            handle_circulation_sync,
            (
                "Store symbolic material, interpret it deliberately, and "
                "manage approval-gated Circulatio memory."
            ),
        )


def _register_tools(ctx: Any) -> None:
    if not hasattr(ctx, "register_tool"):
        return
    for schema in TOOL_SCHEMAS:
        handler = _TOOL_HANDLERS[schema["name"]]
        _register_tool(ctx, schema, handler)


def _register_tool(ctx: Any, schema: dict[str, object], handler: Any) -> None:
    name = str(schema["name"])
    try:
        ctx.register_tool(
            name=name,
            toolset="circulatio",
            schema=schema,
            handler=handler,
            is_async=True,
            description=schema.get("description", ""),
        )
        return
    except TypeError:
        pass
    try:
        ctx.register_tool(name, schema, handler)
        return
    except TypeError:
        pass
    try:
        ctx.register_tool(name=name, schema=schema, handler=handler)
        return
    except TypeError:
        pass
    ctx.register_tool(name, handler, schema=schema)


def _register_skill(ctx: Any) -> None:
    if not hasattr(ctx, "register_skill"):
        return
    _validate_packaged_assets()
    try:
        ctx.register_skill(
            "circulation",
            _SKILL_PATH,
            description="Circulatio ambient intake and interpretation workflow",
        )
    except TypeError:
        try:
            ctx.register_skill("circulation", _SKILL_PATH)
        except TypeError:
            ctx.register_skill(name="circulation", path=_SKILL_PATH)


def _validate_packaged_assets() -> None:
    try:
        raise_for_invalid_plugin_assets()
    except PluginBootError:
        raise
    except Exception as exc:
        raise PluginBootError(f"Circulatio packaged assets could not be validated: {exc}") from exc


__all__ = ["register"]
