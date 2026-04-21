from __future__ import annotations

from copy import deepcopy
from typing import Literal, cast

from ..domain.adaptation import (
    AdaptationSignalEvent,
    RhythmCadenceHints,
    UserAdaptationProfileRecord,
)
from ..domain.ids import create_id, now_iso
from ..domain.types import (
    AdaptationPreferenceScope,
    CommunicationHints,
    CommunicationPreferenceSettings,
    CommunicationQuestioningStyle,
    CommunicationSymbolicDensity,
    CommunicationTone,
    InterpretationDepthPreference,
    InterpretationHints,
    InterpretationModalityBias,
    InterpretationPreferenceSettings,
    PracticeHints,
    PracticePreferenceSettings,
    RhythmPreferenceSettings,
    RuntimeHintSource,
    UserAdaptationProfileSummary,
)

_DEFAULT_COMMUNICATION: CommunicationPreferenceSettings = {
    "tone": "gentle",
    "questioningStyle": "reflective",
    "symbolicDensity": "moderate",
}
_DEFAULT_INTERPRETATION: InterpretationPreferenceSettings = {
    "depthPreference": "cautious_amplification",
    "modalityBias": "body",
}
_LEARNED_POLICY_KEYS: dict[AdaptationPreferenceScope, str] = {
    "communication": "communicationPolicy",
    "interpretation": "interpretationPolicy",
    "practice": "practicePolicy",
    "rhythm": "rhythmPolicy",
}
ValidatedPreferenceSettings = (
    CommunicationPreferenceSettings
    | InterpretationPreferenceSettings
    | PracticePreferenceSettings
    | RhythmPreferenceSettings
)


