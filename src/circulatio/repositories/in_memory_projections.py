from __future__ import annotations

from collections import defaultdict
from copy import deepcopy

from ..domain.errors import ValidationError
from ..domain.graph import (
    DEFAULT_GRAPH_QUERY_ALLOWLIST,
    GraphEdgeProjection,
    GraphNodeProjection,
    GraphQuery,
    GraphQueryResult,
    SymbolicMemorySnapshot,
)
from ..domain.ids import create_id, now_iso
from ..domain.memory import (
    MEMORY_NAMESPACE_ALLOWLIST,
    MemoryKernelItem,
    MemoryKernelSnapshot,
    MemoryNamespace,
    MemoryRetrievalQuery,
)
from ..domain.reviews import DashboardSummary
from ..domain.types import (
    AnalysisPacketInput,
    CirculationSummaryInput,
    Id,
    LifeContextSnapshot,
    LivingMythReviewInput,
    MethodContextSnapshot,
    MethodStateSourceRef,
    ThreadDigest,
    ThreadSurfaceReadiness,
    ThresholdReviewInput,
)
from .in_memory_bucket import UserCirculatioBucket
from .in_memory_projection_contexts import (
    build_analysis_packet_input_locked as _build_analysis_packet_input_locked_context,
)
from .in_memory_projection_contexts import (
    build_living_myth_review_input_locked as _build_living_myth_review_input_locked_context,
)
from .in_memory_projection_contexts import (
    build_method_context_snapshot_locked as _build_method_context_snapshot_locked_context,
)
from .in_memory_projection_contexts import (
    build_threshold_review_input_locked as _build_threshold_review_input_locked_context,
)
from .in_memory_projection_shared import (
    _expand_symbolic_keywords,
    _importance,
    _is_within_optional_window,
    _is_within_window,
    _material_summary_text,
    _material_timestamp,
    _parse_datetime,
    _practice_timestamp,
    _truncate,
)
from .in_memory_projection_summary import (
    _derive_body_state_changes,
    _derive_body_state_energy_summary,
    _derive_dream_series_changes,
    _derive_energy_summary,
    _derive_focus_summary,
    _derive_habit_summary,
    _derive_life_event_refs,
    _derive_mental_state_summary,
    _derive_mood_summary,
    _derive_notable_changes,
    _project_goal_summary,
    _project_goal_tension_summary,
    active_patterns,
    active_symbols,
    active_typology_lenses,
    build_memory_context_locked,
    completed_practices,
    project_pattern_summary,
    project_practice_outcome,
    project_symbol_summary,
    project_typology_summary,
)

_DEFAULT_MEMORY_LIMIT = 12


def build_threshold_review_input_locked(
    bucket: UserCirculatioBucket,
    *,
    user_id: Id,
    window_start: str,
    window_end: str,
    threshold_process_id: Id | None = None,
    explicit_question: str | None = None,
) -> ThresholdReviewInput:
    return _build_threshold_review_input_locked_context(
        bucket,
        user_id=user_id,
        window_start=window_start,
        window_end=window_end,
        threshold_process_id=threshold_process_id,
        explicit_question=explicit_question,
    )


def build_living_myth_review_input_locked(
    bucket: UserCirculatioBucket,
    *,
    user_id: Id,
    window_start: str,
    window_end: str,
    explicit_question: str | None = None,
) -> LivingMythReviewInput:
    return _build_living_myth_review_input_locked_context(
        bucket,
        user_id=user_id,
        window_start=window_start,
        window_end=window_end,
        explicit_question=explicit_question,
    )


def build_analysis_packet_input_locked(
    bucket: UserCirculatioBucket,
    *,
    user_id: Id,
    window_start: str,
    window_end: str,
    packet_focus: str | None = None,
    explicit_question: str | None = None,
) -> AnalysisPacketInput:
    return _build_analysis_packet_input_locked_context(
        bucket,
        user_id=user_id,
        window_start=window_start,
        window_end=window_end,
        packet_focus=packet_focus,
        explicit_question=explicit_question,
    )


def _memory_limit(query: MemoryRetrievalQuery | None) -> int:
    raw_limit = (query or {}).get("limit", _DEFAULT_MEMORY_LIMIT)
    try:
        limit = int(raw_limit)
    except (TypeError, ValueError):
        return _DEFAULT_MEMORY_LIMIT
    return max(1, min(limit, 100))


def _graph_limit(query: GraphQuery | None) -> int:
    raw_limit = (query or {}).get("limit", DEFAULT_GRAPH_QUERY_ALLOWLIST["maxLimit"])
    try:
        limit = int(raw_limit)
    except (TypeError, ValueError):
        return DEFAULT_GRAPH_QUERY_ALLOWLIST["maxLimit"]
    return max(1, min(limit, DEFAULT_GRAPH_QUERY_ALLOWLIST["maxLimit"]))


def _namespace_filter(query: MemoryRetrievalQuery | None) -> set[MemoryNamespace]:
    requested = (query or {}).get("namespaces") or []
    allowlist = set(MEMORY_NAMESPACE_ALLOWLIST)
    return {
        namespace
        for namespace in requested
        if isinstance(namespace, str) and namespace in allowlist
    }


def _item_related_ids(item: MemoryKernelItem) -> set[Id]:
    related: set[Id] = {item["entityId"], item["provenance"]["sourceId"]}
    provenance = item["provenance"]
    material_id = provenance.get("materialId")
    if material_id:
        related.add(material_id)
    run_id = provenance.get("runId")
    if run_id:
        related.add(run_id)
    related.update(provenance.get("evidenceIds", []))
    return related


def _matches_text_query(item: MemoryKernelItem, text_query: object) -> bool:
    needle = str(text_query or "").strip().lower()
    if not needle:
        return True
    haystacks = [
        item["label"],
        item["summary"],
        *item.get("keywords", []),
        *item.get("symbolicFingerprint", []),
    ]
    return any(needle in str(value).lower() for value in haystacks)


def _matches_memory_query(
    item: MemoryKernelItem,
    *,
    namespaces: set[MemoryNamespace],
    query: MemoryRetrievalQuery | None,
) -> bool:
    if namespaces and item["namespace"] not in namespaces:
        return False
    related_entity_ids = {
        value
        for value in (query or {}).get("relatedEntityIds", [])
        if isinstance(value, str) and value
    }
    if related_entity_ids and not related_entity_ids.intersection(_item_related_ids(item)):
        return False
    privacy_classes = {
        value
        for value in (query or {}).get("privacyClasses", [])
        if isinstance(value, str) and value
    }
    if privacy_classes and item["privacyClass"] not in privacy_classes:
        return False
    observed_at = item["provenance"].get("observedAt") or item["createdAt"]
    if not _is_within_optional_window(
        _parse_datetime(observed_at),
        (query or {}).get("windowStart"),
        (query or {}).get("windowEnd"),
    ):
        return False
    return _matches_text_query(item, (query or {}).get("textQuery"))


def _memory_sort_key(
    item: MemoryKernelItem, ranking_profile: str
) -> tuple[float, float, float, str]:
    importance = float(item["importance"]["score"])
    recurrence = float(item["importance"].get("recurrenceCount", 0))
    updated_at = _parse_datetime(item["updatedAt"]).timestamp()
    if ranking_profile == "recency":
        return (updated_at, importance, recurrence, item["label"])
    if ranking_profile == "recurrence":
        return (recurrence, importance, updated_at, item["label"])
    if ranking_profile == "importance":
        return (importance, updated_at, recurrence, item["label"])
    return (importance, updated_at, recurrence, item["label"])


def _build_memory_item(
    *,
    user_id: Id,
    namespace: MemoryNamespace,
    entity_id: Id,
    entity_type: str,
    label: str,
    summary: str,
    keywords: list[str],
    symbolic_fingerprint: list[str] | None = None,
    source_id: Id,
    evidence_ids: list[Id] | None = None,
    material_id: Id | None = None,
    run_id: Id | None = None,
    privacy_class: str = "approved_summary",
    created_at: str | None = None,
    updated_at: str | None = None,
    observed_at: str | None = None,
    importance_score: float = 0.5,
    importance_reasons: list[str] | None = None,
    recurrence_count: int | None = None,
    last_seen: str | None = None,
) -> MemoryKernelItem:
    created = created_at or now_iso()
    updated = updated_at or created
    provenance: dict[str, object] = {
        "sourceNamespace": namespace,
        "sourceId": source_id,
        "evidenceIds": list(evidence_ids or []),
    }
    if material_id:
        provenance["materialId"] = material_id
    if run_id:
        provenance["runId"] = run_id
    if created_at:
        provenance["createdAt"] = created_at
    if observed_at:
        provenance["observedAt"] = observed_at
    item: MemoryKernelItem = {
        "id": create_id("memory_item"),
        "userId": user_id,
        "namespace": namespace,
        "entityId": entity_id,
        "entityType": entity_type,
        "label": _truncate(label or entity_type, 120),
        "summary": _truncate(summary or label or entity_type, 220),
        "keywords": keywords[:8],
        "provenance": provenance,
        "importance": _importance(
            score=importance_score,
            reasons=importance_reasons or ["stored_record"],
            recurrence_count=recurrence_count,
            last_seen=last_seen,
        ),
        "privacyClass": privacy_class,
        "createdAt": created,
        "updatedAt": updated,
    }
    if symbolic_fingerprint:
        item["symbolicFingerprint"] = symbolic_fingerprint[:8]
    return item


def _record_confidence_score(value: object, *, default: float = 0.55) -> float:
    mapping = {"low": 0.45, "medium": 0.6, "high": 0.8}
    return mapping.get(str(value or "").lower(), default)


def _record_detail_keywords(details: object) -> list[str]:
    if not isinstance(details, dict):
        return []
    values: list[str] = []
    for value in details.values():
        if isinstance(value, str):
            values.append(value)
            continue
        if isinstance(value, list):
            for item in value:
                if isinstance(item, str):
                    values.append(item)
                elif isinstance(item, dict):
                    values.extend(
                        str(nested)
                        for nested in item.values()
                        if isinstance(nested, str) and nested.strip()
                    )
    return _expand_symbolic_keywords(values)


def _individuation_node_type(record_type: str) -> str:
    return {
        "reality_anchor_summary": "RealityAnchorSummary",
        "self_orientation_snapshot": "SelfOrientationSnapshot",
        "psychic_opposition": "PsychicOpposition",
        "emergent_third_signal": "EmergentThirdSignal",
        "bridge_moment": "BridgeMoment",
        "numinous_encounter": "NuminousEncounter",
        "aesthetic_resonance": "AestheticResonance",
        "archetypal_pattern": "ArchetypalPattern",
        "threshold_process": "ThresholdProcess",
        "relational_scene": "RelationalScene",
        "projection_hypothesis": "ProjectionHypothesis",
        "inner_outer_correspondence": "InnerOuterCorrespondence",
    }.get(record_type, "Theme")


