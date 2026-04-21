from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from typing import Literal, TypedDict, cast

from ..domain.clarifications import ClarificationCaptureTarget
from ..domain.ids import normalize_claim_key, now_iso
from ..domain.types import (
    ActiveGoalTensionSummary,
    ClarificationAnswerSummary,
    ClarificationPromptSummary,
    ClarificationStateSummary,
    CompensationTendencySummary,
    Confidence,
    ContainmentSummary,
    DreamDynamicsSummary,
    EgoCapacitySummary,
    EgoRelationTrajectorySummary,
    GroundingSummary,
    Id,
    MethodContextSnapshot,
    MethodStateSourceRef,
    MethodStateSummary,
    PracticeLoopSummary,
    PsychologicalFunction,
    QuestioningPreferenceSummary,
    RelationalFieldSummary,
    TypologyMethodStateSummary,
)
from .in_memory_bucket import UserCirculatioBucket
from .in_memory_projection_shared import _is_within_window, _parse_datetime

QuestionStyle = Literal[
    "body_first",
    "image_first",
    "relational_first",
    "choice_based",
    "open_association",
]
ActivationPattern = Literal["low", "moderate", "high", "overwhelming", "mixed", "unknown"]
ContainmentStatus = Literal["steady", "strained", "thin", "unknown"]
GroundingRecommendation = Literal["clear_for_depth", "pace_gently", "grounding_first"]
ReflectiveCapacity = Literal["steady", "fragile", "unknown"]
AgencyTone = Literal["available", "strained", "collapsed", "unknown"]
SymbolicContact = Literal["available", "too_intense", "thin", "unknown"]
CurrentRelation = Literal["aligned", "curious", "conflicted", "avoidant", "unknown"]
AgencyTrend = Literal["expanding", "contracting", "mixed", "unknown"]
RelationshipContact = Literal["available", "thin", "isolated", "unknown"]
Spaciousness = Literal["spacious", "constricted", "mixed", "unknown"]
QuestionDepthPacing = Literal["direct", "gentle", "one_step", "unknown"]


class _GroundingSignalBundle(TypedDict):
    activationPattern: ActivationPattern
    anchorRecommendation: GroundingRecommendation | None
    wellbeingGrounding: Literal["steady", "strained", "unknown"]
    supportSignals: list[str]
    strainSignals: list[str]
    outerSupportSignals: list[str]
    outerStrainSignals: list[str]
    sourceRecordRefs: list[MethodStateSourceRef]
    evidenceIds: list[Id]


def build_recent_dream_dynamics_locked(
    bucket: UserCirculatioBucket,
    *,
    user_id: Id,
    window_start: str,
    window_end: str,
) -> list[DreamDynamicsSummary]:
    start_dt = _parse_datetime(window_start)
    end_dt = _parse_datetime(window_end)
    items: list[DreamDynamicsSummary] = []
    for material in bucket.materials.values():
        if (
            material.get("status") == "deleted"
            or material.get("userId") != user_id
            or material.get("materialType") != "dream"
        ):
            continue
        dream_structure = material.get("dreamStructure")
        if not isinstance(dream_structure, dict):
            continue
        dynamics = dream_structure.get("methodDynamics")
        if not isinstance(dynamics, list):
            continue
        for item in dynamics:
            if not isinstance(item, dict):
                continue
            observed_at = str(item.get("observedAt") or item.get("createdAt") or "").strip()
            if not observed_at:
                continue
            if not _is_within_window(_parse_datetime(observed_at), start_dt, end_dt):
                continue
            ego_stance = _clean_text(item.get("egoStance"))
            action_summary = _clean_text(item.get("actionSummary"))
            if not ego_stance or not action_summary:
                continue
            summary: DreamDynamicsSummary = {
                "materialId": material["id"],
                "observedAt": observed_at,
                "egoStance": ego_stance,
                "actionSummary": action_summary,
                "evidenceIds": _string_ids(item.get("evidenceIds")),
            }
            lysis_summary = _clean_text(item.get("lysisSummary"))
            if lysis_summary:
                summary["lysisSummary"] = lysis_summary
            items.append(summary)
    items.sort(key=lambda item: item["observedAt"], reverse=True)
    return items[:5]


def build_clarification_state_summary_locked(
    bucket: UserCirculatioBucket,
    *,
    user_id: Id,
    material_id: Id | None = None,
) -> ClarificationStateSummary | None:
    pending_prompts: list[ClarificationPromptSummary] = []
    recently_answered: list[ClarificationAnswerSummary] = []
    recently_unrouted: list[ClarificationAnswerSummary] = []
    avoid_repeat_question_keys: list[str] = []

    prompts = [
        item
        for item in bucket.clarification_prompts.values()
        if item.get("userId") == user_id and item.get("status") != "deleted"
    ]
    answers = [
        item
        for item in bucket.clarification_answers.values()
        if item.get("userId") == user_id and item.get("deletedAt") is None
    ]
    if material_id is not None:
        prompts = [item for item in prompts if item.get("materialId") in {None, material_id}]
        answers = [item for item in answers if item.get("materialId") in {None, material_id}]

    prompts.sort(
        key=lambda item: str(item.get("updatedAt") or item.get("createdAt") or ""),
        reverse=True,
    )
    answers.sort(
        key=lambda item: str(item.get("updatedAt") or item.get("createdAt") or ""),
        reverse=True,
    )

    for prompt in prompts[:12]:
        question_text = _clean_text(prompt.get("questionText"))
        if not question_text:
            continue
        question_key = _clean_text(prompt.get("questionKey"))
        if prompt.get("status") == "pending":
            pending_prompt: ClarificationPromptSummary = {
                "id": prompt["id"],
                "questionText": question_text,
                "intent": prompt["intent"],
                "captureTarget": prompt["captureTarget"],
                "expectedAnswerKind": prompt["expectedAnswerKind"],
                "status": str(prompt.get("status") or "pending"),
                "createdAt": str(prompt.get("createdAt") or now_iso()),
                "updatedAt": str(prompt.get("updatedAt") or prompt.get("createdAt") or now_iso()),
            }
            if prompt.get("materialId"):
                pending_prompt["materialId"] = str(prompt["materialId"])
            if prompt.get("runId"):
                pending_prompt["runId"] = str(prompt["runId"])
            if question_key:
                pending_prompt["questionKey"] = question_key
                avoid_repeat_question_keys.append(question_key)
            supporting_refs = _string_values(prompt.get("supportingRefs"))
            if supporting_refs:
                pending_prompt["supportingRefs"] = supporting_refs
            pending_prompts.append(pending_prompt)
            continue
        if question_key:
            avoid_repeat_question_keys.append(question_key)

    for answer in answers[:12]:
        summary: ClarificationAnswerSummary = {
            "id": answer["id"],
            "captureTarget": answer["captureTarget"],
            "routingStatus": str(answer.get("routingStatus") or "unrouted"),
            "createdRecordRefs": [
                {"recordType": str(ref.get("recordType") or ""), "id": str(ref.get("id") or "")}
                for ref in answer["createdRecordRefs"]
                if ref.get("recordType") and ref.get("id")
            ],
            "createdAt": str(answer.get("createdAt") or now_iso()),
            "updatedAt": str(answer.get("updatedAt") or answer.get("createdAt") or now_iso()),
        }
        if answer.get("promptId"):
            summary["promptId"] = str(answer["promptId"])
        if answer.get("materialId"):
            summary["materialId"] = str(answer["materialId"])
        if answer.get("runId"):
            summary["runId"] = str(answer["runId"])
        errors = _string_values(answer.get("validationErrors"))
        if errors:
            summary["validationErrors"] = errors
        routing_status = summary["routingStatus"]
        if routing_status == "routed":
            recently_answered.append(summary)
        elif routing_status in {"unrouted", "needs_review"}:
            recently_unrouted.append(summary)

    if not pending_prompts and not recently_answered and not recently_unrouted:
        return None
    return {
        "pendingPrompts": pending_prompts[:5],
        "recentlyAnswered": recently_answered[:5],
        "recentlyUnrouted": recently_unrouted[:5],
        "avoidRepeatQuestionKeys": list(dict.fromkeys(avoid_repeat_question_keys))[:10],
    }


