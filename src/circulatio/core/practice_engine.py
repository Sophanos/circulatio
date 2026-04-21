from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from typing import cast

from ..domain.adaptation import AdaptationSignalEvent, UserAdaptationProfileRecord
from ..domain.ids import create_id, now_iso
from ..domain.practices import (
    PracticeLifecycleAction,
    PracticeLifecycleDefaults,
    PracticeSessionRecord,
    PracticeSessionSource,
    PracticeSessionStatus,
)
from ..domain.types import (
    DepthReadinessAssessment,
    MethodGateResult,
    PracticeAdaptationHints,
    PracticeOutcomeWritePayload,
    PracticePlan,
    PracticeTriggerSummary,
    SafetyDisposition,
)
from .interpretation_fallbacks import _GROUNDING_FALLBACK, _JOURNALING_FALLBACK

_ACTIVATION_LEVEL = {"low": 1, "moderate": 2, "high": 3}


class PracticeEngine:
    def build_adaptation_hints(
        self,
        *,
        profile: UserAdaptationProfileRecord | None,
    ) -> PracticeAdaptationHints:
        if profile is None:
            return {"maturity": "insufficient_data", "notes": ["No adaptation profile yet."]}
        hints: PracticeAdaptationHints = {
            "maturity": "mature"
            if int(profile.get("sampleCounts", {}).get("total", 0)) >= 20
            else "learning",
            "notes": [],
        }
        practice_preferences = profile.get("explicitPreferences", {}).get("practice", {})
        if isinstance(practice_preferences, dict):
            preferred_modalities = practice_preferences.get("preferredModalities")
            if isinstance(preferred_modalities, list):
                hints["preferredModalities"] = [
                    str(item) for item in preferred_modalities if str(item).strip()
                ]
            max_duration = practice_preferences.get("maxDurationMinutes")
            if isinstance(max_duration, int) and max_duration > 0:
                hints["maxDurationMinutes"] = max_duration
            preferred_duration = practice_preferences.get("preferredDurationMinutes")
            if isinstance(preferred_duration, int) and preferred_duration > 0:
                hints["preferredDurationMinutes"] = preferred_duration
            intensity = str(practice_preferences.get("intensityPreference") or "").strip()
            if intensity == "low":
                hints["intensityPreference"] = "low"
            elif intensity == "moderate":
                hints["intensityPreference"] = "moderate"
        return hints

    def reconcile_llm_practice(
        self,
        *,
        practice: PracticePlan | None,
        safety: SafetyDisposition,
        method_gate: MethodGateResult | None,
        depth_readiness: DepthReadinessAssessment | None,
        consent_preferences: list[dict[str, object]],
        adaptation_hints: PracticeAdaptationHints | None = None,
        fallback_reason: str | None = None,
    ) -> PracticePlan:
        notes: list[str] = []
        if not safety["depthWorkAllowed"]:
            plan = self._fallback_plan("grounding")
            notes.append("safety_blocked_grounding_fallback")
            return self._with_notes(plan, notes)

        if practice is None:
            plan = self._fallback_plan("journaling")
            notes.append(fallback_reason or "llm_missing_practice_fallback_to_journaling")
            return self._with_notes(plan, notes)

        plan = deepcopy(practice)
        plan.setdefault("id", create_id("practice"))
        plan.setdefault("contraindicationsChecked", ["none"])
        plan.setdefault("durationMinutes", 8)
        plan.setdefault("requiresConsent", False)
        plan.setdefault("instructions", [])
        notes.extend([str(item) for item in plan.get("adaptationNotes", []) if str(item).strip()])

        practice_type = str(plan.get("type") or "journaling")
        blocked_moves = set(method_gate.get("blockedMoves", []) if method_gate else [])
        allowed_moves = depth_readiness.get("allowedMoves", {}) if depth_readiness else {}
        consent_status = {
            str(item.get("scope")): str(item.get("status"))
            for item in consent_preferences
            if isinstance(item, dict) and item.get("scope")
        }
        required_scope = self._required_scope(practice_type)
        if practice_type == "active_imagination" and (
            "active_imagination" in blocked_moves
            or allowed_moves.get("active_imagination") not in {None, "allow", "ask_consent"}
        ):
            notes.append("active_imagination_blocked_by_method_fallback_to_journaling")
            return self._with_notes(self._fallback_plan("journaling"), notes)
        if required_scope and required_scope in blocked_moves:
            notes.append(f"{required_scope}_blocked_by_method_fallback_to_journaling")
            return self._with_notes(self._fallback_plan("journaling"), notes)
        if required_scope and consent_status.get(required_scope) in {"declined", "revoked"}:
            notes.append(f"{required_scope}_blocked_by_consent_fallback_to_journaling")
            return self._with_notes(self._fallback_plan("journaling"), notes)
        if plan.get("requiresConsent") and required_scope:
            if consent_status.get(required_scope) == "ask_each_time":
                notes.append(f"{required_scope}_requires_explicit_acceptance")
        max_duration = adaptation_hints.get("maxDurationMinutes") if adaptation_hints else None
        if isinstance(max_duration, int) and max_duration > 0:
            current_duration = int(plan.get("durationMinutes") or 0)
            if current_duration > max_duration:
                plan["durationMinutes"] = max_duration
                notes.append("duration_clamped_to_explicit_preference")
        return self._with_notes(plan, notes)

    def derive_lifecycle_defaults(
        self,
        *,
        practice: PracticePlan,
        created_at: str,
        trigger: PracticeTriggerSummary,
    ) -> PracticeLifecycleDefaults:
        created_dt = self._parse_datetime(created_at)
        trigger_type = str(trigger.get("triggerType") or "manual")
        follow_up_hours = {
            "manual": 24,
            "interpretation": 24,
            "weekly_review": 48,
            "alive_today": 36,
            "practice_followup": 24,
            "rhythmic_brief": 24,
        }.get(trigger_type, 24)
        defaults: PracticeLifecycleDefaults = {
            "source": self._source_for_trigger(trigger_type),
            "nextFollowUpDueAt": self._format_datetime(
                created_dt + timedelta(hours=follow_up_hours)
            ),
            "followUpCount": 0,
        }
        brief_id = trigger.get("briefId")
        if brief_id:
            defaults["relatedBriefId"] = brief_id
        return defaults

    def validate_transition(
        self,
        *,
        current_status: PracticeSessionStatus,
        target_status: PracticeSessionStatus,
    ) -> None:
        allowed: dict[PracticeSessionStatus, set[PracticeSessionStatus]] = {
            "recommended": {"accepted", "skipped", "completed", "deleted"},
            "accepted": {"completed", "skipped", "deleted"},
            "completed": {"completed", "deleted"},
            "skipped": {"accepted", "completed", "deleted"},
            "deleted": set(),
        }
        if target_status not in allowed.get(current_status, set()):
            raise ValueError(
                f"Practice session cannot transition from {current_status} to {target_status}."
            )

    def summarize_outcome_signal(
        self,
        *,
        practice: PracticeSessionRecord,
        previous_status: PracticeSessionStatus | None,
        outcome: PracticeOutcomeWritePayload | None,
        action: PracticeLifecycleAction,
    ) -> AdaptationSignalEvent:
        event_type = (
            "practice_outcome_recorded" if action == "outcome_recorded" else f"practice_{action}"
        )
        signals: dict[str, object] = {
            "practiceType": practice["practiceType"],
            "durationMinutes": practice.get("durationMinutes", 0),
            "modality": practice.get("modality"),
            "intensity": practice.get("intensity"),
            "templateId": practice.get("templateId"),
            "source": practice.get("source"),
            "previousStatus": previous_status,
        }
        success: bool | None = True if action == "completed" else None
        if outcome is not None:
            signals["outcome"] = outcome.get("outcome")
            before = outcome.get("activationBefore")
            after = outcome.get("activationAfter")
            if before:
                signals["activationBefore"] = before
            if after:
                signals["activationAfter"] = after
            if before and after:
                before_score = _ACTIVATION_LEVEL.get(before)
                after_score = _ACTIVATION_LEVEL.get(after)
                if before_score is not None and after_score is not None:
                    signals["activationImproved"] = after_score < before_score
                    signals["activationWorsened"] = after_score > before_score
                    signals["activationUnchanged"] = after_score == before_score
                    if action == "completed":
                        success = after_score <= before_score
        event: AdaptationSignalEvent = {
            "eventType": event_type,
            "timestamp": now_iso(),
            "signals": signals,
        }
        if success is not None:
            event["success"] = success
        return event

    def _fallback_plan(self, kind: str) -> PracticePlan:
        template = _GROUNDING_FALLBACK if kind == "grounding" else _JOURNALING_FALLBACK
        result = cast(PracticePlan, deepcopy(template))
        result["id"] = create_id("practice")
        return result

    def _with_notes(self, plan: PracticePlan, notes: list[str]) -> PracticePlan:
        result = deepcopy(plan)
        result["id"] = str(result.get("id") or create_id("practice"))
        merged = [str(item) for item in result.get("adaptationNotes", []) if str(item).strip()]
        for note in notes:
            if note and note not in merged:
                merged.append(note)
        if merged:
            result["adaptationNotes"] = merged[:8]
        return result

    def _required_scope(self, practice_type: str) -> str | None:
        if practice_type == "active_imagination":
            return "active_imagination"
        if practice_type in {"somatic_tracking", "body_checkin"}:
            return "somatic_correlation"
        return None

    def _source_for_trigger(self, trigger_type: str) -> PracticeSessionSource:
        mapping: dict[str, PracticeSessionSource] = {
            "interpretation": "interpretation",
            "weekly_review": "weekly_review",
            "alive_today": "alive_today",
            "manual": "manual",
            "rhythmic_brief": "rhythmic_brief",
            "practice_followup": "practice_followup",
            "threshold_review": "threshold_review",
            "living_myth_review": "living_myth_review",
            "analysis_packet": "analysis_packet",
        }
        return mapping.get(trigger_type, "manual")

    def _parse_datetime(self, value: str | None) -> datetime:
        if not value:
            return datetime.now(UTC)
        candidate = value.strip()
        if candidate.endswith("Z"):
            candidate = candidate[:-1] + "+00:00"
        parsed = datetime.fromisoformat(candidate)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)

    def _format_datetime(self, value: datetime) -> str:
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
