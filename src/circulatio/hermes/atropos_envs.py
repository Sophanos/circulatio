from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TypedDict

from ..core.method_state_policy import get_containment_summary, get_grounding_summary
from ..domain.feedback import InteractionFeedbackRecord
from ..domain.ids import now_iso
from ..domain.practices import PracticeSessionRecord
from ..domain.timestamps import format_iso_datetime, try_parse_iso_datetime
from ..domain.types import Id
from ..repositories.circulatio_repository import CirculatioRepository

_COMMUNICATION_FEEDBACK_WEIGHTS = {
    "good_level": 1.0,
    "helpful": 1.0,
    "too_much": -0.9,
    "too_vague": -0.8,
    "too_abstract": -0.8,
    "not_helpful": -1.0,
}
_PRACTICE_FEEDBACK_WEIGHTS = {
    "good_fit": 1.0,
    "helpful": 0.8,
    "not_for_me": -0.8,
    "too_intense": -1.0,
    "too_long": -0.7,
    "not_helpful": -1.0,
}
_HARD_NEGATIVE_FLAGS = {
    "safety_violation",
    "approval_boundary_violation",
    "projection_stated_as_fact",
    "archetype_identity_claim",
    "typology_identity_claim",
    "consent_blocked_depth_move",
    "consent_blocked_practice",
    "threshold_ignored",
    "grounding_ignored",
}


class RewardScore(TypedDict, total=False):
    reward: float
    hardNegative: bool
    reasons: list[str]


async def build_circulatio_communication_env(
    repository: CirculatioRepository,
    *,
    user_id: Id,
) -> dict[str, object]:
    profile = await repository.get_adaptation_profile(user_id)
    recent_runs = await repository.list_interpretation_runs(user_id, limit=10)
    recent_runs = sorted(
        recent_runs,
        key=lambda item: str(item.get("createdAt", "")),
        reverse=True,
    )[:10]
    capture_runs = await repository.list_method_state_capture_runs(user_id, limit=50)
    recent_feedback = await repository.list_interaction_feedback(
        user_id,
        domain="interpretation",
        limit=10,
    )

    follow_up_counts: dict[str, int] = {}
    for capture in capture_runs:
        run_id = str(capture.get("anchorRefs", {}).get("runId") or "").strip()
        if run_id:
            follow_up_counts[run_id] = int(follow_up_counts.get(run_id, 0)) + 1

    outcomes: list[dict[str, object]] = []
    for run in recent_runs:
        integrations = await repository.list_integration_records(
            user_id, run_id=run["id"], limit=25
        )
        approved_count = sum(
            1
            for decision in run.get("proposalDecisions", [])
            if decision.get("status") == "approved"
        )
        rejected_count = sum(
            1
            for decision in run.get("proposalDecisions", [])
            if decision.get("status") == "rejected"
        )
        hypothesis_rejected = 0
        hypothesis_refined = 0
        for integration in integrations:
            for feedback in integration.get("feedbackByHypothesisId", {}).values():
                feedback_value = str(feedback.get("feedback") or "").strip()
                if feedback_value == "rejected":
                    hypothesis_rejected += 1
                if feedback_value == "partially_refined":
                    hypothesis_refined += 1
        outcomes.append(
            {
                "runId": run["id"],
                "createdAt": run["createdAt"],
                "methodGateDepthLevel": run.get("result", {})
                .get("methodGate", {})
                .get("depthLevel"),
                "depthReadinessStatus": run.get("result", {})
                .get("depthReadiness", {})
                .get("status"),
                "clarifyingQuestionAsked": bool(
                    str(run.get("result", {}).get("clarifyingQuestion") or "").strip()
                ),
                "followUpAnswered": follow_up_counts.get(run["id"], 0) > 0,
                "proposalApprovalCount": approved_count,
                "proposalRejectionCount": rejected_count,
                "hypothesisRejectedCount": hypothesis_rejected,
                "hypothesisRefinedCount": hypothesis_refined,
            }
        )

    readiness_summary = await _build_readiness_summary(
        repository,
        user_id=user_id,
        recent_timestamps=[run.get("createdAt") for run in recent_runs],
    )
    explicit_preferences = (
        profile.get("explicitPreferences", {}) if isinstance(profile, dict) else {}
    )
    learned_signals = profile.get("learnedSignals", {}) if isinstance(profile, dict) else {}
    return {
        "environment": "circulatio_communication_env",
        "state": {
            "userId": user_id,
            "explicitCommunicationPreferences": _copy_object_dict(
                explicit_preferences.get("communication")
                if isinstance(explicit_preferences, dict)
                else None
            ),
            "explicitInterpretationPreferences": _copy_object_dict(
                explicit_preferences.get("interpretation")
                if isinstance(explicit_preferences, dict)
                else None
            ),
            "learnedCommunicationPolicy": _copy_object_dict(
                learned_signals.get("communicationPolicy")
                if isinstance(learned_signals, dict)
                else None
            ),
            "recentInterpretationOutcomes": outcomes,
            "recentExplicitInterpretationFeedback": [
                _feedback_event_summary(item) for item in recent_feedback[:10]
            ],
            "currentReadinessSummary": readiness_summary,
        },
        "output": {
            "policyTarget": "learnedSignals.communicationPolicy",
            "distillationTargetOptional": True,
        },
    }


