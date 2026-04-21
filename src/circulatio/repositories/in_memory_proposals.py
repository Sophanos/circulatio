from __future__ import annotations

from copy import deepcopy

from ..domain.dream_series import DreamSeriesRecord
from ..domain.errors import ValidationError
from ..domain.ids import create_id, now_iso
from ..domain.interpretations import ProposalDecisionRecord
from ..domain.patterns import PatternRecord
from ..domain.types import (
    Id,
    MemoryWritePlan,
    PersonalAssociationSummary,
)
from .in_memory_bucket import UserCirculatioBucket

_CONFIDENCE_ORDER = {"low": 0, "medium": 1, "high": 2}


def apply_approved_proposals_locked(
    *,
    bucket: UserCirculatioBucket,
    user_id: Id,
    memory_write_plan: MemoryWritePlan,
    approved_proposal_ids: list[Id],
) -> dict[str, list[Id]]:
    approved = set(approved_proposal_ids)
    applied: list[Id] = []
    affected: list[Id] = []
    evidence_map = {item["id"]: item for item in memory_write_plan["evidenceItems"]}
    run = bucket.interpretation_runs.get(memory_write_plan["runId"])
    material_id = run["materialId"] if run else None
    for proposal in memory_write_plan["proposals"]:
        proposal_id = proposal["id"]
        if proposal_id not in approved:
            continue
        if proposal_id in bucket.applied_proposal_ids:
            applied.append(proposal_id)
            continue
        for evidence_id in proposal["evidenceIds"]:
            if evidence_id in evidence_map:
                bucket.evidence.setdefault(evidence_id, deepcopy(evidence_map[evidence_id]))
        action = proposal["action"]
        payload = proposal["payload"]
        if action == "upsert_personal_symbol":
            affected.append(
                apply_personal_symbol_proposal_locked(
                    bucket=bucket,
                    user_id=user_id,
                    proposal_id=proposal_id,
                    evidence_ids=proposal["evidenceIds"],
                    material_id=material_id,
                    run_id=memory_write_plan["runId"],
                    payload=payload,
                )
            )
        elif action == "upsert_complex_candidate":
            affected.append(
                apply_pattern_proposal_locked(
                    bucket=bucket,
                    user_id=user_id,
                    proposal_id=proposal_id,
                    evidence_ids=proposal["evidenceIds"],
                    material_id=material_id,
                    run_id=memory_write_plan["runId"],
                    payload=payload,
                )
            )
        elif action == "record_practice_outcome":
            affected.append(
                apply_practice_outcome_proposal_locked(
                    bucket=bucket,
                    user_id=user_id,
                    material_id=material_id,
                    run_id=memory_write_plan["runId"],
                    payload=payload,
                )
            )
        elif action == "store_material_summary":
            material_target = apply_material_summary_proposal_locked(
                bucket=bucket,
                user_id=user_id,
                material_id=material_id,
                payload=payload,
            )
            if material_target:
                affected.append(material_target)
        elif action == "store_typology_lens":
            affected.append(
                apply_typology_proposal_locked(
                    bucket=bucket,
                    user_id=user_id,
                    material_id=material_id,
                    payload=payload,
                )
            )
        elif action == "upsert_goal_tension":
            affected.append(
                apply_goal_tension_proposal_locked(
                    bucket=bucket,
                    user_id=user_id,
                    payload=payload,
                )
            )
        elif action == "create_dream_series":
            affected.extend(
                apply_create_dream_series_proposal_locked(
                    bucket=bucket,
                    user_id=user_id,
                    proposal_id=proposal_id,
                    material_id=material_id,
                    payload=payload,
                    evidence_ids=proposal["evidenceIds"],
                )
            )
        elif action == "link_material_to_dream_series":
            affected.extend(
                apply_link_dream_series_proposal_locked(
                    bucket=bucket,
                    user_id=user_id,
                    payload=payload,
                    evidence_ids=proposal["evidenceIds"],
                )
            )
        elif action == "update_dream_series_progression":
            affected.append(
                apply_update_dream_series_proposal_locked(
                    bucket=bucket,
                    user_id=user_id,
                    payload=payload,
                    evidence_ids=proposal["evidenceIds"],
                )
            )
        elif action == "create_collective_amplification":
            affected.append(
                apply_collective_amplification_proposal_locked(
                    bucket=bucket,
                    user_id=user_id,
                    material_id=material_id,
                    run_id=memory_write_plan["runId"],
                    payload=payload,
                    evidence_ids=proposal["evidenceIds"],
                )
            )
        elif action in {
            "create_reality_anchor_summary",
            "create_self_orientation_snapshot",
            "upsert_psychic_opposition",
            "create_emergent_third_signal",
            "create_bridge_moment",
            "create_numinous_encounter",
            "create_aesthetic_resonance",
            "upsert_archetypal_pattern",
            "upsert_threshold_process",
            "upsert_relational_scene",
            "upsert_projection_hypothesis",
            "upsert_inner_outer_correspondence",
        }:
            affected.append(
                apply_individuation_proposal_locked(
                    bucket=bucket,
                    user_id=user_id,
                    action=action,
                    payload=payload,
                    evidence_ids=proposal["evidenceIds"],
                    source=proposal_source_locked(bucket, memory_write_plan),
                )
            )
        elif action in {
            "create_life_chapter_snapshot",
            "upsert_mythic_question",
            "create_threshold_marker",
            "upsert_complex_encounter",
            "create_integration_contour",
            "create_symbolic_wellbeing_snapshot",
        }:
            affected.append(
                apply_living_myth_proposal_locked(
                    bucket=bucket,
                    user_id=user_id,
                    action=action,
                    payload=payload,
                    evidence_ids=proposal["evidenceIds"],
                    source=proposal_source_locked(bucket, memory_write_plan),
                )
            )
        else:
            raise ValidationError(f"Unknown proposal action: {action}")
        bucket.applied_proposal_ids.add(proposal_id)
        applied.append(proposal_id)
    return {"appliedProposalIds": applied, "affectedEntityIds": unique_ids(affected)}


def apply_personal_symbol_proposal_locked(
    *,
    bucket: UserCirculatioBucket,
    user_id: Id,
    proposal_id: Id,
    evidence_ids: list[Id],
    material_id: Id | None,
    run_id: Id,
    payload: object,
) -> Id:
    data = deepcopy(payload)
    canonical_name = data["canonicalName"]
    now = now_iso()
    symbol_id = bucket.symbol_name_index.get(canonical_name.lower())
    if symbol_id and symbol_id in bucket.symbols:
        symbol = bucket.symbols[symbol_id]
        previous = deepcopy(symbol)
        symbol["aliases"] = merge_unique(symbol.get("aliases", []), data.get("aliases", []))
        symbol["recurrenceCount"] = symbol.get("recurrenceCount", 0) + 1
        symbol["lastSeen"] = now
        symbol["updatedAt"] = now
        symbol["status"] = "active"
        if material_id:
            symbol["linkedMaterialIds"] = merge_unique(
                symbol.get("linkedMaterialIds", []), [material_id]
            )
        symbol["linkedLifeEventRefs"] = merge_unique(
            symbol.get("linkedLifeEventRefs", []), data.get("linkedLifeEventRefs", [])
        )
        association = build_personal_association(canonical_name, data.get("association"))
        if association:
            symbol["personalAssociations"] = symbol.get("personalAssociations", []) + [association]
        if data.get("tone"):
            symbol["valenceHistory"] = symbol.get("valenceHistory", []) + [
                {"date": now, "tone": data["tone"], "sourceId": material_id}
            ]
        event_type = "recurrence_incremented"
    else:
        symbol_id = create_id("personal_symbol")
        association = build_personal_association(canonical_name, data.get("association"))
        symbol = {
            "id": symbol_id,
            "userId": user_id,
            "canonicalName": canonical_name,
            "aliases": list(data.get("aliases", [])),
            "category": data["category"],
            "recurrenceCount": 1,
            "firstSeen": now,
            "lastSeen": now,
            "valenceHistory": (
                [{"date": now, "tone": data["tone"], "sourceId": material_id}]
                if data.get("tone")
                else []
            ),
            "personalAssociations": [association] if association else [],
            "linkedMaterialIds": [material_id] if material_id else [],
            "linkedLifeEventRefs": list(data.get("linkedLifeEventRefs", [])),
            "status": "active",
            "createdAt": now,
            "updatedAt": now,
        }
        previous = None
        bucket.symbols[symbol_id] = symbol
        bucket.symbol_name_index[canonical_name.lower()] = symbol_id
        event_type = "created"
    append_symbol_history_locked(
        bucket,
        {
            "id": create_id("symbol_history"),
            "userId": user_id,
            "symbolId": symbol_id,
            "eventType": event_type,
            "materialId": material_id,
            "runId": run_id,
            "proposalId": proposal_id,
            "evidenceIds": list(evidence_ids),
            "previousValue": previous,
            "newValue": deepcopy(bucket.symbols[symbol_id]),
            "createdAt": now_iso(),
        },
    )
    return symbol_id