def _living_myth_node_type(record_type: str) -> str:
    return {
        "life_chapter_snapshot": "LifeChapterSnapshot",
        "mythic_question": "MythicQuestion",
        "threshold_marker": "ThresholdMarker",
        "complex_encounter": "ComplexEncounter",
        "integration_contour": "IntegrationContour",
        "symbolic_wellbeing_snapshot": "SymbolicWellbeingSnapshot",
    }.get(record_type, "Theme")


def _graph_record_metadata(record: dict[str, object]) -> dict[str, object]:
    metadata: dict[str, object] = {
        "status": record.get("status"),
        "source": record.get("source"),
    }
    confidence = record.get("confidence")
    if confidence is not None:
        metadata["confidence"] = confidence
    return metadata


def build_memory_kernel_snapshot_locked(
    bucket: UserCirculatioBucket,
    *,
    user_id: Id,
    query: MemoryRetrievalQuery | None = None,
) -> MemoryKernelSnapshot:
    namespaces = _namespace_filter(query)
    items: list[MemoryKernelItem] = []

    for material in bucket.materials.values():
        if material.get("status") == "deleted" or material.get("userId") != user_id:
            continue
        material_date = material.get("materialDate", material.get("createdAt", now_iso()))
        item = _build_memory_item(
            user_id=user_id,
            namespace="materials",
            entity_id=material["id"],
            entity_type="MaterialEntry",
            label=str(material.get("title") or material["materialType"]),
            summary=_material_summary_text(material),
            keywords=_expand_symbolic_keywords(
                [
                    material.get("materialType"),
                    material.get("title"),
                    *material.get("tags", []),
                ]
            ),
            symbolic_fingerprint=[str(value) for value in material.get("tags", [])[:5]],
            source_id=material["id"],
            material_id=material["id"],
            privacy_class=str(material.get("privacyClass", "approved_summary")),
            created_at=material.get("createdAt"),
            updated_at=material.get("updatedAt", material.get("createdAt")),
            observed_at=material_date,
            importance_score=0.55,
            importance_reasons=["recent_capture"],
            last_seen=material_date,
        )
        if _matches_memory_query(item, namespaces=namespaces, query=query):
            items.append(item)

    for symbol in active_symbols(bucket):
        if symbol.get("userId") != user_id:
            continue
        recurrence_count = int(symbol.get("recurrenceCount", 0))
        aliases = [str(value) for value in symbol.get("aliases", [])[:4]]
        item = _build_memory_item(
            user_id=user_id,
            namespace="personal_symbols",
            entity_id=symbol["id"],
            entity_type="PersonalSymbol",
            label=symbol["canonicalName"],
            summary=f"Recurring symbol with {recurrence_count} appearance(s).",
            keywords=_expand_symbolic_keywords([symbol["canonicalName"], *aliases]),
            symbolic_fingerprint=[symbol["canonicalName"], *aliases],
            source_id=symbol["id"],
            material_id=(symbol.get("linkedMaterialIds") or [None])[0],
            privacy_class="approved_summary",
            created_at=symbol.get("createdAt"),
            updated_at=symbol.get("updatedAt", symbol.get("createdAt")),
            observed_at=symbol.get("lastSeen", symbol.get("createdAt")),
            importance_score=min(1.0, 0.35 + recurrence_count * 0.2),
            importance_reasons=["recurrence"],
            recurrence_count=recurrence_count,
            last_seen=symbol.get("lastSeen", symbol.get("updatedAt", symbol.get("createdAt"))),
        )
        if _matches_memory_query(item, namespaces=namespaces, query=query):
            items.append(item)

    for pattern in active_patterns(bucket):
        if pattern.get("userId") != user_id:
            continue
        activation = float(pattern.get("activationIntensity", 0.0))
        label = pattern["label"]
        formulation = pattern["formulation"]
        item = _build_memory_item(
            user_id=user_id,
            namespace="patterns",
            entity_id=pattern["id"],
            entity_type=(
                "ComplexCandidate" if pattern.get("patternType") == "complex_candidate" else "Theme"
            ),
            label=label,
            summary=formulation,
            keywords=_expand_symbolic_keywords(
                [
                    label,
                    formulation,
                    *pattern.get("linkedSymbols", []),
                    *pattern.get("linkedLifeEventRefs", []),
                ]
            ),
            symbolic_fingerprint=[str(value) for value in pattern.get("linkedSymbols", [])[:5]],
            source_id=pattern["id"],
            evidence_ids=list(pattern.get("evidenceIds", [])),
            material_id=(pattern.get("linkedMaterialIds") or [None])[0],
            privacy_class="approved_summary",
            created_at=pattern.get("createdAt"),
            updated_at=pattern.get("updatedAt", pattern.get("createdAt")),
            observed_at=pattern.get("lastSeen", pattern.get("updatedAt", pattern.get("createdAt"))),
            importance_score=max(0.3, min(1.0, activation)),
            importance_reasons=["activation"],
            last_seen=pattern.get("lastSeen", pattern.get("updatedAt", pattern.get("createdAt"))),
        )
        if _matches_memory_query(item, namespaces=namespaces, query=query):
            items.append(item)

    for practice in bucket.practice_sessions.values():
        if practice.get("status") == "deleted" or practice.get("userId") != user_id:
            continue
        observed_at = practice.get(
            "completedAt", practice.get("updatedAt", practice.get("createdAt", now_iso()))
        )
        outcome = practice.get("outcome") or practice.get("reason") or practice["practiceType"]
        item = _build_memory_item(
            user_id=user_id,
            namespace="practice_sessions",
            entity_id=practice["id"],
            entity_type="PracticeSession",
            label=str(practice.get("target") or practice["practiceType"]),
            summary=str(outcome),
            keywords=_expand_symbolic_keywords(
                [practice["practiceType"], practice.get("target"), outcome]
            ),
            symbolic_fingerprint=_expand_symbolic_keywords(
                [practice.get("target"), practice["practiceType"]]
            ),
            source_id=practice["id"],
            material_id=practice.get("materialId"),
            run_id=practice.get("runId"),
            evidence_ids=list(practice.get("evidenceIds", [])),
            privacy_class="approved_summary",
            created_at=practice.get("createdAt"),
            updated_at=practice.get("updatedAt", practice.get("createdAt")),
            observed_at=observed_at,
            importance_score=0.65 if practice.get("status") == "completed" else 0.4,
            importance_reasons=["practice_outcome"],
            last_seen=observed_at,
        )
        if _matches_memory_query(item, namespaces=namespaces, query=query):
            items.append(item)

    for run in bucket.interpretation_runs.values():
        if run.get("status") == "deleted" or run.get("userId") != user_id:
            continue
        summary = str(
            run.get("result", {}).get("userFacingResponse")
            or f"Interpretation run {run.get('status', 'recorded')}."
        )
        item = _build_memory_item(
            user_id=user_id,
            namespace="interpretation_runs",
            entity_id=run["id"],
            entity_type="InterpretationRun",
            label=f"{run['materialType']} interpretation",
            summary=summary,
            keywords=_expand_symbolic_keywords([run["materialType"], run.get("status"), summary]),
            source_id=run["id"],
            material_id=run.get("materialId"),
            evidence_ids=list(run.get("evidenceIds", [])),
            privacy_class="approved_summary",
            created_at=run.get("createdAt"),
            updated_at=run.get("updatedAt", run.get("createdAt")),
            observed_at=run.get("createdAt"),
            importance_score=0.5,
            importance_reasons=["interpretation_history"],
            last_seen=run.get("createdAt"),
        )
        if _matches_memory_query(item, namespaces=namespaces, query=query):
            items.append(item)

    for evidence in bucket.evidence.values():
        source_id = str(evidence.get("sourceId") or evidence["id"])
        item = _build_memory_item(
            user_id=user_id,
            namespace="evidence",
            entity_id=evidence["id"],
            entity_type="EvidenceItem",
            label=str(evidence.get("type") or "evidence"),
            summary=str(evidence.get("quoteOrSummary") or ""),
            keywords=_expand_symbolic_keywords(
                [evidence.get("type"), evidence.get("quoteOrSummary")]
            ),
            source_id=source_id,
            evidence_ids=[evidence["id"]],
            material_id=source_id if source_id in bucket.materials else None,
            privacy_class=str(evidence.get("privacyClass", "approved_summary")),
            created_at=evidence.get("timestamp"),
            updated_at=evidence.get("timestamp"),
            observed_at=evidence.get("timestamp"),
            importance_score={
                "high": 0.8,
                "medium": 0.6,
                "low": 0.4,
            }.get(str(evidence.get("reliability", "medium")), 0.5),
            importance_reasons=["evidence_trace"],
            last_seen=evidence.get("timestamp"),
        )
        if _matches_memory_query(item, namespaces=namespaces, query=query):
            items.append(item)

    for lens in active_typology_lenses(bucket):
        if lens.get("userId") != user_id:
            continue
        item = _build_memory_item(
            user_id=user_id,
            namespace="typology_lenses",
            entity_id=lens["id"],
            entity_type="TypologyLens",
            label=lens["claim"],
            summary=lens["userTestPrompt"],
            keywords=_expand_symbolic_keywords(
                [lens.get("role"), lens.get("function"), lens.get("claim")]
            ),
            source_id=lens["id"],
            evidence_ids=list(lens.get("evidenceIds", [])),
            privacy_class="approved_summary",
            created_at=lens.get("createdAt"),
            updated_at=lens.get("updatedAt", lens.get("createdAt")),
            observed_at=lens.get("updatedAt", lens.get("createdAt")),
            importance_score=0.5,
            importance_reasons=["typology_signal"],
            last_seen=lens.get("updatedAt", lens.get("createdAt")),
        )
        if _matches_memory_query(item, namespaces=namespaces, query=query):
            items.append(item)

    for tension in bucket.goal_tensions.values():
        if tension.get("status") == "deleted" or tension.get("userId") != user_id:
            continue
        status = str(tension.get("status") or "active")
        item = _build_memory_item(
            user_id=user_id,
            namespace="goal_tensions",
            entity_id=tension["id"],
            entity_type="GoalTension",
            label="Goal tension",
            summary=str(tension.get("tensionSummary") or "A live goal tension remains active."),
            keywords=_expand_symbolic_keywords(
                [tension.get("tensionSummary"), *tension.get("polarityLabels", [])]
            ),
            source_id=tension["id"],
            evidence_ids=list(tension.get("evidenceIds", [])),
            privacy_class="approved_summary",
            created_at=tension.get("createdAt"),
            updated_at=tension.get("updatedAt", tension.get("createdAt")),
            observed_at=tension.get("updatedAt", tension.get("createdAt")),
            importance_score=0.68 if status == "active" else 0.5,
            importance_reasons=["goal_tension"],
            last_seen=tension.get("updatedAt", tension.get("createdAt")),
        )
        if _matches_memory_query(item, namespaces=namespaces, query=query):
            items.append(item)

    for series in bucket.dream_series.values():
        if series.get("status") == "deleted" or series.get("userId") != user_id:
            continue
        material_ids = list(series.get("materialIds", []))
        symbol_ids = list(series.get("symbolIds", []))
        item = _build_memory_item(
            user_id=user_id,
            namespace="dream_series",
            entity_id=series["id"],
            entity_type="DreamSeries",
            label=str(series.get("label") or "Dream series"),
            summary=str(
                series.get("progressionSummary")
                or f"Dream series with {len(material_ids)} linked material(s)."
            ),
            keywords=_expand_symbolic_keywords(
                [
                    series.get("label"),
                    series.get("progressionSummary"),
                    *series.get("motifKeys", []),
                    *series.get("settingKeys", []),
                ]
            ),
            symbolic_fingerprint=symbol_ids[:5],
            source_id=series["id"],
            material_id=material_ids[0] if material_ids else None,
            privacy_class="approved_summary",
            created_at=series.get("createdAt"),
            updated_at=series.get("updatedAt", series.get("createdAt")),
            observed_at=series.get("lastSeen", series.get("updatedAt", series.get("createdAt"))),
            importance_score=_record_confidence_score(series.get("confidence"), default=0.62),
            importance_reasons=["dream_series"],
            recurrence_count=len(material_ids),
            last_seen=series.get("lastSeen", series.get("updatedAt", series.get("createdAt"))),
        )
        if _matches_memory_query(item, namespaces=namespaces, query=query):
            items.append(item)

    for journey in bucket.journeys.values():
        if journey.get("status") == "deleted" or journey.get("userId") != user_id:
            continue
        status = str(journey.get("status") or "active")
        material_ids = list(journey.get("relatedMaterialIds", []))
        symbol_ids = list(journey.get("relatedSymbolIds", []))
        item = _build_memory_item(
            user_id=user_id,
            namespace="journeys",
            entity_id=journey["id"],
            entity_type="Journey",
            label=str(journey.get("label") or "Journey"),
            summary=str(
                journey.get("currentQuestion")
                or f"{journey.get('label') or 'Journey'} remains open."
            ),
            keywords=_expand_symbolic_keywords(
                [journey.get("label"), journey.get("currentQuestion"), status]
            ),
            symbolic_fingerprint=symbol_ids[:5],
            source_id=journey["id"],
            material_id=material_ids[0] if material_ids else None,
            privacy_class="approved_summary",
            created_at=journey.get("createdAt"),
            updated_at=journey.get("updatedAt", journey.get("createdAt")),
            observed_at=journey.get(
                "nextReviewDueAt",
                journey.get("updatedAt", journey.get("createdAt")),
            ),
            importance_score=0.72 if status == "active" else 0.48,
            importance_reasons=["journey_thread"],
            last_seen=journey.get("updatedAt", journey.get("createdAt")),
        )
        if _matches_memory_query(item, namespaces=namespaces, query=query):
            items.append(item)

    for record in bucket.individuation_records.values():
        if (
            record.get("status") not in {"active", "user_confirmed"}
            or record.get("deletedAt") is not None
            or record.get("userId") != user_id
        ):
            continue
        item = _build_memory_item(
            user_id=user_id,
            namespace="individuation_records",
            entity_id=record["id"],
            entity_type=_individuation_node_type(str(record["recordType"])),
            label=str(record.get("label") or record["recordType"]),
            summary=str(record.get("summary") or record.get("label") or record["recordType"]),
            keywords=_expand_symbolic_keywords(
                [
                    record.get("label"),
                    record.get("summary"),
                    record.get("recordType"),
                    *_record_detail_keywords(record.get("details")),
                ]
            ),
            symbolic_fingerprint=_record_detail_keywords(record.get("details")),
            source_id=record["id"],
            evidence_ids=list(record.get("evidenceIds", [])),
            material_id=(record.get("relatedMaterialIds") or [None])[0],
            privacy_class=str(record.get("privacyClass", "approved_summary")),
            created_at=record.get("createdAt"),
            updated_at=record.get("updatedAt", record.get("createdAt")),
            observed_at=record.get(
                "windowEnd",
                record.get("updatedAt", record.get("createdAt", now_iso())),
            ),
            importance_score=_record_confidence_score(record.get("confidence"), default=0.65),
            importance_reasons=[f"individuation:{record['recordType']}"],
            last_seen=record.get(
                "windowEnd",
                record.get("updatedAt", record.get("createdAt", now_iso())),
            ),
        )
        if _matches_memory_query(item, namespaces=namespaces, query=query):
            items.append(item)

    for record in bucket.living_myth_records.values():
        if (
            record.get("status") not in {"active", "user_confirmed", "released"}
            or record.get("deletedAt") is not None
            or record.get("userId") != user_id
        ):
            continue
        item = _build_memory_item(
            user_id=user_id,
            namespace="living_myth_records",
            entity_id=record["id"],
            entity_type=_living_myth_node_type(str(record["recordType"])),
            label=str(record.get("label") or record["recordType"]),
            summary=str(record.get("summary") or record.get("label") or record["recordType"]),
            keywords=_expand_symbolic_keywords(
                [
                    record.get("label"),
                    record.get("summary"),
                    record.get("recordType"),
                    *_record_detail_keywords(record.get("details")),
                ]
            ),
            symbolic_fingerprint=_record_detail_keywords(record.get("details")),
            source_id=record["id"],
            evidence_ids=list(record.get("evidenceIds", [])),
            material_id=(record.get("relatedMaterialIds") or [None])[0],
            privacy_class=str(record.get("privacyClass", "approved_summary")),
            created_at=record.get("createdAt"),
            updated_at=record.get("updatedAt", record.get("createdAt")),
            observed_at=record.get(
                "windowEnd",
                record.get("updatedAt", record.get("createdAt", now_iso())),
            ),
            importance_score=_record_confidence_score(record.get("confidence"), default=0.65),
            importance_reasons=[f"living_myth:{record['recordType']}"],
            last_seen=record.get(
                "windowEnd",
                record.get("updatedAt", record.get("createdAt", now_iso())),
            ),
        )
        if _matches_memory_query(item, namespaces=namespaces, query=query):
            items.append(item)

    for review in bucket.living_myth_reviews.values():
        if (
            review.get("status") != "generated"
            or review.get("deletedAt") is not None
            or review.get("userId") != user_id
        ):
            continue
        review_type = str(review.get("reviewType") or "living_myth_review").replace("_", " ")
        response = str(review.get("result", {}).get("userFacingResponse") or review_type)
        item = _build_memory_item(
            user_id=user_id,
            namespace="living_myth_reviews",
            entity_id=review["id"],
            entity_type="LivingMythReview",
            label=review_type.title(),
            summary=response,
            keywords=_expand_symbolic_keywords([review.get("reviewType"), response]),
            source_id=review["id"],
            evidence_ids=list(review.get("evidenceIds", [])),
            material_id=(review.get("materialIds") or [None])[0],
            privacy_class="approved_summary",
            created_at=review.get("createdAt"),
            updated_at=review.get("updatedAt", review.get("createdAt")),
            observed_at=review.get("windowEnd", review.get("createdAt")),
            importance_score=0.65,
            importance_reasons=["review_generated"],
            last_seen=review.get("windowEnd", review.get("createdAt")),
        )
        if _matches_memory_query(item, namespaces=namespaces, query=query):
            items.append(item)

    for packet in bucket.analysis_packets.values():
        if (
            packet.get("status") != "generated"
            or packet.get("deletedAt") is not None
            or packet.get("userId") != user_id
        ):
            continue
        item = _build_memory_item(
            user_id=user_id,
            namespace="analysis_packets",
            entity_id=packet["id"],
            entity_type="AnalysisPacket",
            label=str(packet.get("packetTitle") or "Analysis packet"),
            summary=str(packet.get("userFacingResponse") or packet.get("packetTitle") or ""),
            keywords=_expand_symbolic_keywords(
                [packet.get("packetTitle"), packet.get("userFacingResponse"), packet.get("source")]
            ),
            source_id=packet["id"],
            evidence_ids=list(packet.get("evidenceIds", [])),
            material_id=(packet.get("includedMaterialIds") or [None])[0],
            privacy_class=str(packet.get("privacyClass", "approved_summary")),
            created_at=packet.get("createdAt"),
            updated_at=packet.get("updatedAt", packet.get("createdAt")),
            observed_at=packet.get("windowEnd", packet.get("createdAt")),
            importance_score=0.6,
            importance_reasons=["analysis_packet"],
            last_seen=packet.get("windowEnd", packet.get("createdAt")),
        )
        if _matches_memory_query(item, namespaces=namespaces, query=query):
            items.append(item)

    ranking_profile = str((query or {}).get("rankingProfile") or "default")
    items.sort(key=lambda item: _memory_sort_key(item, ranking_profile), reverse=True)
    limit = _memory_limit(query)
    ranking_notes = [f"Ranking profile: {ranking_profile}."]
    if namespaces:
        ranking_notes.append(
            "Namespace filter: " + ", ".join(sorted(str(namespace) for namespace in namespaces))
        )
    return {
        "userId": user_id,
        "query": deepcopy(query or {}),
        "items": deepcopy(items[:limit]),
        "generatedAt": now_iso(),
        "rankingNotes": ranking_notes,
    }


