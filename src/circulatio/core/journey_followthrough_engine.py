from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Literal, cast

from ..domain.journey_experiments import JourneyExperimentRecord
from ..domain.journeys import JourneyRecord
from ..domain.practices import PracticeSessionRecord
from ..domain.proactive import ProactiveBriefRecord
from ..domain.reviews import DashboardSummary
from ..domain.timestamps import parse_iso_datetime
from ..domain.types import (
    CoachMoveKind,
    CoachSurface,
    Id,
    JourneyFamilyKind,
    JourneyFollowthroughSummary,
    MethodContextSnapshot,
    ThreadDigest,
    UserAdaptationProfileSummary,
)

_ACTIVATION_ORDER = {
    "low": 0,
    "moderate": 1,
    "high": 2,
    "overwhelming": 3,
}

_BLOCKED_ESCALATIONS: dict[JourneyFamilyKind, list[str]] = {
    "embodied_recurrence": [
        "projection_language_without_consent",
        "archetypal_escalation_without_grounding",
        "diagnostic_or_causal_framing",
    ],
    "symbol_body_life_pressure": [
        "premature_amplification",
        "archetypal_certainty",
        "bypassing_body_contact",
    ],
    "thought_loop_typology_restraint": [
        "identity_typing_claims",
        "inferior_function_language",
        "typology_certainty",
    ],
    "relational_scene_recurrence": [
        "projection_claims_without_consent",
        "scene_reductionism",
        "inner_outer_certainty_without_grounding",
    ],
    "practice_reentry": [
        "backlog_pressure",
        "repeat_same_practice_after_skips",
        "high_intensity_after_activation",
        "forced_symbolic_processing",
    ],
    "cross_family": [
        "symbolic_pressure",
        "productivity_language",
        "certainty_language",
    ],
}