def apply_pattern_proposal_locked(
    *,
    bucket: UserCirculatioBucket,
    user_id: Id,
    proposal_id: Id,
    evidence_ids: list[Id],
    material_id: Id | None,
    run_id: Id,
    payload: object,
) -> Id:
    data = deepcopy(payload)
    existing = find_pattern_locked(bucket, label=data["label"], formulation=data["formulation"])
    now = now_iso()
    if existing is None:
        pattern_id = create_id("pattern")
        record: PatternRecord = {
            "id": pattern_id,
            "userId": user_id,
            "patternType": "complex_candidate",
            "label": data["label"],
            "formulation": data["formulation"],
            "status": "candidate",
            "activationIntensity": 0.5,
            "confidence": data["confidence"],
            "evidenceIds": list(evidence_ids),
            "counterevidenceIds": [],
            "linkedSymbols": list(data.get("linkedSymbols", [])),
            "linkedMaterialIds": [material_id] if material_id else [],
            "linkedLifeEventRefs": list(data.get("linkedLifeEventRefs", [])),
            "createdAt": now,
            "updatedAt": now,
            "lastSeen": now,
        }
        bucket.patterns[pattern_id] = record
        previous = None
        event_type = "created"
    else:
        pattern_id, record = existing
        previous = deepcopy(record)
        record["evidenceIds"] = merge_unique(record.get("evidenceIds", []), evidence_ids)
        record["linkedSymbols"] = merge_unique(
            record.get("linkedSymbols", []), data.get("linkedSymbols", [])
        )
        if material_id:
            record["linkedMaterialIds"] = merge_unique(
                record.get("linkedMaterialIds", []), [material_id]
            )
        record["linkedLifeEventRefs"] = merge_unique(
            record.get("linkedLifeEventRefs", []), data.get("linkedLifeEventRefs", [])
        )
        record["confidence"] = max_confidence(record["confidence"], data["confidence"])
        record["status"] = (
            "recurring"
            if len(record.get("linkedMaterialIds", [])) > 1
            else record.get("status", "candidate")
        )
        record["updatedAt"] = now
        record["lastSeen"] = now
        event_type = "linked_material_added"
    append_pattern_history_locked(
        bucket,
        {
            "id": create_id("pattern_history"),
            "userId": user_id,
            "patternId": pattern_id,
            "eventType": event_type,
            "materialId": material_id,
            "runId": run_id,
            "proposalId": proposal_id,
            "evidenceIds": list(evidence_ids),
            "previousValue": previous,
            "newValue": deepcopy(bucket.patterns[pattern_id]),
            "createdAt": now_iso(),
        },
    )
    return pattern_id


def apply_practice_outcome_proposal_locked(
    *,
    bucket: UserCirculatioBucket,
    user_id: Id,
    material_id: Id | None,
    run_id: Id,
    payload: object,
) -> Id:
    data = deepcopy(payload)
    practice_id = create_id("practice_session")
    now = now_iso()
    bucket.practice_sessions[practice_id] = {
        "id": practice_id,
        "userId": user_id,
        "materialId": material_id,
        "runId": run_id,
        "practiceType": data["practiceType"],
        "target": data.get("target"),
        "reason": data.get("outcome", "Recorded as an approved practice outcome."),
        "instructions": [],
        "durationMinutes": 0,
        "contraindicationsChecked": [],
        "requiresConsent": False,
        "status": "completed",
        "outcome": data["outcome"],
        "activationBefore": data.get("activationBefore"),
        "activationAfter": data.get("activationAfter"),
        "createdAt": now,
        "updatedAt": now,
        "completedAt": now,
    }
    return practice_id


def apply_material_summary_proposal_locked(
    *,
    bucket: UserCirculatioBucket,
    user_id: Id,
    material_id: Id | None,
    payload: object,
) -> Id | None:
    del user_id
    if material_id is None:
        return None
    data = deepcopy(payload)
    bucket.material_summaries[material_id] = {
        "id": material_id,
        "materialType": data["materialType"],
        "date": data["date"],
        "summary": data["summary"],
        "symbolNames": list(data.get("symbolNames", [])),
        "themeLabels": list(data.get("themeLabels", [])),
    }
    material = bucket.materials.get(material_id)
    if material is not None:
        material["summary"] = data["summary"]
        material["tags"] = merge_unique(material.get("tags", []), data.get("themeLabels", []))
        material["updatedAt"] = now_iso()
    return material_id


def apply_typology_proposal_locked(
    *,
    bucket: UserCirculatioBucket,
    user_id: Id,
    material_id: Id | None,
    payload: object,
) -> Id:
    data = deepcopy(payload)
    existing = next(
        (
            (lens_id, lens)
            for lens_id, lens in bucket.typology_lenses.items()
            if lens.get("claim") == data["claim"] and lens.get("status") != "deleted"
        ),
        None,
    )
    now = now_iso()
    if existing is None:
        lens_id = create_id("typology_lens")
        bucket.typology_lenses[lens_id] = {
            "id": lens_id,
            "userId": user_id,
            "role": data["role"],
            "function": data["function"],
            "claim": data["claim"],
            "confidence": data["confidence"],
            "status": data["status"],
            "evidenceIds": list(data.get("evidenceIds", [])),
            "counterevidenceIds": [],
            "userTestPrompt": data["userTestPrompt"],
            "linkedMaterialIds": [material_id] if material_id else [],
            "createdAt": now,
            "updatedAt": now,
            "lastSeen": now,
        }
        return lens_id
    lens_id, lens = existing
    lens["evidenceIds"] = merge_unique(lens.get("evidenceIds", []), data.get("evidenceIds", []))
    if material_id:
        lens["linkedMaterialIds"] = merge_unique(lens.get("linkedMaterialIds", []), [material_id])
    lens["updatedAt"] = now
    lens["lastSeen"] = now
    return lens_id


