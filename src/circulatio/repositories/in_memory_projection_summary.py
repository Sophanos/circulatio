from __future__ import annotations

from collections import Counter
from copy import deepcopy

from ..domain.adaptation import UserAdaptationProfileRecord
from ..domain.amplifications import AmplificationPromptRecord, PersonalAmplificationRecord
from ..domain.conscious_attitude import ConsciousAttitudeSnapshotRecord
from ..domain.culture import CollectiveAmplificationRecord, CulturalFrameRecord
from ..domain.dream_series import DreamSeriesMembershipRecord, DreamSeriesRecord
from ..domain.goals import GoalRecord, GoalTensionRecord
from ..domain.ids import create_id, now_iso
from ..domain.journeys import JourneyRecord
from ..domain.normalization import normalize_hermes_memory_context
from ..domain.patterns import PatternRecord
from ..domain.practices import PracticeSessionRecord
from ..domain.readiness import ConsentPreferenceRecord
from ..domain.soma import BodyStateRecord
from ..domain.symbols import SymbolRecord
from ..domain.types import (
    AmplificationPromptSummary,
    BodyStateSummary,
    CollectiveAmplificationSummary,
    ComplexCandidateSummary,
    ConsciousAttitudeSummary,
    ConsentPreferenceSummary,
    CulturalFrameSummary,
    DreamSeriesMembershipSummary,
    DreamSeriesSummary,
    GoalSummary,
    GoalTensionSummary,
    HermesMemoryContext,
    Id,
    JourneySummary,
    LongitudinalSignalSummary,
    PersonalAmplificationSummary,
    PersonalSymbolSummary,
    PracticeOutcomeSummary,
    PracticeSessionSummary,
    TypologyLensSummary,
    UserAdaptationProfileSummary,
)
from ..domain.typology import TypologyLensRecord
from .in_memory_bucket import UserCirculatioBucket
from .in_memory_projection_shared import _material_summary_text, _practice_timestamp, _truncate


def build_memory_context_locked(
    bucket: UserCirculatioBucket, *, max_items: int | None = None
) -> HermesMemoryContext:
    limit = max_items or 12
    material_summaries = list(bucket.material_summaries.values())
    if not material_summaries:
        material_summaries = [
            {
                "id": record_id,
                "materialType": record["materialType"],
                "date": record.get("materialDate", record.get("createdAt", now_iso())),
                "summary": _material_summary_text(record),
                "symbolNames": [],
                "themeLabels": list(record.get("tags", [])),
            }
            for record_id, record in bucket.materials.items()
            if record.get("status") != "deleted" and _material_summary_text(record)
        ]
    memory = {
        "recurringSymbols": [
            project_symbol_summary(item) for item in active_symbols(bucket)[:limit]
        ],
        "activeComplexCandidates": [
            project_pattern_summary(item)
            for item in active_patterns(bucket)[:5]
            if item["patternType"] == "complex_candidate"
        ],
        "recentMaterialSummaries": [
            deepcopy(item)
            for item in sorted(material_summaries, key=lambda value: value["date"], reverse=True)[
                :5
            ]
        ],
        "recentInterpretationFeedback": deepcopy(bucket.feedback[:10]),
        "practiceOutcomes": [
            project_practice_outcome(item) for item in completed_practices(bucket)[:5]
        ],
        "culturalOriginPreferences": deepcopy(bucket.cultural_origins[:limit]),
        "suppressedHypotheses": [
            deepcopy(item)
            for item in sorted(
                bucket.suppressed.values(), key=lambda value: value["timestamp"], reverse=True
            )[:25]
        ],
        "typologyLensSummaries": [
            project_typology_summary(item) for item in active_typology_lenses(bucket)[:10]
        ],
        "recentTypologySignals": [item["claim"] for item in active_typology_lenses(bucket)[:10]],
    }
    return normalize_hermes_memory_context(memory)


def _copy_if_present(result: dict[str, object], record: dict[str, object], key: str) -> None:
    if record.get(key):
        result[key] = record[key]