def build_method_state_summary_locked(
    bucket: UserCirculatioBucket,
    *,
    user_id: Id,
    window_start: str,
    window_end: str,
    snapshot: MethodContextSnapshot,
) -> MethodStateSummary | None:
    generated_at = now_iso()
    result: MethodStateSummary = {"generatedAt": generated_at}

    grounding = _derive_grounding_summary(snapshot)
    if grounding is not None:
        result["grounding"] = grounding

    containment = _derive_containment_summary(snapshot, grounding=grounding)
    if containment is not None:
        result["containment"] = containment

    ego_capacity = _derive_ego_capacity_summary(
        snapshot,
        grounding=grounding,
        containment=containment,
    )
    if ego_capacity is not None:
        result["egoCapacity"] = ego_capacity

    ego_relation = _derive_ego_relation_trajectory_summary(snapshot)
    if ego_relation is not None:
        result["egoRelationTrajectory"] = ego_relation

    relational_field = _derive_relational_field_summary(snapshot)
    if relational_field is not None:
        result["relationalField"] = relational_field

    compensation_tendencies = _derive_compensation_tendencies(snapshot)
    if compensation_tendencies:
        result["compensationTendencies"] = compensation_tendencies[:3]

    active_goal_tension = _derive_active_goal_tension_summary(snapshot)
    if active_goal_tension is not None:
        result["activeGoalTension"] = active_goal_tension

    practice_loop = _derive_practice_loop_summary(snapshot)
    if practice_loop is not None:
        result["practiceLoop"] = practice_loop

    typology_method_state = _derive_typology_method_state_summary(
        bucket,
        user_id=user_id,
        snapshot=snapshot,
    )
    if typology_method_state is not None:
        result["typologyMethodState"] = typology_method_state

    questioning_preference = _derive_questioning_preference_summary(
        bucket,
        user_id=user_id,
        window_start=window_start,
        window_end=window_end,
    )
    if questioning_preference is not None:
        result["questioningPreference"] = questioning_preference

    return result if len(result) > 1 else None


def _derive_grounding_summary(snapshot: MethodContextSnapshot) -> GroundingSummary | None:
    signals = _collect_grounding_signal_bundle(snapshot)
    support_signals = _dedupe(signals["supportSignals"])[:4]
    strain_signals = _dedupe(signals["strainSignals"])[:4]
    source_refs = _dedupe_refs(signals["sourceRecordRefs"])[:5]
    evidence_ids = _dedupe_ids(signals["evidenceIds"])
    if (
        signals["activationPattern"] == "unknown"
        and not support_signals
        and not strain_signals
        and not source_refs
        and not evidence_ids
    ):
        return None

    recommendation: GroundingRecommendation = "clear_for_depth"
    if (
        signals["anchorRecommendation"] == "grounding_first"
        or signals["activationPattern"] == "overwhelming"
        or _count_matching_signal(strain_signals, "Recent practice outcomes increased activation.") >= 1
    ):
        recommendation = "grounding_first"
    elif (
        signals["anchorRecommendation"] == "pace_gently"
        or signals["wellbeingGrounding"] == "strained"
        or signals["activationPattern"] in {"high", "mixed"}
        or _count_matching_signal(strain_signals, "Recent practice outcomes increased activation.") >= 1
    ):
        recommendation = "pace_gently"

    return {
        "recommendation": recommendation,
        "activationPattern": signals["activationPattern"],
        "supportSignals": support_signals,
        "strainSignals": strain_signals,
        "sourceRecordRefs": source_refs,
        "evidenceIds": evidence_ids,
        "confidence": _confidence_from_signal_count(len(support_signals) + len(strain_signals)),
        "updatedAt": now_iso(),
    }


def _derive_containment_summary(
    snapshot: MethodContextSnapshot,
    *,
    grounding: GroundingSummary | None,
) -> ContainmentSummary | None:
    signals = _collect_grounding_signal_bundle(snapshot)
    support_signals = _dedupe([*signals["supportSignals"], *signals["outerSupportSignals"]])[:4]
    strain_signals = _dedupe([*signals["strainSignals"], *signals["outerStrainSignals"]])[:4]
    source_refs = _dedupe_refs(signals["sourceRecordRefs"])[:5]
    evidence_ids = _dedupe_ids(signals["evidenceIds"])
    if not support_signals and not strain_signals and not source_refs and not evidence_ids:
        return None

    status: ContainmentStatus = "unknown"
    recommendation = (
        str(grounding.get("recommendation") or "").strip() if isinstance(grounding, dict) else ""
    )
    if recommendation == "grounding_first":
        status = "thin"
    elif recommendation == "pace_gently":
        status = "strained"
    elif recommendation == "clear_for_depth":
        status = "steady"

    return {
        "status": status,
        "supportSignals": support_signals,
        "strainSignals": strain_signals,
        "sourceRecordRefs": source_refs,
        "evidenceIds": evidence_ids,
        "confidence": _confidence_from_signal_count(len(support_signals) + len(strain_signals)),
        "updatedAt": now_iso(),
    }