def apply_goal_tension_proposal_locked(
    *,
    bucket: UserCirculatioBucket,
    user_id: Id,
    payload: object,
) -> Id:
    data = deepcopy(payload)
    goal_ids = sorted(str(item) for item in data.get("goalIds", []) if str(item).strip())
    if not goal_ids:
        raise ValidationError("Goal-tension proposals require goalIds.")
    tension_summary = str(data.get("tensionSummary") or "").strip()
    if not tension_summary:
        raise ValidationError("Goal-tension proposals require tensionSummary.")
    existing = next(
        (
            (record_id, record)
            for record_id, record in bucket.goal_tensions.items()
            if record.get("status") != "deleted"
            and sorted(record.get("goalIds", [])) == goal_ids
            and record.get("tensionSummary", "").strip().lower() == tension_summary.lower()
        ),
        None,
    )
    now = now_iso()
    if existing is None:
        tension_id = create_id("goal_tension")
        bucket.goal_tensions[tension_id] = {
            "id": tension_id,
            "userId": user_id,
            "goalIds": goal_ids,
            "tensionSummary": tension_summary,
            "polarityLabels": [
                str(item) for item in data.get("polarityLabels", []) if str(item).strip()
            ],
            "evidenceIds": list(data.get("evidenceIds", [])),
            "status": str(data.get("status") or "candidate"),
            "createdAt": now,
            "updatedAt": now,
        }
        return tension_id
    tension_id, record = existing
    record["polarityLabels"] = merge_unique(
        record.get("polarityLabels", []), data.get("polarityLabels", [])
    )
    record["evidenceIds"] = merge_unique(record.get("evidenceIds", []), data.get("evidenceIds", []))
    record["status"] = str(data.get("status") or record.get("status") or "active")
    record["updatedAt"] = now
    return tension_id


def apply_create_dream_series_proposal_locked(
    *,
    bucket: UserCirculatioBucket,
    user_id: Id,
    proposal_id: Id,
    material_id: Id | None,
    payload: object,
    evidence_ids: list[Id],
) -> list[Id]:
    data = deepcopy(payload)
    series_id = create_id("dream_series")
    now = now_iso()
    material_ids = merge_unique(
        list(data.get("materialIds", [])), [material_id] if material_id else []
    )
    record: DreamSeriesRecord = {
        "id": series_id,
        "userId": user_id,
        "label": str(data.get("label") or "Dream series").strip(),
        "status": "active",
        "seedMaterialId": material_ids[0] if material_ids else None,
        "materialIds": material_ids,
        "symbolIds": [str(item) for item in data.get("symbolIds", []) if str(item).strip()],
        "motifKeys": [str(item) for item in data.get("motifKeys", []) if str(item).strip()],
        "settingKeys": [str(item) for item in data.get("settingKeys", []) if str(item).strip()],
        "figureKeys": [str(item) for item in data.get("figureKeys", []) if str(item).strip()],
        "confidence": str(data.get("confidence") or "medium"),
        "evidenceIds": list(data.get("evidenceIds", []) or evidence_ids),
        "createdAt": now,
        "updatedAt": now,
        "lastSeen": now,
    }
    for key in ("progressionSummary", "egoTrajectory", "compensationTrajectory"):
        value = data.get(key)
        if value:
            record[key] = str(value)
    bucket.dream_series[series_id] = record
    affected = [series_id]
    if material_ids:
        membership_id = create_id("dream_series_membership")
        bucket.dream_series_memberships[membership_id] = {
            "id": membership_id,
            "userId": user_id,
            "seriesId": series_id,
            "materialId": material_ids[0],
            "sequenceIndex": len(material_ids),
            "matchScore": float(data.get("matchScore") or 0.5),
            "matchingFeatures": [
                str(item) for item in data.get("matchingFeatures", []) if str(item).strip()
            ],
            "narrativeRole": str(data.get("narrativeRole") or "continuation"),
            "egoStance": data.get("egoStance"),
            "lysisSummary": data.get("lysisSummary"),
            "evidenceIds": list(data.get("evidenceIds", []) or evidence_ids),
            "status": "active",
            "createdAt": now,
            "updatedAt": now,
        }
        affected.append(membership_id)
    return affected


def apply_link_dream_series_proposal_locked(
    *,
    bucket: UserCirculatioBucket,
    user_id: Id,
    payload: object,
    evidence_ids: list[Id],
) -> list[Id]:
    data = deepcopy(payload)
    series_id = str(data.get("seriesId") or "").strip()
    if not series_id or series_id not in bucket.dream_series:
        raise ValidationError("Dream-series link proposal requires an existing seriesId.")
    material_ids = [str(item) for item in data.get("materialIds", []) if str(item).strip()]
    if not material_ids:
        raise ValidationError("Dream-series link proposal requires materialIds.")
    material_id = material_ids[0]
    now = now_iso()
    existing = next(
        (
            (membership_id, record)
            for membership_id, record in bucket.dream_series_memberships.items()
            if record.get("status") != "deleted"
            and record.get("seriesId") == series_id
            and record.get("materialId") == material_id
        ),
        None,
    )
    if existing is None:
        membership_id = create_id("dream_series_membership")
        bucket.dream_series_memberships[membership_id] = {
            "id": membership_id,
            "userId": user_id,
            "seriesId": series_id,
            "materialId": material_id,
            "sequenceIndex": len(bucket.dream_series[series_id].get("materialIds", [])) + 1,
            "matchScore": float(data.get("matchScore") or 0.5),
            "matchingFeatures": [
                str(item) for item in data.get("matchingFeatures", []) if str(item).strip()
            ],
            "narrativeRole": str(data.get("narrativeRole") or "continuation"),
            "egoStance": data.get("egoStance"),
            "lysisSummary": data.get("lysisSummary"),
            "evidenceIds": list(data.get("evidenceIds", []) or evidence_ids),
            "status": "active",
            "createdAt": now,
            "updatedAt": now,
        }
    else:
        membership_id, record = existing
        record["matchScore"] = float(data.get("matchScore") or record.get("matchScore") or 0.5)
        record["matchingFeatures"] = merge_unique(
            record.get("matchingFeatures", []), data.get("matchingFeatures", [])
        )
        record["narrativeRole"] = str(
            data.get("narrativeRole") or record.get("narrativeRole") or "continuation"
        )
        if data.get("egoStance"):
            record["egoStance"] = str(data["egoStance"])
        if data.get("lysisSummary"):
            record["lysisSummary"] = str(data["lysisSummary"])
        record["evidenceIds"] = merge_unique(
            record.get("evidenceIds", []), data.get("evidenceIds", []) or evidence_ids
        )
        record["status"] = "active"
        record["updatedAt"] = now
    series = bucket.dream_series[series_id]
    series["materialIds"] = merge_unique(series.get("materialIds", []), [material_id])
    series["updatedAt"] = now
    series["lastSeen"] = now
    return [series_id, membership_id]


def apply_update_dream_series_proposal_locked(
    *,
    bucket: UserCirculatioBucket,
    user_id: Id,
    payload: object,
    evidence_ids: list[Id],
) -> Id:
    del user_id
    data = deepcopy(payload)
    series_id = str(data.get("seriesId") or "").strip()
    if not series_id or series_id not in bucket.dream_series:
        raise ValidationError("Dream-series update proposal requires an existing seriesId.")
    series = bucket.dream_series[series_id]
    for key in ("progressionSummary", "egoTrajectory", "compensationTrajectory"):
        value = data.get(key)
        if value:
            series[key] = str(value)
    if data.get("confidence"):
        series["confidence"] = str(data["confidence"])
    series["evidenceIds"] = merge_unique(
        series.get("evidenceIds", []), data.get("evidenceIds", []) or evidence_ids
    )
    series["updatedAt"] = now_iso()
    series["lastSeen"] = series["updatedAt"]
    return series_id


def apply_collective_amplification_proposal_locked(
    *,
    bucket: UserCirculatioBucket,
    user_id: Id,
    material_id: Id | None,
    run_id: Id,
    payload: object,
    evidence_ids: list[Id],
) -> Id:
    data = deepcopy(payload)
    amplification_id = create_id("collective_amplification")
    now = now_iso()
    bucket.collective_amplifications[amplification_id] = {
        "id": amplification_id,
        "userId": user_id,
        "materialId": material_id,
        "runId": run_id,
        "symbolId": data.get("symbolId"),
        "culturalFrameId": data.get("culturalFrameId"),
        "reference": str(data.get("reference") or data.get("amplificationText") or "").strip(),
        "fitReason": str(data.get("fitReason") or data.get("lensLabel") or "").strip(),
        "caveat": str(data.get("caveat") or "").strip(),
        "confidence": str(data.get("confidence") or "medium"),
        "evidenceIds": list(evidence_ids),
        "status": "user_resonated",
        "createdAt": now,
        "updatedAt": now,
    }
    return amplification_id


