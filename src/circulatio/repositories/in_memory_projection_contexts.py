from __future__ import annotations

from copy import deepcopy

from ..domain.reviews import DashboardSummary
from ..domain.types import (
    AnalysisPacketInput,
    CirculationSummaryInput,
    Id,
    LifeContextSnapshot,
    LivingMythReviewInput,
    MethodContextSnapshot,
    ThresholdReviewInput,
)
from .in_memory_bucket import UserCirculatioBucket
from .in_memory_projection_method_state import (
    build_clarification_state_summary_locked,
    build_method_state_summary_locked,
    build_recent_dream_dynamics_locked,
)
from .in_memory_projection_shared import (
    _is_within_window,
    _material_timestamp,
    _parse_datetime,
    _practice_timestamp,
)
from .in_memory_projection_summary import (
    _derive_body_state_changes,
    _derive_body_state_energy_summary,
    _derive_dream_series_changes,
    _derive_energy_summary,
    _derive_focus_summary,
    _derive_habit_summary,
    _derive_life_event_refs,
    _derive_longitudinal_signals,
    _derive_mental_state_summary,
    _derive_mood_summary,
    _derive_notable_changes,
    _latest_adaptation_profile,
    _project_adaptation_profile_summary,
    _project_amplification_prompt_summary,
    _project_body_state_summary,
    _project_collective_amplification_summary,
    _project_conscious_attitude_summary,
    _project_consent_preference_summary,
    _project_cultural_frame_summary,
    _project_dream_series_membership_summary,
    _project_dream_series_summary,
    _project_goal_summary,
    _project_goal_tension_summary,
    _project_journey_summary,
    _project_personal_amplification_summary,
    _project_practice_session_summary,
    active_patterns,
    active_symbols,
    build_memory_context_locked,
    project_practice_outcome,
)


def _window_overlaps(
    record_start: str | None,
    record_end: str | None,
    *,
    window_start: str,
    window_end: str,
) -> bool:
    start_value = record_start or record_end or window_start
    end_value = record_end or record_start or window_end
    return end_value >= window_start and start_value <= window_end


def _consent_status_map(snapshot: MethodContextSnapshot | None) -> dict[str, str]:
    if snapshot is None:
        return {}
    return {
        item["scope"]: item["status"]
        for item in snapshot.get("consentPreferences", [])
        if isinstance(item, dict) and item.get("scope") and item.get("status")
    }