def _collect_grounding_signal_bundle(snapshot: MethodContextSnapshot) -> _GroundingSignalBundle:
    body_states = snapshot.get("recentBodyStates", [])
    activations = [str(item.get("activation") or "unknown") for item in body_states]
    activation_pattern = _dominant_activation_pattern(activations)

    support_signals: list[str] = []
    strain_signals: list[str] = []
    outer_support_signals: list[str] = []
    outer_strain_signals: list[str] = []
    source_refs: list[MethodStateSourceRef] = []
    evidence_ids: list[Id] = []

    reality_anchor = snapshot.get("individuationContext", {}).get("realityAnchors")
    latest_anchor = reality_anchor if isinstance(reality_anchor, dict) else None
    anchor_grounding = (
        _normalize_grounding_recommendation(latest_anchor.get("groundingRecommendation"))
        if latest_anchor
        else None
    )
    if latest_anchor and latest_anchor.get("id"):
        source_refs.append(
            {"recordType": "RealityAnchorSummary", "recordId": str(latest_anchor["id"])}
        )
        evidence_ids.extend(_string_ids(latest_anchor.get("evidenceIds")))
    if anchor_grounding == "grounding_first":
        strain_signals.append("Recent reality anchors ask for grounding first.")
    elif anchor_grounding == "clear_for_depth":
        support_signals.append("Reality anchors suggest depth work can be held.")
    elif anchor_grounding == "pace_gently":
        strain_signals.append("Reality anchors suggest pacing gently.")
    if latest_anchor:
        work_continuity = str(latest_anchor.get("workDailyLifeContinuity") or "").strip()
        sleep_regulation = str(latest_anchor.get("sleepBodyRegulation") or "").strip()
        relationship_contact = str(latest_anchor.get("relationshipContact") or "").strip()
        reflective_capacity = str(latest_anchor.get("reflectiveCapacity") or "").strip()
        if work_continuity == "stable":
            outer_support_signals.append("Work and daily life continuity remain available.")
        elif work_continuity == "strained":
            outer_strain_signals.append("Work and daily life continuity are under strain.")
        if sleep_regulation == "stable":
            outer_support_signals.append("Sleep and body regulation still offer support.")
        elif sleep_regulation == "strained":
            outer_strain_signals.append("Sleep and body regulation look strained.")
        if relationship_contact == "available":
            outer_support_signals.append("Ordinary relationship contact remains available.")
        elif relationship_contact == "thin":
            outer_strain_signals.append("Ordinary relationship contact looks thin.")
        if reflective_capacity == "steady":
            outer_support_signals.append("Reflective capacity still looks steady.")
        elif reflective_capacity == "fragile":
            outer_strain_signals.append("Reflective capacity looks fragile right now.")

    wellbeing = snapshot.get("livingMythContext", {}).get("latestSymbolicWellbeing")
    wellbeing_grounding: Literal["steady", "strained", "unknown"] = "unknown"
    if isinstance(wellbeing, dict) and wellbeing.get("id"):
        source_refs.append(
            {"recordType": "SymbolicWellbeingSnapshot", "recordId": str(wellbeing["id"])}
        )
        evidence_ids.extend(_string_ids(wellbeing.get("evidenceIds")))
        wellbeing_grounding = _normalize_wellbeing_grounding(wellbeing.get("groundingCapacity"))
        if wellbeing_grounding == "steady":
            support_signals.append("Symbolic wellbeing still shows workable grounding.")
        elif wellbeing_grounding == "strained":
            strain_signals.append("Symbolic wellbeing shows grounding strain.")
        support_needed = _clean_text(wellbeing.get("supportNeeded"))
        if support_needed:
            strain_signals.append(f"Support needed: {support_needed}")

    for body_state in body_states[:5]:
        if body_state.get("id"):
            source_refs.append({"recordType": "BodyState", "recordId": str(body_state["id"])})
        if body_state.get("activation") == "overwhelming":
            strain_signals.append("Recent body activation reached overwhelming intensity.")
        elif body_state.get("activation") == "high":
            strain_signals.append("Recent body activation has stayed high.")
        elif body_state.get("activation") in {"low", "moderate"}:
            support_signals.append("Recent body activation stayed within a workable range.")

    practices = snapshot.get("recentPracticeSessions", [])
    worsened = 0
    improved = 0
    for practice in practices:
        before = _activation_score(practice.get("activationBefore"))
        after = _activation_score(practice.get("activationAfter"))
        if before is None or after is None:
            continue
        if after > before:
            worsened += 1
        elif after < before:
            improved += 1
    if worsened:
        strain_signals.append("Recent practice outcomes increased activation.")
    if improved:
        support_signals.append("Recent practice outcomes helped activation settle.")

    return {
        "activationPattern": activation_pattern,
        "anchorRecommendation": anchor_grounding,
        "wellbeingGrounding": wellbeing_grounding,
        "supportSignals": support_signals,
        "strainSignals": strain_signals,
        "outerSupportSignals": outer_support_signals,
        "outerStrainSignals": outer_strain_signals,
        "sourceRecordRefs": source_refs,
        "evidenceIds": evidence_ids,
    }