def apply_individuation_proposal_locked(
    *,
    bucket: UserCirculatioBucket,
    user_id: Id,
    action: str,
    payload: object,
    evidence_ids: list[Id],
    source: str,
) -> Id:
    data = deepcopy(payload)
    now = now_iso()

    if action == "create_reality_anchor_summary":
        record = _new_individuation_record(
            record_id=create_id("reality_anchor_summary"),
            user_id=user_id,
            record_type="reality_anchor_summary",
            source=source,
            label="Reality anchors",
            summary=_text(data.get("anchorSummary"), "Reality anchors"),
            details={
                "anchorSummary": _text(data.get("anchorSummary"), "Reality anchors"),
                "workDailyLifeContinuity": _text(data.get("workDailyLifeContinuity"), "unknown"),
                "sleepBodyRegulation": _text(data.get("sleepBodyRegulation"), "unknown"),
                "relationshipContact": _text(data.get("relationshipContact"), "unknown"),
                "reflectiveCapacity": _text(data.get("reflectiveCapacity"), "unknown"),
                "groundingRecommendation": _text(
                    data.get("groundingRecommendation"), "pace_gently"
                ),
                "reasons": _strings(data.get("reasons")),
            },
            evidence_ids=evidence_ids,
            related_material_ids=_ids(data.get("relatedMaterialIds")),
            related_symbol_ids=_ids(data.get("relatedSymbolIds")),
            related_goal_ids=_ids(data.get("relatedGoalIds")),
            created_at=now,
        )
        bucket.individuation_records[record["id"]] = record
        return record["id"]

    if action == "create_self_orientation_snapshot":
        record = _new_individuation_record(
            record_id=create_id("self_orientation_snapshot"),
            user_id=user_id,
            record_type="self_orientation_snapshot",
            source=source,
            label="Self orientation",
            summary=_text(data.get("orientationSummary"), "Self orientation"),
            details={
                "orientationSummary": _text(data.get("orientationSummary"), "Self orientation"),
                "emergentDirection": _text(data.get("emergentDirection"), ""),
                "egoRelation": _text(data.get("egoRelation"), "unknown"),
                "movementLanguage": _strings(data.get("movementLanguage")),
                "notMetaphysicalClaim": True,
            },
            evidence_ids=evidence_ids,
            related_material_ids=_ids(data.get("relatedMaterialIds")),
            related_symbol_ids=_ids(data.get("relatedSymbolIds")),
            related_goal_ids=_ids(data.get("relatedGoalIds")),
            created_at=now,
        )
        bucket.individuation_records[record["id"]] = record
        return record["id"]

    if action == "upsert_psychic_opposition":
        normalized_key = _normalized_text(data.get("normalizedOppositionKey"))
        if not normalized_key:
            raise ValidationError("Psychic-opposition proposals require normalizedOppositionKey.")
        existing = _find_individuation_record_locked(
            bucket,
            record_type="psychic_opposition",
            matcher=lambda item: (
                _normalized_text(item.get("details", {}).get("normalizedOppositionKey"))
                == normalized_key
            ),
        )
        label = f"{_text(data.get('poleA'), 'Opposition')} / {_text(data.get('poleB'), 'tension')}"
        summary = _text(data.get("oppositionSummary"), label)
        details = {
            "poleA": _text(data.get("poleA"), ""),
            "poleB": _text(data.get("poleB"), ""),
            "oppositionSummary": summary,
            "currentHoldingPattern": _text(data.get("currentHoldingPattern"), ""),
            "normalizedOppositionKey": normalized_key,
        }
        if data.get("pressureTone"):
            details["pressureTone"] = _text(data.get("pressureTone"))
        if data.get("holdingInstruction"):
            details["holdingInstruction"] = _text(data.get("holdingInstruction"))
        if existing is None:
            record = _new_individuation_record(
                record_id=create_id("psychic_opposition"),
                user_id=user_id,
                record_type="psychic_opposition",
                source=source,
                label=label,
                summary=summary,
                details=details,
                evidence_ids=evidence_ids,
                related_material_ids=_ids(data.get("relatedMaterialIds")),
                related_goal_ids=_ids(data.get("relatedGoalIds")),
                created_at=now,
            )
            bucket.individuation_records[record["id"]] = record
            return record["id"]
        record_id, record = existing
        record["label"] = label
        record["summary"] = summary
        record["source"] = source
        record["status"] = "active"
        record["confidence"] = max_confidence(record.get("confidence", "low"), "medium")
        record["evidenceIds"] = merge_unique(record.get("evidenceIds", []), evidence_ids)
        record["relatedMaterialIds"] = merge_unique(
            record.get("relatedMaterialIds", []), _ids(data.get("relatedMaterialIds"))
        )
        record["relatedGoalIds"] = merge_unique(
            record.get("relatedGoalIds", []), _ids(data.get("relatedGoalIds"))
        )
        record["details"] = details
        record["updatedAt"] = now
        return record_id

    if action == "create_emergent_third_signal":
        record = _new_individuation_record(
            record_id=create_id("emergent_third_signal"),
            user_id=user_id,
            record_type="emergent_third_signal",
            source=source,
            label="Emergent third signal",
            summary=_text(data.get("signalSummary"), "Emergent third signal"),
            details={
                "signalType": _text(data.get("signalType"), "unknown"),
                "signalSummary": _text(data.get("signalSummary"), "Emergent third signal"),
                "oppositionIds": _ids(data.get("oppositionIds")),
                "novelty": _text(data.get("novelty"), "unclear"),
            },
            evidence_ids=evidence_ids,
            related_material_ids=_ids(data.get("relatedMaterialIds")),
            related_symbol_ids=_ids(data.get("relatedSymbolIds")),
            related_practice_session_ids=_ids(data.get("relatedPracticeSessionIds")),
            created_at=now,
        )
        bucket.individuation_records[record["id"]] = record
        return record["id"]

    if action == "create_bridge_moment":
        summary = _text(data.get("bridgeSummary"), "Bridge moment")
        details = {
            "bridgeType": _text(data.get("bridgeType"), "unknown"),
            "bridgeSummary": summary,
        }
        if data.get("beforeAfter"):
            details["beforeAfter"] = _text(data.get("beforeAfter"))
        record = _new_individuation_record(
            record_id=create_id("bridge_moment"),
            user_id=user_id,
            record_type="bridge_moment",
            source=source,
            label="Bridge moment",
            summary=summary,
            details=details,
            evidence_ids=evidence_ids,
            related_material_ids=_ids(data.get("relatedMaterialIds")),
            related_symbol_ids=_ids(data.get("relatedSymbolIds")),
            related_practice_session_ids=_ids(data.get("relatedPracticeSessionIds")),
            created_at=now,
        )
        bucket.individuation_records[record["id"]] = record
        return record["id"]

    if action == "create_numinous_encounter":
        summary = _text(
            data.get("interpretationConstraint"),
            f"{_text(data.get('encounterMedium'), 'unknown')} encounter",
        )
        record = _new_individuation_record(
            record_id=create_id("numinous_encounter"),
            user_id=user_id,
            record_type="numinous_encounter",
            source=source,
            label="Numinous encounter",
            summary=summary,
            details={
                "encounterMedium": _text(data.get("encounterMedium"), "unknown"),
                "affectTone": _text(data.get("affectTone"), ""),
                "containmentNeed": _text(data.get("containmentNeed"), "ordinary_reflection"),
                "interpretationConstraint": summary,
            },
            evidence_ids=evidence_ids,
            related_material_ids=_ids(data.get("relatedMaterialIds")),
            related_symbol_ids=_ids(data.get("relatedSymbolIds")),
            created_at=now,
        )
        bucket.individuation_records[record["id"]] = record
        return record["id"]

    if action == "create_aesthetic_resonance":
        summary = _text(data.get("resonanceSummary"), "Aesthetic resonance")
        details = {
            "medium": _text(data.get("medium"), "unknown"),
            "objectDescription": _text(data.get("objectDescription"), ""),
            "resonanceSummary": summary,
            "bodySensations": _strings(data.get("bodySensations")),
        }
        if data.get("feelingTone"):
            details["feelingTone"] = _text(data.get("feelingTone"))
        record = _new_individuation_record(
            record_id=create_id("aesthetic_resonance"),
            user_id=user_id,
            record_type="aesthetic_resonance",
            source=source,
            label="Aesthetic resonance",
            summary=summary,
            details=details,
            evidence_ids=evidence_ids,
            related_material_ids=_ids(data.get("relatedMaterialIds")),
            related_symbol_ids=_ids(data.get("relatedSymbolIds")),
            created_at=now,
        )
        bucket.individuation_records[record["id"]] = record
        return record["id"]

    if action == "upsert_archetypal_pattern":
        pattern_family = _text(data.get("patternFamily"), "unknown")
        summary = _text(data.get("resonanceSummary"), pattern_family)
        summary_key = _normalized_text(summary)
        existing = _find_individuation_record_locked(
            bucket,
            record_type="archetypal_pattern",
            matcher=lambda item: (
                _text(item.get("details", {}).get("patternFamily"), "unknown") == pattern_family
                and _normalized_text(item.get("details", {}).get("resonanceSummary")) == summary_key
            ),
        )
        details = {
            "patternFamily": pattern_family,
            "resonanceSummary": summary,
            "caveat": _text(data.get("caveat"), "Held as a tentative archetypal resonance."),
            "counterevidenceIds": _ids(data.get("counterevidenceIds")),
            "phrasingPolicy": "very_tentative",
        }
        if existing is None:
            record = _new_individuation_record(
                record_id=create_id("archetypal_pattern"),
                user_id=user_id,
                record_type="archetypal_pattern",
                source=source,
                label="Archetypal pattern",
                summary=summary,
                details=details,
                evidence_ids=evidence_ids,
                related_material_ids=_ids(data.get("relatedMaterialIds")),
                related_symbol_ids=_ids(data.get("relatedSymbolIds")),
                created_at=now,
            )
            bucket.individuation_records[record["id"]] = record
            return record["id"]
        record_id, record = existing
        record["summary"] = summary
        record["source"] = source
        record["status"] = "active"
        record["evidenceIds"] = merge_unique(record.get("evidenceIds", []), evidence_ids)
        record["relatedMaterialIds"] = merge_unique(
            record.get("relatedMaterialIds", []), _ids(data.get("relatedMaterialIds"))
        )
        record["relatedSymbolIds"] = merge_unique(
            record.get("relatedSymbolIds", []), _ids(data.get("relatedSymbolIds"))
        )
        existing_details = deepcopy(record.get("details", {}))
        existing_details["counterevidenceIds"] = merge_unique(
            existing_details.get("counterevidenceIds", []), _ids(data.get("counterevidenceIds"))
        )
        existing_details["patternFamily"] = pattern_family
        existing_details["resonanceSummary"] = summary
        existing_details["caveat"] = _text(
            data.get("caveat"), "Held as a tentative archetypal resonance."
        )
        existing_details["phrasingPolicy"] = "very_tentative"
        record["details"] = existing_details
        record["updatedAt"] = now
        return record_id

    if action == "upsert_threshold_process":
        normalized_key = _normalized_text(data.get("normalizedThresholdKey"))
        if not normalized_key:
            raise ValidationError("Threshold-process proposals require normalizedThresholdKey.")
        existing = _find_individuation_record_locked(
            bucket,
            record_type="threshold_process",
            matcher=lambda item: (
                _normalized_text(item.get("details", {}).get("normalizedThresholdKey"))
                == normalized_key
            ),
        )
        label = _text(data.get("thresholdName"), "Threshold process")
        summary = _text(data.get("whatIsEnding"), label)
        details = {
            "thresholdName": label,
            "phase": _text(data.get("phase"), "unknown"),
            "whatIsEnding": summary,
            "notYetBegun": _text(data.get("notYetBegun"), ""),
            "groundingStatus": _text(data.get("groundingStatus"), "unknown"),
            "invitationReadiness": _text(data.get("invitationReadiness"), "ask"),
            "normalizedThresholdKey": normalized_key,
        }
        if data.get("bodyCarrying"):
            details["bodyCarrying"] = _text(data.get("bodyCarrying"))
        if data.get("symbolicLens"):
            details["symbolicLens"] = _text(data.get("symbolicLens"))
        if existing is None:
            record = _new_individuation_record(
                record_id=create_id("threshold_process"),
                user_id=user_id,
                record_type="threshold_process",
                source=source,
                label=label,
                summary=summary,
                details=details,
                evidence_ids=evidence_ids,
                related_material_ids=_ids(data.get("relatedMaterialIds")),
                related_symbol_ids=_ids(data.get("relatedSymbolIds")),
                related_goal_ids=_ids(data.get("relatedGoalIds")),
                related_dream_series_ids=_ids(data.get("relatedDreamSeriesIds")),
                created_at=now,
            )
            bucket.individuation_records[record["id"]] = record
            return record["id"]
        record_id, record = existing
        record["label"] = label
        record["summary"] = summary
        record["source"] = source
        record["status"] = "active"
        record["evidenceIds"] = merge_unique(record.get("evidenceIds", []), evidence_ids)
        record["relatedMaterialIds"] = merge_unique(
            record.get("relatedMaterialIds", []), _ids(data.get("relatedMaterialIds"))
        )
        record["relatedSymbolIds"] = merge_unique(
            record.get("relatedSymbolIds", []), _ids(data.get("relatedSymbolIds"))
        )
        record["relatedGoalIds"] = merge_unique(
            record.get("relatedGoalIds", []), _ids(data.get("relatedGoalIds"))
        )
        record["relatedDreamSeriesIds"] = merge_unique(
            record.get("relatedDreamSeriesIds", []), _ids(data.get("relatedDreamSeriesIds"))
        )
        record["details"] = details
        record["updatedAt"] = now
        return record_id

    if action == "upsert_relational_scene":
        normalized_key = _normalized_text(data.get("normalizedSceneKey"))
        if not normalized_key:
            raise ValidationError("Relational-scene proposals require normalizedSceneKey.")
        existing = _find_individuation_record_locked(
            bucket,
            record_type="relational_scene",
            matcher=lambda item: (
                _normalized_text(item.get("details", {}).get("normalizedSceneKey"))
                == normalized_key
            ),
        )
        label = "Relational scene"
        summary = _text(data.get("sceneSummary"), label)
        roles = _role_dicts(data.get("chargedRoles"))
        details = {
            "sceneSummary": summary,
            "chargedRoles": roles,
            "recurringAffect": _strings(data.get("recurringAffect")),
            "recurrenceContexts": _strings(data.get("recurrenceContexts")),
            "normalizedSceneKey": normalized_key,
        }
        if existing is None:
            record = _new_individuation_record(
                record_id=create_id("relational_scene"),
                user_id=user_id,
                record_type="relational_scene",
                source=source,
                label=label,
                summary=summary,
                details=details,
                evidence_ids=evidence_ids,
                related_material_ids=_ids(data.get("relatedMaterialIds")),
                related_goal_ids=_ids(data.get("relatedGoalIds")),
                created_at=now,
            )
            bucket.individuation_records[record["id"]] = record
            return record["id"]
        record_id, record = existing
        existing_details = deepcopy(record.get("details", {}))
        existing_details["chargedRoles"] = _merge_unique_dicts(
            existing_details.get("chargedRoles", []), roles
        )
        existing_details["recurringAffect"] = merge_unique(
            existing_details.get("recurringAffect", []), _strings(data.get("recurringAffect"))
        )
        existing_details["recurrenceContexts"] = merge_unique(
            existing_details.get("recurrenceContexts", []), _strings(data.get("recurrenceContexts"))
        )
        existing_details["sceneSummary"] = summary
        existing_details["normalizedSceneKey"] = normalized_key
        record["label"] = label
        record["summary"] = summary
        record["source"] = source
        record["status"] = "active"
        record["evidenceIds"] = merge_unique(record.get("evidenceIds", []), evidence_ids)
        record["relatedMaterialIds"] = merge_unique(
            record.get("relatedMaterialIds", []), _ids(data.get("relatedMaterialIds"))
        )
        record["relatedGoalIds"] = merge_unique(
            record.get("relatedGoalIds", []), _ids(data.get("relatedGoalIds"))
        )
        record["details"] = existing_details
        record["updatedAt"] = now
        return record_id

    if action == "upsert_projection_hypothesis":
        normalized_key = _normalized_text(data.get("normalizedHypothesisKey"))
        if not normalized_key:
            raise ValidationError(
                "Projection-hypothesis proposals require normalizedHypothesisKey."
            )
        relational_scene_id = _text(data.get("relationalSceneId")) or None
        existing = _find_individuation_record_locked(
            bucket,
            record_type="projection_hypothesis",
            matcher=lambda item: (
                _normalized_text(item.get("details", {}).get("normalizedHypothesisKey"))
                == normalized_key
                and _text(item.get("details", {}).get("relationalSceneId"))
                == (relational_scene_id or "")
            ),
        )
        summary = _text(data.get("hypothesisSummary"), "Projection hypothesis")
        details = {
            "hypothesisSummary": summary,
            "projectionPattern": _text(data.get("projectionPattern"), ""),
            "userTestPrompt": _text(data.get("userTestPrompt"), ""),
            "counterevidenceIds": _ids(data.get("counterevidenceIds")),
            "phrasingPolicy": "very_tentative",
            "consentScope": "projection_language",
            "normalizedHypothesisKey": normalized_key,
        }
        if relational_scene_id:
            details["relationalSceneId"] = relational_scene_id
        if existing is None:
            record = _new_individuation_record(
                record_id=create_id("projection_hypothesis"),
                user_id=user_id,
                record_type="projection_hypothesis",
                source=source,
                label="Projection hypothesis",
                summary=summary,
                details=details,
                evidence_ids=evidence_ids,
                related_material_ids=_ids(data.get("relatedMaterialIds")),
                created_at=now,
            )
            bucket.individuation_records[record["id"]] = record
            return record["id"]
        record_id, record = existing
        existing_details = deepcopy(record.get("details", {}))
        existing_details["counterevidenceIds"] = merge_unique(
            existing_details.get("counterevidenceIds", []), _ids(data.get("counterevidenceIds"))
        )
        existing_details["hypothesisSummary"] = summary
        existing_details["projectionPattern"] = _text(data.get("projectionPattern"), "")
        existing_details["userTestPrompt"] = _text(data.get("userTestPrompt"), "")
        existing_details["phrasingPolicy"] = "very_tentative"
        existing_details["consentScope"] = "projection_language"
        existing_details["normalizedHypothesisKey"] = normalized_key
        if relational_scene_id:
            existing_details["relationalSceneId"] = relational_scene_id
        record["summary"] = summary
        record["source"] = source
        record["status"] = "active"
        record["evidenceIds"] = merge_unique(record.get("evidenceIds", []), evidence_ids)
        record["relatedMaterialIds"] = merge_unique(
            record.get("relatedMaterialIds", []), _ids(data.get("relatedMaterialIds"))
        )
        record["details"] = existing_details
        record["updatedAt"] = now
        return record_id

    if action == "upsert_inner_outer_correspondence":
        normalized_key = _normalized_text(data.get("normalizedCorrespondenceKey"))
        if not normalized_key:
            raise ValidationError(
                "Inner-outer correspondence proposals require normalizedCorrespondenceKey."
            )
        existing = _find_individuation_record_locked(
            bucket,
            record_type="inner_outer_correspondence",
            matcher=lambda item: (
                _normalized_text(item.get("details", {}).get("normalizedCorrespondenceKey"))
                == normalized_key
            ),
        )
        summary = _text(data.get("correspondenceSummary"), "Inner-outer correspondence")
        details = {
            "correspondenceSummary": summary,
            "innerRefs": _ids(data.get("innerRefs")),
            "outerRefs": _ids(data.get("outerRefs")),
            "symbolIds": _ids(data.get("symbolIds")),
            "userCharge": _text(data.get("userCharge"), "unclear"),
            "caveat": _text(data.get("caveat"), "Held without causal claim."),
            "causalityPolicy": "no_causal_claim",
            "normalizedCorrespondenceKey": normalized_key,
        }
        if data.get("timeWindowStart"):
            details["timeWindowStart"] = _text(data.get("timeWindowStart"))
        if data.get("timeWindowEnd"):
            details["timeWindowEnd"] = _text(data.get("timeWindowEnd"))
        if existing is None:
            record = _new_individuation_record(
                record_id=create_id("inner_outer_correspondence"),
                user_id=user_id,
                record_type="inner_outer_correspondence",
                source=source,
                label="Inner-outer correspondence",
                summary=summary,
                details=details,
                evidence_ids=evidence_ids,
                related_material_ids=_ids(data.get("relatedMaterialIds")),
                related_symbol_ids=_ids(data.get("symbolIds")),
                created_at=now,
            )
            bucket.individuation_records[record["id"]] = record
            return record["id"]
        record_id, record = existing
        existing_details = deepcopy(record.get("details", {}))
        existing_details["innerRefs"] = merge_unique(
            existing_details.get("innerRefs", []), _ids(data.get("innerRefs"))
        )
        existing_details["outerRefs"] = merge_unique(
            existing_details.get("outerRefs", []), _ids(data.get("outerRefs"))
        )
        existing_details["symbolIds"] = merge_unique(
            existing_details.get("symbolIds", []), _ids(data.get("symbolIds"))
        )
        existing_details["correspondenceSummary"] = summary
        existing_details["userCharge"] = _text(data.get("userCharge"), "unclear")
        existing_details["caveat"] = _text(data.get("caveat"), "Held without causal claim.")
        existing_details["causalityPolicy"] = "no_causal_claim"
        existing_details["normalizedCorrespondenceKey"] = normalized_key
        if data.get("timeWindowStart"):
            existing_details["timeWindowStart"] = _text(data.get("timeWindowStart"))
        if data.get("timeWindowEnd"):
            existing_details["timeWindowEnd"] = _text(data.get("timeWindowEnd"))
        record["summary"] = summary
        record["source"] = source
        record["status"] = "active"
        record["evidenceIds"] = merge_unique(record.get("evidenceIds", []), evidence_ids)
        record["relatedMaterialIds"] = merge_unique(
            record.get("relatedMaterialIds", []), _ids(data.get("relatedMaterialIds"))
        )
        record["relatedSymbolIds"] = merge_unique(
            record.get("relatedSymbolIds", []), _ids(data.get("symbolIds"))
        )
        record["details"] = existing_details
        record["updatedAt"] = now
        return record_id

    raise ValidationError(f"Unsupported individuation proposal action: {action}")