def project_symbol_summary(record: SymbolRecord) -> PersonalSymbolSummary:
    return {
        "id": record["id"],
        "canonicalName": record["canonicalName"],
        "aliases": deepcopy(record.get("aliases", [])),
        "category": record["category"],
        "recurrenceCount": record.get("recurrenceCount", 0),
        "firstSeen": record.get("firstSeen"),
        "lastSeen": record.get("lastSeen"),
        "valenceHistory": deepcopy(record.get("valenceHistory", [])),
        "personalAssociations": deepcopy(record.get("personalAssociations", [])),
        "linkedMaterialIds": deepcopy(record.get("linkedMaterialIds", [])),
        "linkedLifeEventRefs": deepcopy(record.get("linkedLifeEventRefs", [])),
    }


def project_pattern_summary(record: PatternRecord) -> ComplexCandidateSummary:
    return {
        "id": record["id"],
        "label": record["label"],
        "formulation": record["formulation"],
        "status": record["status"] if record["status"] != "deleted" else "disconfirmed",
        "activationIntensity": record.get("activationIntensity", 0.0),
        "confidence": record["confidence"],
        "evidenceIds": deepcopy(record.get("evidenceIds", [])),
        "counterevidenceIds": deepcopy(record.get("counterevidenceIds", [])),
        "linkedSymbols": deepcopy(record.get("linkedSymbols", [])),
        "linkedLifeEventRefs": deepcopy(record.get("linkedLifeEventRefs", [])),
        "lastUpdated": record.get("updatedAt", record["createdAt"]),
    }


def project_practice_outcome(record: PracticeSessionRecord) -> PracticeOutcomeSummary:
    return {
        "id": record["id"],
        "practiceType": record["practiceType"],
        "target": record.get("target"),
        "outcome": record.get("outcome", record["reason"]),
        "activationBefore": record.get("activationBefore"),
        "activationAfter": record.get("activationAfter"),
        "timestamp": record.get("completedAt", record.get("updatedAt", record["createdAt"])),
    }


def _project_practice_session_summary(record: PracticeSessionRecord) -> PracticeSessionSummary:
    result: PracticeSessionSummary = {
        "id": record["id"],
        "practiceType": record["practiceType"],
        "status": record["status"],
        "createdAt": record["createdAt"],
    }
    for key in (
        "target",
        "activationBefore",
        "activationAfter",
        "templateId",
        "modality",
        "intensity",
        "completedAt",
        "nextFollowUpDueAt",
    ):
        _copy_if_present(result, record, key)
    outcome = str(record.get("outcome") or "").strip()
    if outcome:
        result["outcome"] = _truncate(outcome, 180)
    return result


def project_typology_summary(record: TypologyLensRecord) -> TypologyLensSummary:
    return {
        "id": record["id"],
        "role": record["role"],
        "function": record["function"],
        "claim": record["claim"],
        "confidence": record["confidence"],
        "status": "disconfirmed" if record["status"] == "deleted" else record["status"],
        "evidenceIds": deepcopy(record.get("evidenceIds", [])),
        "userTestPrompt": record["userTestPrompt"],
        "lastUpdated": record.get("updatedAt", record["createdAt"]),
    }


def active_symbols(bucket: UserCirculatioBucket) -> list[SymbolRecord]:
    records = [item for item in bucket.symbols.values() if item.get("status") != "deleted"]
    return sorted(
        records,
        key=lambda item: (
            item.get("recurrenceCount", 0),
            item.get("lastSeen", item.get("createdAt", "")),
        ),
        reverse=True,
    )


def active_patterns(bucket: UserCirculatioBucket) -> list[PatternRecord]:
    records = [
        item
        for item in bucket.patterns.values()
        if item.get("status") not in {"deleted", "disconfirmed"}
    ]
    return sorted(
        records, key=lambda item: item.get("updatedAt", item.get("createdAt", "")), reverse=True
    )


def active_typology_lenses(bucket: UserCirculatioBucket) -> list[TypologyLensRecord]:
    records = [item for item in bucket.typology_lenses.values() if item.get("status") != "deleted"]
    return sorted(
        records, key=lambda item: item.get("updatedAt", item.get("createdAt", "")), reverse=True
    )