def _derive_ego_capacity_summary(
    snapshot: MethodContextSnapshot,
    *,
    grounding: GroundingSummary | None,
    containment: ContainmentSummary | None,
) -> EgoCapacitySummary | None:
    reasons: list[str] = []
    source_refs: list[MethodStateSourceRef] = []
    evidence_ids: list[Id] = []

    reflective_capacity: ReflectiveCapacity = "unknown"
    self_orientation = snapshot.get("individuationContext", {}).get("selfOrientation")
    if isinstance(self_orientation, dict):
        if self_orientation.get("id"):
            source_refs.append(
                {"recordType": "SelfOrientationSnapshot", "recordId": str(self_orientation["id"])}
            )
            evidence_ids.extend(_string_ids(self_orientation.get("evidenceIds")))
        ego_relation = str(self_orientation.get("egoRelation") or "").strip()
        if ego_relation in {"aligned", "curious"}:
            reflective_capacity = "steady"
            reasons.append("Self-orientation remains reflective enough for symbolic contact.")
        elif ego_relation in {"conflicted", "avoidant"}:
            reflective_capacity = "fragile"
            reasons.append("Self-orientation shows conflict or avoidance around the material.")

    wellbeing = snapshot.get("livingMythContext", {}).get("latestSymbolicWellbeing")
    agency_tone: AgencyTone = "unknown"
    symbolic_contact: SymbolicContact = "unknown"
    if isinstance(wellbeing, dict):
        if wellbeing.get("id"):
            source_refs.append(
                {"recordType": "SymbolicWellbeingSnapshot", "recordId": str(wellbeing["id"])}
            )
            evidence_ids.extend(_string_ids(wellbeing.get("evidenceIds")))
        agency_tone = _normalize_agency_tone(wellbeing.get("agencyTone"))
        symbolic_contact = _normalize_symbolic_contact(wellbeing.get("symbolicLiveliness"))

    if reflective_capacity == "unknown":
        grounding_recommendation = (
            str(grounding.get("recommendation") or "").strip() if isinstance(grounding, dict) else ""
        )
        containment_status = (
            str(containment.get("status") or "").strip() if isinstance(containment, dict) else ""
        )
        if grounding_recommendation == "grounding_first" or containment_status == "thin":
            reflective_capacity = "fragile"
            reasons.append("Grounding needs to lead before deeper symbolic contact.")
            if isinstance(grounding, dict):
                source_refs.extend(grounding.get("sourceRecordRefs", []))
                evidence_ids.extend(_string_ids(grounding.get("evidenceIds")))
            if isinstance(containment, dict):
                source_refs.extend(containment.get("sourceRecordRefs", []))
                evidence_ids.extend(_string_ids(containment.get("evidenceIds")))

    if not reasons and symbolic_contact != "unknown":
        reasons.append("Recent symbolic wellbeing offers a bounded signal of symbolic contact.")

    return {
        "reflectiveCapacity": reflective_capacity,
        "agencyTone": agency_tone,
        "symbolicContact": symbolic_contact,
        "confidence": _confidence_from_signal_count(len(reasons) + len(source_refs)),
        "reasons": reasons[:4],
        "sourceRecordRefs": _dedupe_refs(source_refs)[:5],
        "evidenceIds": _dedupe_ids(evidence_ids),
        "updatedAt": now_iso(),
    }


def _derive_ego_relation_trajectory_summary(
    snapshot: MethodContextSnapshot,
) -> EgoRelationTrajectorySummary | None:
    current_relation: CurrentRelation = "unknown"
    agency_trend: AgencyTrend = "unknown"
    movement_language: list[str] = []
    recent_ego_stances: list[str] = []
    source_refs: list[MethodStateSourceRef] = []
    evidence_ids: list[Id] = []

    self_orientation = snapshot.get("individuationContext", {}).get("selfOrientation")
    if isinstance(self_orientation, dict):
        current_relation = _normalize_current_relation(self_orientation.get("egoRelation"))
        movement_language = _string_values(self_orientation.get("movementLanguage"))[:5]
        if self_orientation.get("id"):
            source_refs.append(
                {"recordType": "SelfOrientationSnapshot", "recordId": str(self_orientation["id"])}
            )
            evidence_ids.extend(_string_ids(self_orientation.get("evidenceIds")))

    for dream_series in snapshot.get("activeDreamSeries", [])[:3]:
        ego_trajectory = _clean_text(dream_series.get("egoTrajectory"))
        if dream_series.get("id"):
            source_refs.append({"recordType": "DreamSeries", "recordId": str(dream_series["id"])})
        if ego_trajectory:
            recent_ego_stances.append(ego_trajectory)
            if any(token in ego_trajectory.lower() for token in ("expand", "approach", "engage")):
                agency_trend = "expanding"
            elif any(
                token in ego_trajectory.lower()
                for token in ("contract", "flee", "freeze", "withdraw")
            ):
                agency_trend = "contracting"

    for dream_dynamic in snapshot.get("recentDreamDynamics", [])[:3]:
        ego_stance = _clean_text(dream_dynamic.get("egoStance"))
        if ego_stance:
            recent_ego_stances.append(ego_stance)
            if any(token in ego_stance.lower() for token in ("approach", "speak", "stay")):
                agency_trend = "expanding" if agency_trend == "unknown" else agency_trend
            elif any(token in ego_stance.lower() for token in ("run", "hide", "freeze")):
                agency_trend = "contracting"
        if dream_dynamic.get("materialId"):
            source_refs.append(
                {"recordType": "Material", "recordId": str(dream_dynamic["materialId"])}
            )
        evidence_ids.extend(_string_ids(dream_dynamic.get("evidenceIds")))

    if agency_trend == "unknown" and len(set(recent_ego_stances)) > 1:
        agency_trend = "mixed"

    return {
        "currentRelation": current_relation,
        "agencyTrend": agency_trend,
        "movementLanguage": _dedupe(movement_language)[:5],
        "recentEgoStances": _dedupe(recent_ego_stances)[:5],
        "confidence": _confidence_from_signal_count(len(source_refs)),
        "sourceRecordRefs": _dedupe_refs(source_refs)[:5],
        "evidenceIds": _dedupe_ids(evidence_ids),
        "updatedAt": now_iso(),
    }