def apply_living_myth_proposal_locked(
    *,
    bucket: UserCirculatioBucket,
    user_id: Id,
    action: str,
    payload: object,
    evidence_ids: list[Id],
    source: str,
) -> Id:
    data = deepcopy(payload)
    now = now_iso()

    if action == "create_life_chapter_snapshot":
        record = _new_living_myth_record(
            record_id=create_id("life_chapter_snapshot"),
            user_id=user_id,
            record_type="life_chapter_snapshot",
            source=source,
            label=_text(data.get("chapterLabel"), "Current chapter"),
            summary=_text(data.get("chapterSummary"), "Current chapter"),
            details={
                "chapterLabel": _text(data.get("chapterLabel"), "Current chapter"),
                "chapterSummary": _text(data.get("chapterSummary"), "Current chapter"),
                "governingSymbolIds": _ids(data.get("governingSymbolIds")),
                "governingQuestions": _strings(data.get("governingQuestions")),
                "activeOppositionIds": _ids(data.get("activeOppositionIds")),
                "thresholdProcessIds": _ids(data.get("thresholdProcessIds")),
                "relationalSceneIds": _ids(data.get("relationalSceneIds")),
                "correspondenceIds": _ids(data.get("correspondenceIds")),
            },
            evidence_ids=evidence_ids,
            related_material_ids=_ids(data.get("relatedMaterialIds")),
            related_symbol_ids=_ids(data.get("governingSymbolIds")),
            related_individuation_record_ids=merge_unique(
                merge_unique(
                    _ids(data.get("activeOppositionIds")),
                    _ids(data.get("thresholdProcessIds")),
                ),
                merge_unique(
                    _ids(data.get("relationalSceneIds")),
                    _ids(data.get("correspondenceIds")),
                ),
            ),
            created_at=now,
        )
        if data.get("chapterTone"):
            record["details"]["chapterTone"] = _text(data.get("chapterTone"))
        bucket.living_myth_records[record["id"]] = record
        return record["id"]

    if action == "upsert_mythic_question":
        question_text = _text(data.get("questionText"))
        normalized_question = _normalized_text(question_text)
        if not normalized_question:
            raise ValidationError("Mythic-question proposals require questionText.")
        existing = _find_living_myth_record_locked(
            bucket,
            record_type="mythic_question",
            matcher=lambda item: (
                _normalized_text(item.get("details", {}).get("questionText")) == normalized_question
            ),
        )
        details = {
            "questionText": question_text,
            "questionStatus": _text(data.get("questionStatus"), "active"),
        }
        if data.get("relatedChapterId"):
            details["relatedChapterId"] = _text(data.get("relatedChapterId"))
        if data.get("lastReturnedAt"):
            details["lastReturnedAt"] = _text(data.get("lastReturnedAt"))
        if existing is None:
            record = _new_living_myth_record(
                record_id=create_id("mythic_question"),
                user_id=user_id,
                record_type="mythic_question",
                source=source,
                label="Mythic question",
                summary=question_text,
                details=details,
                evidence_ids=evidence_ids,
                created_at=now,
            )
            bucket.living_myth_records[record["id"]] = record
            return record["id"]
        record_id, record = existing
        existing_details = deepcopy(record.get("details", {}))
        existing_details.update(details)
        record["summary"] = question_text
        record["source"] = source
        record["status"] = "active"
        record["evidenceIds"] = merge_unique(record.get("evidenceIds", []), evidence_ids)
        record["details"] = existing_details
        record["updatedAt"] = now
        return record_id

    if action == "create_threshold_marker":
        details = {
            "markerType": _text(data.get("markerType"), "unknown"),
            "markerSummary": _text(data.get("markerSummary"), "Threshold marker"),
        }
        threshold_process_id = _text(data.get("thresholdProcessId")) or None
        if threshold_process_id:
            details["thresholdProcessId"] = threshold_process_id
        record = _new_living_myth_record(
            record_id=create_id("threshold_marker"),
            user_id=user_id,
            record_type="threshold_marker",
            source=source,
            label="Threshold marker",
            summary=details["markerSummary"],
            details=details,
            evidence_ids=evidence_ids,
            related_material_ids=_ids(data.get("relatedMaterialIds")),
            related_individuation_record_ids=[threshold_process_id] if threshold_process_id else [],
            created_at=now,
        )
        bucket.living_myth_records[record["id"]] = record
        return record["id"]

    if action == "upsert_complex_encounter":
        complex_candidate_id = _text(data.get("complexCandidateId")) or None
        pattern_id = _text(data.get("patternId")) or None
        encounter_key = _normalized_text(data.get("encounterSummary"))
        existing = _find_living_myth_record_locked(
            bucket,
            record_type="complex_encounter",
            matcher=lambda item: (
                (
                    (
                        _text(item.get("details", {}).get("complexCandidateId"))
                        == (complex_candidate_id or "")
                    )
                    or (_text(item.get("details", {}).get("patternId")) == (pattern_id or ""))
                )
                and (
                    _normalized_text(item.get("details", {}).get("encounterSummary"))
                    == encounter_key
                )
            ),
        )
        summary = _text(data.get("encounterSummary"), "Complex encounter")
        details = {
            "encounterSummary": summary,
            "trajectorySummary": _text(data.get("trajectorySummary"), summary),
            "movement": _text(data.get("movement"), "unknown"),
        }
        if complex_candidate_id:
            details["complexCandidateId"] = complex_candidate_id
        if pattern_id:
            details["patternId"] = pattern_id
        if existing is None:
            record = _new_living_myth_record(
                record_id=create_id("complex_encounter"),
                user_id=user_id,
                record_type="complex_encounter",
                source=source,
                label="Complex encounter",
                summary=summary,
                details=details,
                evidence_ids=evidence_ids,
                related_material_ids=_ids(data.get("relatedMaterialIds")),
                related_individuation_record_ids=_ids(data.get("relatedIndividuationRecordIds")),
                created_at=now,
            )
            bucket.living_myth_records[record["id"]] = record
            return record["id"]
        record_id, record = existing
        record["summary"] = summary
        record["source"] = source
        record["status"] = "active"
        record["evidenceIds"] = merge_unique(record.get("evidenceIds", []), evidence_ids)
        record["relatedMaterialIds"] = merge_unique(
            record.get("relatedMaterialIds", []), _ids(data.get("relatedMaterialIds"))
        )
        record["relatedIndividuationRecordIds"] = merge_unique(
            record.get("relatedIndividuationRecordIds", []),
            _ids(data.get("relatedIndividuationRecordIds")),
        )
        record["details"] = details
        record["updatedAt"] = now
        return record_id

    if action == "create_integration_contour":
        summary = _text(data.get("contourSummary"), "Integration contour")
        record = _new_living_myth_record(
            record_id=create_id("integration_contour"),
            user_id=user_id,
            record_type="integration_contour",
            source=source,
            label="Integration contour",
            summary=summary,
            details={
                "contourSummary": summary,
                "symbolicStrands": _strings(data.get("symbolicStrands")),
                "somaticStrands": _strings(data.get("somaticStrands")),
                "relationalStrands": _strings(data.get("relationalStrands")),
                "existentialStrands": _strings(data.get("existentialStrands")),
                "tensionsHeld": _strings(data.get("tensionsHeld")),
                "assimilatedSignals": _strings(data.get("assimilatedSignals")),
                "unassimilatedEdges": _strings(data.get("unassimilatedEdges")),
                "nextQuestions": _strings(data.get("nextQuestions")),
            },
            evidence_ids=evidence_ids,
            related_material_ids=_ids(data.get("relatedMaterialIds")),
            related_individuation_record_ids=_ids(data.get("relatedIndividuationRecordIds")),
            created_at=now,
        )
        bucket.living_myth_records[record["id"]] = record
        return record["id"]

    if action == "create_symbolic_wellbeing_snapshot":
        summary = _text(data.get("capacitySummary"), "Symbolic wellbeing")
        record = _new_living_myth_record(
            record_id=create_id("symbolic_wellbeing_snapshot"),
            user_id=user_id,
            record_type="symbolic_wellbeing_snapshot",
            source=source,
            label="Symbolic wellbeing",
            summary=summary,
            details={
                "capacitySummary": summary,
                "groundingCapacity": _text(data.get("groundingCapacity"), "unknown"),
                "symbolicLiveliness": _text(data.get("symbolicLiveliness"), ""),
                "somaticContact": _text(data.get("somaticContact"), ""),
                "relationalSpaciousness": _text(data.get("relationalSpaciousness"), ""),
                "agencyTone": _text(data.get("agencyTone"), ""),
            },
            evidence_ids=evidence_ids,
            related_material_ids=_ids(data.get("relatedMaterialIds")),
            related_individuation_record_ids=_ids(data.get("relatedIndividuationRecordIds")),
            created_at=now,
        )
        if data.get("supportNeeded"):
            record["details"]["supportNeeded"] = _text(data.get("supportNeeded"))
        bucket.living_myth_records[record["id"]] = record
        return record["id"]

    raise ValidationError(f"Unsupported living-myth proposal action: {action}")