async def build_circulatio_practice_env(
    repository: CirculatioRepository,
    *,
    user_id: Id,
) -> dict[str, object]:
    profile = await repository.get_adaptation_profile(user_id)
    recent_sessions = await repository.list_practice_sessions(
        user_id,
        include_deleted=False,
        limit=10,
    )
    recent_sessions = sorted(
        recent_sessions,
        key=lambda item: str(
            item.get("completedAt") or item.get("updatedAt") or item.get("createdAt", "")
        ),
        reverse=True,
    )[:10]
    recent_feedback = await repository.list_interaction_feedback(
        user_id,
        domain="practice",
        limit=10,
    )
    readiness_summary = await _build_readiness_summary(
        repository,
        user_id=user_id,
        recent_timestamps=[
            item.get("completedAt") or item.get("updatedAt") or item.get("createdAt")
            for item in recent_sessions
        ],
    )
    explicit_preferences = (
        profile.get("explicitPreferences", {}) if isinstance(profile, dict) else {}
    )
    learned_signals = profile.get("learnedSignals", {}) if isinstance(profile, dict) else {}
    return {
        "environment": "circulatio_practice_env",
        "state": {
            "userId": user_id,
            "explicitPracticePreferences": _copy_object_dict(
                explicit_preferences.get("practice")
                if isinstance(explicit_preferences, dict)
                else None
            ),
            "learnedPracticePolicy": _copy_object_dict(
                learned_signals.get("practicePolicy") if isinstance(learned_signals, dict) else None
            ),
            "recentPracticeOutcomes": [
                {
                    "practiceSessionId": item["id"],
                    "status": item["status"],
                    "practiceType": item["practiceType"],
                    "modality": item.get("modality"),
                    "durationMinutes": item.get("durationMinutes"),
                    "intensity": item.get("intensity"),
                    "activationImproved": _activation_delta(item) == "improved",
                    "activationWorsened": _activation_delta(item) == "worsened",
                }
                for item in recent_sessions
            ],
            "recentExplicitPracticeFeedback": [
                _feedback_event_summary(item) for item in recent_feedback[:10]
            ],
            "currentReadinessAndConsentConstraints": readiness_summary,
        },
        "output": {
            "policyTarget": "learnedSignals.practicePolicy",
            "distillationTargetOptional": True,
        },
    }


def score_circulatio_communication_reward(
    *,
    explicit_feedback_events: list[dict[str, object]] | None = None,
    implicit_signals: dict[str, object] | None = None,
    hard_negative_flags: list[str] | None = None,
) -> RewardScore:
    return _score_reward(
        explicit_feedback_events=explicit_feedback_events,
        implicit_signals=implicit_signals,
        hard_negative_flags=hard_negative_flags,
        explicit_weights=_COMMUNICATION_FEEDBACK_WEIGHTS,
        positive_keys={
            "proposalApprovedCount": 0.35,
            "clarifyingFollowUpAnswered": 0.25,
            "hypothesisRefinedCount": 0.15,
        },
        negative_keys={
            "proposalRejectedCount": -0.2,
            "clarifyingFollowUpIgnored": -0.1,
            "hypothesisRejectedCount": -0.15,
        },
    )


def score_circulatio_practice_reward(
    *,
    explicit_feedback_events: list[dict[str, object]] | None = None,
    implicit_signals: dict[str, object] | None = None,
    hard_negative_flags: list[str] | None = None,
) -> RewardScore:
    return _score_reward(
        explicit_feedback_events=explicit_feedback_events,
        implicit_signals=implicit_signals,
        hard_negative_flags=hard_negative_flags,
        explicit_weights=_PRACTICE_FEEDBACK_WEIGHTS,
        positive_keys={
            "practiceAcceptedCount": 0.25,
            "practiceCompletedCount": 0.45,
            "activationImprovedCount": 0.35,
            "rhythmicBriefActedOnCount": 0.1,
        },
        negative_keys={
            "practiceSkippedCount": -0.15,
            "activationWorsenedCount": -0.45,
            "rhythmicBriefDismissedCount": -0.05,
        },
    )