class JourneyFollowthroughEngine:
    def build_summaries(
        self,
        *,
        method_context: MethodContextSnapshot | None,
        thread_digests: list[ThreadDigest] | None,
        journeys: list[JourneyRecord],
        journey_experiments: list[JourneyExperimentRecord],
        recent_practices: list[PracticeSessionRecord],
        existing_briefs: list[ProactiveBriefRecord],
        dashboard: DashboardSummary | None,
        adaptation_profile: UserAdaptationProfileSummary | None,
        now: str,
    ) -> list[JourneyFollowthroughSummary]:
        del dashboard
        snapshot = self._dict(method_context)
        method_state = self._dict(snapshot.get("methodState"))
        body_states = self._dict_list(snapshot.get("recentBodyStates"))
        body_state_by_id = {
            str(item.get("id") or "").strip(): item
            for item in body_states
            if str(item.get("id") or "").strip()
        }
        goal_tensions = self._dict_list(snapshot.get("goalTensions"))
        active_goal_tension = self._dict(method_state.get("activeGoalTension"))
        active_goal_tension_id = str(active_goal_tension.get("goalTensionId") or "").strip()
        if active_goal_tension_id and not any(
            str(item.get("id") or "").strip() == active_goal_tension_id for item in goal_tensions
        ):
            goal_tensions.append(
                {
                    "id": active_goal_tension_id,
                    "goalIds": self._ids(active_goal_tension.get("linkedGoalIds")),
                    "status": "active",
                    "tensionSummary": str(active_goal_tension.get("summary") or "").strip(),
                    "evidenceIds": self._ids(active_goal_tension.get("evidenceIds")),
                }
            )
        practice_loop = self._dict(method_state.get("practiceLoop"))
        typology_state = self._dict(method_state.get("typologyMethodState"))
        practices_by_journey: dict[Id, list[PracticeSessionRecord]] = defaultdict(list)
        for practice in recent_practices:
            for journey_id in self._ids(practice.get("relatedJourneyIds")):
                practices_by_journey[journey_id].append(practice)
        briefs_by_journey: dict[Id, list[ProactiveBriefRecord]] = defaultdict(list)
        for brief in existing_briefs:
            for journey_id in self._ids(brief.get("relatedJourneyIds")):
                briefs_by_journey[journey_id].append(brief)
        experiments_by_journey: dict[Id, list[JourneyExperimentRecord]] = defaultdict(list)
        for experiment in journey_experiments:
            journey_id = str(experiment.get("journeyId") or "").strip()
            if journey_id:
                experiments_by_journey[cast(Id, journey_id)].append(experiment)
        digests_by_journey: dict[Id, list[ThreadDigest]] = defaultdict(list)
        for digest in thread_digests or []:
            if not isinstance(digest, dict):
                continue
            for journey_id in self._journey_ids_from_digest(digest):
                digests_by_journey[journey_id].append(digest)
        now_dt = self._parse_datetime(now)
        summaries = [
            self._build_summary(
                journey=journey,
                journey_experiments=experiments_by_journey.get(cast(Id, journey["id"]), []),
                practices=practices_by_journey.get(cast(Id, journey["id"]), []),
                briefs=briefs_by_journey.get(cast(Id, journey["id"]), []),
                related_digests=digests_by_journey.get(cast(Id, journey["id"]), []),
                body_state_by_id=body_state_by_id,
                goal_tensions=goal_tensions,
                practice_loop=practice_loop,
                typology_state=typology_state,
                adaptation_profile=adaptation_profile,
                now=now_dt,
            )
            for journey in journeys
            if str(journey.get("status") or "").strip() != "deleted"
        ]
        summaries.sort(
            key=lambda item: (
                int(item.get("priority", 0)),
                item.get("lastTouchedAt", ""),
                item.get("journeyId", ""),
            ),
            reverse=True,
        )
        return summaries

    def _build_summary(
        self,
        *,
        journey: JourneyRecord,
        journey_experiments: list[JourneyExperimentRecord],
        practices: list[PracticeSessionRecord],
        briefs: list[ProactiveBriefRecord],
        related_digests: list[ThreadDigest],
        body_state_by_id: dict[str, dict[str, object]],
        goal_tensions: list[dict[str, object]],
        practice_loop: dict[str, object],
        typology_state: dict[str, object],
        adaptation_profile: UserAdaptationProfileSummary | None,
        now: datetime,
    ) -> JourneyFollowthroughSummary:
        journey_id = cast(Id, str(journey["id"]))
        related_body_state_ids = self._ids(journey.get("relatedBodyStateIds"))
        related_body_states = [
            body_state_by_id[state_id] for state_id in related_body_state_ids if state_id in body_state_by_id
        ]
        related_goal_ids = self._ids(journey.get("relatedGoalIds"))
        related_goal_tensions = [
            tension
            for tension in goal_tensions
            if self._intersects(self._ids(tension.get("goalIds")), related_goal_ids)
        ]
        related_goal_tension_ids = [
            cast(Id, str(tension["id"]))
            for tension in related_goal_tensions
            if str(tension.get("id") or "").strip()
        ]
        current_experiment, experiment_reason = self._current_experiment(journey_experiments)
        practice_signal = self._practice_signal(
            practices=practices,
            practice_loop=practice_loop,
            adaptation_profile=adaptation_profile,
            now=now,
            fallback_ts=str(journey.get("updatedAt") or journey.get("createdAt") or now.isoformat()),
        )
        family = self._detect_family(
            journey=journey,
            practice_signal=practice_signal,
            related_body_states=related_body_states,
            related_goal_tension_ids=related_goal_tension_ids,
            related_digests=related_digests,
            typology_state=typology_state,
        )
        (
            priority,
            recommended_move,
            body_first,
            reasons,
        ) = self._family_behavior(
            family=family,
            practice_signal=practice_signal,
            related_body_states=related_body_states,
            related_goal_tension_ids=related_goal_tension_ids,
            related_digests=related_digests,
        )
        if experiment_reason:
            reasons.append(experiment_reason)
        preferred_move = (
            str(current_experiment.get("preferredMoveKind") or "").strip()
            if isinstance(current_experiment, dict)
            else ""
        )
        if preferred_move and recommended_move != "offer_resource":
            recommended_move = cast(CoachMoveKind, preferred_move)
            reasons.append("journey_experiment_preferred_move_applied")
        last_touched_at = self._last_touched_at(
            journey=journey,
            current_experiment=current_experiment,
            practices=practices,
            related_body_states=related_body_states,
            related_digests=related_digests,
            fallback=now.isoformat(),
        )
        last_briefed_at = self._last_briefed_at(journey=journey, briefs=briefs)
        cooldown_until = self._active_cooldown(
            briefs=briefs,
            current_experiment=current_experiment,
            now=now,
        )
        has_open_brief = any(
            str(brief.get("status") or "").strip() in {"candidate", "shown"} for brief in briefs
        )
        status = str(journey.get("status") or "active").strip()
        fresh_signal = (
            last_briefed_at is None
            or self._parse_datetime(last_touched_at) > self._parse_datetime(last_briefed_at)
        )
        quiet_window_days = 14 if family in {"symbol_body_life_pressure", "cross_family"} else 7
        signal_is_recent = self._parse_datetime(last_touched_at) >= now - timedelta(days=quiet_window_days)
        stabilized = self._successful_stabilization(
            practices=practices,
            related_body_states=related_body_states,
            now=now,
        )
        base_readiness: Literal["quiet", "available", "ready"]
        if has_open_brief:
            base_readiness = "quiet"
            reasons.append("journey_brief_pending")
        elif cooldown_until is not None:
            base_readiness = "quiet"
            reasons.append("journey_brief_cooldown_active")
        elif practice_signal["kind"] in {"due_followup", "repeated_skip", "return_after_absence"}:
            base_readiness = "ready"
        elif fresh_signal and signal_is_recent:
            base_readiness = "ready"
        elif fresh_signal:
            base_readiness = "available"
        else:
            base_readiness = "available"
        experiment_status = (
            str(current_experiment.get("status") or "").strip()
            if isinstance(current_experiment, dict)
            else ""
        )
        experiment_due = (
            str(current_experiment.get("nextCheckInDueAt") or "").strip()
            if isinstance(current_experiment, dict)
            else ""
        )
        experiment_has_linked_brief = bool(
            current_experiment
            and any(
                cast(Id, current_experiment["id"]) in self._ids(brief.get("relatedExperimentIds"))
                for brief in briefs
                if str(brief.get("status") or "").strip() != "deleted"
            )
        )
        readiness: Literal["quiet", "available", "ready"]
        if status in {"paused", "completed", "archived"}:
            readiness = "quiet"
            reasons.append(f"journey_status_{status}")
        elif experiment_status == "quiet" and not fresh_signal:
            readiness = "quiet"
            reasons.append("journey_experiment_quiet")
        elif cooldown_until is not None:
            readiness = "quiet"
        elif stabilized and not fresh_signal:
            readiness = "quiet"
            reasons.append("journey_recent_practice_quieting")
        elif experiment_status == "active" and fresh_signal:
            readiness = base_readiness
        elif (
            experiment_status == "active"
            and experiment_due
            and self._parse_datetime(experiment_due) <= now
            and not experiment_has_linked_brief
        ):
            readiness = "available"
            reasons.append("journey_experiment_checkin_window_open")
        elif experiment_status == "active":
            readiness = "quiet"
            reasons.append("journey_experiment_holding")
        else:
            readiness = base_readiness
        recommended_surface = self._recommended_surface(
            readiness=readiness,
            move_kind=recommended_move,
            practice_signal=practice_signal["kind"],
        )
        summary: JourneyFollowthroughSummary = {
            "journeyId": journey_id,
            "family": family,
            "readiness": readiness,
            "recommendedSurface": recommended_surface,
            "bodyFirst": body_first,
            "priority": priority,
            "reasons": self._dedupe_strings(reasons),
            "blockedEscalations": list(_BLOCKED_ESCALATIONS[family]),
            "relatedExperimentIds": (
                [cast(Id, current_experiment["id"])] if current_experiment else []
            ),
            "relatedPracticeSessionIds": [
                cast(Id, str(item["id"]))
                for item in practices
                if str(item.get("id") or "").strip()
            ],
            "relatedBodyStateIds": related_body_state_ids,
            "relatedGoalTensionIds": related_goal_tension_ids,
            "lastTouchedAt": last_touched_at,
        }
        if recommended_move is not None and readiness != "quiet":
            summary["recommendedMoveKind"] = recommended_move
        if experiment_status:
            summary["currentExperimentStatus"] = cast(
                Literal["active", "quiet", "completed", "released", "archived", "deleted"],
                experiment_status,
            )
        if last_briefed_at is not None:
            summary["lastBriefedAt"] = last_briefed_at
        if cooldown_until is not None:
            summary["cooldownUntil"] = cooldown_until
        return summary

    def _detect_family(
        self,
        *,
        journey: JourneyRecord,
        practice_signal: dict[str, object],
        related_body_states: list[dict[str, object]],
        related_goal_tension_ids: list[Id],
        related_digests: list[ThreadDigest],
        typology_state: dict[str, object],
    ) -> JourneyFamilyKind:
        if practice_signal["kind"] != "none":
            return "practice_reentry"
        has_related_scene = any(
            str(digest.get("kind") or "").strip() == "relational_scene" for digest in related_digests
        )
        if related_body_states and journey.get("relatedSymbolIds") and related_goal_tension_ids:
            return "symbol_body_life_pressure"
        if related_body_states:
            return "embodied_recurrence"
        if has_related_scene:
            return "relational_scene_recurrence"
        if related_goal_tension_ids and typology_state:
            return "thought_loop_typology_restraint"
        return "cross_family"

    def _family_behavior(
        self,
        *,
        family: JourneyFamilyKind,
        practice_signal: dict[str, object],
        related_body_states: list[dict[str, object]],
        related_goal_tension_ids: list[Id],
        related_digests: list[ThreadDigest],
    ) -> tuple[int, CoachMoveKind | None, bool, list[str]]:
        reasons: list[str] = []
        if family == "practice_reentry":
            signal_kind = str(practice_signal["kind"])
            if signal_kind == "due_followup":
                if bool(practice_signal.get("bodyFirst")):
                    return 95, "offer_resource", True, [
                        "journey_practice_followup_due",
                        "journey_practice_activation_requires_gentler_reentry",
                    ]
                return 93, "ask_practice_followup", False, ["journey_practice_followup_due"]
            if signal_kind == "repeated_skip":
                return 90, "offer_resource", True, [
                    "journey_practice_repeated_skips",
                    "journey_practice_skip_softening",
                ]
            return 85, "return_to_journey", bool(related_body_states), [
                "journey_return_after_absence",
            ]
        if family == "embodied_recurrence":
            if self._body_pressure_level(related_body_states) >= 2:
                return 80, "offer_resource", True, ["journey_embodied_pressure_active"]
            return 80, "ask_body_checkin", True, ["journey_embodied_recurrence_active"]
        if family == "symbol_body_life_pressure":
            if self._body_pressure_level(related_body_states) >= 2:
                return 75, "ask_body_checkin", True, [
                    "journey_symbol_body_goal_convergence",
                    "journey_body_pressure_present",
                ]
            return 75, "return_to_journey", True, ["journey_symbol_body_goal_convergence"]
        if family == "relational_scene_recurrence":
            if self._body_pressure_level(related_body_states) >= 2:
                return 70, "return_to_journey", True, [
                    "journey_relational_scene_recurrence",
                    "journey_body_pressure_present",
                ]
            return 70, "ask_relational_scene", False, ["journey_relational_scene_recurrence"]
        if family == "thought_loop_typology_restraint":
            if related_goal_tension_ids:
                return 65, "ask_goal_tension", False, [
                    "journey_goal_tension_present",
                    "journey_typology_restraint_active",
                ]
            return 65, "track_without_prompt", False, ["journey_typology_restraint_active"]
        if related_digests or related_goal_tension_ids or related_body_states:
            reasons.append("journey_cross_family_thread_active")
        else:
            reasons.append("journey_cross_family_thread_available")
        return 60, "return_to_journey", bool(related_body_states), reasons

    def _practice_signal(
        self,
        *,
        practices: list[PracticeSessionRecord],
        practice_loop: dict[str, object],
        adaptation_profile: UserAdaptationProfileSummary | None,
        now: datetime,
        fallback_ts: str,
    ) -> dict[str, object]:
        sorted_practices = sorted(
            practices,
            key=lambda item: self._practice_timestamp(item, fallback=fallback_ts),
            reverse=True,
        )
        repeated_skips = [
            item for item in sorted_practices[:3] if str(item.get("status") or "").strip() == "skipped"
        ]
        repeated_skip_same_modality = bool(repeated_skips) and len(
            {
                str(item.get("modality") or item.get("practiceType") or "").strip()
                for item in repeated_skips
                if str(item.get("modality") or item.get("practiceType") or "").strip()
            }
        ) <= 1
        if len(repeated_skips) >= 2 and repeated_skip_same_modality:
            return {
                "kind": "repeated_skip",
                "practice": repeated_skips[0],
                "bodyFirst": True,
            }
        for practice in sorted_practices:
            status = str(practice.get("status") or "").strip()
            due_at = str(practice.get("nextFollowUpDueAt") or "").strip()
            if status not in {"recommended", "accepted", "completed", "skipped"}:
                continue
            if due_at and self._parse_datetime(due_at) > now:
                continue
            follow_up_count = int(practice.get("followUpCount", 0) or 0)
            if follow_up_count >= 2:
                continue
            after = str(practice.get("activationAfter") or "").strip()
            trend = str(practice_loop.get("recentOutcomeTrend") or "").strip()
            return {
                "kind": "due_followup",
                "practice": practice,
                "bodyFirst": after in {"high", "overwhelming"} or trend in {"activating", "mixed"},
            }
        if sorted_practices:
            last_touch = self._parse_datetime(self._practice_timestamp(sorted_practices[0], fallback=fallback_ts))
        else:
            last_touch = self._parse_datetime(fallback_ts)
        threshold_days = self._reentry_threshold_days(practices=sorted_practices, adaptation_profile=adaptation_profile)
        if now - last_touch >= timedelta(days=threshold_days):
            return {"kind": "return_after_absence", "bodyFirst": False}
        return {"kind": "none", "bodyFirst": False}

    def _reentry_threshold_days(
        self,
        *,
        practices: list[PracticeSessionRecord],
        adaptation_profile: UserAdaptationProfileSummary | None,
    ) -> float:
        threshold = 3.0
        if not self._adaptation_is_mature(adaptation_profile):
            return threshold
        timestamps = [
            self._parse_datetime(self._practice_timestamp(item, fallback="1970-01-01T00:00:00Z"))
            for item in reversed(practices[:5])
        ]
        if len(timestamps) < 2:
            return threshold
        gaps = [
            max((right - left).total_seconds() / 86400.0, 0.0)
            for left, right in zip(timestamps, timestamps[1:])
        ]
        if not gaps:
            return threshold
        return max(threshold, round(gaps[-1] * 2, 1))

    def _recommended_surface(
        self,
        *,
        readiness: Literal["quiet", "available", "ready"],
        move_kind: CoachMoveKind | None,
        practice_signal: str,
    ) -> CoachSurface | Literal["none"]:
        if readiness == "quiet":
            return "none"
        if move_kind == "ask_practice_followup" or practice_signal == "due_followup":
            return "practice_followup"
        if readiness == "ready":
            return "rhythmic_brief"
        if move_kind in {"ask_body_checkin", "offer_resource"}:
            return "alive_today"
        return "journey_page"

    def _last_touched_at(
        self,
        *,
        journey: JourneyRecord,
        current_experiment: JourneyExperimentRecord | None,
        practices: list[PracticeSessionRecord],
        related_body_states: list[dict[str, object]],
        related_digests: list[ThreadDigest],
        fallback: str,
    ) -> str:
        timestamps = [
            str(journey.get("updatedAt") or journey.get("createdAt") or fallback),
            *(
                [
                    str(
                        current_experiment.get("updatedAt")
                        or current_experiment.get("createdAt")
                        or fallback
                    )
                ]
                if current_experiment is not None
                else []
            ),
            *[
                self._practice_timestamp(item, fallback=fallback)
                for item in practices
            ],
            *[
                str(item.get("observedAt") or item.get("updatedAt") or item.get("createdAt") or fallback)
                for item in related_body_states
            ],
            *[
                str(item.get("lastTouchedAt") or fallback)
                for item in related_digests
            ],
        ]
        return max(timestamps)

    def _last_briefed_at(
        self,
        *,
        journey: JourneyRecord,
        briefs: list[ProactiveBriefRecord],
    ) -> str | None:
        timestamps = [
            str(journey.get("lastBriefedAt") or "").strip(),
            *[
                str(
                    brief.get("actedOnAt")
                    or brief.get("shownAt")
                    or brief.get("updatedAt")
                    or ""
                ).strip()
                for brief in briefs
                if str(brief.get("status") or "").strip() in {"shown", "acted_on"}
            ],
        ]
        filtered = [item for item in timestamps if item]
        return max(filtered) if filtered else None

    def _active_cooldown(
        self,
        *,
        briefs: list[ProactiveBriefRecord],
        current_experiment: JourneyExperimentRecord | None,
        now: datetime,
    ) -> str | None:
        active = [
            str(brief.get("cooldownUntil") or "").strip()
            for brief in briefs
            if str(brief.get("cooldownUntil") or "").strip()
            and self._parse_datetime(str(brief["cooldownUntil"])) > now
        ]
        if current_experiment is not None:
            experiment_cooldown = str(current_experiment.get("cooldownUntil") or "").strip()
            if experiment_cooldown and self._parse_datetime(experiment_cooldown) > now:
                active.append(experiment_cooldown)
        return max(active) if active else None

    def _current_experiment(
        self, experiments: list[JourneyExperimentRecord]
    ) -> tuple[JourneyExperimentRecord | None, str | None]:
        current = [
            item
            for item in experiments
            if str(item.get("status") or "").strip() in {"active", "quiet"}
        ]
        if not current:
            return None, None
        current.sort(
            key=lambda item: (
                1 if str(item.get("status") or "").strip() == "active" else 0,
                str(item.get("updatedAt") or item.get("createdAt") or ""),
            ),
            reverse=True,
        )
        reason = "journey_experiment_collision_resolved" if len(current) > 1 else None
        return current[0], reason

    def _successful_stabilization(
        self,
        *,
        practices: list[PracticeSessionRecord],
        related_body_states: list[dict[str, object]],
        now: datetime,
    ) -> bool:
        completed = next(
            (
                item
                for item in sorted(
                    practices,
                    key=lambda practice: self._practice_timestamp(
                        practice,
                        fallback=now.isoformat(),
                    ),
                    reverse=True,
                )
                if str(item.get("status") or "").strip() == "completed"
            ),
            None,
        )
        if completed is None:
            return False
        completed_at = self._parse_datetime(
            self._practice_timestamp(completed, fallback=now.isoformat())
        )
        if now - completed_at > timedelta(days=7):
            return False
        after_level = self._activation_rank(completed.get("activationAfter"))
        before_level = self._activation_rank(completed.get("activationBefore"))
        if after_level > before_level or after_level > 1:
            return False
        latest_body_after = max(
            (
                self._parse_datetime(
                    str(
                        body_state.get("observedAt")
                        or body_state.get("updatedAt")
                        or body_state.get("createdAt")
                        or completed_at.isoformat()
                    )
                )
                for body_state in related_body_states
            ),
            default=completed_at,
        )
        return latest_body_after <= completed_at

    def _body_pressure_level(self, body_states: list[dict[str, object]]) -> int:
        if not body_states:
            return 0
        return max(self._activation_rank(item.get("activation")) for item in body_states)

    def _journey_ids_from_digest(self, digest: ThreadDigest) -> list[Id]:
        journey_ids = self._ids(digest.get("journeyIds"))
        entity_refs = digest.get("entityRefs") if isinstance(digest.get("entityRefs"), dict) else {}
        return self._dedupe_ids(
            [
                *journey_ids,
                *self._ids(entity_refs.get("journeys")),
            ]
        )

    def _adaptation_is_mature(
        self,
        adaptation_profile: UserAdaptationProfileSummary | None,
    ) -> bool:
        if not isinstance(adaptation_profile, dict):
            return False
        learned_signals = (
            adaptation_profile.get("learnedSignals")
            if isinstance(adaptation_profile.get("learnedSignals"), dict)
            else {}
        )
        return bool(learned_signals.get("matured")) or int(
            adaptation_profile.get("sampleCounts", {}).get("total", 0)
        ) >= 20

    def _practice_timestamp(self, practice: PracticeSessionRecord, *, fallback: str) -> str:
        return str(
            practice.get("completedAt")
            or practice.get("skippedAt")
            or practice.get("nextFollowUpDueAt")
            or practice.get("updatedAt")
            or practice.get("createdAt")
            or fallback
        )

    def _activation_rank(self, value: object) -> int:
        key = str(value or "").strip()
        return _ACTIVATION_ORDER.get(key, 1)

    def _intersects(self, left: list[Id], right: list[Id]) -> bool:
        return bool(set(left).intersection(right))

    def _dict(self, value: object) -> dict[str, object]:
        return dict(value) if isinstance(value, dict) else {}

    def _dict_list(self, value: object) -> list[dict[str, object]]:
        if not isinstance(value, list):
            return []
        return [dict(item) for item in value if isinstance(item, dict)]

    def _ids(self, value: object) -> list[Id]:
        if isinstance(value, list):
            return self._dedupe_ids([str(item) for item in value if str(item).strip()])
        if isinstance(value, str) and value.strip():
            return [cast(Id, value.strip())]
        return []

    def _dedupe_ids(self, values: list[str]) -> list[Id]:
        deduped: list[str] = []
        for value in values:
            candidate = str(value).strip()
            if candidate and candidate not in deduped:
                deduped.append(candidate)
        return cast(list[Id], deduped)

    def _dedupe_strings(self, values: list[str]) -> list[str]:
        deduped: list[str] = []
        for value in values:
            candidate = str(value).strip()
            if candidate and candidate not in deduped:
                deduped.append(candidate)
        return deduped

    def _parse_datetime(self, value: str | None) -> datetime:
        return parse_iso_datetime(value, default=datetime.now(UTC))