def _derive_relational_field_summary(
    snapshot: MethodContextSnapshot,
) -> RelationalFieldSummary | None:
    reasons: list[str] = []
    source_refs: list[MethodStateSourceRef] = []
    evidence_ids: list[Id] = []
    recurring_affect: list[str] = []
    active_scene_ids: list[Id] = []

    relationship_contact: RelationshipContact = "unknown"
    reality_anchor = snapshot.get("individuationContext", {}).get("realityAnchors")
    latest_anchor = reality_anchor if isinstance(reality_anchor, dict) else None
    if isinstance(latest_anchor, dict):
        relationship_contact = _normalize_relationship_contact(
            latest_anchor.get("relationshipContact")
        )
        if latest_anchor.get("id"):
            source_refs.append(
                {"recordType": "RealityAnchorSummary", "recordId": str(latest_anchor["id"])}
            )
            evidence_ids.extend(_string_ids(latest_anchor.get("evidenceIds")))

    spaciousness: Spaciousness = "unknown"
    support_needed = ""
    wellbeing = snapshot.get("livingMythContext", {}).get("latestSymbolicWellbeing")
    if isinstance(wellbeing, dict):
        spaciousness = _normalize_spaciousness(wellbeing.get("relationalSpaciousness"))
        support_needed = _clean_text(wellbeing.get("supportNeeded"))
        if wellbeing.get("id"):
            source_refs.append(
                {"recordType": "SymbolicWellbeingSnapshot", "recordId": str(wellbeing["id"])}
            )
            evidence_ids.extend(_string_ids(wellbeing.get("evidenceIds")))

    scenes = snapshot.get("individuationContext", {}).get("relationalScenes", [])
    for item in scenes[:5]:
        if item.get("id"):
            active_scene_ids.append(str(item["id"]))
            source_refs.append({"recordType": "RelationalScene", "recordId": str(item["id"])})
            evidence_ids.extend(_string_ids(item.get("evidenceIds")))
        recurring_affect.extend(_string_values(item.get("recurringAffect")))

    consent_status = {
        str(item.get("scope")): str(item.get("status"))
        for item in snapshot.get("consentPreferences", [])
        if isinstance(item, dict) and item.get("scope")
    }
    projection_allowed = consent_status.get("projection_language") == "allow"
    if relationship_contact in {"thin", "isolated"}:
        reasons.append("Relational contact currently looks thin.")
    if spaciousness == "constricted":
        reasons.append("Relational spaciousness looks constricted.")
    if not projection_allowed:
        reasons.append("Projection language is still consent-gated.")
    lowered_relational_text = " ".join([*recurring_affect, support_needed]).lower()
    isolation_risk: Literal["low", "moderate", "high", "unknown"] = "unknown"
    if relationship_contact == "isolated" or (
        relationship_contact == "thin" and spaciousness == "constricted"
    ):
        isolation_risk = "high"
    elif relationship_contact == "thin" or spaciousness == "constricted":
        isolation_risk = "moderate"
    elif relationship_contact == "available" and spaciousness == "spacious":
        isolation_risk = "low"
    dependency_pressure: Literal["low", "moderate", "high", "unknown"] = "unknown"
    if any(
        token in lowered_relational_text
        for token in ("pressure", "cling", "dependent", "obligation", "stuck", "desperate")
    ):
        dependency_pressure = "high"
    elif support_needed or relationship_contact in {"thin", "isolated"}:
        dependency_pressure = "moderate"
    elif relationship_contact == "available" and spaciousness == "spacious":
        dependency_pressure = "low"
    support_direction: Literal[
        "increase_contact", "protect_space", "hold_contact_lightly", "stabilize_field"
    ] = "stabilize_field"
    if isolation_risk == "high":
        support_direction = "increase_contact"
        reasons.append("Start by strengthening ordinary contact and support.")
    elif spaciousness == "constricted":
        support_direction = "protect_space"
        reasons.append("Relational work should protect space before deepening.")
    elif relationship_contact == "available":
        support_direction = "hold_contact_lightly"
    if dependency_pressure == "high":
        reasons.append("Dependency pressure looks elevated in the recent relational field.")

    return {
        "relationshipContact": relationship_contact,
        "spaciousness": spaciousness,
        "isolationRisk": isolation_risk,
        "dependencyPressure": dependency_pressure,
        "supportDirection": support_direction,
        "recurringAffect": _dedupe(recurring_affect)[:5],
        "activeSceneIds": _dedupe_ids(active_scene_ids)[:5],
        "projectionLanguageAllowed": projection_allowed,
        "reasons": reasons[:4],
        "sourceRecordRefs": _dedupe_refs(source_refs)[:5],
        "evidenceIds": _dedupe_ids(evidence_ids),
        "confidence": _confidence_from_signal_count(len(source_refs)),
        "updatedAt": now_iso(),
    }


def _derive_active_goal_tension_summary(
    snapshot: MethodContextSnapshot,
) -> ActiveGoalTensionSummary | None:
    ranked_statuses = {"active": 0, "integrating": 1, "candidate": 2}
    candidate_tensions: list[tuple[int, dict[str, object]]] = []
    for index, raw_tension in enumerate(snapshot.get("goalTensions", [])[:5]):
        if not isinstance(raw_tension, dict):
            continue
        status = str(raw_tension.get("status") or "").strip()
        if status not in ranked_statuses:
            continue
        candidate_tensions.append((ranked_statuses[status] * 10 + index, raw_tension))
    for _, tension in sorted(candidate_tensions, key=lambda item: item[0]):
        if not isinstance(tension, dict):
            continue
        tension_id = _clean_text(tension.get("id"), limit=80)
        summary = _clean_text(tension.get("tensionSummary"))
        if not tension_id or not summary:
            continue
        polarity_labels = _string_values(tension.get("polarityLabels"))[:4]
        if len(polarity_labels) >= 2:
            balancing_direction = (
                f"Hold {polarity_labels[0]} and {polarity_labels[1]} together "
                "before choosing a side."
            )
        elif polarity_labels:
            balancing_direction = (
                f"Stay near the live tension around {polarity_labels[0]} before resolving it."
            )
        else:
            balancing_direction = "Stay with the active tension before forcing resolution."
        return {
            "goalTensionId": tension_id,
            "linkedGoalIds": _string_ids(tension.get("goalIds")),
            "summary": summary,
            "polarityLabels": polarity_labels,
            "balancingDirection": balancing_direction,
            "evidenceIds": _string_ids(tension.get("evidenceIds")),
            "updatedAt": now_iso(),
        }
    return None