def completed_practices(bucket: UserCirculatioBucket) -> list[PracticeSessionRecord]:
    records = [
        item
        for item in bucket.practice_sessions.values()
        if item.get("status") == "completed" and item.get("outcome")
    ]
    return sorted(
        records,
        key=lambda item: item.get("completedAt", item.get("updatedAt", item.get("createdAt", ""))),
        reverse=True,
    )


def _project_conscious_attitude_summary(
    record: ConsciousAttitudeSnapshotRecord,
) -> ConsciousAttitudeSummary:
    result: ConsciousAttitudeSummary = {
        "id": record["id"],
        "stanceSummary": record["stanceSummary"],
        "activeValues": list(record.get("activeValues", [])),
        "activeConflicts": list(record.get("activeConflicts", [])),
        "avoidedThemes": list(record.get("avoidedThemes", [])),
        "confidence": record["confidence"],
        "status": record["status"],
        "evidenceIds": list(record.get("evidenceIds", [])),
    }
    _copy_if_present(result, record, "emotionalTone")
    _copy_if_present(result, record, "egoPosition")
    return result


def _project_body_state_summary(record: BodyStateRecord) -> BodyStateSummary:
    result: BodyStateSummary = {
        "id": record["id"],
        "observedAt": record.get("observedAt", record["createdAt"]),
        "sensation": record["sensation"],
    }
    for key in ("bodyRegion", "activation", "tone"):
        _copy_if_present(result, record, key)
    if record.get("linkedSymbolIds"):
        result["linkedSymbolIds"] = list(record["linkedSymbolIds"])
    if record.get("linkedGoalIds"):
        result["linkedGoalIds"] = list(record["linkedGoalIds"])
    return result


def _project_goal_summary(record: GoalRecord) -> GoalSummary:
    result: GoalSummary = {
        "id": record["id"],
        "label": record["label"],
        "status": record["status"],
        "valueTags": list(record.get("valueTags", [])),
    }
    _copy_if_present(result, record, "description")
    return result


def _project_goal_tension_summary(record: GoalTensionRecord) -> GoalTensionSummary:
    return {
        "id": record["id"],
        "goalIds": list(record.get("goalIds", [])),
        "tensionSummary": record["tensionSummary"],
        "polarityLabels": list(record.get("polarityLabels", [])),
        "status": record["status"],
        "evidenceIds": list(record.get("evidenceIds", [])),
    }


def _project_personal_amplification_summary(
    record: PersonalAmplificationRecord,
) -> PersonalAmplificationSummary:
    result: PersonalAmplificationSummary = {
        "id": record["id"],
        "canonicalName": record["canonicalName"],
        "surfaceText": record["surfaceText"],
        "associationText": record["associationText"],
        "createdAt": record["createdAt"],
    }
    _copy_if_present(result, record, "feelingTone")
    if record.get("bodySensations"):
        result["bodySensations"] = list(record["bodySensations"])
    return result


def _project_amplification_prompt_summary(
    record: AmplificationPromptRecord,
) -> AmplificationPromptSummary:
    result: AmplificationPromptSummary = {
        "id": record["id"],
        "canonicalName": record["canonicalName"],
        "surfaceText": record["surfaceText"],
        "promptText": record["promptText"],
        "reason": record["reason"],
        "status": record["status"],
        "createdAt": record["createdAt"],
    }
    _copy_if_present(result, record, "symbolMentionId")
    return result


def _project_consent_preference_summary(
    record: ConsentPreferenceRecord,
) -> ConsentPreferenceSummary:
    result: ConsentPreferenceSummary = {
        "id": record["id"],
        "scope": record["scope"],
        "status": record["status"],
    }
    _copy_if_present(result, record, "note")
    return result


def _project_dream_series_summary(record: DreamSeriesRecord) -> DreamSeriesSummary:
    result: DreamSeriesSummary = {
        "id": record["id"],
        "label": record["label"],
        "status": record["status"],
        "confidence": record["confidence"],
        "materialIds": list(record.get("materialIds", [])),
    }
    _copy_if_present(result, record, "progressionSummary")
    _copy_if_present(result, record, "egoTrajectory")
    _copy_if_present(result, record, "compensationTrajectory")
    _copy_if_present(result, record, "lastSeen")
    for key in ("symbolIds", "motifKeys", "settingKeys", "figureKeys"):
        if record.get(key):
            result[key] = list(record[key])  # type: ignore[index]
    return result