def _build_individuation_context_summary(
    bucket: UserCirculatioBucket,
    *,
    user_id: Id,
    window_start: str,
    window_end: str,
    consent_status: dict[str, str],
) -> dict[str, object] | None:
    records = [
        item
        for item in bucket.individuation_records.values()
        if item.get("status") in {"active", "user_confirmed"}
        and item["userId"] == user_id
        and item.get("deletedAt") is None
        and _window_overlaps(
            item.get("windowStart"),
            item.get("windowEnd"),
            window_start=window_start,
            window_end=window_end,
        )
    ]
    records.sort(key=lambda item: item.get("updatedAt", item.get("createdAt", "")), reverse=True)
    result: dict[str, object] = {}
    for record in records:
        details = dict(record.get("details", {}))
        summary = {
            "id": record["id"],
            "label": record["label"],
            "summary": record["summary"],
            "confidence": record.get("confidence", "low"),
            "evidenceIds": list(record.get("evidenceIds", [])),
        }
        record_type = record["recordType"]
        if record_type == "reality_anchor_summary" and "realityAnchors" not in result:
            result["realityAnchors"] = {
                **summary,
                "anchorSummary": details.get("anchorSummary", record["summary"]),
                "workDailyLifeContinuity": details.get("workDailyLifeContinuity"),
                "sleepBodyRegulation": details.get("sleepBodyRegulation"),
                "relationshipContact": details.get("relationshipContact"),
                "reflectiveCapacity": details.get("reflectiveCapacity"),
                "groundingRecommendation": details.get("groundingRecommendation", "pace_gently"),
                "reasons": list(details.get("reasons", [])),
            }
        elif record_type == "self_orientation_snapshot" and "selfOrientation" not in result:
            result["selfOrientation"] = {
                **summary,
                "orientationSummary": details.get("orientationSummary", record["summary"]),
                "emergentDirection": details.get("emergentDirection", record["summary"]),
                "egoRelation": details.get("egoRelation", "unknown"),
                "movementLanguage": list(details.get("movementLanguage", [])),
            }
        elif record_type == "psychic_opposition":
            result.setdefault("activeOppositions", []).append(
                {
                    **summary,
                    "poleA": details.get("poleA", ""),
                    "poleB": details.get("poleB", ""),
                    "oppositionSummary": details.get("oppositionSummary", record["summary"]),
                    "currentHoldingPattern": details.get("currentHoldingPattern", ""),
                    "normalizedOppositionKey": details.get("normalizedOppositionKey", record["id"]),
                }
            )
        elif record_type == "emergent_third_signal":
            result.setdefault("emergentThirdSignals", []).append(
                {
                    **summary,
                    "signalType": details.get("signalType", "unknown"),
                    "signalSummary": details.get("signalSummary", record["summary"]),
                    "oppositionIds": list(details.get("oppositionIds", [])),
                    "novelty": details.get("novelty", "unclear"),
                }
            )
        elif record_type == "bridge_moment":
            result.setdefault("bridgeMoments", []).append(
                {
                    **summary,
                    "bridgeType": details.get("bridgeType", "unknown"),
                    "bridgeSummary": details.get("bridgeSummary", record["summary"]),
                    "beforeAfter": details.get("beforeAfter"),
                }
            )
        elif record_type == "threshold_process":
            result.setdefault("thresholdProcesses", []).append(
                {
                    **summary,
                    "phase": details.get("phase", "unknown"),
                    "whatIsEnding": details.get("whatIsEnding", ""),
                    "notYetBegun": details.get("notYetBegun", ""),
                    "groundingStatus": details.get("groundingStatus", "unknown"),
                    "invitationReadiness": details.get("invitationReadiness", "not_now"),
                    "normalizedThresholdKey": details.get("normalizedThresholdKey", record["id"]),
                }
            )
        elif record_type == "relational_scene":
            result.setdefault("relationalScenes", []).append(
                {
                    **summary,
                    "sceneSummary": details.get("sceneSummary", record["summary"]),
                    "chargedRoles": list(details.get("chargedRoles", [])),
                    "recurringAffect": list(details.get("recurringAffect", [])),
                    "recurrenceContexts": list(details.get("recurrenceContexts", [])),
                    "normalizedSceneKey": details.get("normalizedSceneKey", record["id"]),
                }
            )
        elif (
            record_type == "projection_hypothesis"
            and consent_status.get("projection_language") == "allow"
        ):
            result.setdefault("projectionHypotheses", []).append(
                {
                    **summary,
                    "relationalSceneId": details.get("relationalSceneId"),
                    "hypothesisSummary": details.get("hypothesisSummary", record["summary"]),
                    "projectionPattern": details.get("projectionPattern", ""),
                    "userTestPrompt": details.get("userTestPrompt", ""),
                    "counterevidenceIds": list(details.get("counterevidenceIds", [])),
                    "normalizedHypothesisKey": details.get("normalizedHypothesisKey", record["id"]),
                }
            )
        elif (
            record_type == "inner_outer_correspondence"
            and consent_status.get("inner_outer_correspondence") == "allow"
        ):
            result.setdefault("innerOuterCorrespondences", []).append(
                {
                    **summary,
                    "correspondenceSummary": details.get(
                        "correspondenceSummary", record["summary"]
                    ),
                    "innerRefs": list(details.get("innerRefs", [])),
                    "outerRefs": list(details.get("outerRefs", [])),
                    "symbolIds": list(details.get("symbolIds", [])),
                    "userCharge": details.get("userCharge", "unclear"),
                    "caveat": details.get("caveat", ""),
                    "normalizedCorrespondenceKey": details.get(
                        "normalizedCorrespondenceKey", record["id"]
                    ),
                }
            )
        elif record_type == "numinous_encounter":
            result.setdefault("numinousEncounters", []).append(
                {
                    **summary,
                    "encounterMedium": details.get("encounterMedium", "unknown"),
                    "affectTone": details.get("affectTone", ""),
                    "containmentNeed": details.get("containmentNeed", "pace_gently"),
                    "interpretationConstraint": details.get("interpretationConstraint", ""),
                }
            )
        elif record_type == "aesthetic_resonance":
            result.setdefault("aestheticResonances", []).append(
                {
                    **summary,
                    "medium": details.get("medium", ""),
                    "objectDescription": details.get("objectDescription", record["label"]),
                    "resonanceSummary": details.get("resonanceSummary", record["summary"]),
                    "feelingTone": details.get("feelingTone"),
                    "bodySensations": list(details.get("bodySensations", [])),
                }
            )
        elif (
            record_type == "archetypal_pattern"
            and consent_status.get("archetypal_patterning") == "allow"
        ):
            result.setdefault("archetypalPatterns", []).append(
                {
                    **summary,
                    "patternFamily": details.get("patternFamily", "unknown"),
                    "resonanceSummary": details.get("resonanceSummary", record["summary"]),
                    "caveat": details.get("caveat", ""),
                    "counterevidenceIds": list(details.get("counterevidenceIds", [])),
                    "phrasingPolicy": details.get("phrasingPolicy", "very_tentative"),
                }
            )
    for key in (
        "activeOppositions",
        "emergentThirdSignals",
        "bridgeMoments",
        "thresholdProcesses",
        "relationalScenes",
        "projectionHypotheses",
        "innerOuterCorrespondences",
        "numinousEncounters",
        "aestheticResonances",
        "archetypalPatterns",
    ):
        if key in result:
            result[key] = result[key][:5]
    return result or None