def _derive_practice_loop_summary(
    snapshot: MethodContextSnapshot,
) -> PracticeLoopSummary | None:
    profile = snapshot.get("adaptationProfile")
    explicit_practice: dict[str, object] = {}
    learned_practice: dict[str, object] = {}
    practice_stats: dict[str, object] = {}
    if isinstance(profile, dict):
        explicit = profile.get("explicitPreferences")
        learned = profile.get("learnedSignals")
        if isinstance(explicit, dict):
            scope = explicit.get("practice")
            if isinstance(scope, dict):
                explicit_practice = scope
        if isinstance(learned, dict):
            scope = learned.get("practicePolicy")
            if isinstance(scope, dict):
                learned_practice = scope
            stats = learned.get("practiceStats")
            if isinstance(stats, dict):
                practice_stats = stats

    stats_preferred, stats_avoided, stats_reasons = _practice_modalities_from_stats(practice_stats)

    preferred = _dedupe(
        [
            *_string_values(explicit_practice.get("preferredModalities")),
            *_string_values(learned_practice.get("preferredModalities")),
            *stats_preferred,
        ]
    )[:5]
    avoided = [
        item
        for item in _dedupe(
            [
                *_string_values(explicit_practice.get("avoidedModalities")),
                *_string_values(learned_practice.get("avoidedModalities")),
                *stats_avoided,
            ]
        )[:5]
        if item not in preferred
    ]
    max_duration = explicit_practice.get("maxDurationMinutes")
    if not isinstance(max_duration, int) or max_duration <= 0:
        learned_duration = learned_practice.get("maxDurationMinutes")
        max_duration = (
            learned_duration if isinstance(learned_duration, int) and learned_duration > 0 else None
        )

    recent_completed_types = [
        str(item.get("practiceType") or "")
        for item in snapshot.get("recentPracticeSessions", [])
        if isinstance(item, dict)
        and item.get("status") == "completed"
        and str(item.get("practiceType") or "").strip()
    ][:5]
    recent_skipped_types = [
        str(item.get("practiceType") or "")
        for item in snapshot.get("recentPracticeSessions", [])
        if isinstance(item, dict)
        and item.get("status") == "skipped"
        and str(item.get("practiceType") or "").strip()
    ][:5]

    improved = 0
    worsened = 0
    for item in snapshot.get("recentPracticeSessions", [])[:5]:
        if not isinstance(item, dict):
            continue
        before = _activation_score(item.get("activationBefore"))
        after = _activation_score(item.get("activationAfter"))
        if before is None or after is None:
            continue
        if after < before:
            improved += 1
        elif after > before:
            worsened += 1
    recent_outcome_trend: Literal["settling", "activating", "mixed", "unknown"] = "unknown"
    if improved and not worsened:
        recent_outcome_trend = "settling"
    elif worsened and not improved:
        recent_outcome_trend = "activating"
    elif improved or worsened:
        recent_outcome_trend = "mixed"
    recommended_intensity: Literal["low", "moderate", "unknown"] = "unknown"
    if recent_outcome_trend == "activating" or len(recent_skipped_types) > len(
        recent_completed_types
    ):
        recommended_intensity = "low"
    elif recent_outcome_trend == "settling" or recent_completed_types:
        recommended_intensity = "moderate"

    reasons: list[str] = []
    if preferred:
        reasons.append("Recent practice feedback names preferred modalities.")
    if avoided:
        reasons.append("Recent practice feedback names avoided modalities.")
    reasons.extend(stats_reasons)
    if recent_outcome_trend == "settling":
        reasons.append("Recent practice outcomes often help activation settle.")
    elif recent_outcome_trend == "activating":
        reasons.append("Recent practice outcomes often raise activation; keep intensity low.")
    elif recent_outcome_trend == "mixed":
        reasons.append("Recent practice outcomes are mixed and need pacing.")
    if isinstance(max_duration, int):
        reasons.append(f"Practice duration should stay within about {max_duration} minutes.")

    has_preference_signal = bool(preferred or avoided or isinstance(max_duration, int))
    has_outcome_signal = bool(
        recent_completed_types or recent_skipped_types or recent_outcome_trend != "unknown"
    )
    if not has_preference_signal and not has_outcome_signal:
        return None
    source: Literal["adaptation_profile", "practice_outcomes", "mixed"] = "adaptation_profile"
    if has_preference_signal and has_outcome_signal:
        source = "mixed"
    elif has_outcome_signal:
        source = "practice_outcomes"
    summary: PracticeLoopSummary = {
        "preferredModalities": preferred,
        "avoidedModalities": avoided,
        "recentCompletedTypes": recent_completed_types,
        "recentSkippedTypes": recent_skipped_types,
        "recentOutcomeTrend": recent_outcome_trend,
        "recommendedIntensity": recommended_intensity,
        "reasons": _dedupe(reasons)[:4],
        "source": source,
        "updatedAt": now_iso(),
    }
    if isinstance(max_duration, int):
        summary["maxDurationMinutes"] = max_duration
    return summary


def _derive_compensation_tendencies(
    snapshot: MethodContextSnapshot,
) -> list[CompensationTendencySummary]:
    items: list[CompensationTendencySummary] = []
    conscious_attitude = snapshot.get("consciousAttitude")
    if isinstance(conscious_attitude, dict):
        active_conflicts = _string_values(conscious_attitude.get("activeConflicts"))
        avoided_themes = _string_values(conscious_attitude.get("avoidedThemes"))
        if active_conflicts or avoided_themes:
            conscious_pole = active_conflicts[0] if active_conflicts else ""
            compensating_pole = avoided_themes[0] if avoided_themes else ""
            pattern_summary = (
                f"Current stance circles around '{conscious_pole or 'a named conflict'}' "
                f"while '{compensating_pole or 'another theme'}' stays more avoided."
            )
            items.append(
                {
                    "status": "hypothesis_available"
                    if conscious_pole and compensating_pole
                    else "signals_only",
                    "consciousPole": conscious_pole,
                    "compensatingPole": compensating_pole,
                    "patternSummary": pattern_summary,
                    "confidence": "medium" if conscious_pole and compensating_pole else "low",
                    "evidenceIds": _string_ids(conscious_attitude.get("evidenceIds")),
                    "sourceRecordRefs": [
                        {
                            "recordType": "ConsciousAttitudeSnapshot",
                            "recordId": str(conscious_attitude["id"]),
                        }
                    ]
                    if conscious_attitude.get("id")
                    else [],
                    "counterevidenceIds": [],
                    "userTestPrompt": (
                        "Where do you notice the less-favored pole showing up anyway, "
                        "even if only in a small or indirect way?"
                    ),
                    "normalizedClaimKey": normalize_claim_key(
                        "compensation_tendency", pattern_summary
                    ),
                    "approvalRequired": True,
                    "updatedAt": now_iso(),
                }
            )

    for tension in snapshot.get("goalTensions", [])[:2]:
        polarity_labels = _string_values(tension.get("polarityLabels"))
        tension_summary = _clean_text(tension.get("tensionSummary"))
        if not tension_summary:
            continue
        conscious_pole = polarity_labels[0] if polarity_labels else ""
        compensating_pole = polarity_labels[1] if len(polarity_labels) > 1 else ""
        items.append(
            {
                "status": "signals_only",
                "consciousPole": conscious_pole,
                "compensatingPole": compensating_pole,
                "patternSummary": tension_summary,
                "confidence": "low",
                "evidenceIds": _string_ids(tension.get("evidenceIds")),
                "sourceRecordRefs": [{"recordType": "GoalTension", "recordId": str(tension["id"])}]
                if tension.get("id")
                else [],
                "counterevidenceIds": [],
                "userTestPrompt": (
                    "What happens if you let each side of this tension speak in its own words?"
                ),
                "normalizedClaimKey": normalize_claim_key(
                    "compensation_tendency",
                    " ".join([*polarity_labels[:2], tension_summary]),
                ),
                "approvalRequired": True,
                "updatedAt": now_iso(),
            }
        )

    deduped: list[CompensationTendencySummary] = []
    seen: set[str] = set()
    for item in items:
        key = item["normalizedClaimKey"]
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped[:3]


