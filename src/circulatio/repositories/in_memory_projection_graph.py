from __future__ import annotations

from copy import deepcopy

from ..domain.graph import (
    DEFAULT_GRAPH_QUERY_ALLOWLIST,
    GraphEdgeProjection,
    GraphNodeProjection,
    GraphQuery,
    GraphQueryResult,
)
from ..domain.ids import create_id, now_iso
from ..domain.types import Id
from .in_memory_bucket import UserCirculatioBucket
from .in_memory_projection_shared import _material_summary_text, _truncate


def query_graph_locked(
    bucket: UserCirculatioBucket,
    *,
    user_id: Id,
    query: GraphQuery | None = None,
) -> GraphQueryResult:
    del query
    nodes: list[GraphNodeProjection] = []
    edges: list[GraphEdgeProjection] = []
    material_node_ids: set[Id] = set()
    symbol_node_ids: set[Id] = set()
    for material in bucket.materials.values():
        if material.get("status") == "deleted":
            continue
        node_type = {
            "dream": "DreamEntry",
            "reflection": "ReflectionEntry",
            "charged_event": "ChargedEventNote",
        }.get(material["materialType"], "MaterialEntry")
        nodes.append(
            {
                "id": material["id"],
                "userId": user_id,
                "type": node_type,
                "sourceId": material["id"],
                "label": material.get("title") or material["materialType"],
                "summary": _truncate(_material_summary_text(material), 160),
                "privacyClass": material.get("privacyClass", "approved_summary"),
                "createdAt": material.get("createdAt", now_iso()),
                "updatedAt": material.get("updatedAt", material.get("createdAt", now_iso())),
                "metadata": {"tags": list(material.get("tags", []))[:5]},
            }
        )
        material_node_ids.add(material["id"])
    for symbol in bucket.symbols.values():
        if symbol.get("status") == "deleted":
            continue
        nodes.append(
            {
                "id": symbol["id"],
                "userId": user_id,
                "type": "PersonalSymbol",
                "sourceId": symbol["id"],
                "label": symbol["canonicalName"],
                "summary": _truncate(
                    f"Recurring symbol with {symbol.get('recurrenceCount', 0)} appearances.",
                    160,
                ),
                "privacyClass": "approved_summary",
                "createdAt": symbol.get("createdAt", now_iso()),
                "updatedAt": symbol.get("updatedAt", symbol.get("createdAt", now_iso())),
            }
        )
        symbol_node_ids.add(symbol["id"])
        for material_id in symbol.get("linkedMaterialIds", []):
            if material_id in material_node_ids:
                edges.append(
                    {
                        "id": create_id("graph_edge"),
                        "userId": user_id,
                        "type": "FEATURES",
                        "fromNodeId": material_id,
                        "toNodeId": symbol["id"],
                        "evidenceIds": [],
                        "createdAt": now_iso(),
                    }
                )
    for body_state in bucket.body_states.values():
        if body_state.get("status") == "deleted":
            continue
        nodes.append(
            {
                "id": body_state["id"],
                "userId": user_id,
                "type": "BodyState",
                "sourceId": body_state["id"],
                "label": body_state["sensation"],
                "summary": _truncate(body_state["sensation"], 160),
                "privacyClass": body_state.get("privacyClass", "approved_summary"),
                "createdAt": body_state.get("createdAt", now_iso()),
                "updatedAt": body_state.get("updatedAt", body_state.get("createdAt", now_iso())),
            }
        )
        for symbol_id in body_state.get("linkedSymbolIds", []):
            if symbol_id in symbol_node_ids:
                edges.append(
                    {
                        "id": create_id("graph_edge"),
                        "userId": user_id,
                        "type": "TRIGGERS",
                        "fromNodeId": symbol_id,
                        "toNodeId": body_state["id"],
                        "evidenceIds": list(body_state.get("evidenceIds", [])),
                        "createdAt": now_iso(),
                    }
                )
        for material_id in body_state.get("linkedMaterialIds", []):
            if material_id in material_node_ids:
                edges.append(
                    {
                        "id": create_id("graph_edge"),
                        "userId": user_id,
                        "type": "HAS_BODY_STATE",
                        "fromNodeId": material_id,
                        "toNodeId": body_state["id"],
                        "evidenceIds": list(body_state.get("evidenceIds", [])),
                        "createdAt": now_iso(),
                    }
                )
    for goal in bucket.goals.values():
        if goal.get("status") == "deleted":
            continue
        nodes.append(
            {
                "id": goal["id"],
                "userId": user_id,
                "type": "Goal",
                "sourceId": goal["id"],
                "label": goal["label"],
                "summary": _truncate(goal.get("description") or goal["label"], 160),
                "privacyClass": "approved_summary",
                "createdAt": goal.get("createdAt", now_iso()),
                "updatedAt": goal.get("updatedAt", goal.get("createdAt", now_iso())),
            }
        )
        for symbol_id in goal.get("linkedSymbolIds", []):
            if symbol_id in symbol_node_ids:
                edges.append(
                    {
                        "id": create_id("graph_edge"),
                        "userId": user_id,
                        "type": "RELATES_TO_GOAL",
                        "fromNodeId": symbol_id,
                        "toNodeId": goal["id"],
                        "evidenceIds": [],
                        "createdAt": now_iso(),
                    }
                )
    for tension in bucket.goal_tensions.values():
        if tension.get("status") == "deleted":
            continue
        nodes.append(
            {
                "id": tension["id"],
                "userId": user_id,
                "type": "GoalTension",
                "sourceId": tension["id"],
                "label": tension["tensionSummary"],
                "summary": _truncate(tension["tensionSummary"], 160),
                "privacyClass": "approved_summary",
                "createdAt": tension.get("createdAt", now_iso()),
                "updatedAt": tension.get("updatedAt", tension.get("createdAt", now_iso())),
            }
        )
    for series in bucket.dream_series.values():
        if series.get("status") == "deleted":
            continue
        nodes.append(
            {
                "id": series["id"],
                "userId": user_id,
                "type": "DreamSeries",
                "sourceId": series["id"],
                "label": series["label"],
                "summary": _truncate(series.get("progressionSummary") or series["label"], 160),
                "privacyClass": "approved_summary",
                "createdAt": series.get("createdAt", now_iso()),
                "updatedAt": series.get("updatedAt", series.get("createdAt", now_iso())),
            }
        )
        for material_id in series.get("materialIds", []):
            if material_id in material_node_ids:
                edges.append(
                    {
                        "id": create_id("graph_edge"),
                        "userId": user_id,
                        "type": "BELONGS_TO_SERIES",
                        "fromNodeId": material_id,
                        "toNodeId": series["id"],
                        "evidenceIds": list(series.get("evidenceIds", [])),
                        "createdAt": now_iso(),
                    }
                )
    nodes = nodes[: DEFAULT_GRAPH_QUERY_ALLOWLIST["maxLimit"]]
    edges = edges[: DEFAULT_GRAPH_QUERY_ALLOWLIST["maxLimit"]]
    return {
        "userId": user_id,
        "nodes": deepcopy(nodes),
        "edges": deepcopy(edges),
        "allowlist": deepcopy(DEFAULT_GRAPH_QUERY_ALLOWLIST),
        "warnings": [],
    }