def _build_living_myth_context_summary(
    bucket: UserCirculatioBucket,
    *,
    user_id: Id,
    window_start: str,
    window_end: str,
) -> dict[str, object] | None:
    records = [
        item
        for item in bucket.living_myth_records.values()
        if item.get("status") in {"active", "user_confirmed"}
        and item["userId"] == user_id
        and item.get("deletedAt") is None
        and _window_overlaps(
            item.get("windowStart"),
            item.get("windowEnd"),
            window_start=window_start,
            window_end=window_end,
        )
    ]
    records.sort(key=lambda item: item.get("updatedAt", item.get("createdAt", "")), reverse=True)
    result: dict[str, object] = {}
    for record in records:
        details = dict(record.get("details", {}))
        summary = {
            "id": record["id"],
            "label": record["label"],
            "summary": record["summary"],
            "confidence": record.get("confidence", "low"),
            "evidenceIds": list(record.get("evidenceIds", [])),
        }
        record_type = record["recordType"]
        if record_type == "life_chapter_snapshot" and "currentLifeChapter" not in result:
            result["currentLifeChapter"] = {
                **summary,
                "chapterLabel": details.get("chapterLabel", record["label"]),
                "chapterSummary": details.get("chapterSummary", record["summary"]),
                "governingSymbolIds": list(details.get("governingSymbolIds", [])),
                "governingQuestions": list(details.get("governingQuestions", [])),
                "activeOppositionIds": list(details.get("activeOppositionIds", [])),
                "thresholdProcessIds": list(details.get("thresholdProcessIds", [])),
                "relationalSceneIds": list(details.get("relationalSceneIds", [])),
                "correspondenceIds": list(details.get("correspondenceIds", [])),
                "chapterTone": details.get("chapterTone"),
            }
        elif record_type == "mythic_question":
            result.setdefault("activeMythicQuestions", []).append(
                {
                    **summary,
                    "questionText": details.get("questionText", record["summary"]),
                    "questionStatus": details.get("questionStatus", "active"),
                    "relatedChapterId": details.get("relatedChapterId"),
                    "lastReturnedAt": details.get("lastReturnedAt"),
                }
            )
        elif record_type == "threshold_marker":
            result.setdefault("recentThresholdMarkers", []).append(
                {
                    **summary,
                    "markerType": details.get("markerType", "unknown"),
                    "markerSummary": details.get("markerSummary", record["summary"]),
                    "thresholdProcessId": details.get("thresholdProcessId"),
                }
            )
        elif record_type == "complex_encounter":
            result.setdefault("complexEncounters", []).append(
                {
                    **summary,
                    "complexCandidateId": details.get("complexCandidateId"),
                    "patternId": details.get("patternId"),
                    "encounterSummary": details.get("encounterSummary", record["summary"]),
                    "trajectorySummary": details.get("trajectorySummary", record["summary"]),
                    "movement": details.get("movement", "unknown"),
                }
            )
        elif record_type == "integration_contour" and "latestIntegrationContour" not in result:
            result["latestIntegrationContour"] = {
                **summary,
                "contourSummary": details.get("contourSummary", record["summary"]),
                "symbolicStrands": list(details.get("symbolicStrands", [])),
                "somaticStrands": list(details.get("somaticStrands", [])),
                "relationalStrands": list(details.get("relationalStrands", [])),
                "existentialStrands": list(details.get("existentialStrands", [])),
                "tensionsHeld": list(details.get("tensionsHeld", [])),
                "assimilatedSignals": list(details.get("assimilatedSignals", [])),
                "unassimilatedEdges": list(details.get("unassimilatedEdges", [])),
                "nextQuestions": list(details.get("nextQuestions", [])),
            }
        elif (
            record_type == "symbolic_wellbeing_snapshot" and "latestSymbolicWellbeing" not in result
        ):
            result["latestSymbolicWellbeing"] = {
                **summary,
                "capacitySummary": details.get("capacitySummary", record["summary"]),
                "groundingCapacity": details.get("groundingCapacity", "unknown"),
                "symbolicLiveliness": details.get("symbolicLiveliness", ""),
                "somaticContact": details.get("somaticContact", ""),
                "relationalSpaciousness": details.get("relationalSpaciousness", ""),
                "agencyTone": details.get("agencyTone", ""),
                "supportNeeded": details.get("supportNeeded"),
            }
    for key in ("activeMythicQuestions", "recentThresholdMarkers", "complexEncounters"):
        if key in result:
            result[key] = result[key][:5]
    return result or None


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
                _parse_datetime(item.get("observedAt", item.get("createdAt"))), start_dt, end_dt
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
                    _parse_datetime(item.get("observedAt", item.get("createdAt"))), start_dt, end_dt
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
    start_dt = _parse_datetime(window_start)
    end_dt = _parse_datetime(window_end)
    snapshot: MethodContextSnapshot = {
        "windowStart": window_start,
        "windowEnd": window_end,
        "source": "circulatio-backend",
    }
    attitudes = [
        item
        for item in bucket.conscious_attitudes.values()
        if item.get("status") != "deleted"
        and item["userId"] == user_id
        and item.get("windowEnd", window_end) >= window_start
        and item.get("windowStart", window_start) <= window_end
    ]
    attitudes.sort(key=lambda item: item.get("updatedAt", item.get("createdAt", "")), reverse=True)
    if attitudes:
        snapshot["consciousAttitude"] = _project_conscious_attitude_summary(attitudes[0])
    body_states = [
        item
        for item in bucket.body_states.values()
        if item.get("status") != "deleted"
        and item["userId"] == user_id
        and _is_within_window(
            _parse_datetime(item.get("observedAt", item.get("createdAt"))), start_dt, end_dt
        )
    ]
    body_states.sort(
        key=lambda item: item.get("observedAt", item.get("updatedAt", item.get("createdAt", ""))),
        reverse=True,
    )
    if body_states:
        snapshot["recentBodyStates"] = [
            _project_body_state_summary(item) for item in body_states[:5]
        ]
    goals = [
        item
        for item in bucket.goals.values()
        if item.get("status") not in {"deleted", "completed"} and item["userId"] == user_id
    ]
    goals.sort(key=lambda item: item.get("updatedAt", item.get("createdAt", "")), reverse=True)
    if goals:
        snapshot["activeGoals"] = [_project_goal_summary(item) for item in goals[:5]]
    goal_tensions = [
        item
        for item in bucket.goal_tensions.values()
        if item.get("status") != "deleted" and item["userId"] == user_id
    ]
    goal_tensions.sort(
        key=lambda item: item.get("updatedAt", item.get("createdAt", "")), reverse=True
    )
    if goal_tensions:
        snapshot["goalTensions"] = [
            _project_goal_tension_summary(item) for item in goal_tensions[:5]
        ]
    amplifications = [
        item
        for item in bucket.personal_amplifications.values()
        if item.get("status") != "deleted"
        and item["userId"] == user_id
        and _is_within_window(_parse_datetime(item.get("createdAt")), start_dt, end_dt)
    ]
    amplifications.sort(key=lambda item: item.get("createdAt", ""), reverse=True)
    if amplifications:
        snapshot["personalAmplifications"] = [
            _project_personal_amplification_summary(item) for item in amplifications[:5]
        ]
    consent = [item for item in bucket.consent_preferences.values() if item["userId"] == user_id]
    consent.sort(key=lambda item: item.get("updatedAt", item.get("createdAt", "")), reverse=True)
    if consent:
        snapshot["consentPreferences"] = [
            _project_consent_preference_summary(item) for item in consent[:6]
        ]
    prompts = [
        item
        for item in bucket.amplification_prompts.values()
        if item.get("status") == "pending"
        and item["userId"] == user_id
        and (material_id is None or item.get("materialId") == material_id or item.get("runId"))
    ]
    prompts.sort(key=lambda item: item.get("updatedAt", item.get("createdAt", "")), reverse=True)
    if prompts:
        snapshot["pendingAmplificationPrompts"] = [
            _project_amplification_prompt_summary(item) for item in prompts[:5]
        ]
    memberships_by_series: dict[Id, list[dict[str, object]]] = {}
    for membership in bucket.dream_series_memberships.values():
        if membership.get("status") == "deleted" or membership["userId"] != user_id:
            continue
        memberships_by_series.setdefault(membership["seriesId"], []).append(membership)
    series = [
        item
        for item in bucket.dream_series.values()
        if item.get("status") != "deleted" and item["userId"] == user_id
    ]
    series.sort(
        key=lambda item: (
            item.get("lastSeen", item.get("updatedAt", item.get("createdAt", ""))),
            item.get("updatedAt", item.get("createdAt", "")),
        ),
        reverse=True,
    )
    if series:
        projected = []
        for item in series[:5]:
            summary = _project_dream_series_summary(item)
            memberships = sorted(
                memberships_by_series.get(item["id"], []),
                key=lambda value: value.get("updatedAt", value.get("createdAt", "")),
                reverse=True,
            )[:3]
            if memberships:
                summary["recentMemberships"] = [
                    _project_dream_series_membership_summary(value) for value in memberships
                ]
            projected.append(summary)
        snapshot["activeDreamSeries"] = projected
    enabled_frames = [
        item
        for item in bucket.cultural_frames.values()
        if item["userId"] == user_id and item.get("status") == "enabled"
    ]
    enabled_frames.sort(
        key=lambda item: item.get("updatedAt", item.get("createdAt", "")), reverse=True
    )
    if enabled_frames:
        snapshot["activeCulturalFrames"] = [
            _project_cultural_frame_summary(item) for item in enabled_frames[:5]
        ]
    consent_status = {item["scope"]: item["status"] for item in consent}
    frame_label_by_id = {item["id"]: item["label"] for item in enabled_frames}
    collective = [
        item
        for item in bucket.collective_amplifications.values()
        if item["userId"] == user_id
        and item.get("status") in {"offered", "user_resonated"}
        and (
            consent_status.get("collective_amplification") == "allow"
            or item.get("status") == "user_resonated"
        )
    ]
    collective.sort(key=lambda item: item.get("updatedAt", item.get("createdAt", "")), reverse=True)
    if collective:
        snapshot["collectiveAmplifications"] = [
            _project_collective_amplification_summary(item, frame_label_by_id=frame_label_by_id)
            for item in collective[:5]
        ]
    adaptation = _latest_adaptation_profile(bucket)
    if adaptation is not None:
        snapshot["adaptationProfile"] = _project_adaptation_profile_summary(adaptation)
    journeys = [
        item
        for item in bucket.journeys.values()
        if item.get("status") != "deleted" and item["userId"] == user_id
    ]
    journeys.sort(key=lambda item: item.get("updatedAt", item.get("createdAt", "")), reverse=True)
    if journeys:
        snapshot["activeJourneys"] = [_project_journey_summary(item) for item in journeys[:5]]
    practices = [
        item
        for item in bucket.practice_sessions.values()
        if item.get("status") != "deleted"
        and item["userId"] == user_id
        and _is_within_window(_practice_timestamp(item), start_dt, end_dt)
    ]
    practices.sort(
        key=lambda item: item.get(
            "completedAt",
            item.get("updatedAt", item.get("createdAt", "")),
        ),
        reverse=True,
    )
    if practices:
        snapshot["recentPracticeSessions"] = [
            _project_practice_session_summary(item) for item in practices[:5]
        ]
    recent_dream_dynamics = build_recent_dream_dynamics_locked(
        bucket,
        user_id=user_id,
        window_start=window_start,
        window_end=window_end,
    )
    if recent_dream_dynamics:
        snapshot["recentDreamDynamics"] = recent_dream_dynamics
    signals = _derive_longitudinal_signals(bucket)
    if signals:
        snapshot["longitudinalSignals"] = signals
    consent_status = _consent_status_map(snapshot)
    individuation_context = _build_individuation_context_summary(
        bucket,
        user_id=user_id,
        window_start=window_start,
        window_end=window_end,
        consent_status=consent_status,
    )
    if individuation_context:
        snapshot["individuationContext"] = individuation_context
    living_myth_context = _build_living_myth_context_summary(
        bucket,
        user_id=user_id,
        window_start=window_start,
        window_end=window_end,
    )
    if living_myth_context:
        snapshot["livingMythContext"] = living_myth_context
    method_state = build_method_state_summary_locked(
        bucket,
        user_id=user_id,
        window_start=window_start,
        window_end=window_end,
        snapshot=snapshot,
    )
    if method_state:
        snapshot["methodState"] = method_state
    clarification_state = build_clarification_state_summary_locked(
        bucket,
        user_id=user_id,
        material_id=material_id,
    )
    if clarification_state:
        snapshot["clarificationState"] = clarification_state
    return snapshot if len(snapshot) > 3 else None


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