def _build_graph_node(
    *,
    user_id: Id,
    node_id: Id,
    node_type: str,
    source_id: Id,
    label: str,
    summary: str | None = None,
    privacy_class: str = "approved_summary",
    created_at: str | None = None,
    updated_at: str | None = None,
    metadata: dict[str, object] | None = None,
) -> GraphNodeProjection:
    node: GraphNodeProjection = {
        "id": node_id,
        "userId": user_id,
        "type": node_type,
        "sourceId": source_id,
        "label": _truncate(label or node_type, 120),
        "privacyClass": privacy_class,
        "createdAt": created_at or now_iso(),
        "updatedAt": updated_at or created_at or now_iso(),
    }
    if summary:
        node["summary"] = _truncate(summary, 220)
    if metadata:
        node["metadata"] = metadata
    return node


def _validate_graph_types(query: GraphQuery | None) -> None:
    node_types = set(DEFAULT_GRAPH_QUERY_ALLOWLIST["nodeTypes"])
    edge_types = set(DEFAULT_GRAPH_QUERY_ALLOWLIST["edgeTypes"])
    requested_node_types = {
        value for value in (query or {}).get("nodeTypes", []) if isinstance(value, str) and value
    }
    invalid_node_types = sorted(requested_node_types - node_types)
    if invalid_node_types:
        raise ValidationError("Unsupported graph node types: " + ", ".join(invalid_node_types))
    requested_edge_types = {
        value for value in (query or {}).get("edgeTypes", []) if isinstance(value, str) and value
    }
    invalid_edge_types = sorted(requested_edge_types - edge_types)
    if invalid_edge_types:
        raise ValidationError("Unsupported graph edge types: " + ", ".join(invalid_edge_types))