def proposal_source_locked(bucket: UserCirculatioBucket, plan: MemoryWritePlan) -> str:
    run_id = plan["runId"]
    if run_id in bucket.interpretation_runs:
        return "interpretation_proposal"
    for review in bucket.living_myth_reviews.values():
        if review.get("status") == "deleted":
            continue
        review_plan = review.get("memoryWritePlan") or {}
        if review_plan.get("runId") != run_id:
            continue
        if review.get("reviewType") == "threshold_review":
            return "threshold_review"
        return "living_myth_review"
    return "interpretation_proposal"


def _new_individuation_record(
    *,
    record_id: Id,
    user_id: Id,
    record_type: str,
    source: str,
    label: str,
    summary: str,
    details: dict[str, object],
    evidence_ids: list[Id],
    created_at: str,
    related_material_ids: list[Id] | None = None,
    related_symbol_ids: list[Id] | None = None,
    related_goal_ids: list[Id] | None = None,
    related_dream_series_ids: list[Id] | None = None,
    related_journey_ids: list[Id] | None = None,
    related_practice_session_ids: list[Id] | None = None,
) -> dict[str, object]:
    return {
        "id": record_id,
        "userId": user_id,
        "recordType": record_type,
        "status": "active",
        "source": source,
        "label": label,
        "summary": summary,
        "confidence": "medium",
        "evidenceIds": list(evidence_ids),
        "relatedMaterialIds": list(related_material_ids or []),
        "relatedSymbolIds": list(related_symbol_ids or []),
        "relatedGoalIds": list(related_goal_ids or []),
        "relatedDreamSeriesIds": list(related_dream_series_ids or []),
        "relatedJourneyIds": list(related_journey_ids or []),
        "relatedPracticeSessionIds": list(related_practice_session_ids or []),
        "privacyClass": "approved_summary",
        "details": deepcopy(details),
        "createdAt": created_at,
        "updatedAt": created_at,
    }


