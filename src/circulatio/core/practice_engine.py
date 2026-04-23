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
from ..domain.timestamps import format_iso_datetime, parse_iso_datetime
from ..domain.types import (
    CoachLoopKind,
    CoachMoveKind,
    DepthReadinessAssessment,
    Id,
    MethodContextSnapshot,
    MethodGateResult,
    PracticeAdaptationHints,
    PracticeOutcomeWritePayload,
    PracticePlan,
    PracticeTriggerSummary,
    ResourceInvitationSummary,
    RuntimeHintSource,
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
            return {"maturity": "default", "source": "default"}
        explicit = profile.get("explicitPreferences", {}).get("practice", {})
        learned = profile.get("learnedSignals", {}).get("practicePolicy", {})
        explicit_scope = explicit if isinstance(explicit, dict) else {}
        learned_scope = learned if isinstance(learned, dict) else {}
        total = int(profile.get("sampleCounts", {}).get("total", 0))
        hints: PracticeAdaptationHints = {
            "maturity": "mature" if total >= 20 else "learning" if total > 0 else "default",
            "source": self._hint_source(explicit_scope=explicit_scope, learned_scope=learned_scope),
        }
        preferred = self._resolve_string_list(
            explicit_scope=explicit_scope,
            learned_scope=learned_scope,
            key="preferredModalities",
        )
        avoided = self._resolve_string_list(
            explicit_scope=explicit_scope,
            learned_scope=learned_scope,
            key="avoidedModalities",
        )
        if preferred:
            hints["preferredModalities"] = preferred
        if avoided:
            hints["avoidedModalities"] = [item for item in avoided if item not in preferred]
        max_duration = self._resolve_value(
            explicit_scope=explicit_scope,
            learned_scope=learned_scope,
            key="maxDurationMinutes",
        )
        if isinstance(max_duration, int) and max_duration > 0:
            hints["maxDurationMinutes"] = max_duration
        return hints

    def reconcile_llm_practice(
        self,
        *,
        practice: PracticePlan | None,
        safety: SafetyDisposition,
        method_gate: MethodGateResult | None,
        depth_readiness: DepthReadinessAssessment | None,
        consent_preferences: list[dict[str, object]],
        practice_hints: PracticeAdaptationHints | None = None,
        adaptation_hints: PracticeAdaptationHints | None = None,
        goal_tensions: list[dict[str, object]] | None = None,
        body_states: list[dict[str, object]] | None = None,
        method_context: MethodContextSnapshot | None = None,
        runtime_policy: dict[str, object] | None = None,
        fallback_reason: str | None = None,
    ) -> PracticePlan:
        notes: list[str] = []
        resolved_goal_tensions = goal_tensions or []
        resolved_body_states = body_states or []
        if practice_hints is not None:
            resolved_hints: PracticeAdaptationHints = practice_hints
        elif adaptation_hints is not None:
            resolved_hints = adaptation_hints
        else:
            resolved_hints = {"maturity": "default", "source": "default"}
        source_experiment_ids = (
            [str(item) for item in practice.get("relatedExperimentIds", []) if str(item).strip()]
            if isinstance(practice, dict)
            else []
        )

        def finalize(candidate: PracticePlan, extra_notes: list[str]) -> PracticePlan:
            framed = self._with_notes(candidate, extra_notes)
            framed = self._apply_method_state_practice_frame(
                framed,
                method_context=method_context,
                runtime_policy=runtime_policy,
            )
            if source_experiment_ids and not framed.get("relatedExperimentIds"):
                framed["relatedExperimentIds"] = cast(list[Id], source_experiment_ids)
            return self._annotate_target_refs(
                framed,
                goal_tensions=resolved_goal_tensions,
                body_states=resolved_body_states,
            )

        if not safety["depthWorkAllowed"]:
            plan = self._fallback_plan("grounding")
            notes.append("safety_blocked_grounding_fallback")
            return finalize(plan, notes)

        if method_gate and method_gate.get("depthLevel") == "grounding_only" and practice is None:
            plan = self._fallback_plan("grounding")
            notes.append("method_state_grounding_first_fallback")
            return finalize(plan, notes)

        if practice is None:
            plan = self._fallback_plan("journaling")
            notes.append(fallback_reason or "llm_missing_practice_fallback_to_journaling")
            return finalize(plan, notes)

        plan = deepcopy(practice)
        plan.setdefault("id", create_id("practice"))
        plan.setdefault("contraindicationsChecked", ["none"])
        plan.setdefault("durationMinutes", 8)
        plan.setdefault("requiresConsent", False)
        plan.setdefault("instructions", [])
        notes.extend([str(item) for item in plan.get("adaptationNotes", []) if str(item).strip()])

        practice_type = str(plan.get("type") or "journaling")
        if method_gate and method_gate.get("depthLevel") == "grounding_only":
            if practice_type not in {"grounding", "body_checkin", "somatic_tracking"}:
                notes.append("method_state_grounding_first_fallback")
                return finalize(self._fallback_plan("grounding"), notes)
        blocked_moves = set(method_gate.get("blockedMoves", []) if method_gate else [])
        allowed_moves = depth_readiness.get("allowedMoves", {}) if depth_readiness else {}
        consent_status = {
            str(item.get("scope")): str(item.get("status"))
            for item in consent_preferences
            if isinstance(item, dict) and item.get("scope")
        }
        required_scope = self._required_scope(practice_type)
        if required_scope and consent_status.get(required_scope) in {"declined", "revoked"}:
            notes.append(f"{required_scope}_blocked_by_consent_fallback_to_journaling")
            return finalize(self._fallback_plan("journaling"), notes)
        if practice_type == "active_imagination" and (
            "active_imagination" in blocked_moves
            or allowed_moves.get("active_imagination") not in {None, "allow", "ask_consent"}
        ):
            notes.append("active_imagination_blocked_by_method_fallback_to_journaling")
            return finalize(self._fallback_plan("journaling"), notes)
        if required_scope and required_scope in blocked_moves:
            notes.append(f"{required_scope}_blocked_by_method_fallback_to_journaling")
            return finalize(self._fallback_plan("journaling"), notes)
        if plan.get("requiresConsent") and required_scope:
            if consent_status.get(required_scope) == "ask_each_time":
                notes.append(f"{required_scope}_requires_explicit_acceptance")
        max_duration = resolved_hints.get("maxDurationMinutes")
        if isinstance(max_duration, int) and max_duration > 0:
            current_duration = int(plan.get("durationMinutes") or 0)
            if current_duration > max_duration:
                plan["durationMinutes"] = max_duration
                notes.append("duration_clamped_to_explicit_preference")
        return finalize(
            plan,
            notes,
        )

    def _resolve_value(
        self,
        *,
        explicit_scope: dict[str, object],
        learned_scope: dict[str, object],
        key: str,
    ) -> object | None:
        if key in explicit_scope:
            return explicit_scope.get(key)
        return learned_scope.get(key)

    def _resolve_string_list(
        self,
        *,
        explicit_scope: dict[str, object],
        learned_scope: dict[str, object],
        key: str,
    ) -> list[str]:
        raw = self._resolve_value(
            explicit_scope=explicit_scope, learned_scope=learned_scope, key=key
        )
        if not isinstance(raw, list):
            return []
        return list(dict.fromkeys(str(item).strip() for item in raw if str(item).strip()))

    def _hint_source(
        self,
        *,
        explicit_scope: dict[str, object],
        learned_scope: dict[str, object],
    ) -> RuntimeHintSource:
        keys = {"preferredModalities", "avoidedModalities", "maxDurationMinutes"}
        explicit_hits = any(key in explicit_scope for key in keys)
        learned_hits = any(key in learned_scope for key in keys)
        if explicit_hits and learned_hits:
            return "mixed"
        if explicit_hits:
            return "explicit"
        if learned_hits:
            return "learned"
        return "default"

    def _annotate_target_refs(
        self,
        plan: PracticePlan,
        *,
        goal_tensions: list[dict[str, object]],
        body_states: list[dict[str, object]],
    ) -> PracticePlan:
        tension_id = next(
            (
                str(item.get("id"))
                for item in goal_tensions
                if isinstance(item, dict) and str(item.get("id") or "").strip()
            ),
            None,
        )
        if tension_id:
            plan["targetedTensionId"] = tension_id
        body_state_id = next(
            (
                str(item.get("id"))
                for item in body_states
                if isinstance(item, dict) and str(item.get("id") or "").strip()
            ),
            None,
        )
        if body_state_id:
            plan["targetedBodyStateId"] = body_state_id
        return plan

    def _apply_method_state_practice_frame(
        self,
        plan: PracticePlan,
        *,
        method_context: MethodContextSnapshot | None,
        runtime_policy: dict[str, object] | None,
    ) -> PracticePlan:
        if not isinstance(method_context, dict):
            return plan
        result = deepcopy(plan)
        method_state_value = method_context.get("methodState")
        method_state: dict[str, object] = (
            dict(method_state_value) if isinstance(method_state_value, dict) else {}
        )
        coach_state_value = method_context.get("coachState")
        coach_state: dict[str, object] = (
            dict(coach_state_value) if isinstance(coach_state_value, dict) else {}
        )
        selected_move_value = coach_state.get("selectedMove")
        selected_move: dict[str, object] = (
            dict(selected_move_value) if isinstance(selected_move_value, dict) else {}
        )
        active_loops_value = coach_state.get("activeLoops")
        active_loops: list[dict[str, object]] = (
            [item for item in active_loops_value if isinstance(item, dict)]
            if isinstance(active_loops_value, list)
            else []
        )
        selected_loop = next(
            (
                item
                for item in active_loops
                if str(item.get("loopKey") or "").strip()
                == str(selected_move.get("loopKey") or "").strip()
            ),
            None,
        )
        runtime_policy_dict: dict[str, object] = (
            runtime_policy if isinstance(runtime_policy, dict) else {}
        )
        runtime_constraints_value = runtime_policy_dict.get("practiceConstraints")
        runtime_constraints: dict[str, object] = (
            dict(runtime_constraints_value) if isinstance(runtime_constraints_value, dict) else {}
        )
        active_goal_tension_value = method_state.get("activeGoalTension")
        active_goal_tension: dict[str, object] = (
            dict(active_goal_tension_value) if isinstance(active_goal_tension_value, dict) else {}
        )
        practice_loop_value = method_state.get("practiceLoop")
        practice_loop: dict[str, object] = (
            dict(practice_loop_value) if isinstance(practice_loop_value, dict) else {}
        )
        compensation_tendencies_value = method_state.get("compensationTendencies")
        compensation_tendencies: list[dict[str, object]] = (
            [item for item in compensation_tendencies_value if isinstance(item, dict)]
            if isinstance(compensation_tendencies_value, list)
            else []
        )
        notes = [str(item) for item in result.get("adaptationNotes", []) if str(item).strip()]
        instructions = [str(item) for item in result.get("instructions", []) if str(item).strip()]
        practice_type = str(result.get("type") or "journaling")
        current_modality = str(result.get("modality") or "").strip().lower()
        selected_loop_kind = (
            str(selected_loop.get("kind") or "").strip()
            if isinstance(selected_loop, dict)
            else ""
        )
        selected_move_kind = str(selected_move.get("kind") or "").strip()
        if str(selected_move.get("loopKey") or "").strip():
            result["coachLoopKey"] = str(selected_move["loopKey"])
        if selected_loop_kind:
            result["coachLoopKind"] = cast(CoachLoopKind, selected_loop_kind)
        if selected_move_kind:
            result["coachMoveKind"] = cast(CoachMoveKind, selected_move_kind)
        resource_invitation_value = selected_move.get("resourceInvitation")
        resource_invitation = (
            dict(resource_invitation_value)
            if isinstance(resource_invitation_value, dict)
            else {}
        )
        resource_invitation_id = str(resource_invitation.get("id") or "").strip()
        if resource_invitation_id:
            result["resourceInvitationId"] = resource_invitation_id
            result["resourceInvitation"] = cast(
                ResourceInvitationSummary,
                deepcopy(resource_invitation),
            )
        related_resource_ids_value = selected_move.get("relatedResourceIds")
        related_resource_ids = (
            [str(item) for item in related_resource_ids_value if str(item).strip()]
            if isinstance(related_resource_ids_value, list)
            else []
        )
        if not related_resource_ids and resource_invitation:
            resource = resource_invitation.get("resource")
            resource_id = (
                str(resource.get("id") or "").strip()
                if isinstance(resource, dict)
                else ""
            )
            if resource_id:
                related_resource_ids = [resource_id]
        if related_resource_ids:
            result["relatedResourceIds"] = cast(list[Id], related_resource_ids)
        related_experiment_ids_value = selected_move.get("relatedExperimentIds")
        related_experiment_ids = (
            [str(item) for item in related_experiment_ids_value if str(item).strip()]
            if isinstance(related_experiment_ids_value, list)
            else []
        )
        if not related_experiment_ids and isinstance(selected_loop, dict):
            loop_experiment_ids_value = selected_loop.get("relatedExperimentIds")
            if isinstance(loop_experiment_ids_value, list):
                related_experiment_ids = [
                    str(item) for item in loop_experiment_ids_value if str(item).strip()
                ]
        if related_experiment_ids:
            result["relatedExperimentIds"] = cast(list[Id], related_experiment_ids)

        max_duration = runtime_constraints.get("maxDurationMinutes")
        if not isinstance(max_duration, int):
            max_duration = practice_loop.get("maxDurationMinutes")
        if isinstance(max_duration, int) and max_duration > 0:
            current_duration = int(result.get("durationMinutes") or 0)
            if current_duration <= 0 or current_duration > max_duration:
                result["durationMinutes"] = max_duration
                notes.append("duration_clamped_to_method_state_loop")

        if (
            runtime_constraints.get("preferLowIntensity")
            or practice_loop.get("recommendedIntensity") == "low"
        ):
            if int(result.get("durationMinutes") or 0) > 6:
                result["durationMinutes"] = 6
                notes.append("duration_shortened_for_low_intensity")
            if str(result.get("intensity") or "").strip() not in {"", "low"}:
                result["intensity"] = "low"
                notes.append("intensity_downgraded_by_method_state")

        preferred_modalities = self._resolve_string_list(
            explicit_scope=runtime_constraints,
            learned_scope=practice_loop,
            key="preferredModalities",
        )
        avoided_modalities = [
            item
            for item in self._resolve_string_list(
                explicit_scope=runtime_constraints,
                learned_scope=practice_loop,
                key="avoidedModalities",
            )
            if item not in preferred_modalities
        ]
        if (
            current_modality
            and current_modality in avoided_modalities
            and current_modality not in preferred_modalities
        ):
            if current_modality == "imaginal" and practice_type == "active_imagination":
                result = self._fallback_plan("journaling")
                instructions = [
                    str(item) for item in result.get("instructions", []) if str(item).strip()
                ]
                notes.append("avoided_imaginal_modality_fallback_to_journaling")
                practice_type = str(result.get("type") or "journaling")
            else:
                notes.append("current_modality_marked_as_avoided")

        goal_frame = str(runtime_policy_dict.get("activeGoalFrame") or "").strip()
        if not goal_frame and active_goal_tension:
            goal_frame = str(active_goal_tension.get("balancingDirection") or "").strip()
        goal_tension_id = str(active_goal_tension.get("goalTensionId") or "").strip()
        if goal_tension_id:
            result["targetedTensionId"] = goal_tension_id
        if goal_frame and goal_frame not in instructions:
            instructions.append(goal_frame)
            notes.append("goal_tension_frame_added")

        compensation_prompt = str(runtime_constraints.get("compensationPrompt") or "").strip()
        if not compensation_prompt:
            first_compensation = compensation_tendencies[0] if compensation_tendencies else None
            if isinstance(first_compensation, dict):
                compensation_prompt = str(first_compensation.get("userTestPrompt") or "").strip()
        if compensation_prompt and compensation_prompt not in instructions:
            instructions.append(compensation_prompt)
            notes.append("compensation_prompt_added_from_method_state")

        practice_bias = str(runtime_constraints.get("practiceBias") or "").strip()
        bias_instruction_map = {
            "sensation_grounding": "Start with the body before explaining the pattern.",
            "image_tracking": "Name the strongest image before interpreting it.",
            "value_discernment": "Let each side of the value tension speak in its own words.",
            "pattern_noting": "Note the repeating pattern before deciding what it means.",
        }
        bias_instruction = bias_instruction_map.get(practice_bias, "")
        if bias_instruction and bias_instruction not in instructions:
            instructions.append(bias_instruction)
            notes.append("practice_bias_instruction_added")

        if isinstance(selected_loop, dict):
            related_body_state_ids_value = selected_loop.get("relatedBodyStateIds")
            related_body_state_ids = (
                [str(item) for item in related_body_state_ids_value if str(item).strip()]
                if isinstance(related_body_state_ids_value, list)
                else []
            )
            if related_body_state_ids and not str(result.get("targetedBodyStateId") or "").strip():
                result["targetedBodyStateId"] = related_body_state_ids[0]
            related_scene_ids_value = selected_loop.get("relatedRelationalSceneIds")
            related_scene_ids = (
                [str(item) for item in related_scene_ids_value if str(item).strip()]
                if isinstance(related_scene_ids_value, list)
                else []
            )
            if related_scene_ids and not str(result.get("targetedRelationalSceneId") or "").strip():
                result["targetedRelationalSceneId"] = related_scene_ids[0]

        if selected_move_kind == "offer_resource" and selected_loop_kind == "resource_support":
            if int(result.get("durationMinutes") or 0) > 5:
                result["durationMinutes"] = 5
            if str(result.get("intensity") or "").strip() != "low":
                result["intensity"] = "low"
            notes.append("coach_loop_prefers_gentler_modality")
            resource_follow_up = str(
                resource_invitation.get("resource", {}).get("followUpQuestion") or ""
            ).strip()
            if resource_follow_up and not str(result.get("followUpPrompt") or "").strip():
                result["followUpPrompt"] = resource_follow_up
        elif (
            selected_move_kind in {"ask_practice_followup", "offer_resource"}
            and selected_loop_kind == "practice_integration"
            and practice_loop.get("recentOutcomeTrend") in {"activating", "mixed"}
        ):
            if int(result.get("durationMinutes") or 0) > 6:
                result["durationMinutes"] = 6
            result["intensity"] = "low"
            notes.append("coach_loop_prefers_gentler_modality")
            resource_follow_up = str(
                resource_invitation.get("resource", {}).get("followUpQuestion") or ""
            ).strip()
            if resource_follow_up and not str(result.get("followUpPrompt") or "").strip():
                result["followUpPrompt"] = resource_follow_up

        if practice_type in {
            "journaling",
            "active_imagination",
            "body_checkin",
            "somatic_tracking",
        }:
            result["instructions"] = instructions[:6]
        if notes:
            result["adaptationNotes"] = list(dict.fromkeys(notes))[:8]
        return result

    def derive_lifecycle_defaults(
        self,
        *,
        practice: PracticePlan,
        created_at: str,
        trigger: PracticeTriggerSummary,
    ) -> PracticeLifecycleDefaults:
        created_dt = parse_iso_datetime(created_at, default=datetime.now(UTC))
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
            "nextFollowUpDueAt": format_iso_datetime(
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