def _graph_traversal_depth(query: GraphQuery | None, warnings: list[str]) -> int:
    raw_depth = (query or {}).get("maxDepth", DEFAULT_GRAPH_QUERY_ALLOWLIST["maxDepth"])
    try:
        max_depth = int(raw_depth)
    except (TypeError, ValueError):
        return DEFAULT_GRAPH_QUERY_ALLOWLIST["maxDepth"]
    if max_depth > DEFAULT_GRAPH_QUERY_ALLOWLIST["maxDepth"]:
        warnings.append(f"maxDepth clamped to {DEFAULT_GRAPH_QUERY_ALLOWLIST['maxDepth']}.")
        return DEFAULT_GRAPH_QUERY_ALLOWLIST["maxDepth"]
    return max(0, max_depth)


def _traverse_graph(
    root_node_ids: list[Id],
    *,
    nodes_by_id: dict[Id, GraphNodeProjection],
    edges: list[GraphEdgeProjection],
    direction: str,
    max_depth: int,
) -> set[Id]:
    discovered = {node_id for node_id in root_node_ids if node_id in nodes_by_id}
    if not discovered or max_depth <= 0:
        return discovered
    outbound: dict[Id, set[Id]] = defaultdict(set)
    inbound: dict[Id, set[Id]] = defaultdict(set)
    for edge in edges:
        outbound[edge["fromNodeId"]].add(edge["toNodeId"])
        inbound[edge["toNodeId"]].add(edge["fromNodeId"])
    frontier = set(discovered)
    for _ in range(max_depth):
        next_frontier: set[Id] = set()
        for node_id in frontier:
            if direction in {"outbound", "both"}:
                next_frontier.update(outbound.get(node_id, set()))
            if direction in {"inbound", "both"}:
                next_frontier.update(inbound.get(node_id, set()))
        next_frontier -= discovered
        if not next_frontier:
            break
        discovered.update(next_frontier)
        frontier = next_frontier
    return discovered