def _project_dream_series_membership_summary(
    record: DreamSeriesMembershipRecord,
) -> DreamSeriesMembershipSummary:
    result: DreamSeriesMembershipSummary = {
        "id": record["id"],
        "seriesId": record["seriesId"],
        "materialId": record["materialId"],
        "matchScore": float(record.get("matchScore", 0.0)),
        "matchingFeatures": list(record.get("matchingFeatures", [])),
        "narrativeRole": record["narrativeRole"],
        "status": record["status"],
        "createdAt": record["createdAt"],
    }
    _copy_if_present(result, record, "sequenceIndex")
    _copy_if_present(result, record, "egoStance")
    _copy_if_present(result, record, "lysisSummary")
    return result


def _project_cultural_frame_summary(record: CulturalFrameRecord) -> CulturalFrameSummary:
    result: CulturalFrameSummary = {
        "id": record["id"],
        "label": record["label"],
        "type": record.get("frameType"),
        "status": record["status"],
    }
    if record.get("allowedUses"):
        result["allowedUses"] = list(record["allowedUses"])
    if record.get("avoidUses"):
        result["avoidUses"] = list(record["avoidUses"])
    _copy_if_present(result, record, "notes")
    return result


def _project_collective_amplification_summary(
    record: CollectiveAmplificationRecord,
    *,
    frame_label_by_id: dict[Id, str] | None = None,
) -> CollectiveAmplificationSummary:
    reference = str(record.get("reference") or "").strip()
    fit_reason = str(record.get("fitReason") or "").strip()
    amplification_text = (
        reference if not fit_reason else _truncate(f"{reference} {fit_reason}".strip(), 220)
    )
    result: CollectiveAmplificationSummary = {
        "id": record["id"],
        "canonicalName": _truncate(reference or "collective lens", 120),
        "amplificationText": amplification_text or "Collective lens held for review.",
        "status": record["status"],
        "createdAt": record["createdAt"],
    }
    _copy_if_present(result, record, "symbolId")
    if record.get("culturalFrameId"):
        result["culturalFrameId"] = record["culturalFrameId"]
        if frame_label_by_id and record["culturalFrameId"] in frame_label_by_id:
            result["lensLabel"] = frame_label_by_id[record["culturalFrameId"]]
    return result


def _project_adaptation_profile_summary(
    record: UserAdaptationProfileRecord,
) -> UserAdaptationProfileSummary:
    return {
        "id": record["id"],
        "explicitPreferences": deepcopy(record.get("explicitPreferences", {})),
        "learnedSignals": deepcopy(record.get("learnedSignals", {})),
        "sampleCounts": deepcopy(record.get("sampleCounts", {})),
    }


def _project_journey_summary(record: JourneyRecord) -> JourneySummary:
    result: JourneySummary = {
        "id": record["id"],
        "label": record["label"],
        "status": record["status"],
        "relatedMaterialIds": list(record.get("relatedMaterialIds", [])),
        "relatedSymbolIds": list(record.get("relatedSymbolIds", [])),
        "relatedPatternIds": list(record.get("relatedPatternIds", [])),
        "relatedDreamSeriesIds": list(record.get("relatedDreamSeriesIds", [])),
        "relatedGoalIds": list(record.get("relatedGoalIds", [])),
    }
    _copy_if_present(result, record, "currentQuestion")
    return result


def _latest_adaptation_profile(bucket: UserCirculatioBucket) -> UserAdaptationProfileRecord | None:
    active = [
        item for item in bucket.adaptation_profiles.values() if item.get("status") != "deleted"
    ]
    if not active:
        return None
    active.sort(key=lambda item: item.get("updatedAt", item.get("createdAt", "")), reverse=True)
    return active[0]


