from __future__ import annotations

from copy import deepcopy

from ..domain.graph import SymbolicMemorySnapshot
from ..domain.ids import create_id, now_iso
from ..domain.memory import (
    MemoryKernelItem,
    MemoryKernelSnapshot,
    MemoryRetrievalQuery,
)
from ..domain.types import Id
from .in_memory_bucket import UserCirculatioBucket
from .in_memory_projection_shared import _material_summary_text, _truncate
from .in_memory_projection_summary import (
    active_patterns,
    active_symbols,
    build_memory_context_locked,
    completed_practices,
    project_pattern_summary,
    project_practice_outcome,
    project_symbol_summary,
    project_typology_summary,
)


def build_memory_kernel_snapshot_locked(
    bucket: UserCirculatioBucket,
    *,
    user_id: Id,
    query: MemoryRetrievalQuery | None = None,
) -> MemoryKernelSnapshot:
    limit = int((query or {}).get("limit", 12))
    items: list[MemoryKernelItem] = []
    for symbol in active_symbols(bucket)[:limit]:
        items.append(
            {
                "id": create_id("memory_item"),
                "userId": user_id,
                "namespace": "symbol",
                "entityId": symbol["id"],
                "entityType": "PersonalSymbol",
                "label": symbol["canonicalName"],
                "summary": _truncate(
                    f"Recurring symbol with {symbol.get('recurrenceCount', 0)} appearances.",
                    160,
                ),
                "keywords": [symbol["canonicalName"], *symbol.get("aliases", [])[:3]],
                "symbolicFingerprint": [symbol["canonicalName"]],
                "provenance": {
                    "sourceNamespace": "symbol",
                    "sourceId": symbol["id"],
                    "createdAt": symbol.get("createdAt", now_iso()),
                },
                "importance": {
                    "score": float(max(symbol.get("recurrenceCount", 1), 1)),
                    "reasons": ["recurrence"],
                    "recurrenceCount": symbol.get("recurrenceCount", 1),
                },
                "privacyClass": "approved_summary",
                "createdAt": symbol.get("createdAt", now_iso()),
                "updatedAt": symbol.get("updatedAt", symbol.get("createdAt", now_iso())),
            }
        )
    for material in list(bucket.materials.values())[: max(0, limit - len(items))]:
        if material.get("status") == "deleted":
            continue
        items.append(
            {
                "id": create_id("memory_item"),
                "userId": user_id,
                "namespace": material["materialType"],
                "entityId": material["id"],
                "entityType": "MaterialEntry",
                "label": material.get("title") or material["materialType"],
                "summary": _truncate(_material_summary_text(material), 160),
                "keywords": list(material.get("tags", []))[:5],
                "symbolicFingerprint": list(material.get("tags", []))[:5],
                "provenance": {
                    "sourceNamespace": material["materialType"],
                    "sourceId": material["id"],
                    "materialId": material["id"],
                    "createdAt": material.get("createdAt", now_iso()),
                    "observedAt": material.get(
                        "materialDate", material.get("createdAt", now_iso())
                    ),
                },
                "importance": {"score": 1.0, "reasons": ["recent_capture"]},
                "privacyClass": material.get("privacyClass", "approved_summary"),
                "createdAt": material.get("createdAt", now_iso()),
                "updatedAt": material.get("updatedAt", material.get("createdAt", now_iso())),
            }
        )
        if len(items) >= limit:
            break
    return {
        "userId": user_id,
        "query": deepcopy(query or {}),
        "items": items[:limit],
        "generatedAt": now_iso(),
        "rankingNotes": ["Derived from current in-memory symbolic records."],
    }


def build_symbolic_memory_snapshot_locked(
    bucket: UserCirculatioBucket, *, max_items: int | None = None
) -> SymbolicMemorySnapshot:
    limit = max_items or 12
    memory = build_memory_context_locked(bucket, max_items=limit)
    return {
        "personalSymbols": [
            project_symbol_summary(item) for item in active_symbols(bucket)[:limit]
        ],
        "complexCandidates": [
            project_pattern_summary(item) for item in active_patterns(bucket)[:limit]
        ],
        "materialSummaries": deepcopy(memory["recentMaterialSummaries"]),
        "evidence": deepcopy(list(bucket.evidence.values())[:limit]),
        "practiceOutcomes": [
            project_practice_outcome(item) for item in completed_practices(bucket)[:limit]
        ],
        "culturalOrigins": deepcopy(bucket.cultural_origins[:limit]),
        "typologyLenses": [
            project_typology_summary(item)
            for item in list(bucket.typology_lenses.values())[:limit]
            if item.get("status") != "deleted"
        ],
    }