def query_graph_locked(
    bucket: UserCirculatioBucket,
    *,
    user_id: Id,
    query: GraphQuery | None = None,
) -> GraphQueryResult:
    _validate_graph_types(query)
    warnings: list[str] = []
    max_depth = _graph_traversal_depth(query, warnings)
    include_evidence = bool((query or {}).get("includeEvidence"))
    requested_node_types = set((query or {}).get("nodeTypes", []))
    requested_edge_types = set((query or {}).get("edgeTypes", []))
    limit = _graph_limit(query)
    nodes_by_id: dict[Id, GraphNodeProjection] = {}
    edges: list[GraphEdgeProjection] = []

    def add_node(node: GraphNodeProjection) -> None:
        nodes_by_id.setdefault(node["id"], node)

    def add_edge(
        edge_type: str,
        from_node_id: Id,
        to_node_id: Id,
        *,
        evidence_ids: list[Id] | None = None,
        created_at: str | None = None,
    ) -> None:
        if from_node_id not in nodes_by_id or to_node_id not in nodes_by_id:
            return
        edges.append(
            {
                "id": create_id("graph_edge"),
                "userId": user_id,
                "type": edge_type,
                "fromNodeId": from_node_id,
                "toNodeId": to_node_id,
                "evidenceIds": list(evidence_ids or []),
                "createdAt": created_at or now_iso(),
            }
        )

    for material in bucket.materials.values():
        if material.get("status") == "deleted" or material.get("userId") != user_id:
            continue
        node_type = {
            "dream": "DreamEntry",
            "reflection": "ReflectionEntry",
            "charged_event": "ChargedEventNote",
        }.get(material["materialType"], "MaterialEntry")
        add_node(
            _build_graph_node(
                user_id=user_id,
                node_id=material["id"],
                node_type=node_type,
                source_id=material["id"],
                label=str(material.get("title") or material["materialType"]),
                summary=_material_summary_text(material),
                privacy_class=str(material.get("privacyClass", "approved_summary")),
                created_at=material.get("createdAt"),
                updated_at=material.get("updatedAt", material.get("createdAt")),
                metadata={"tags": list(material.get("tags", []))[:5]},
            )
        )

    if include_evidence:
        for evidence in bucket.evidence.values():
            source_id = str(evidence.get("sourceId") or evidence["id"])
            add_node(
                _build_graph_node(
                    user_id=user_id,
                    node_id=evidence["id"],
                    node_type="EvidenceItem",
                    source_id=source_id,
                    label=str(evidence.get("type") or "evidence"),
                    summary=str(evidence.get("quoteOrSummary") or ""),
                    privacy_class=str(evidence.get("privacyClass", "approved_summary")),
                    created_at=evidence.get("timestamp"),
                    updated_at=evidence.get("timestamp"),
                    metadata={
                        "reliability": evidence.get("reliability"),
                        "sourceId": source_id,
                    },
                )
            )

    for symbol in bucket.symbols.values():
        if symbol.get("status") == "deleted" or symbol.get("userId") != user_id:
            continue
        add_node(
            _build_graph_node(
                user_id=user_id,
                node_id=symbol["id"],
                node_type="PersonalSymbol",
                source_id=symbol["id"],
                label=symbol["canonicalName"],
                summary=(
                    f"Recurring symbol with {symbol.get('recurrenceCount', 0)} appearance(s)."
                ),
                created_at=symbol.get("createdAt"),
                updated_at=symbol.get("updatedAt", symbol.get("createdAt")),
            )
        )

    for pattern in bucket.patterns.values():
        if pattern.get("status") in {"deleted", "disconfirmed"}:
            continue
        add_node(
            _build_graph_node(
                user_id=user_id,
                node_id=pattern["id"],
                node_type=(
                    "ComplexCandidate"
                    if pattern.get("patternType") == "complex_candidate"
                    else "Theme"
                ),
                source_id=pattern["id"],
                label=pattern["label"],
                summary=pattern["formulation"],
                created_at=pattern.get("createdAt"),
                updated_at=pattern.get("updatedAt", pattern.get("createdAt")),
                metadata={
                    "activationIntensity": pattern.get("activationIntensity"),
                    "confidence": pattern.get("confidence"),
                },
            )
        )

    for run in bucket.interpretation_runs.values():
        if run.get("status") == "deleted" or run.get("userId") != user_id:
            continue
        add_node(
            _build_graph_node(
                user_id=user_id,
                node_id=run["id"],
                node_type="InterpretationRun",
                source_id=run["id"],
                label=f"{run['materialType']} interpretation",
                summary=str(
                    run.get("result", {}).get("userFacingResponse")
                    or f"Run status: {run.get('status', 'recorded')}."
                ),
                created_at=run.get("createdAt"),
                updated_at=run.get("updatedAt", run.get("createdAt")),
                metadata={"status": run.get("status")},
            )
        )

    for practice in bucket.practice_sessions.values():
        if practice.get("status") == "deleted" or practice.get("userId") != user_id:
            continue
        add_node(
            _build_graph_node(
                user_id=user_id,
                node_id=practice["id"],
                node_type="PracticeSession",
                source_id=practice["id"],
                label=str(practice.get("target") or practice["practiceType"]),
                summary=str(practice.get("outcome") or practice.get("reason") or ""),
                created_at=practice.get("createdAt"),
                updated_at=practice.get("updatedAt", practice.get("createdAt")),
                metadata={"practiceType": practice.get("practiceType")},
            )
        )

    for body_state in bucket.body_states.values():
        if body_state.get("status") == "deleted" or body_state.get("userId") != user_id:
            continue
        add_node(
            _build_graph_node(
                user_id=user_id,
                node_id=body_state["id"],
                node_type="BodyState",
                source_id=body_state["id"],
                label=body_state["sensation"],
                summary=body_state.get("bodyRegion") or body_state["sensation"],
                privacy_class=str(body_state.get("privacyClass", "approved_summary")),
                created_at=body_state.get("createdAt"),
                updated_at=body_state.get("updatedAt", body_state.get("createdAt")),
            )
        )

    for goal in bucket.goals.values():
        if goal.get("status") == "deleted" or goal.get("userId") != user_id:
            continue
        add_node(
            _build_graph_node(
                user_id=user_id,
                node_id=goal["id"],
                node_type="Goal",
                source_id=goal["id"],
                label=goal["label"],
                summary=str(goal.get("description") or goal["label"]),
                created_at=goal.get("createdAt"),
                updated_at=goal.get("updatedAt", goal.get("createdAt")),
                metadata={"status": goal.get("status")},
            )
        )

    for tension in bucket.goal_tensions.values():
        if tension.get("status") == "deleted" or tension.get("userId") != user_id:
            continue
        add_node(
            _build_graph_node(
                user_id=user_id,
                node_id=tension["id"],
                node_type="GoalTension",
                source_id=tension["id"],
                label=tension["tensionSummary"],
                summary=", ".join(str(value) for value in tension.get("polarityLabels", [])[:4]),
                created_at=tension.get("createdAt"),
                updated_at=tension.get("updatedAt", tension.get("createdAt")),
            )
        )

    for series in bucket.dream_series.values():
        if series.get("status") == "deleted" or series.get("userId") != user_id:
            continue
        add_node(
            _build_graph_node(
                user_id=user_id,
                node_id=series["id"],
                node_type="DreamSeries",
                source_id=series["id"],
                label=series["label"],
                summary=str(series.get("progressionSummary") or series["label"]),
                created_at=series.get("createdAt"),
                updated_at=series.get("updatedAt", series.get("createdAt")),
            )
        )

    for record in bucket.individuation_records.values():
        if (
            record.get("status") not in {"active", "user_confirmed"}
            or record.get("deletedAt") is not None
            or record.get("userId") != user_id
        ):
            continue
        add_node(
            _build_graph_node(
                user_id=user_id,
                node_id=record["id"],
                node_type=_individuation_node_type(str(record["recordType"])),
                source_id=record["id"],
                label=str(record.get("label") or record["recordType"]),
                summary=str(record.get("summary") or record.get("label") or record["recordType"]),
                privacy_class=str(record.get("privacyClass", "approved_summary")),
                created_at=record.get("createdAt"),
                updated_at=record.get("updatedAt", record.get("createdAt")),
                metadata=_graph_record_metadata(record),
            )
        )

    for record in bucket.living_myth_records.values():
        if (
            record.get("status") not in {"active", "user_confirmed", "released"}
            or record.get("deletedAt") is not None
            or record.get("userId") != user_id
        ):
            continue
        add_node(
            _build_graph_node(
                user_id=user_id,
                node_id=record["id"],
                node_type=_living_myth_node_type(str(record["recordType"])),
                source_id=record["id"],
                label=str(record.get("label") or record["recordType"]),
                summary=str(record.get("summary") or record.get("label") or record["recordType"]),
                privacy_class=str(record.get("privacyClass", "approved_summary")),
                created_at=record.get("createdAt"),
                updated_at=record.get("updatedAt", record.get("createdAt")),
                metadata=_graph_record_metadata(record),
            )
        )

    for review in bucket.living_myth_reviews.values():
        if (
            review.get("status") not in {"generated", "withheld"}
            or review.get("deletedAt") is not None
            or review.get("userId") != user_id
        ):
            continue
        add_node(
            _build_graph_node(
                user_id=user_id,
                node_id=review["id"],
                node_type="LivingMythReview",
                source_id=review["id"],
                label=str(review.get("reviewType", "living_myth_review")).replace("_", " "),
                summary=str(
                    review.get("result", {}).get("userFacingResponse")
                    or review.get("reviewType", "living_myth_review")
                ),
                created_at=review.get("createdAt"),
                updated_at=review.get("updatedAt", review.get("createdAt")),
                metadata={"status": review.get("status"), "reviewType": review.get("reviewType")},
            )
        )

    for packet in bucket.analysis_packets.values():
        if (
            packet.get("status") != "generated"
            or packet.get("deletedAt") is not None
            or packet.get("userId") != user_id
        ):
            continue
        add_node(
            _build_graph_node(
                user_id=user_id,
                node_id=packet["id"],
                node_type="AnalysisPacket",
                source_id=packet["id"],
                label=str(packet.get("packetTitle") or "Analysis packet"),
                summary=str(packet.get("userFacingResponse") or packet.get("packetTitle") or ""),
                privacy_class=str(packet.get("privacyClass", "approved_summary")),
                created_at=packet.get("createdAt"),
                updated_at=packet.get("updatedAt", packet.get("createdAt")),
                metadata={"source": packet.get("source")},
            )
        )

    for symbol in bucket.symbols.values():
        if symbol.get("status") == "deleted" or symbol.get("userId") != user_id:
            continue
        for material_id in symbol.get("linkedMaterialIds", []):
            add_edge("MENTIONS", material_id, symbol["id"])
            add_edge("FEATURES", material_id, symbol["id"])

    for pattern in bucket.patterns.values():
        if pattern.get("status") in {"deleted", "disconfirmed"}:
            continue
        for material_id in pattern.get("linkedMaterialIds", []):
            add_edge(
                "MAY_EXPRESS",
                material_id,
                pattern["id"],
                evidence_ids=list(pattern.get("evidenceIds", [])),
            )
        for symbol_id in pattern.get("linkedSymbolIds", []):
            add_edge(
                "LINKED_TO",
                pattern["id"],
                symbol_id,
                evidence_ids=list(pattern.get("evidenceIds", [])),
            )
        if include_evidence:
            for evidence_id in pattern.get("evidenceIds", []):
                add_edge("SUPPORTED_BY", pattern["id"], evidence_id, evidence_ids=[evidence_id])

    for run in bucket.interpretation_runs.values():
        if run.get("status") == "deleted" or run.get("userId") != user_id:
            continue
        add_edge("DRAWS_FROM", run["id"], run["materialId"])
        if include_evidence:
            for evidence_id in run.get("evidenceIds", []):
                add_edge("USED_EVIDENCE", run["id"], evidence_id, evidence_ids=[evidence_id])

    for practice in bucket.practice_sessions.values():
        if practice.get("status") == "deleted" or practice.get("userId") != user_id:
            continue
        material_id = practice.get("materialId")
        if material_id:
            add_edge("PRECEDED_BY_PRACTICE", material_id, practice["id"])
        run_id = practice.get("runId")
        if run_id:
            add_edge("TARGETED", practice["id"], run_id)

    for body_state in bucket.body_states.values():
        if body_state.get("status") == "deleted" or body_state.get("userId") != user_id:
            continue
        for symbol_id in body_state.get("linkedSymbolIds", []):
            add_edge(
                "TRIGGERS",
                symbol_id,
                body_state["id"],
                evidence_ids=list(body_state.get("evidenceIds", [])),
            )
        for material_id in body_state.get("linkedMaterialIds", []):
            add_edge(
                "HAS_BODY_STATE",
                material_id,
                body_state["id"],
                evidence_ids=list(body_state.get("evidenceIds", [])),
            )
        for goal_id in body_state.get("linkedGoalIds", []):
            add_edge(
                "CORRELATES_WITH",
                body_state["id"],
                goal_id,
                evidence_ids=list(body_state.get("evidenceIds", [])),
            )

    for goal in bucket.goals.values():
        if goal.get("status") == "deleted" or goal.get("userId") != user_id:
            continue
        for symbol_id in goal.get("linkedSymbolIds", []):
            add_edge("RELATES_TO_GOAL", symbol_id, goal["id"])
        for material_id in goal.get("linkedMaterialIds", []):
            add_edge("RELATES_TO_GOAL", material_id, goal["id"])

    for tension in bucket.goal_tensions.values():
        if tension.get("status") == "deleted" or tension.get("userId") != user_id:
            continue
        for goal_id in tension.get("goalIds", []):
            add_edge(
                "TENSIONS_WITH",
                goal_id,
                tension["id"],
                evidence_ids=list(tension.get("evidenceIds", [])),
            )
        if include_evidence:
            for evidence_id in tension.get("evidenceIds", []):
                add_edge("SUPPORTED_BY", tension["id"], evidence_id, evidence_ids=[evidence_id])

    for series in bucket.dream_series.values():
        if series.get("status") == "deleted" or series.get("userId") != user_id:
            continue
        for material_id in series.get("materialIds", []):
            add_edge(
                "BELONGS_TO_SERIES",
                material_id,
                series["id"],
                evidence_ids=list(series.get("evidenceIds", [])),
            )

    for record in bucket.individuation_records.values():
        if (
            record.get("status") not in {"active", "user_confirmed"}
            or record.get("deletedAt") is not None
            or record.get("userId") != user_id
        ):
            continue
        evidence_ids = list(record.get("evidenceIds", []))
        record_type = str(record["recordType"])
        material_edge_type = {
            "threshold_process": "MARKS_THRESHOLD",
            "relational_scene": "REPEATS_AS_SCENE",
        }.get(record_type, "EMERGED_FROM")
        for material_id in record.get("relatedMaterialIds", []):
            add_edge(material_edge_type, material_id, record["id"], evidence_ids=evidence_ids)
        for symbol_id in record.get("relatedSymbolIds", []):
            edge_type = (
                "CORRESPONDS_WITH"
                if record_type == "inner_outer_correspondence"
                else "ASSOCIATED_WITH"
            )
            add_edge(edge_type, record["id"], symbol_id, evidence_ids=evidence_ids)
        for goal_id in record.get("relatedGoalIds", []):
            add_edge("RELATES_TO_GOAL", record["id"], goal_id, evidence_ids=evidence_ids)
        for series_id in record.get("relatedDreamSeriesIds", []):
            add_edge(material_edge_type, series_id, record["id"], evidence_ids=evidence_ids)
        for practice_id in record.get("relatedPracticeSessionIds", []):
            add_edge("FOLLOWED_BY", practice_id, record["id"], evidence_ids=evidence_ids)
        details = record.get("details", {})
        if isinstance(details, dict):
            for opposition_id in details.get("oppositionIds", []):
                add_edge("EMERGES_FROM", record["id"], opposition_id, evidence_ids=evidence_ids)
            relational_scene_id = details.get("relationalSceneId")
            if isinstance(relational_scene_id, str) and relational_scene_id:
                add_edge(
                    "MAY_PROJECT",
                    relational_scene_id,
                    record["id"],
                    evidence_ids=evidence_ids,
                )
            for related_id in [*details.get("innerRefs", []), *details.get("outerRefs", [])]:
                if isinstance(related_id, str) and related_id:
                    add_edge(
                        "CORRESPONDS_WITH",
                        record["id"],
                        related_id,
                        evidence_ids=evidence_ids,
                    )
            if include_evidence:
                for counterevidence_id in details.get("counterevidenceIds", []):
                    add_edge(
                        "CONTRADICTED_BY",
                        record["id"],
                        counterevidence_id,
                        evidence_ids=[counterevidence_id],
                    )
        if include_evidence:
            for evidence_id in evidence_ids:
                add_edge("SUPPORTED_BY", record["id"], evidence_id, evidence_ids=[evidence_id])

    for record in bucket.living_myth_records.values():
        if (
            record.get("status") not in {"active", "user_confirmed", "released"}
            or record.get("deletedAt") is not None
            or record.get("userId") != user_id
        ):
            continue
        evidence_ids = list(record.get("evidenceIds", []))
        record_type = str(record["recordType"])
        for material_id in record.get("relatedMaterialIds", []):
            edge_type = (
                "BELONGS_TO_CHAPTER" if record_type == "life_chapter_snapshot" else "EMERGED_FROM"
            )
            add_edge(edge_type, material_id, record["id"], evidence_ids=evidence_ids)
        for symbol_id in record.get("relatedSymbolIds", []):
            edge_type = (
                "ORIENTS_TOWARD" if record_type == "life_chapter_snapshot" else "ASSOCIATED_WITH"
            )
            add_edge(edge_type, record["id"], symbol_id, evidence_ids=evidence_ids)
        for goal_id in record.get("relatedGoalIds", []):
            add_edge("RELATES_TO_GOAL", record["id"], goal_id, evidence_ids=evidence_ids)
        for series_id in record.get("relatedDreamSeriesIds", []):
            add_edge("ASSOCIATED_WITH", record["id"], series_id, evidence_ids=evidence_ids)
        details = record.get("details", {})
        if isinstance(details, dict):
            if record_type == "life_chapter_snapshot":
                for related_record_id in details.get("activeOppositionIds", []):
                    add_edge(
                        "BELONGS_TO_CHAPTER",
                        related_record_id,
                        record["id"],
                        evidence_ids=evidence_ids,
                    )
                for related_record_id in details.get("thresholdProcessIds", []):
                    add_edge(
                        "BELONGS_TO_CHAPTER",
                        related_record_id,
                        record["id"],
                        evidence_ids=evidence_ids,
                    )
                for related_record_id in details.get("relationalSceneIds", []):
                    add_edge(
                        "BELONGS_TO_CHAPTER",
                        related_record_id,
                        record["id"],
                        evidence_ids=evidence_ids,
                    )
                for related_record_id in details.get("correspondenceIds", []):
                    add_edge(
                        "BELONGS_TO_CHAPTER",
                        related_record_id,
                        record["id"],
                        evidence_ids=evidence_ids,
                    )
            related_chapter_id = details.get("relatedChapterId")
            if isinstance(related_chapter_id, str) and related_chapter_id:
                add_edge(
                    "ORIENTS_TOWARD",
                    record["id"],
                    related_chapter_id,
                    evidence_ids=evidence_ids,
                )
            threshold_process_id = details.get("thresholdProcessId")
            if isinstance(threshold_process_id, str) and threshold_process_id:
                add_edge(
                    "MARKS_THRESHOLD",
                    record["id"],
                    threshold_process_id,
                    evidence_ids=evidence_ids,
                )
            for complex_id in [details.get("complexCandidateId"), details.get("patternId")]:
                if isinstance(complex_id, str) and complex_id:
                    add_edge("TRACKS_COMPLEX", record["id"], complex_id, evidence_ids=evidence_ids)
        for individuation_record_id in record.get("relatedIndividuationRecordIds", []):
            edge_type = (
                "BELONGS_TO_CHAPTER"
                if record_type == "life_chapter_snapshot"
                else "ASSOCIATED_WITH"
            )
            add_edge(edge_type, individuation_record_id, record["id"], evidence_ids=evidence_ids)
        if include_evidence:
            for evidence_id in evidence_ids:
                add_edge("SUPPORTED_BY", record["id"], evidence_id, evidence_ids=[evidence_id])

    for review in bucket.living_myth_reviews.values():
        if (
            review.get("status") not in {"generated", "withheld"}
            or review.get("deletedAt") is not None
            or review.get("userId") != user_id
        ):
            continue
        for material_id in review.get("materialIds", []):
            add_edge(
                "SUMMARIZES",
                review["id"],
                material_id,
                evidence_ids=list(review.get("evidenceIds", [])),
            )
        if include_evidence:
            for evidence_id in review.get("evidenceIds", []):
                add_edge("USED_EVIDENCE", review["id"], evidence_id, evidence_ids=[evidence_id])

    for packet in bucket.analysis_packets.values():
        if (
            packet.get("status") != "generated"
            or packet.get("deletedAt") is not None
            or packet.get("userId") != user_id
        ):
            continue
        evidence_ids = list(packet.get("evidenceIds", []))
        for material_id in packet.get("includedMaterialIds", []):
            add_edge("SUMMARIZES", packet["id"], material_id, evidence_ids=evidence_ids)
        for record_ref in packet.get("includedRecordRefs", []):
            if not isinstance(record_ref, dict):
                continue
            record_id = record_ref.get("recordId")
            if isinstance(record_id, str) and record_id:
                add_edge("CONTAINED_IN_PACKET", record_id, packet["id"], evidence_ids=evidence_ids)
        if include_evidence:
            for evidence_id in evidence_ids:
                add_edge("USED_EVIDENCE", packet["id"], evidence_id, evidence_ids=[evidence_id])

    nodes = list(nodes_by_id.values())
    if requested_node_types:
        nodes = [node for node in nodes if node["type"] in requested_node_types]
    visible_node_ids = {node["id"] for node in nodes}
    filtered_edges = [
        edge
        for edge in edges
        if edge["fromNodeId"] in visible_node_ids and edge["toNodeId"] in visible_node_ids
    ]
    if requested_edge_types:
        filtered_edges = [edge for edge in filtered_edges if edge["type"] in requested_edge_types]

    root_node_ids = [
        value for value in (query or {}).get("rootNodeIds", []) if isinstance(value, str)
    ]
    direction = str((query or {}).get("direction") or "both")
    if direction not in {"outbound", "inbound", "both"}:
        direction = "both"
    if root_node_ids:
        nodes_by_id = {node["id"]: node for node in nodes}
        discovered = _traverse_graph(
            root_node_ids,
            nodes_by_id=nodes_by_id,
            edges=filtered_edges,
            direction=direction,
            max_depth=max_depth,
        )
        nodes = [node for node in nodes if node["id"] in discovered]
        visible_node_ids = {node["id"] for node in nodes}
        filtered_edges = [
            edge
            for edge in filtered_edges
            if edge["fromNodeId"] in visible_node_ids and edge["toNodeId"] in visible_node_ids
        ]

    nodes.sort(
        key=lambda item: (
            _parse_datetime(item.get("updatedAt", item["createdAt"])).timestamp(),
            item["label"],
        ),
        reverse=True,
    )
    filtered_edges.sort(
        key=lambda item: _parse_datetime(item["createdAt"]).timestamp(),
        reverse=True,
    )
    return {
        "userId": user_id,
        "nodes": deepcopy(nodes[:limit]),
        "edges": deepcopy(filtered_edges[:limit]),
        "allowlist": deepcopy(DEFAULT_GRAPH_QUERY_ALLOWLIST),
        "warnings": warnings,
    }