class AdaptationEngine:
    def ensure_profile(
        self, *, user_id: str, current: UserAdaptationProfileRecord | None = None
    ) -> UserAdaptationProfileRecord:
        if current is not None:
            return deepcopy(current)
        timestamp = now_iso()
        return {
            "id": create_id("adaptation_profile"),
            "userId": user_id,
            "explicitPreferences": {},
            "learnedSignals": {},
            "sampleCounts": {},
            "createdAt": timestamp,
            "updatedAt": timestamp,
            "status": "active",
        }

    def record_signal(
        self,
        *,
        profile: UserAdaptationProfileRecord,
        signal_key: str,
        success: bool | None = None,
    ) -> UserAdaptationProfileRecord:
        event: AdaptationSignalEvent = {
            "eventType": signal_key,
            "timestamp": now_iso(),
            "signals": {},
        }
        if success is not None:
            event["success"] = success
        return self.record_event(profile=profile, event=event)

    def record_event(
        self,
        *,
        profile: UserAdaptationProfileRecord,
        event: AdaptationSignalEvent,
    ) -> UserAdaptationProfileRecord:
        updated = deepcopy(profile)
        counts = dict(updated.get("sampleCounts", {}))
        learned = deepcopy(updated.get("learnedSignals", {}))
        weight = max(1, int(event.get("sampleWeight", 1)))
        event_type = event["eventType"]
        counts["total"] = int(counts.get("total", 0)) + weight
        counts[event_type] = int(counts.get(event_type, 0)) + weight
        recent_events = learned.get("recentEvents", [])
        if not isinstance(recent_events, list):
            recent_events = []
        recent_events = list(recent_events)[-24:] + [
            {
                "type": event_type,
                "signals": deepcopy(event.get("signals", {})),
                "timestamp": event["timestamp"],
            }
        ]
        learned["recentEvents"] = recent_events
        if counts["total"] >= 20:
            learned["matured"] = True
        if event_type.startswith("practice_"):
            self._update_practice_stats(
                learned=learned,
                counts=counts,
                event_type=event_type,
                signals=event.get("signals", {}),
            )
        if event_type.startswith("rhythmic_brief_"):
            self._update_rhythm_stats(
                learned=learned,
                signals=event.get("signals", {}),
                event_type=event_type,
            )
        if event_type.startswith("clarification_") or event_type in {
            "question_style_preferred",
            "question_style_avoided",
        }:
            self._update_questioning_stats(
                learned=learned,
                event_type=event_type,
                signals=event.get("signals", {}),
            )
        if event_type.startswith("interpretation_response_") or event_type in {
            "depth_pacing_corrected",
        }:
            self._update_interpretation_stats(
                learned=learned,
                event_type=event_type,
                signals=event.get("signals", {}),
            )
        if event_type.startswith("interaction_feedback_"):
            self._update_interaction_feedback_stats(
                learned=learned,
                event_type=event_type,
                signals=event.get("signals", {}),
            )
        if event.get("success") is not None:
            successes_key = f"{event_type}_successes"
            counts[successes_key] = int(counts.get(successes_key, 0)) + (
                1 if event["success"] else 0
            )
            if counts[event_type] >= 20:
                learned[f"{event_type}Rate"] = round(
                    counts[successes_key] / max(counts[event_type], 1), 3
                )
        updated["sampleCounts"] = counts
        updated["learnedSignals"] = learned
        updated["updatedAt"] = event["timestamp"]
        return updated

    def set_explicit_preferences(
        self,
        *,
        profile: UserAdaptationProfileRecord,
        scope: AdaptationPreferenceScope,
        preferences: dict[str, object],
    ) -> UserAdaptationProfileRecord:
        validated = self._validate_preferences(scope=scope, payload=preferences)
        updated = deepcopy(profile)
        explicit = deepcopy(updated.get("explicitPreferences", {}))
        explicit[scope] = validated
        updated["explicitPreferences"] = explicit
        updated["updatedAt"] = now_iso()
        return updated

    def set_learned_policy(
        self,
        *,
        profile: UserAdaptationProfileRecord,
        scope: AdaptationPreferenceScope,
        policy: dict[str, object],
    ) -> UserAdaptationProfileRecord:
        validated = self._validate_preferences(scope=scope, payload=policy)
        updated = deepcopy(profile)
        learned = deepcopy(updated.get("learnedSignals", {}))
        learned[_LEARNED_POLICY_KEYS[scope]] = validated
        updated["learnedSignals"] = learned
        updated["updatedAt"] = now_iso()
        return updated

    def derive_communication_hints(
        self,
        *,
        profile: UserAdaptationProfileRecord | None,
    ) -> CommunicationHints:
        if profile is None:
            return {
                "tone": _DEFAULT_COMMUNICATION["tone"],
                "questioningStyle": _DEFAULT_COMMUNICATION["questioningStyle"],
                "symbolicDensity": _DEFAULT_COMMUNICATION["symbolicDensity"],
                "source": "default",
            }
        explicit = self._scope_dict(profile, "explicitPreferences", "communication")
        learned = self._scope_dict(profile, "learnedSignals", _LEARNED_POLICY_KEYS["communication"])
        keys = ("tone", "questioningStyle", "symbolicDensity")
        tone = cast(
            CommunicationTone,
            self._resolve_scope_value(
                explicit=explicit,
                learned=learned,
                key="tone",
                default=_DEFAULT_COMMUNICATION["tone"],
            ),
        )
        questioning_style = cast(
            CommunicationQuestioningStyle,
            self._resolve_scope_value(
                explicit=explicit,
                learned=learned,
                key="questioningStyle",
                default=_DEFAULT_COMMUNICATION["questioningStyle"],
            ),
        )
        symbolic_density = cast(
            CommunicationSymbolicDensity,
            self._resolve_scope_value(
                explicit=explicit,
                learned=learned,
                key="symbolicDensity",
                default=_DEFAULT_COMMUNICATION["symbolicDensity"],
            ),
        )
        return {
            "tone": tone,
            "questioningStyle": questioning_style,
            "symbolicDensity": symbolic_density,
            "source": self._resolve_hint_source(explicit=explicit, learned=learned, keys=keys),
        }

    def derive_interpretation_hints(
        self,
        *,
        profile: UserAdaptationProfileRecord | None,
    ) -> InterpretationHints:
        if profile is None:
            return {
                "depthPreference": _DEFAULT_INTERPRETATION["depthPreference"],
                "modalityBias": _DEFAULT_INTERPRETATION["modalityBias"],
                "source": "default",
            }
        explicit = self._scope_dict(profile, "explicitPreferences", "interpretation")
        learned = self._scope_dict(
            profile, "learnedSignals", _LEARNED_POLICY_KEYS["interpretation"]
        )
        keys = ("depthPreference", "modalityBias")
        depth_preference = cast(
            InterpretationDepthPreference,
            self._resolve_scope_value(
                explicit=explicit,
                learned=learned,
                key="depthPreference",
                default=_DEFAULT_INTERPRETATION["depthPreference"],
            ),
        )
        modality_bias = cast(
            InterpretationModalityBias,
            self._resolve_scope_value(
                explicit=explicit,
                learned=learned,
                key="modalityBias",
                default=_DEFAULT_INTERPRETATION["modalityBias"],
            ),
        )
        return {
            "depthPreference": depth_preference,
            "modalityBias": modality_bias,
            "source": self._resolve_hint_source(explicit=explicit, learned=learned, keys=keys),
        }

    def derive_practice_hints(
        self,
        *,
        profile: UserAdaptationProfileRecord | None,
    ) -> PracticeHints:
        if profile is None:
            return {"maturity": "default", "source": "default"}
        explicit = self._scope_dict(profile, "explicitPreferences", "practice")
        learned = self._scope_dict(profile, "learnedSignals", _LEARNED_POLICY_KEYS["practice"])
        hints: PracticeHints = {
            "maturity": self._practice_maturity(profile),
            "source": self._resolve_hint_source(
                explicit=explicit,
                learned=learned,
                keys=("preferredModalities", "avoidedModalities", "maxDurationMinutes"),
            ),
        }
        preferred = self._resolve_scope_list(
            explicit=explicit,
            learned=learned,
            key="preferredModalities",
        )
        avoided = self._resolve_scope_list(
            explicit=explicit,
            learned=learned,
            key="avoidedModalities",
        )
        if preferred:
            hints["preferredModalities"] = preferred
        if avoided:
            hints["avoidedModalities"] = [item for item in avoided if item not in preferred]
        max_duration = self._resolve_scope_value(
            explicit=explicit,
            learned=learned,
            key="maxDurationMinutes",
            default=None,
        )
        if isinstance(max_duration, int) and max_duration > 0:
            hints["maxDurationMinutes"] = max_duration
        recent_events = profile.get("learnedSignals", {}).get("recentEvents", [])
        if isinstance(recent_events, list):
            recent_skips = [
                str(item.get("signals", {}).get("practiceType"))
                for item in recent_events
                if isinstance(item, dict)
                and item.get("type") == "practice_skipped"
                and item.get("signals", {}).get("practiceType")
            ][-5:]
            recent_completions = [
                str(item.get("signals", {}).get("practiceType"))
                for item in recent_events
                if isinstance(item, dict)
                and item.get("type") == "practice_completed"
                and item.get("signals", {}).get("practiceType")
            ][-5:]
            if recent_skips:
                hints["recentSkips"] = recent_skips
            if recent_completions:
                hints["recentCompletions"] = recent_completions
        return hints

    def derive_rhythm_hints(
        self,
        *,
        profile: UserAdaptationProfileRecord | None,
    ) -> RhythmCadenceHints:
        hints: RhythmCadenceHints = {
            "maxBriefsPerDay": 1,
            "minimumHoursBetweenBriefs": 20,
            "dismissedTriggerCooldownHours": 48,
            "actedOnTriggerCooldownHours": 96,
            "maturity": "default",
        }
        if profile is None:
            return hints
        rhythm_preferences = self._scope_dict(profile, "explicitPreferences", "rhythm")
        if rhythm_preferences:
            max_briefs_per_day = rhythm_preferences.get("maxBriefsPerDay")
            if isinstance(max_briefs_per_day, int) and max_briefs_per_day > 0:
                hints["maxBriefsPerDay"] = max_briefs_per_day
            minimum_hours_between_briefs = rhythm_preferences.get("minimumHoursBetweenBriefs")
            if isinstance(minimum_hours_between_briefs, int) and minimum_hours_between_briefs > 0:
                hints["minimumHoursBetweenBriefs"] = minimum_hours_between_briefs
            dismissed_trigger_cooldown_hours = rhythm_preferences.get(
                "dismissedTriggerCooldownHours"
            )
            if (
                isinstance(dismissed_trigger_cooldown_hours, int)
                and dismissed_trigger_cooldown_hours > 0
            ):
                hints["dismissedTriggerCooldownHours"] = dismissed_trigger_cooldown_hours
            acted_on_trigger_cooldown_hours = rhythm_preferences.get("actedOnTriggerCooldownHours")
            if (
                isinstance(acted_on_trigger_cooldown_hours, int)
                and acted_on_trigger_cooldown_hours > 0
            ):
                hints["actedOnTriggerCooldownHours"] = acted_on_trigger_cooldown_hours
            quiet_hours = rhythm_preferences.get("quietHours")
            if isinstance(quiet_hours, dict):
                hints["quietHours"] = {
                    str(key): str(value) for key, value in quiet_hours.items() if value
                }
        rhythm_policy = self._scope_dict(profile, "learnedSignals", _LEARNED_POLICY_KEYS["rhythm"])
        if rhythm_policy:
            if "maxBriefsPerDay" not in rhythm_preferences:
                max_briefs_per_day = rhythm_policy.get("maxBriefsPerDay")
                if isinstance(max_briefs_per_day, int) and max_briefs_per_day > 0:
                    hints["maxBriefsPerDay"] = max_briefs_per_day
            if "minimumHoursBetweenBriefs" not in rhythm_preferences:
                minimum_hours_between_briefs = rhythm_policy.get("minimumHoursBetweenBriefs")
                if (
                    isinstance(minimum_hours_between_briefs, int)
                    and minimum_hours_between_briefs > 0
                ):
                    hints["minimumHoursBetweenBriefs"] = minimum_hours_between_briefs
            if "dismissedTriggerCooldownHours" not in rhythm_preferences:
                dismissed_trigger_cooldown_hours = rhythm_policy.get(
                    "dismissedTriggerCooldownHours"
                )
                if (
                    isinstance(dismissed_trigger_cooldown_hours, int)
                    and dismissed_trigger_cooldown_hours > 0
                ):
                    hints["dismissedTriggerCooldownHours"] = dismissed_trigger_cooldown_hours
            if "actedOnTriggerCooldownHours" not in rhythm_preferences:
                acted_on_trigger_cooldown_hours = rhythm_policy.get("actedOnTriggerCooldownHours")
                if (
                    isinstance(acted_on_trigger_cooldown_hours, int)
                    and acted_on_trigger_cooldown_hours > 0
                ):
                    hints["actedOnTriggerCooldownHours"] = acted_on_trigger_cooldown_hours
            if "quietHours" not in rhythm_preferences:
                quiet_hours = rhythm_policy.get("quietHours")
                if isinstance(quiet_hours, dict):
                    hints["quietHours"] = {
                        str(key): str(value) for key, value in quiet_hours.items() if value
                    }
        rhythm_stats = profile.get("learnedSignals", {}).get("rhythmStats", {})
        shown = 0
        dismissed = 0
        acted_on = 0
        if isinstance(rhythm_stats, dict):
            shown = int(rhythm_stats.get("shown", 0))
            dismissed = int(rhythm_stats.get("dismissed", 0))
            acted_on = int(rhythm_stats.get("actedOn", 0))
        rhythm_samples = shown + dismissed + acted_on
        if rhythm_samples >= 10:
            hints["maturity"] = "mature"
            engagement_rate = (
                float(rhythm_stats.get("engagementRate", 0.0))
                if isinstance(rhythm_stats, dict)
                else 0.0
            )
            if engagement_rate < 0.25:
                hints["minimumHoursBetweenBriefs"] = max(
                    int(hints["minimumHoursBetweenBriefs"]), 24
                )
                hints["dismissedTriggerCooldownHours"] = max(
                    int(hints["dismissedTriggerCooldownHours"]), 72
                )
            elif engagement_rate > 0.6:
                hints["minimumHoursBetweenBriefs"] = min(
                    int(hints["minimumHoursBetweenBriefs"]), 16
                )
        elif profile.get("sampleCounts", {}).get("total", 0):
            hints["maturity"] = "learning"
        return hints

    def summarize(
        self, profile: UserAdaptationProfileRecord | None
    ) -> UserAdaptationProfileSummary | None:
        if profile is None:
            return None
        return {
            "id": profile["id"],
            "explicitPreferences": deepcopy(profile.get("explicitPreferences", {})),
            "learnedSignals": deepcopy(profile.get("learnedSignals", {})),
            "sampleCounts": deepcopy(profile.get("sampleCounts", {})),
        }

    def _scope_dict(
        self,
        profile: UserAdaptationProfileRecord,
        bucket_key: str,
        scope_key: str,
    ) -> dict[str, object]:
        bucket = profile.get(bucket_key, {})
        if not isinstance(bucket, dict):
            return {}
        scope_value = bucket.get(scope_key, {})
        return deepcopy(scope_value) if isinstance(scope_value, dict) else {}

    def _practice_maturity(
        self, profile: UserAdaptationProfileRecord
    ) -> Literal["default", "learning", "mature"]:
        total = int(profile.get("sampleCounts", {}).get("total", 0))
        if total >= 20:
            return "mature"
        if total > 0:
            return "learning"
        return "default"

    def _resolve_scope_value(
        self,
        *,
        explicit: dict[str, object],
        learned: dict[str, object],
        key: str,
        default: object,
    ) -> object:
        if key in explicit:
            return deepcopy(explicit[key])
        if key in learned:
            return deepcopy(learned[key])
        return deepcopy(default)

    def _resolve_scope_list(
        self,
        *,
        explicit: dict[str, object],
        learned: dict[str, object],
        key: str,
    ) -> list[str]:
        value = explicit.get(key) if key in explicit else learned.get(key)
        return self._normalize_string_list(value)

    def _resolve_hint_source(
        self,
        *,
        explicit: dict[str, object],
        learned: dict[str, object],
        keys: tuple[str, ...],
    ) -> RuntimeHintSource:
        explicit_hits = any(key in explicit for key in keys)
        learned_hits = any(key in learned for key in keys)
        if explicit_hits and learned_hits:
            return "mixed"
        if explicit_hits:
            return "explicit"
        if learned_hits:
            return "learned"
        return "default"

    def _validate_preferences(
        self,
        *,
        scope: AdaptationPreferenceScope,
        payload: dict[str, object],
    ) -> ValidatedPreferenceSettings:
        if not isinstance(payload, dict):
            raise ValueError(f"{scope} preferences must be an object.")
        if scope == "communication":
            return self._validate_communication_preferences(payload)
        if scope == "interpretation":
            return self._validate_interpretation_preferences(payload)
        if scope == "practice":
            return self._validate_practice_preferences(payload)
        if scope == "rhythm":
            return self._validate_rhythm_preferences(payload)
        raise ValueError(f"Unsupported preference scope: {scope}")

    def _validate_communication_preferences(
        self, payload: dict[str, object]
    ) -> CommunicationPreferenceSettings:
        allowed = {"tone", "questioningStyle", "symbolicDensity"}
        self._assert_allowed_keys(scope="communication", payload=payload, allowed=allowed)
        result: CommunicationPreferenceSettings = {}
        tone = self._optional_literal(payload.get("tone"), {"gentle", "direct", "spacious"})
        if tone:
            result["tone"] = cast(CommunicationTone, tone)
        style = self._optional_literal(
            payload.get("questioningStyle"),
            {"soma_first", "image_first", "feeling_first", "reflective"},
        )
        if style:
            result["questioningStyle"] = cast(CommunicationQuestioningStyle, style)
        density = self._optional_literal(
            payload.get("symbolicDensity"),
            {"sparse", "moderate", "dense"},
        )
        if density:
            result["symbolicDensity"] = cast(CommunicationSymbolicDensity, density)
        return result

    def _validate_interpretation_preferences(
        self, payload: dict[str, object]
    ) -> InterpretationPreferenceSettings:
        allowed = {"depthPreference", "modalityBias"}
        self._assert_allowed_keys(scope="interpretation", payload=payload, allowed=allowed)
        result: InterpretationPreferenceSettings = {}
        depth = self._optional_literal(
            payload.get("depthPreference"),
            {
                "brief_pattern_notes",
                "cautious_amplification",
                "deep_amplification",
            },
        )
        if depth:
            result["depthPreference"] = cast(InterpretationDepthPreference, depth)
        modality = self._optional_literal(
            payload.get("modalityBias"),
            {"body", "image", "emotion", "narrative", "cultural"},
        )
        if modality:
            result["modalityBias"] = cast(InterpretationModalityBias, modality)
        return result

    def _validate_practice_preferences(
        self, payload: dict[str, object]
    ) -> PracticePreferenceSettings:
        allowed = {"preferredModalities", "avoidedModalities", "maxDurationMinutes"}
        self._assert_allowed_keys(scope="practice", payload=payload, allowed=allowed)
        result: PracticePreferenceSettings = {}
        preferred = self._normalize_string_list(payload.get("preferredModalities"))
        avoided = self._normalize_string_list(payload.get("avoidedModalities"))
        overlap = sorted(set(preferred).intersection(avoided))
        if overlap:
            raise ValueError(
                "practice preferredModalities and avoidedModalities cannot overlap: "
                + ", ".join(overlap)
            )
        if preferred:
            result["preferredModalities"] = preferred
        if avoided:
            result["avoidedModalities"] = avoided
        max_duration = payload.get("maxDurationMinutes")
        if max_duration is not None:
            if not isinstance(max_duration, int) or max_duration <= 0:
                raise ValueError("practice maxDurationMinutes must be a positive integer.")
            result["maxDurationMinutes"] = max_duration
        return result

    def _validate_rhythm_preferences(self, payload: dict[str, object]) -> RhythmPreferenceSettings:
        allowed = {
            "maxBriefsPerDay",
            "minimumHoursBetweenBriefs",
            "dismissedTriggerCooldownHours",
            "actedOnTriggerCooldownHours",
            "quietHours",
        }
        self._assert_allowed_keys(scope="rhythm", payload=payload, allowed=allowed)
        result: RhythmPreferenceSettings = {}
        max_briefs_per_day = payload.get("maxBriefsPerDay")
        if max_briefs_per_day is not None:
            if not isinstance(max_briefs_per_day, int) or max_briefs_per_day <= 0:
                raise ValueError("rhythm maxBriefsPerDay must be a positive integer.")
            result["maxBriefsPerDay"] = max_briefs_per_day
        minimum_hours_between_briefs = payload.get("minimumHoursBetweenBriefs")
        if minimum_hours_between_briefs is not None:
            if (
                not isinstance(minimum_hours_between_briefs, int)
                or minimum_hours_between_briefs <= 0
            ):
                raise ValueError("rhythm minimumHoursBetweenBriefs must be a positive integer.")
            result["minimumHoursBetweenBriefs"] = minimum_hours_between_briefs
        dismissed_trigger_cooldown_hours = payload.get("dismissedTriggerCooldownHours")
        if dismissed_trigger_cooldown_hours is not None:
            if (
                not isinstance(dismissed_trigger_cooldown_hours, int)
                or dismissed_trigger_cooldown_hours <= 0
            ):
                raise ValueError("rhythm dismissedTriggerCooldownHours must be a positive integer.")
            result["dismissedTriggerCooldownHours"] = dismissed_trigger_cooldown_hours
        acted_on_trigger_cooldown_hours = payload.get("actedOnTriggerCooldownHours")
        if acted_on_trigger_cooldown_hours is not None:
            if (
                not isinstance(acted_on_trigger_cooldown_hours, int)
                or acted_on_trigger_cooldown_hours <= 0
            ):
                raise ValueError("rhythm actedOnTriggerCooldownHours must be a positive integer.")
            result["actedOnTriggerCooldownHours"] = acted_on_trigger_cooldown_hours
        quiet_hours = payload.get("quietHours")
        if quiet_hours is not None:
            if not isinstance(quiet_hours, dict):
                raise ValueError("rhythm quietHours must be an object.")
            result["quietHours"] = {
                str(key): str(value).strip()
                for key, value in quiet_hours.items()
                if str(key).strip() and str(value).strip()
            }
        return result

    def _assert_allowed_keys(
        self,
        *,
        scope: str,
        payload: dict[str, object],
        allowed: set[str],
    ) -> None:
        unknown = sorted(set(payload).difference(allowed))
        if unknown:
            raise ValueError(f"Unsupported {scope} preference keys: {', '.join(unknown)}.")

    def _optional_literal(self, value: object, allowed: set[str]) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        if text not in allowed:
            raise ValueError(f"Unsupported value '{text}'.")
        return text

    def _normalize_string_list(self, value: object) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError("Expected a list of strings.")
        return list(dict.fromkeys(str(item).strip() for item in value if str(item).strip()))

    def _update_practice_stats(
        self,
        *,
        learned: dict[str, object],
        counts: dict[str, int],
        event_type: str,
        signals: dict[str, object],
    ) -> None:
        practice_stats = learned.get("practiceStats", {})
        if not isinstance(practice_stats, dict):
            practice_stats = {}
        practice_stats.setdefault("byType", {})
        practice_stats.setdefault("byModality", {})
        practice_stats.setdefault("byTemplateId", {})
        status_key = {
            "practice_recommended": "recommended",
            "practice_accepted": "accepted",
            "practice_completed": "completed",
            "practice_skipped": "skipped",
        }.get(event_type)
        if status_key:
            practice_type = str(signals.get("practiceType") or "unknown")
            modality = str(signals.get("modality") or "unknown")
            template_id = str(signals.get("templateId") or "unknown")
            self._increment_nested(practice_stats["byType"], practice_type, status_key)
            self._increment_nested(practice_stats["byModality"], modality, status_key)
            self._increment_nested(practice_stats["byTemplateId"], template_id, status_key)
            if signals.get("activationImproved"):
                self._increment_nested(
                    practice_stats["byType"], practice_type, "activationImproved"
                )
            if signals.get("activationWorsened"):
                self._increment_nested(
                    practice_stats["byType"], practice_type, "activationWorsened"
                )
            if signals.get("activationUnchanged"):
                self._increment_nested(
                    practice_stats["byType"], practice_type, "activationUnchanged"
                )
        learned["practiceStats"] = practice_stats
        learned["matured"] = counts.get("total", 0) >= 20

    def _update_rhythm_stats(
        self,
        *,
        learned: dict[str, object],
        signals: dict[str, object],
        event_type: str,
    ) -> None:
        rhythm_stats = learned.get("rhythmStats", {})
        if not isinstance(rhythm_stats, dict):
            rhythm_stats = {}
        mapping = {
            "rhythmic_brief_shown": "shown",
            "rhythmic_brief_acted_on": "actedOn",
            "rhythmic_brief_dismissed": "dismissed",
        }
        stat_key = mapping.get(event_type)
        if stat_key:
            rhythm_stats[stat_key] = int(rhythm_stats.get(stat_key, 0)) + 1
        if event_type == "rhythmic_brief_candidate_created":
            rhythm_stats["created"] = int(rhythm_stats.get("created", 0)) + 1
        shown = int(rhythm_stats.get("shown", 0))
        acted_on = int(rhythm_stats.get("actedOn", 0))
        dismissed = int(rhythm_stats.get("dismissed", 0))
        total = shown + acted_on + dismissed
        if total > 0:
            rhythm_stats["engagementRate"] = round((acted_on + shown) / total, 3)
        last_trigger_key = signals.get("triggerKey")
        if last_trigger_key:
            rhythm_stats["lastTriggerKey"] = str(last_trigger_key)
        learned["rhythmStats"] = rhythm_stats

    def _update_questioning_stats(
        self,
        *,
        learned: dict[str, object],
        event_type: str,
        signals: dict[str, object],
    ) -> None:
        questioning_stats = learned.get("questioningStats", {})
        if not isinstance(questioning_stats, dict):
            questioning_stats = {}
        for key in (
            "byIntent",
            "byCaptureTarget",
            "byExpectedAnswerKind",
            "skippedByIntent",
            "answeredByIntent",
            "routedByTarget",
            "unroutedByTarget",
        ):
            questioning_stats.setdefault(key, {})
        intent = str(signals.get("intent") or "").strip()
        capture_target = str(signals.get("captureTarget") or "").strip()
        expected_kind = str(signals.get("expectedAnswerKind") or "").strip()
        question_style = str(signals.get("questionStyle") or "").strip()
        routing_status = str(signals.get("routingStatus") or "").strip()

        if intent:
            self._increment_nested(questioning_stats["byIntent"], intent, "count")
        if capture_target:
            self._increment_nested(questioning_stats["byCaptureTarget"], capture_target, "count")
        if expected_kind:
            self._increment_nested(
                questioning_stats["byExpectedAnswerKind"], expected_kind, "count"
            )
        if event_type == "clarification_skipped" and intent:
            self._increment_nested(questioning_stats["skippedByIntent"], intent, "count")
        if event_type == "clarification_answered" and intent:
            self._increment_nested(questioning_stats["answeredByIntent"], intent, "count")
        if event_type == "clarification_answered" and capture_target and routing_status == "routed":
            self._increment_nested(questioning_stats["routedByTarget"], capture_target, "count")
        if (
            event_type in {"clarification_unrouted", "clarification_answered"}
            and capture_target
            and routing_status
            in {
                "unrouted",
                "needs_review",
            }
        ):
            self._increment_nested(questioning_stats["unroutedByTarget"], capture_target, "count")

        if question_style:
            preferred = questioning_stats.get("preferredQuestionStyles", [])
            avoided = questioning_stats.get("avoidedQuestionStyles", [])
            if not isinstance(preferred, list):
                preferred = []
            if not isinstance(avoided, list):
                avoided = []
            if event_type == "question_style_preferred" and question_style not in preferred:
                preferred = [*preferred[-4:], question_style]
            if event_type == "question_style_avoided" and question_style not in avoided:
                avoided = [*avoided[-4:], question_style]
            questioning_stats["preferredQuestionStyles"] = preferred
            questioning_stats["avoidedQuestionStyles"] = avoided

        learned["questioningStats"] = questioning_stats

    def _update_interpretation_stats(
        self,
        *,
        learned: dict[str, object],
        event_type: str,
        signals: dict[str, object],
    ) -> None:
        interpretation_stats = learned.get("interpretationStats", {})
        if not isinstance(interpretation_stats, dict):
            interpretation_stats = {}
        if event_type == "depth_pacing_corrected":
            depth_pacing = str(signals.get("depthPacing") or "").strip()
            if depth_pacing in {"direct", "gentle", "one_step"}:
                interpretation_stats["depthPacing"] = depth_pacing
                history = interpretation_stats.get("depthPacingCorrections", [])
                if not isinstance(history, list):
                    history = []
                interpretation_stats["depthPacingCorrections"] = [*history[-4:], depth_pacing]
        if event_type == "interpretation_response_resonated":
            witness_voice = str(signals.get("witnessVoice") or "").strip()
            if witness_voice:
                history = interpretation_stats.get("preferredWitnessVoice", [])
                if not isinstance(history, list):
                    history = []
                if witness_voice not in history:
                    interpretation_stats["preferredWitnessVoice"] = [*history[-4:], witness_voice]
        if event_type == "interpretation_response_rejected":
            phrasing = str(signals.get("phrasingPattern") or "").strip()
            if phrasing:
                history = interpretation_stats.get("rejectedPhrasingPatterns", [])
                if not isinstance(history, list):
                    history = []
                if phrasing not in history:
                    interpretation_stats["rejectedPhrasingPatterns"] = [*history[-4:], phrasing]
        learned["interpretationStats"] = interpretation_stats

    def _update_interaction_feedback_stats(
        self,
        *,
        learned: dict[str, object],
        event_type: str,
        signals: dict[str, object],
    ) -> None:
        stats = learned.get("interactionFeedbackStats", {})
        if not isinstance(stats, dict):
            stats = {}
        domain = "interpretation" if event_type.endswith("_interpretation") else "practice"
        domain_stats = stats.get(domain, {})
        if not isinstance(domain_stats, dict):
            domain_stats = {}
        by_feedback = domain_stats.get("byFeedback", {})
        if not isinstance(by_feedback, dict):
            by_feedback = {}
        feedback = str(signals.get("feedback") or "").strip()
        if feedback:
            by_feedback[feedback] = int(by_feedback.get(feedback, 0)) + 1
        locale = str(signals.get("locale") or "").strip()
        if locale:
            locales = domain_stats.get("recentLocales", [])
            if not isinstance(locales, list):
                locales = []
            if locale not in locales:
                locales = [*locales[-4:], locale]
            domain_stats["recentLocales"] = locales
        domain_stats["byFeedback"] = by_feedback
        stats[domain] = domain_stats
        learned["interactionFeedbackStats"] = stats

    def _increment_nested(self, store: object, bucket_key: str, stat_key: str) -> None:
        if not isinstance(store, dict):
            return
        bucket = store.get(bucket_key)
        if not isinstance(bucket, dict):
            bucket = {}
            store[bucket_key] = bucket
        bucket[stat_key] = int(bucket.get(stat_key, 0)) + 1