def _derive_body_state_energy_summary(body_states: list[BodyStateRecord]) -> str | None:
    if not body_states:
        return None
    counts = Counter(item.get("activation") or "unknown" for item in body_states)
    dominant, _ = counts.most_common(1)[0]
    return f"Recent body activation trends feel {dominant}."


def _derive_body_state_changes(body_states: list[BodyStateRecord]) -> list[str]:
    changes: list[str] = []
    for item in sorted(
        body_states,
        key=lambda value: value.get("observedAt", value.get("createdAt", "")),
        reverse=True,
    )[:2]:
        region = item.get("bodyRegion") or "body"
        changes.append(f"Body signal noted in the {region}: {item['sensation']}.")
    return changes


def _derive_dream_series_changes(series: list[DreamSeriesRecord]) -> list[str]:
    changes: list[str] = []
    for item in sorted(
        series, key=lambda value: value.get("updatedAt", value.get("createdAt", "")), reverse=True
    )[:2]:
        if item.get("progressionSummary"):
            changes.append(f"Dream series '{item['label']}' shifted: {item['progressionSummary']}")
    return changes


def _derive_longitudinal_signals(bucket: UserCirculatioBucket) -> list[LongitudinalSignalSummary]:
    signals: list[LongitudinalSignalSummary] = []
    body_states = [item for item in bucket.body_states.values() if item.get("status") != "deleted"]
    goals = [item for item in bucket.goals.values() if item.get("status") != "deleted"]
    symbols = [item for item in bucket.symbols.values() if item.get("status") != "deleted"]
    series = [item for item in bucket.dream_series.values() if item.get("status") != "deleted"]
    frames = {
        item["id"]: item["label"]
        for item in bucket.cultural_frames.values()
        if item.get("status") == "enabled"
    }
    collective = [
        item
        for item in bucket.collective_amplifications.values()
        if item.get("status") in {"offered", "user_resonated"}
    ]
    for symbol in symbols:
        symbol_materials = set(symbol.get("linkedMaterialIds", []))
        linked_body_states = [
            item
            for item in body_states
            if symbol["id"] in item.get("linkedSymbolIds", [])
            or symbol_materials.intersection(item.get("linkedMaterialIds", []))
        ]
        if len(linked_body_states) >= 2:
            region = (
                _first_value(item.get("bodyRegion") for item in linked_body_states) or "the body"
            )
            signals.append(
                {
                    "id": create_id("signal"),
                    "signalType": "symbol_body_cooccurrence",
                    "summary": _truncate(
                        (
                            f"{symbol['canonicalName'].title()} appears "
                            f"alongside {region} in {len(linked_body_states)} "
                            "recorded item(s)."
                        ),
                        180,
                    ),
                    "sourceEntityIds": [symbol["id"]]
                    + [item["id"] for item in linked_body_states[:4]],
                    "materialIds": [
                        material_id
                        for item in linked_body_states
                        for material_id in item.get("linkedMaterialIds", [])[:1]
                    ][:5],
                    "count": len(linked_body_states),
                    "lastSeen": max(
                        item.get("observedAt", item.get("updatedAt", item["createdAt"]))
                        for item in linked_body_states
                    ),
                    "strength": "moderate" if len(linked_body_states) < 3 else "strong",
                }
            )
        linked_goals = [
            item
            for item in goals
            if symbol["id"] in item.get("linkedSymbolIds", [])
            or symbol_materials.intersection(item.get("linkedMaterialIds", []))
        ]
        if len(linked_goals) >= 2:
            signals.append(
                {
                    "id": create_id("signal"),
                    "signalType": "symbol_goal_cooccurrence",
                    "summary": _truncate(
                        (
                            f"{symbol['canonicalName'].title()} co-occurs with "
                            f"{len(linked_goals)} active goal record(s)."
                        ),
                        180,
                    ),
                    "sourceEntityIds": [symbol["id"]] + [item["id"] for item in linked_goals[:4]],
                    "materialIds": [
                        material_id
                        for item in linked_goals
                        for material_id in item.get("linkedMaterialIds", [])[:1]
                    ][:5],
                    "count": len(linked_goals),
                    "lastSeen": max(
                        item.get("updatedAt", item["createdAt"]) for item in linked_goals
                    ),
                    "strength": "moderate" if len(linked_goals) < 3 else "strong",
                }
            )
    for body_state in body_states:
        linked_goal_ids = [
            goal_id for goal_id in body_state.get("linkedGoalIds", []) if goal_id in bucket.goals
        ]
        if linked_goal_ids:
            signals.append(
                {
                    "id": create_id("signal"),
                    "signalType": "body_goal_cooccurrence",
                    "summary": _truncate(
                        (
                            f"{body_state['sensation'].title()} is linked with "
                            f"{len(linked_goal_ids)} goal record(s)."
                        ),
                        180,
                    ),
                    "sourceEntityIds": [body_state["id"], *linked_goal_ids[:4]],
                    "materialIds": list(body_state.get("linkedMaterialIds", []))[:5],
                    "count": len(linked_goal_ids),
                    "lastSeen": body_state.get(
                        "observedAt", body_state.get("updatedAt", body_state["createdAt"])
                    ),
                    "strength": "weak" if len(linked_goal_ids) == 1 else "moderate",
                }
            )
    for record in series:
        if record.get("progressionSummary"):
            signals.append(
                {
                    "id": create_id("signal"),
                    "signalType": "dream_series_shift",
                    "summary": _truncate(
                        f"{record['label']} shows a stored shift: {record['progressionSummary']}",
                        180,
                    ),
                    "sourceEntityIds": [record["id"]],
                    "materialIds": list(record.get("materialIds", []))[:5],
                    "count": max(1, len(record.get("materialIds", []))),
                    "lastSeen": record.get(
                        "lastSeen", record.get("updatedAt", record["createdAt"])
                    ),
                    "strength": "moderate",
                }
            )
    for item in collective:
        frame_label = frames.get(item.get("culturalFrameId", ""))
        if not frame_label or not item.get("symbolId"):
            continue
        signals.append(
            {
                "id": create_id("signal"),
                "signalType": "culture_symbol_lens",
                "summary": _truncate(
                    (
                        f"{frame_label} is already linked as an optional lens "
                        "for one recorded symbol thread."
                    ),
                    180,
                ),
                "sourceEntityIds": [item["id"], item["symbolId"]],
                "materialIds": [item["materialId"]] if item.get("materialId") else [],
                "count": 1,
                "lastSeen": item.get("updatedAt", item["createdAt"]),
                "strength": "weak",
            }
        )
    signals.sort(
        key=lambda item: (
            {"strong": 2, "moderate": 1, "weak": 0}[item["strength"]],
            item["count"],
            item["lastSeen"],
        ),
        reverse=True,
    )
    return signals[:5]