def build_life_context_snapshot_locked(
    bucket: UserCirculatioBucket,
    *,
    user_id: Id,
    window_start: str,
    window_end: str,
    exclude_material_id: Id | None = None,
) -> LifeContextSnapshot | None:
    start_dt = _parse_datetime(window_start)
    end_dt = _parse_datetime(window_end)
    materials = [
        item
        for item in bucket.materials.values()
        if item.get("status") != "deleted"
        and item["userId"] == user_id
        and item["id"] != exclude_material_id
        and _is_within_window(_material_timestamp(item), start_dt, end_dt)
    ]
    practices = [
        item
        for item in bucket.practice_sessions.values()
        if item.get("status") != "deleted"
        and item["userId"] == user_id
        and _is_within_window(_practice_timestamp(item), start_dt, end_dt)
    ]
    symbols = active_symbols(bucket)
    patterns = active_patterns(bucket)
    goals = [
        item
        for item in bucket.goals.values()
        if item.get("status") not in {"deleted", "completed"} and item["userId"] == user_id
    ]
    goal_tensions = [
        item
        for item in bucket.goal_tensions.values()
        if item.get("status") != "deleted" and item["userId"] == user_id
    ]
    if (
        not materials
        and not practices
        and not symbols
        and not patterns
        and not goals
        and not goal_tensions
    ):
        return None
    snapshot: LifeContextSnapshot = {
        "windowStart": window_start,
        "windowEnd": window_end,
        "source": "circulatio-backend",
    }
    life_event_refs = _derive_life_event_refs(materials)
    if life_event_refs:
        snapshot["lifeEventRefs"] = life_event_refs
    mood_summary = _derive_mood_summary(symbols)
    if mood_summary:
        snapshot["moodSummary"] = mood_summary
    energy_summary = _derive_body_state_energy_summary(
        [
            item
            for item in bucket.body_states.values()
            if item.get("status") != "deleted"
            and _is_within_window(
                _parse_datetime(item.get("observedAt", item.get("createdAt"))),
                start_dt,
                end_dt,
            )
        ]
    ) or _derive_energy_summary(practices)
    if energy_summary:
        snapshot["energySummary"] = energy_summary
    focus_summary = _derive_focus_summary(symbols, patterns)
    if focus_summary:
        snapshot["focusSummary"] = focus_summary
    goals.sort(key=lambda item: item.get("updatedAt", item.get("createdAt", "")), reverse=True)
    if goals:
        snapshot["activeGoals"] = [_project_goal_summary(item) for item in goals[:5]]
    goal_tensions.sort(
        key=lambda item: item.get("updatedAt", item.get("createdAt", "")),
        reverse=True,
    )
    if goal_tensions:
        snapshot["goalTensions"] = [
            _project_goal_tension_summary(item) for item in goal_tensions[:5]
        ]
    mental_state = _derive_mental_state_summary(
        [
            item
            for item in bucket.interpretation_runs.values()
            if item.get("status") != "deleted"
            and _is_within_window(_parse_datetime(item.get("createdAt")), start_dt, end_dt)
        ],
        bucket.feedback,
        list(bucket.suppressed.values()),
    )
    if mental_state:
        snapshot["mentalStateSummary"] = mental_state
    habit_summary = _derive_habit_summary(materials, practices, start_dt, end_dt)
    if habit_summary:
        snapshot["habitSummary"] = habit_summary
    notable_changes = _derive_notable_changes(
        [
            entry
            for values in bucket.symbol_history.values()
            for entry in values
            if _is_within_window(_parse_datetime(entry.get("createdAt")), start_dt, end_dt)
        ],
        [
            entry
            for values in bucket.pattern_history.values()
            for entry in values
            if _is_within_window(_parse_datetime(entry.get("createdAt")), start_dt, end_dt)
        ],
        practices,
        patterns,
    )
    notable_changes.extend(
        _derive_body_state_changes(
            [
                item
                for item in bucket.body_states.values()
                if item.get("status") != "deleted"
                and _is_within_window(
                    _parse_datetime(item.get("observedAt", item.get("createdAt"))),
                    start_dt,
                    end_dt,
                )
            ]
        )
    )
    notable_changes.extend(_derive_dream_series_changes(list(bucket.dream_series.values())))
    if notable_changes:
        snapshot["notableChanges"] = list(dict.fromkeys(notable_changes))[:5]
    return snapshot if len(snapshot) > 3 else None


def build_method_context_snapshot_locked(
    bucket: UserCirculatioBucket,
    *,
    user_id: Id,
    window_start: str,
    window_end: str,
    material_id: Id | None = None,
) -> MethodContextSnapshot | None:
    return _build_method_context_snapshot_locked_context(
        bucket,
        user_id=user_id,
        window_start=window_start,
        window_end=window_end,
        material_id=material_id,
    )


def _thread_source_ref(
    record_type: str,
    record_id: Id,
    *,
    summary: str | None = None,
) -> MethodStateSourceRef:
    ref: MethodStateSourceRef = {
        "recordType": record_type,
        "recordId": record_id,
    }
    if summary:
        ref["summary"] = _truncate(summary, 180)
    return ref