def _derive_questioning_preference_summary(
    bucket: UserCirculatioBucket,
    *,
    user_id: Id,
    window_start: str,
    window_end: str,
) -> QuestioningPreferenceSummary | None:
    start_dt = _parse_datetime(window_start)
    end_dt = _parse_datetime(window_end)
    profile = next(
        (
            item
            for item in sorted(
                bucket.adaptation_profiles.values(),
                key=lambda value: str(value.get("updatedAt") or value.get("createdAt") or ""),
                reverse=True,
            )
            if item.get("userId") == user_id and item.get("status") != "deleted"
        ),
        None,
    )
    learned: dict[str, object] = {}
    if isinstance(profile, dict):
        learned_candidate = profile.get("learnedSignals")
        if isinstance(learned_candidate, dict):
            learned = learned_candidate
    questioning_stats: dict[str, object] = {}
    questioning_stats_candidate = learned.get("questioningStats")
    if isinstance(questioning_stats_candidate, dict):
        questioning_stats = questioning_stats_candidate
    interpretation_stats: dict[str, object] = {}
    interpretation_stats_candidate = learned.get("interpretationStats")
    if isinstance(interpretation_stats_candidate, dict):
        interpretation_stats = interpretation_stats_candidate

    answers = [
        item
        for item in bucket.clarification_answers.values()
        if item.get("userId") == user_id
        and item.get("deletedAt") is None
        and _is_within_window(_parse_datetime(item.get("createdAt")), start_dt, end_dt)
    ]
    prompts = [
        item
        for item in bucket.clarification_prompts.values()
        if item.get("userId") == user_id
        and item.get("status") != "deleted"
        and _is_within_window(_parse_datetime(item.get("createdAt")), start_dt, end_dt)
    ]

    routed_counts: Counter[ClarificationCaptureTarget] = Counter(
        answer["captureTarget"] for answer in answers if answer.get("routingStatus") == "routed"
    )
    skipped_counts = Counter(
        prompt["intent"] for prompt in prompts if prompt.get("status") == "skipped"
    )
    unrouted_count = sum(
        1 for item in answers if item.get("routingStatus") in {"unrouted", "needs_review"}
    )
    routed_count = sum(1 for item in answers if item.get("routingStatus") == "routed")

    preferred_styles: list[QuestionStyle] = []
    avoided_styles: list[QuestionStyle] = []
    preferred_targets = [item for item, _ in routed_counts.most_common(3) if item]
    if routed_counts.get("body_state", 0) >= 1:
        preferred_styles.append("body_first")
    if routed_counts.get("relational_scene", 0) >= 1:
        preferred_styles.append("relational_first")
    if routed_counts.get("personal_amplification", 0) >= 1:
        preferred_styles.append("open_association")
    if routed_count and routed_count >= unrouted_count:
        preferred_styles.append("choice_based")
    if unrouted_count > routed_count:
        avoided_styles.append("open_association")
        preferred_styles.append("choice_based")
    if skipped_counts.get("body_signal", 0) >= 2:
        avoided_styles.append("body_first")
    if skipped_counts.get("relational_scene", 0) >= 2:
        avoided_styles.append("relational_first")

    preferred_styles = cast_question_styles(_dedupe(preferred_styles))[:4]
    avoided_styles = [
        item
        for item in cast_question_styles(_dedupe(avoided_styles))
        if item not in preferred_styles
    ][:4]

    depth_pacing: QuestionDepthPacing = "unknown"
    max_questions = 2
    recent_events = learned.get("recentEvents", [])
    if isinstance(recent_events, list):
        event_types = [
            str(item.get("type") or "") for item in recent_events if isinstance(item, dict)
        ]
        if "depth_pacing_corrected" in event_types or "clarification_skipped" in event_types:
            depth_pacing = "gentle"
            max_questions = 1
        if "question_style_preferred" in event_types:
            depth_pacing = "direct" if max_questions > 1 else "gentle"
    preferred_question_styles = cast_question_styles(
        _string_values(questioning_stats.get("preferredQuestionStyles"))
    )
    if preferred_question_styles:
        preferred_styles = cast_question_styles(
            _dedupe([*preferred_question_styles, *preferred_styles])
        )[:4]
    avoided_question_styles = cast_question_styles(
        _string_values(questioning_stats.get("avoidedQuestionStyles"))
    )
    if avoided_question_styles:
        avoided_styles = [
            item
            for item in cast_question_styles(_dedupe([*avoided_styles, *avoided_question_styles]))
            if item not in preferred_styles
        ][:4]
    interpreted_depth_pacing = _normalize_depth_pacing(interpretation_stats.get("depthPacing"))
    if interpreted_depth_pacing != "unknown":
        depth_pacing = interpreted_depth_pacing
        if interpreted_depth_pacing == "one_step":
            max_questions = 1

    if (
        not preferred_styles
        and not avoided_styles
        and not preferred_targets
        and depth_pacing == "unknown"
    ):
        return None
    summary: QuestioningPreferenceSummary = {
        "preferredQuestionStyles": list(preferred_styles),
        "avoidedQuestionStyles": [str(item) for item in avoided_styles],
        "preferredCaptureTargets": preferred_targets,
        "maxQuestionsPerTurn": max_questions,
        "depthPacing": depth_pacing,
        "answerFrictionSignals": (
            ["free_text_answers_often_remain_unrouted"] if unrouted_count > routed_count else []
        )[:4],
        "confidence": _confidence_from_signal_count(routed_count + unrouted_count),
        "source": "adaptation_profile",
        "updatedAt": str(profile.get("updatedAt") or now_iso()) if profile else now_iso(),
    }
    return summary