def _first_value(values) -> str | None:
    for value in values:
        if value:
            return str(value)
    return None


def _derive_life_event_refs(materials: list[dict[str, object]]) -> list[dict[str, object]]:
    refs: list[dict[str, object]] = []
    for record in sorted(
        materials,
        key=lambda item: item.get("materialDate", item.get("createdAt", "")),
        reverse=True,
    ):
        if record["materialType"] not in {"charged_event", "reflection"}:
            continue
        summary = _material_summary_text(record)
        if not summary:
            continue
        ref = {
            "id": record["id"],
            "date": record.get("materialDate", record.get("createdAt", now_iso())),
            "summary": summary,
        }
        tags = [str(item).strip() for item in record.get("tags", []) if str(item).strip()]
        if tags:
            ref["symbolicAnnotation"] = ", ".join(tags[:3])
        refs.append(ref)
        if len(refs) >= 5:
            break
    return refs


def _derive_mood_summary(symbols: list[SymbolRecord]) -> str | None:
    tones = [
        point.get("tone")
        for symbol in symbols
        for point in symbol.get("valenceHistory", [])
        if point.get("tone")
    ]
    if not tones:
        return None
    counts = Counter(tones)
    top_tones = [tone for tone, _ in counts.most_common(2)]
    return _truncate("Recent symbol valence leans toward " + " and ".join(top_tones) + ".", 220)