def build_threshold_review_input_locked(
    bucket: UserCirculatioBucket,
    *,
    user_id: Id,
    window_start: str,
    window_end: str,
    threshold_process_id: Id | None = None,
    explicit_question: str | None = None,
) -> ThresholdReviewInput:
    payload: ThresholdReviewInput = {
        "userId": user_id,
        "windowStart": window_start,
        "windowEnd": window_end,
        "hermesMemoryContext": build_memory_context_locked(bucket),
    }
    if explicit_question:
        payload["explicitQuestion"] = explicit_question
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
    thresholds = (
        (method_context or {}).get("individuationContext", {}).get("thresholdProcesses", [])
    )
    if threshold_process_id:
        target = next((item for item in thresholds if item.get("id") == threshold_process_id), None)
        if target is not None:
            payload["targetThresholdProcess"] = deepcopy(target)
    elif thresholds:
        payload["targetThresholdProcess"] = deepcopy(thresholds[0])
    reality_anchor = (method_context or {}).get("individuationContext", {}).get("realityAnchors")
    if reality_anchor:
        payload["relatedRealityAnchors"] = [deepcopy(reality_anchor)]
    if method_context and method_context.get("recentBodyStates"):
        payload["relatedBodyStates"] = deepcopy(method_context["recentBodyStates"][:5])
    if method_context and method_context.get("activeDreamSeries"):
        payload["relatedDreamSeries"] = deepcopy(method_context["activeDreamSeries"][:5])
    scenes = (method_context or {}).get("individuationContext", {}).get("relationalScenes", [])
    if scenes:
        payload["relatedRelationalScenes"] = deepcopy(scenes[:5])
    if bucket.evidence:
        payload["evidence"] = deepcopy(list(bucket.evidence.values())[:20])
    return payload