def _new_living_myth_record(
    *,
    record_id: Id,
    user_id: Id,
    record_type: str,
    source: str,
    label: str,
    summary: str,
    details: dict[str, object],
    evidence_ids: list[Id],
    created_at: str,
    related_material_ids: list[Id] | None = None,
    related_symbol_ids: list[Id] | None = None,
    related_goal_ids: list[Id] | None = None,
    related_dream_series_ids: list[Id] | None = None,
    related_individuation_record_ids: list[Id] | None = None,
) -> dict[str, object]:
    return {
        "id": record_id,
        "userId": user_id,
        "recordType": record_type,
        "status": "active",
        "source": source,
        "label": label,
        "summary": summary,
        "confidence": "medium",
        "evidenceIds": list(evidence_ids),
        "relatedMaterialIds": list(related_material_ids or []),
        "relatedSymbolIds": list(related_symbol_ids or []),
        "relatedGoalIds": list(related_goal_ids or []),
        "relatedDreamSeriesIds": list(related_dream_series_ids or []),
        "relatedIndividuationRecordIds": list(related_individuation_record_ids or []),
        "privacyClass": "approved_summary",
        "details": deepcopy(details),
        "createdAt": created_at,
        "updatedAt": created_at,
    }


def _find_individuation_record_locked(
    bucket: UserCirculatioBucket,
    *,
    record_type: str,
    matcher,
) -> tuple[Id, dict[str, object]] | None:
    for record_id, record in bucket.individuation_records.items():
        if record.get("status") == "deleted" or record.get("recordType") != record_type:
            continue
        if matcher(record):
            return record_id, record
    return None