def _derive_energy_summary(practices: list[PracticeSessionRecord]) -> str | None:
    levels = {"low": 1, "moderate": 2, "high": 3}
    deltas = []
    for record in practices:
        before = levels.get(record.get("activationBefore"))
        after = levels.get(record.get("activationAfter"))
        if before is None or after is None:
            continue
        deltas.append(after - before)
    if not deltas:
        return None
    average = sum(deltas) / len(deltas)
    if average <= -0.5:
        trend = "tension tends to settle after practice"
    elif average >= 0.5:
        trend = "activation tends to rise after practice"
    else:
        trend = "activation has stayed mixed across recent practices"
    return _truncate(f"Practice outcomes suggest {trend}.", 220)


def _derive_focus_summary(symbols: list[SymbolRecord], patterns: list[PatternRecord]) -> str | None:
    parts: list[str] = []
    if symbols:
        names = [
            symbol["canonicalName"]
            for symbol in sorted(
                symbols, key=lambda item: item.get("recurrenceCount", 0), reverse=True
            )[:3]
        ]
        parts.append("Recurring symbols: " + ", ".join(names))
    if patterns:
        labels = [
            pattern["label"]
            for pattern in sorted(
                patterns, key=lambda item: item.get("activationIntensity", 0.0), reverse=True
            )[:2]
        ]
        parts.append("active patterns: " + ", ".join(labels))
    if not parts:
        return None
    return _truncate("; ".join(parts) + ".", 220)


def _derive_mental_state_summary(
    runs: list[dict[str, object]],
    feedback: list[dict[str, object]],
    suppressed: list[dict[str, object]],
) -> str | None:
    parts: list[str] = []
    blocked_count = sum(1 for run in runs if run.get("status") == "blocked_by_safety")
    rejected_count = sum(1 for item in feedback if item.get("feedback") == "rejected")
    if blocked_count:
        parts.append(f"{blocked_count} recent run(s) hit the safety gate")
    if rejected_count:
        parts.append(f"{rejected_count} hypothesis rejection(s) tightened interpretation caution")
    if suppressed:
        parts.append(f"{len(suppressed)} suppressed claim(s) remain part of the audit trail")
    if not parts:
        return None
    return _truncate("; ".join(parts) + ".", 220)


def _derive_habit_summary(
    materials: list[dict[str, object]],
    practices: list[PracticeSessionRecord],
    start_dt,  # datetime annotations are postponed
    end_dt,
) -> str | None:
    if not materials and not practices:
        return None
    span_days = max(1, int((end_dt - start_dt).total_seconds() // 86400) + 1)
    completed = sum(1 for record in practices if record.get("status") == "completed")
    skipped = sum(1 for record in practices if record.get("status") == "skipped")
    return _truncate(
        (
            f"{len(materials)} material capture(s) landed across "
            f"{span_days} day(s); {completed} practice(s) completed and "
            f"{skipped} skipped."
        ),
        220,
    )


def _derive_notable_changes(
    symbol_history: list[dict[str, object]],
    pattern_history: list[dict[str, object]],
    practices: list[PracticeSessionRecord],
    patterns: list[PatternRecord],
) -> list[str]:
    changes: list[str] = []
    for entry in sorted(symbol_history, key=lambda item: item.get("createdAt", ""), reverse=True):
        note = entry.get("note") or entry.get("eventType")
        if note:
            changes.append(f"Symbol change: {_truncate(str(note), 120)}")
    for entry in sorted(pattern_history, key=lambda item: item.get("createdAt", ""), reverse=True):
        note = entry.get("note") or entry.get("eventType")
        if note:
            changes.append(f"Pattern change: {_truncate(str(note), 120)}")
    for record in sorted(practices, key=_practice_timestamp, reverse=True):
        if record.get("status") == "completed":
            changes.append(
                "Practice completed: "
                f"{_truncate(record.get('target') or record['practiceType'], 120)}"
            )
    for record in sorted(
        patterns, key=lambda item: item.get("updatedAt", item.get("createdAt", "")), reverse=True
    ):
        if record.get("status") in {"active", "recurring", "integrating"}:
            changes.append(f"Pattern now {record['status']}: {_truncate(record['label'], 120)}")
    return list(dict.fromkeys(changes))[:5]