def build_living_myth_review_input_locked(
    bucket: UserCirculatioBucket,
    *,
    user_id: Id,
    window_start: str,
    window_end: str,
    explicit_question: str | None = None,
) -> LivingMythReviewInput:
    payload: LivingMythReviewInput = {
        "userId": user_id,
        "windowStart": window_start,
        "windowEnd": window_end,
        "hermesMemoryContext": build_memory_context_locked(bucket),
    }
    if explicit_question:
        payload["explicitQuestion"] = explicit_question
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
    payload["recentMaterialSummaries"] = build_memory_context_locked(bucket)[
        "recentMaterialSummaries"
    ][:8]
    if bucket.evidence:
        payload["evidence"] = deepcopy(list(bucket.evidence.values())[:20])
    return payload


def build_analysis_packet_input_locked(
    bucket: UserCirculatioBucket,
    *,
    user_id: Id,
    window_start: str,
    window_end: str,
    packet_focus: str | None = None,
    explicit_question: str | None = None,
) -> AnalysisPacketInput:
    payload: AnalysisPacketInput = {
        "userId": user_id,
        "windowStart": window_start,
        "windowEnd": window_end,
        "hermesMemoryContext": build_memory_context_locked(bucket),
    }
    if packet_focus:
        payload["packetFocus"] = packet_focus
    if explicit_question:
        payload["explicitQuestion"] = explicit_question
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
        if method_context.get("activeDreamSeries"):
            payload["currentDreamSeries"] = deepcopy(method_context["activeDreamSeries"][:5])
        if method_context.get("recentBodyStates"):
            payload["bodyEchoes"] = deepcopy(method_context["recentBodyStates"][:5])
        individuation_context = method_context.get("individuationContext") or {}
        living_myth_context = method_context.get("livingMythContext") or {}
        if individuation_context.get("thresholdProcesses"):
            payload["activeThresholdProcesses"] = deepcopy(
                individuation_context["thresholdProcesses"][:5]
            )
        if individuation_context.get("relationalScenes"):
            payload["relationalScenes"] = deepcopy(individuation_context["relationalScenes"][:5])
        if individuation_context.get("projectionHypotheses"):
            payload["projectionHypotheses"] = deepcopy(
                individuation_context["projectionHypotheses"][:5]
            )
        if individuation_context.get("innerOuterCorrespondences"):
            payload["innerOuterCorrespondences"] = deepcopy(
                individuation_context["innerOuterCorrespondences"][:5]
            )
        if living_myth_context.get("activeMythicQuestions"):
            payload["activeMythicQuestions"] = deepcopy(
                living_myth_context["activeMythicQuestions"][:5]
            )
    if bucket.feedback:
        payload["userCorrectionsAndRejectedClaims"] = deepcopy(bucket.feedback[:8])
    practice_outcomes = [
        project_practice_outcome(item)
        for item in bucket.practice_sessions.values()
        if item.get("status") == "completed" and item.get("userId") == user_id
    ]
    if practice_outcomes:
        payload["recentPracticeOutcomes"] = practice_outcomes[:8]
    if bucket.evidence:
        payload["evidence"] = deepcopy(list(bucket.evidence.values())[:20])
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