def _thread_entity_refs(
    *,
    entity_ids: list[Id] | None = None,
    material_ids: list[Id] | None = None,
    symbol_ids: list[Id] | None = None,
    pattern_ids: list[Id] | None = None,
    goal_ids: list[Id] | None = None,
    dream_series_ids: list[Id] | None = None,
    journey_ids: list[Id] | None = None,
    practice_session_ids: list[Id] | None = None,
) -> dict[str, list[Id]]:
    refs: dict[str, list[Id]] = {}
    if entity_ids:
        refs["entities"] = list(dict.fromkeys(entity_ids))
    if material_ids:
        refs["materials"] = list(dict.fromkeys(material_ids))
    if symbol_ids:
        refs["symbols"] = list(dict.fromkeys(symbol_ids))
    if pattern_ids:
        refs["patterns"] = list(dict.fromkeys(pattern_ids))
    if goal_ids:
        refs["goals"] = list(dict.fromkeys(goal_ids))
    if dream_series_ids:
        refs["dreamSeries"] = list(dict.fromkeys(dream_series_ids))
    if journey_ids:
        refs["journeys"] = list(dict.fromkeys(journey_ids))
    if practice_session_ids:
        refs["practiceSessions"] = list(dict.fromkeys(practice_session_ids))
    return refs


def _thread_surface_readiness(
    kind: str,
    *,
    status: str,
    invitation_readiness: str | None = None,
) -> ThreadSurfaceReadiness:
    ready = status in {"active", "eligible", "ready", "user_confirmed"}
    review_ready = invitation_readiness in {"ask", "ready"} or ready
    if kind == "journey":
        return {
            "intakeContext": "available",
            "discovery": "ready" if ready else "available",
            "aliveToday": "ready" if ready else "available",
            "weeklyReview": "available",
            "journeyPage": "ready" if ready else "available",
            "rhythmicBrief": "available",
            "livingMythReview": "available",
            "analysisPacket": "available",
            "methodStateResponse": "available",
        }
    if kind == "dream_series":
        return {
            "intakeContext": "available",
            "discovery": "available",
            "aliveToday": "available",
            "journeyPage": "available",
            "rhythmicBrief": "ready" if ready else "available",
            "analysisPacket": "available",
        }
    if kind == "threshold_process":
        return {
            "intakeContext": "available",
            "discovery": "available",
            "journeyPage": "available",
            "rhythmicBrief": "ready" if review_ready else "available",
            "thresholdReview": "ready" if review_ready else "available",
            "livingMythReview": "available",
            "analysisPacket": "available",
            "methodStateResponse": "available",
        }
    if kind == "relational_scene":
        return {
            "intakeContext": "available",
            "discovery": "available",
            "journeyPage": "available",
            "rhythmicBrief": "available",
            "thresholdReview": "available",
            "analysisPacket": "available",
            "methodStateResponse": "available",
        }
    if kind == "goal_tension":
        return {
            "discovery": "ready" if ready else "available",
            "aliveToday": "available",
            "journeyPage": "available",
            "rhythmicBrief": "available",
            "livingMythReview": "available",
            "analysisPacket": "available",
            "methodStateResponse": "available",
            "practice": "available",
        }
    if kind == "practice_loop":
        return {
            "discovery": "available",
            "journeyPage": "available",
            "rhythmicBrief": "available",
            "analysisPacket": "available",
            "methodStateResponse": "available",
            "practice": "ready" if ready else "available",
        }
    return {
        "discovery": "available",
        "aliveToday": "available",
        "journeyPage": "available",
        "rhythmicBrief": "available",
        "analysisPacket": "available",
        "methodStateResponse": "available",
    }


def _journey_ids_for_entity_refs(
    bucket: UserCirculatioBucket,
    entity_refs: dict[str, list[Id]],
) -> list[Id]:
    journey_ids = list(entity_refs.get("journeys", []))
    material_ids = set(entity_refs.get("materials", []))
    symbol_ids = set(entity_refs.get("symbols", []))
    pattern_ids = set(entity_refs.get("patterns", []))
    goal_ids = set(entity_refs.get("goals", []))
    dream_series_ids = set(entity_refs.get("dreamSeries", []))
    entity_ids = set(entity_refs.get("entities", []))
    for journey in bucket.journeys.values():
        if journey.get("status") == "deleted":
            continue
        explicit_ids = set(journey.get("relatedMaterialIds", []))
        explicit_ids.update(journey.get("relatedSymbolIds", []))
        explicit_ids.update(journey.get("relatedPatternIds", []))
        explicit_ids.update(journey.get("relatedGoalIds", []))
        explicit_ids.update(journey.get("relatedDreamSeriesIds", []))
        if (
            material_ids.intersection(journey.get("relatedMaterialIds", []))
            or symbol_ids.intersection(journey.get("relatedSymbolIds", []))
            or pattern_ids.intersection(journey.get("relatedPatternIds", []))
            or goal_ids.intersection(journey.get("relatedGoalIds", []))
            or dream_series_ids.intersection(journey.get("relatedDreamSeriesIds", []))
            or entity_ids.intersection(explicit_ids)
        ):
            journey_ids.append(journey["id"])
    return list(dict.fromkeys(journey_ids))


def _thread_source_last_touched(
    bucket: UserCirculatioBucket,
    source_refs: list[MethodStateSourceRef],
    *,
    fallback: str,
) -> str:
    timestamps = [fallback]
    stores = {
        "PracticeSession": bucket.practice_sessions,
        "GoalTension": bucket.goal_tensions,
        "Journey": bucket.journeys,
        "DreamSeries": bucket.dream_series,
        "ThresholdProcess": bucket.individuation_records,
        "RelationalScene": bucket.individuation_records,
    }
    for ref in source_refs:
        record_type = str(ref.get("recordType") or "")
        record_id = str(ref.get("recordId") or "")
        store = stores.get(record_type)
        if store is None or record_id not in store:
            continue
        record = store[record_id]
        timestamp = str(
            record.get("updatedAt")
            or record.get("windowEnd")
            or record.get("lastSeen")
            or record.get("completedAt")
            or record.get("createdAt")
            or fallback
        )
        timestamps.append(timestamp)
    return max(timestamps)