async def _build_readiness_summary(
    repository: CirculatioRepository,
    *,
    user_id: Id,
    recent_timestamps: list[object],
) -> dict[str, object]:
    end_dt = _latest_timestamp(recent_timestamps) or _parse_timestamp(now_iso())
    if end_dt is None:
        end_dt = datetime.now(tz=UTC)
    start_dt = end_dt - timedelta(days=30)
    method_context = await repository.build_method_context_snapshot_from_records(
        user_id,
        window_start=_format_timestamp(start_dt),
        window_end=_format_timestamp(end_dt),
    )
    consent_preferences = (
        list(method_context.get("consentPreferences", []))
        if isinstance(method_context, dict)
        else []
    )
    containment = get_containment_summary(method_context) or {}
    grounding = get_grounding_summary(method_context) or {}
    individuation_context = (
        method_context.get("individuationContext", {}) if isinstance(method_context, dict) else {}
    )
    blocked_scopes = [
        str(item.get("scope"))
        for item in consent_preferences
        if isinstance(item, dict) and str(item.get("status") or "") in {"declined", "revoked"}
    ]
    return {
        "thresholdActive": bool(
            isinstance(individuation_context, dict)
            and individuation_context.get("thresholdProcesses")
        ),
        "groundingStrained": str(containment.get("status") or "") in {"strained", "thin"}
        or str(grounding.get("recommendation") or "") == "grounding_first",
        "relevantConsentBlocks": blocked_scopes,
    }


def _feedback_event_summary(record: InteractionFeedbackRecord) -> dict[str, object]:
    return {
        "id": record.get("id"),
        "targetId": record.get("targetId"),
        "feedback": record.get("feedback"),
        "locale": record.get("locale"),
        "createdAt": record.get("createdAt"),
    }


def _activation_delta(record: PracticeSessionRecord) -> str:
    levels = {"low": 1, "moderate": 2, "high": 3}
    before = levels.get(str(record.get("activationBefore") or ""))
    after = levels.get(str(record.get("activationAfter") or ""))
    if before is None or after is None:
        return "unknown"
    if after < before:
        return "improved"
    if after > before:
        return "worsened"
    return "unchanged"


def _score_reward(
    *,
    explicit_feedback_events: list[dict[str, object]] | None,
    implicit_signals: dict[str, object] | None,
    hard_negative_flags: list[str] | None,
    explicit_weights: dict[str, float],
    positive_keys: dict[str, float],
    negative_keys: dict[str, float],
) -> RewardScore:
    flags = [
        str(flag)
        for flag in (hard_negative_flags or [])
        if str(flag).strip() in _HARD_NEGATIVE_FLAGS
    ]
    if flags:
        return {
            "reward": round(-2.0 - (0.5 * max(len(flags) - 1, 0)), 3),
            "hardNegative": True,
            "reasons": [f"hard_negative:{flag}" for flag in flags],
        }

    reward = 0.0
    reasons: list[str] = []
    for event in explicit_feedback_events or []:
        feedback = str(event.get("feedback") or "").strip()
        if feedback in explicit_weights:
            reward += explicit_weights[feedback]
            reasons.append(f"explicit:{feedback}")

    signals = implicit_signals or {}
    for key, weight in positive_keys.items():
        count = _signal_count(signals.get(key))
        if count:
            reward += count * weight
            reasons.append(f"implicit:{key}:{count}")
    for key, weight in negative_keys.items():
        count = _signal_count(signals.get(key))
        if count:
            reward += count * weight
            reasons.append(f"implicit:{key}:{count}")

    return {"reward": round(reward, 3), "hardNegative": False, "reasons": reasons}


def _signal_count(value: object) -> int:
    if isinstance(value, bool):
        return 1 if value else 0
    if isinstance(value, int):
        return max(0, value)
    return 0


def _copy_object_dict(value: object) -> dict[str, object]:
    if isinstance(value, dict):
        return {str(key): item for key, item in value.items()}
    return {}


def _latest_timestamp(values: list[object]) -> datetime | None:
    parsed: list[datetime] = []
    for value in values:
        parsed_value = _parse_timestamp(value)
        if parsed_value is not None:
            parsed.append(parsed_value)
    return max(parsed) if parsed else None


def _parse_timestamp(value: object) -> datetime | None:
    return try_parse_iso_datetime(value)


def _format_timestamp(value: datetime) -> str:
    return format_iso_datetime(value)


__all__ = [
    "build_circulatio_communication_env",
    "build_circulatio_practice_env",
    "score_circulatio_communication_reward",
    "score_circulatio_practice_reward",
]