def _find_living_myth_record_locked(
    bucket: UserCirculatioBucket,
    *,
    record_type: str,
    matcher,
) -> tuple[Id, dict[str, object]] | None:
    for record_id, record in bucket.living_myth_records.items():
        if record.get("status") == "deleted" or record.get("recordType") != record_type:
            continue
        if matcher(record):
            return record_id, record
    return None


def _normalized_text(value: object | None) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _text(value: object | None, default: str = "") -> str:
    text = str(value or "").strip()
    return text or default


def _ids(value: object | None) -> list[Id]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _strings(value: object | None) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _role_dicts(value: object | None) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [deepcopy(item) for item in value if isinstance(item, dict) and item]


def _merge_unique_dicts(
    existing: list[dict[str, object]], new_items: list[dict[str, object]]
) -> list[dict[str, object]]:
    result = [deepcopy(item) for item in existing]
    for item in new_items:
        if item not in result:
            result.append(deepcopy(item))
    return result


def proposal_action(plan: MemoryWritePlan, proposal_id: Id) -> str:
    proposal = next((item for item in plan["proposals"] if item["id"] == proposal_id), None)
    if proposal is None:
        raise ValidationError(f"Unknown proposal id: {proposal_id}")
    return proposal["action"]


def proposal_entity_type(plan: MemoryWritePlan, proposal_id: Id) -> str:
    proposal = next((item for item in plan["proposals"] if item["id"] == proposal_id), None)
    if proposal is None:
        raise ValidationError(f"Unknown proposal id: {proposal_id}")
    return proposal["entityType"]


def merge_decisions(
    existing: list[ProposalDecisionRecord], updates: list[ProposalDecisionRecord]
) -> list[ProposalDecisionRecord]:
    by_id = {item["proposalId"]: deepcopy(item) for item in existing}
    for update in updates:
        merged = by_id.get(update["proposalId"], {})
        merged.update(deepcopy(update))
        by_id[update["proposalId"]] = merged
    return list(by_id.values())


def append_symbol_history_locked(bucket: UserCirculatioBucket, entry) -> None:
    bucket.symbol_history.setdefault(entry["symbolId"], []).append(deepcopy(entry))


def append_pattern_history_locked(bucket: UserCirculatioBucket, entry) -> None:
    bucket.pattern_history.setdefault(entry["patternId"], []).append(deepcopy(entry))


def find_pattern_locked(
    bucket: UserCirculatioBucket, *, label: str, formulation: str
) -> tuple[Id, PatternRecord] | None:
    lowered_label = label.lower()
    lowered_formulation = formulation.lower()
    for pattern_id, record in bucket.patterns.items():
        if record.get("status") == "deleted":
            continue
        if (
            record["label"].lower() == lowered_label
            and record["formulation"].lower() == lowered_formulation
        ):
            return pattern_id, record
    return None


def build_personal_association(
    canonical_name: str, association: object | None
) -> PersonalAssociationSummary | None:
    if not association:
        return None
    return {
        "id": create_id("assoc"),
        "symbolName": canonical_name,
        "association": str(association),
        "source": "user_confirmed",
        "date": now_iso(),
    }


def max_confidence(left: str, right: str) -> str:
    return left if _CONFIDENCE_ORDER[left] >= _CONFIDENCE_ORDER[right] else right


def merge_unique(existing: list[object], new_items: list[object] | None) -> list[object]:
    result = list(existing)
    for item in new_items or []:
        if item not in result:
            result.append(item)
    return result


def unique_ids(items: list[Id]) -> list[Id]:
    seen: list[Id] = []
    for item in items:
        if item not in seen:
            seen.append(item)
    return seen