def build_thread_digests_locked(
    bucket: UserCirculatioBucket,
    *,
    user_id: Id,
    window_start: str,
    window_end: str,
    material_id: Id | None = None,
) -> list[ThreadDigest]:
    method_context = build_method_context_snapshot_locked(
        bucket,
        user_id=user_id,
        window_start=window_start,
        window_end=window_end,
        material_id=material_id,
    )
    if not isinstance(method_context, dict):
        return []
    digests: list[ThreadDigest] = []
    seen_keys: set[str] = set()

    def append_digest(digest: ThreadDigest) -> None:
        thread_key = str(digest.get("threadKey") or "").strip()
        if not thread_key or thread_key in seen_keys:
            return
        seen_keys.add(thread_key)
        digests.append(digest)

    for summary in method_context.get("activeJourneys", []):
        if not isinstance(summary, dict):
            continue
        journey_id = str(summary.get("id") or "").strip()
        if not journey_id:
            continue
        record = bucket.journeys.get(journey_id, {})
        entity_refs = _thread_entity_refs(
            journey_ids=[journey_id],
            material_ids=list(
                record.get("relatedMaterialIds", summary.get("relatedMaterialIds", []))
            ),
            symbol_ids=list(record.get("relatedSymbolIds", summary.get("relatedSymbolIds", []))),
            pattern_ids=list(record.get("relatedPatternIds", summary.get("relatedPatternIds", []))),
            goal_ids=list(record.get("relatedGoalIds", summary.get("relatedGoalIds", []))),
            dream_series_ids=list(
                record.get("relatedDreamSeriesIds", summary.get("relatedDreamSeriesIds", []))
            ),
        )
        summary_text = str(
            summary.get("currentQuestion")
            or record.get("currentQuestion")
            or summary.get("label")
            or record.get("label")
            or "Journey thread"
        )
        status = str(record.get("status") or summary.get("status") or "active")
        append_digest(
            {
                "threadKey": f"journey:{journey_id}",
                "kind": "journey",
                "status": status,
                "summary": _truncate(summary_text, 220),
                "entityRefs": entity_refs,
                "evidenceIds": [],
                "journeyIds": [journey_id],
                "sourceRecordRefs": [
                    _thread_source_ref("Journey", journey_id, summary=summary_text)
                ],
                "lastTouchedAt": str(
                    record.get("updatedAt")
                    or record.get("nextReviewDueAt")
                    or record.get("createdAt")
                    or window_end
                ),
                "surfaceReadiness": _thread_surface_readiness("journey", status=status),
            }
        )

    for summary in method_context.get("activeDreamSeries", []):
        if not isinstance(summary, dict):
            continue
        series_id = str(summary.get("id") or "").strip()
        if not series_id:
            continue
        record = bucket.dream_series.get(series_id, {})
        entity_refs = _thread_entity_refs(
            dream_series_ids=[series_id],
            material_ids=list(record.get("materialIds", summary.get("materialIds", []))),
            symbol_ids=list(record.get("symbolIds", summary.get("symbolIds", []))),
        )
        summary_text = str(
            record.get("progressionSummary")
            or summary.get("progressionSummary")
            or record.get("label")
            or summary.get("label")
            or "Dream series"
        )
        status = str(record.get("status") or summary.get("status") or "active")
        append_digest(
            {
                "threadKey": f"dream_series:{series_id}",
                "kind": "dream_series",
                "status": status,
                "summary": _truncate(summary_text, 220),
                "entityRefs": entity_refs,
                "evidenceIds": [],
                "journeyIds": _journey_ids_for_entity_refs(bucket, entity_refs),
                "sourceRecordRefs": [
                    _thread_source_ref("DreamSeries", series_id, summary=summary_text),
                ],
                "lastTouchedAt": str(
                    record.get("lastSeen")
                    or record.get("updatedAt")
                    or record.get("createdAt")
                    or window_end
                ),
                "surfaceReadiness": _thread_surface_readiness("dream_series", status=status),
            }
        )

    individuation = (
        method_context.get("individuationContext")
        if isinstance(method_context.get("individuationContext"), dict)
        else {}
    )
    for collection_name, record_type, kind in (
        ("thresholdProcesses", "ThresholdProcess", "threshold_process"),
        ("relationalScenes", "RelationalScene", "relational_scene"),
    ):
        for summary in individuation.get(collection_name, [])[:8]:
            if not isinstance(summary, dict):
                continue
            record_id = str(summary.get("id") or "").strip()
            if not record_id:
                continue
            record = bucket.individuation_records.get(record_id, {})
            entity_refs = _thread_entity_refs(
                entity_ids=[record_id],
                material_ids=list(record.get("relatedMaterialIds", [])),
                symbol_ids=list(record.get("relatedSymbolIds", [])),
                goal_ids=list(record.get("relatedGoalIds", [])),
                dream_series_ids=list(record.get("relatedDreamSeriesIds", [])),
                journey_ids=list(record.get("relatedJourneyIds", [])),
                practice_session_ids=list(record.get("relatedPracticeSessionIds", [])),
            )
            summary_text = str(
                record.get("summary")
                or summary.get("summary")
                or summary.get("sceneSummary")
                or summary.get("whatIsEnding")
                or summary.get("label")
                or record_type
            )
            status = str(record.get("status") or "active")
            invitation_readiness = None
            if isinstance(record.get("details"), dict):
                invitation_readiness = str(
                    record["details"].get("invitationReadiness") or ""
                ).strip()
            append_digest(
                {
                    "threadKey": f"{kind}:{record_id}",
                    "kind": kind,
                    "status": status,
                    "summary": _truncate(summary_text, 220),
                    "entityRefs": entity_refs,
                    "evidenceIds": list(record.get("evidenceIds", summary.get("evidenceIds", []))),
                    "journeyIds": _journey_ids_for_entity_refs(bucket, entity_refs),
                    "sourceRecordRefs": [
                        _thread_source_ref(record_type, record_id, summary=summary_text),
                    ],
                    "lastTouchedAt": str(
                        record.get("windowEnd")
                        or record.get("updatedAt")
                        or record.get("createdAt")
                        or window_end
                    ),
                    "surfaceReadiness": _thread_surface_readiness(
                        kind,
                        status=status,
                        invitation_readiness=invitation_readiness,
                    ),
                }
            )

    for summary in method_context.get("goalTensions", []):
        if not isinstance(summary, dict):
            continue
        tension_id = str(summary.get("id") or "").strip()
        if not tension_id:
            continue
        record = bucket.goal_tensions.get(tension_id, {})
        entity_refs = _thread_entity_refs(
            entity_ids=[tension_id],
            goal_ids=list(record.get("goalIds", summary.get("goalIds", []))),
        )
        summary_text = str(
            record.get("tensionSummary")
            or summary.get("tensionSummary")
            or "Goal tension remains active."
        )
        status = str(record.get("status") or summary.get("status") or "active")
        append_digest(
            {
                "threadKey": f"goal_tension:{tension_id}",
                "kind": "goal_tension",
                "status": status,
                "summary": _truncate(summary_text, 220),
                "entityRefs": entity_refs,
                "evidenceIds": list(record.get("evidenceIds", summary.get("evidenceIds", []))),
                "journeyIds": _journey_ids_for_entity_refs(bucket, entity_refs),
                "sourceRecordRefs": [
                    _thread_source_ref("GoalTension", tension_id, summary=summary_text),
                ],
                "lastTouchedAt": str(
                    record.get("updatedAt") or record.get("createdAt") or window_end
                ),
                "surfaceReadiness": _thread_surface_readiness("goal_tension", status=status),
            }
        )

    method_state = (
        method_context.get("methodState")
        if isinstance(method_context.get("methodState"), dict)
        else {}
    )
    practice_loop = (
        method_state.get("practiceLoop")
        if isinstance(method_state.get("practiceLoop"), dict)
        else {}
    )
    if practice_loop:
        source_refs = [
            _thread_source_ref(
                str(item.get("recordType") or "PracticeSession"),
                str(item.get("recordId") or ""),
                summary=str(item.get("summary") or "").strip() or None,
            )
            for item in practice_loop.get("sourceRecordRefs", [])
            if isinstance(item, dict) and str(item.get("recordId") or "").strip()
        ]
        practice_session_ids: list[Id] = []
        material_ids: list[Id] = []
        goal_ids: list[Id] = []
        journey_ids: list[Id] = []
        entity_ids: list[Id] = []
        for ref in source_refs:
            record_type = str(ref.get("recordType") or "")
            record_id = str(ref.get("recordId") or "")
            entity_ids.append(record_id)
            if record_type == "PracticeSession" and record_id in bucket.practice_sessions:
                practice = bucket.practice_sessions[record_id]
                practice_session_ids.append(record_id)
                if practice.get("materialId"):
                    material_ids.append(str(practice["materialId"]))
            elif record_type == "GoalTension" and record_id in bucket.goal_tensions:
                goal_ids.extend(
                    str(item) for item in bucket.goal_tensions[record_id].get("goalIds", [])
                )
            elif record_type == "Journey":
                journey_ids.append(record_id)
        entity_refs = _thread_entity_refs(
            entity_ids=entity_ids,
            material_ids=material_ids,
            goal_ids=goal_ids,
            journey_ids=journey_ids,
            practice_session_ids=practice_session_ids,
        )
        summary_text = str(
            practice_loop.get("recentOutcomeTrend")
            or practice_loop.get("guidance")
            or "Practice loop remains active."
        )
        append_digest(
            {
                "threadKey": "practice_loop:current",
                "kind": "practice_loop",
                "status": "active",
                "summary": _truncate(summary_text, 220),
                "entityRefs": entity_refs,
                "evidenceIds": list(practice_loop.get("evidenceIds", [])),
                "journeyIds": _journey_ids_for_entity_refs(bucket, entity_refs),
                "sourceRecordRefs": source_refs
                or [
                    _thread_source_ref(
                        "PracticeLoop", "practice_loop:current", summary=summary_text
                    )
                ],
                "lastTouchedAt": _thread_source_last_touched(
                    bucket,
                    source_refs,
                    fallback=str(method_context.get("windowEnd") or window_end),
                ),
                "surfaceReadiness": _thread_surface_readiness("practice_loop", status="active"),
            }
        )

    for signal in method_context.get("longitudinalSignals", [])[:8]:
        if not isinstance(signal, dict):
            continue
        signal_id = str(signal.get("id") or "").strip()
        signal_summary = str(signal.get("summary") or "").strip()
        if not signal_id or not signal_summary:
            continue
        entity_refs = _thread_entity_refs(
            entity_ids=[
                str(item)
                for item in signal.get("sourceEntityIds", [])
                if isinstance(item, str) and item.strip()
            ],
            material_ids=[
                str(item)
                for item in signal.get("materialIds", [])
                if isinstance(item, str) and item.strip()
            ],
        )
        append_digest(
            {
                "threadKey": f"longitudinal_signal:{signal_id}",
                "kind": "longitudinal_signal",
                "status": str(signal.get("strength") or "active"),
                "summary": _truncate(signal_summary, 220),
                "entityRefs": entity_refs,
                "evidenceIds": [],
                "journeyIds": _journey_ids_for_entity_refs(bucket, entity_refs),
                "sourceRecordRefs": [
                    _thread_source_ref(
                        "LongitudinalSignal",
                        signal_id,
                        summary=signal_summary,
                    )
                ],
                "lastTouchedAt": str(signal.get("lastSeen") or window_end),
                "surfaceReadiness": _thread_surface_readiness(
                    "longitudinal_signal",
                    status=str(signal.get("strength") or "active"),
                ),
            }
        )

    digests.sort(key=lambda item: str(item.get("lastTouchedAt") or ""), reverse=True)
    return deepcopy(digests[:20])


def build_circulation_summary_input_locked(
    bucket: UserCirculatioBucket,
    *,
    user_id: Id,
    window_start: str,
    window_end: str,
) -> CirculationSummaryInput:
    payload: CirculationSummaryInput = {
        "userId": user_id,
        "windowStart": window_start,
        "windowEnd": window_end,
        "hermesMemoryContext": build_memory_context_locked(bucket),
    }
    life_context = build_life_context_snapshot_locked(
        bucket,
        user_id=user_id,
        window_start=window_start,
        window_end=window_end,
    )
    if life_context is not None:
        payload["lifeContextSnapshot"] = life_context
    method_context = build_method_context_snapshot_locked(
        bucket,
        user_id=user_id,
        window_start=window_start,
        window_end=window_end,
    )
    if method_context is not None:
        payload["methodContextSnapshot"] = method_context
    return payload


def build_dashboard_summary_locked(
    bucket: UserCirculatioBucket, *, user_id: Id
) -> DashboardSummary:
    recent_materials = [
        deepcopy(item)
        for item in sorted(
            [
                item
                for item in bucket.materials.values()
                if item.get("status") != "deleted" and item["userId"] == user_id
            ],
            key=lambda item: item.get("materialDate", item.get("createdAt", "")),
            reverse=True,
        )[:5]
    ]
    latest_review = next(
        iter(
            sorted(
                [
                    item
                    for item in bucket.weekly_reviews.values()
                    if item.get("status") != "deleted" and item["userId"] == user_id
                ],
                key=lambda item: item.get("createdAt", ""),
                reverse=True,
            )
        ),
        None,
    )
    latest_practice = next(
        iter(
            sorted(
                [
                    item
                    for item in bucket.practice_sessions.values()
                    if item.get("status") == "recommended" and item["userId"] == user_id
                ],
                key=lambda item: item.get("createdAt", ""),
                reverse=True,
            )
        ),
        None,
    )
    pending_count = sum(
        1
        for run in bucket.interpretation_runs.values()
        for decision in run.get("proposalDecisions", [])
        if decision.get("status") == "pending"
    )
    summary: DashboardSummary = {
        "recentMaterials": recent_materials,
        "pendingProposalCount": pending_count,
        "recurringSymbols": [
            deepcopy(item) for item in active_symbols(bucket)[:5] if item["userId"] == user_id
        ],
        "activePatterns": [
            deepcopy(item) for item in active_patterns(bucket)[:5] if item["userId"] == user_id
        ],
        "safetyBlockedRecentRunsCount": sum(
            1
            for item in bucket.interpretation_runs.values()
            if item["userId"] == user_id and item.get("status") == "blocked_by_safety"
        ),
    }
    if latest_review is not None:
        summary["latestReview"] = deepcopy(latest_review)
    if latest_practice is not None:
        summary["latestPracticeRecommendation"] = deepcopy(latest_practice)
    return summary


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


__all__ = [
    "build_memory_context_locked",
    "build_memory_kernel_snapshot_locked",
    "query_graph_locked",
    "build_life_context_snapshot_locked",
    "build_method_context_snapshot_locked",
    "build_thread_digests_locked",
    "build_circulation_summary_input_locked",
    "build_dashboard_summary_locked",
    "build_symbolic_memory_snapshot_locked",
]