def _derive_typology_method_state_summary(
    bucket: UserCirculatioBucket,
    *,
    user_id: Id,
    snapshot: MethodContextSnapshot,
) -> TypologyMethodStateSummary | None:
    lenses = [
        item
        for item in bucket.typology_lenses.values()
        if item.get("userId") == user_id and item.get("status") != "deleted"
    ]
    if not lenses:
        return None
    active_lenses = [item for item in lenses if item.get("status") != "disconfirmed"]
    active_lens_ids = [str(item["id"]) for item in active_lenses][:5]
    feedback_signal_count = sum(
        1 for item in lenses if item.get("status") in {"user_refined", "disconfirmed"}
    )
    status: Literal["candidate_available", "signals_only"] = (
        "candidate_available" if active_lens_ids else "signals_only"
    )
    allowed_functions = {"thinking", "feeling", "sensation", "intuition"}
    active_functions = [
        cast(PsychologicalFunction, item)
        for item in _dedupe(
            [
                str(item.get("function") or "").strip()
                for item in active_lenses
                if item.get("function")
            ]
        )[:4]
        if item in allowed_functions
    ]
    balancing_function = next(
        (
            cast(PsychologicalFunction, str(item.get("function") or "").strip())
            for item in active_lenses
            if item.get("role") in {"inferior", "compensation_link"}
            and str(item.get("function") or "").strip() in allowed_functions
        ),
        None,
    )
    prompt_bias_map = {
        "sensation": "body_first",
        "intuition": "image_first",
        "feeling": "relational_first",
        "thinking": "reflection_first",
    }
    practice_bias_map = {
        "sensation": "sensation_grounding",
        "intuition": "image_tracking",
        "feeling": "value_discernment",
        "thinking": "pattern_noting",
    }
    bias_function = balancing_function or (active_functions[0] if active_functions else "")
    prompt_bias = cast(
        Literal["body_first", "image_first", "relational_first", "reflection_first", "neutral"],
        prompt_bias_map.get(bias_function, "neutral"),
    )
    practice_bias = cast(
        Literal[
            "sensation_grounding",
            "image_tracking",
            "value_discernment",
            "pattern_noting",
            "neutral",
        ],
        practice_bias_map.get(bias_function, "neutral"),
    )
    if practice_bias == "neutral":
        activation_levels = [
            _activation_score(item.get("activation"))
            for item in snapshot.get("recentBodyStates", [])
            if isinstance(item, dict)
        ]
        if any(level is not None and level >= 3 for level in activation_levels):
            practice_bias = "sensation_grounding"
    summary: TypologyMethodStateSummary = {
        "status": status,
        "activeLensIds": active_lens_ids,
        "feedbackSignalCount": feedback_signal_count,
        "activeFunctions": active_functions,
        "promptBias": prompt_bias,
        "practiceBias": practice_bias,
        "caution": "Typology remains tentative and should stay evidence-backed.",
        "confidence": "medium" if feedback_signal_count >= 2 else "low",
        "updatedAt": max(
            str(item.get("updatedAt") or item.get("createdAt") or now_iso()) for item in lenses
        ),
    }
    if balancing_function is not None:
        summary["balancingFunction"] = balancing_function
    return summary


def cast_question_styles(values: Sequence[str]) -> list[QuestionStyle]:
    allowed: tuple[QuestionStyle, ...] = (
        "body_first",
        "image_first",
        "relational_first",
        "choice_based",
        "open_association",
    )
    return [cast(QuestionStyle, item) for item in values if item in allowed]


def _dominant_activation_pattern(values: list[str]) -> ActivationPattern:
    filtered = [item for item in values if item]
    if not filtered:
        return "unknown"
    counts = Counter(filtered)
    top, count = counts.most_common(1)[0]
    if top == "high" and counts.get("overwhelming"):
        return "mixed"
    if len(counts) > 1 and count == 1:
        return "mixed"
    if top in {"low", "moderate", "high", "overwhelming"}:
        return cast(ActivationPattern, top)
    return "unknown"


def _activation_score(value: object) -> int | None:
    scores = {"low": 1, "moderate": 2, "high": 3}
    return scores.get(str(value or "").strip())


def _confidence_from_signal_count(count: int) -> Confidence:
    if count >= 4:
        return "high"
    if count >= 2:
        return "medium"
    return "low"


def _clean_text(value: object, *, limit: int = 220) -> str:
    text = " ".join(str(value or "").split())
    if not text:
        return ""
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _string_values(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [text for item in value if (text := _clean_text(item, limit=120))]


def _string_ids(value: object) -> list[Id]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _dedupe(values: Sequence[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def _dedupe_ids(values: list[Id]) -> list[Id]:
    return list(dict.fromkeys(value for value in values if value))


def _dedupe_refs(values: list[MethodStateSourceRef]) -> list[MethodStateSourceRef]:
    seen: set[tuple[str, str]] = set()
    deduped: list[MethodStateSourceRef] = []
    for item in values:
        record_type = str(item.get("recordType") or "")
        record_id = str(item.get("recordId") or "")
        if not record_type or not record_id:
            continue
        key = (record_type, record_id)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _normalize_current_relation(value: object) -> CurrentRelation:
    candidate = str(value or "").strip()
    if candidate in {"aligned", "curious", "conflicted", "avoidant"}:
        return cast(CurrentRelation, candidate)
    return "unknown"


def _normalize_relationship_contact(value: object) -> RelationshipContact:
    candidate = str(value or "").strip()
    if candidate in {"available", "thin", "isolated"}:
        return cast(RelationshipContact, candidate)
    return "unknown"


def _normalize_spaciousness(value: object) -> Spaciousness:
    candidate = str(value or "").strip().lower()
    if candidate in {"spacious", "constricted", "mixed"}:
        return cast(Spaciousness, candidate)
    if candidate in {"available", "open"}:
        return "spacious"
    if candidate:
        return "constricted"
    return "unknown"


def _normalize_agency_tone(value: object) -> AgencyTone:
    candidate = str(value or "").strip().lower()
    if candidate in {"available", "strained", "collapsed"}:
        return cast(AgencyTone, candidate)
    if candidate in {"open", "engaged"}:
        return "available"
    if candidate:
        return "strained"
    return "unknown"


def _normalize_symbolic_contact(value: object) -> SymbolicContact:
    candidate = str(value or "").strip().lower()
    if candidate in {"available", "too_intense", "thin"}:
        return cast(SymbolicContact, candidate)
    if "intense" in candidate:
        return "too_intense"
    if candidate:
        return "available"
    return "unknown"


def _normalize_depth_pacing(value: object) -> QuestionDepthPacing:
    candidate = str(value or "").strip()
    if candidate in {"direct", "gentle", "one_step"}:
        return cast(QuestionDepthPacing, candidate)
    return "unknown"
