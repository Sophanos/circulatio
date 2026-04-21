from __future__ import annotations

from copy import deepcopy

from ..domain.adaptation import (
    AdaptationSignalEvent,
    RhythmCadenceHints,
    UserAdaptationProfileRecord,
)
from ..domain.ids import create_id, now_iso
from ..domain.types import PracticeAdaptationHints, UserAdaptationProfileSummary


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
        return self.record_event(
            profile=profile,
            event=event,
        )

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

    def derive_practice_hints(
        self,
        *,
        profile: UserAdaptationProfileRecord | None,
    ) -> PracticeAdaptationHints:
        if profile is None:
            return {"maturity": "insufficient_data", "notes": ["No adaptation samples yet."]}
        counts = profile.get("sampleCounts", {})
        total = int(counts.get("total", 0))
        practice_preferences = profile.get("explicitPreferences", {}).get("practice", {})
        stats = profile.get("learnedSignals", {}).get("practiceStats", {})
        hints: PracticeAdaptationHints = {
            "maturity": "mature" if total >= 20 else "learning",
            "notes": [],
        }
        if total < 20:
            hints["maturity"] = "insufficient_data"
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
        if total >= 20 and isinstance(stats, dict):
            modality_stats = stats.get("byModality", {})
            if isinstance(modality_stats, dict):
                hints["preferredModalities"] = hints.get("preferredModalities", []) + [
                    modality
                    for modality, item in modality_stats.items()
                    if isinstance(item, dict)
                    and int(item.get("recommended", 0)) >= 5
                    and int(item.get("completed", 0)) + int(item.get("accepted", 0))
                    > int(item.get("skipped", 0))
                ]
                hints["avoidedModalities"] = [
                    modality
                    for modality, item in modality_stats.items()
                    if isinstance(item, dict)
                    and int(item.get("recommended", 0)) >= 5
                    and int(item.get("skipped", 0))
                    > int(item.get("completed", 0)) + int(item.get("accepted", 0))
                ]
        recent_events = profile.get("learnedSignals", {}).get("recentEvents", [])
        if isinstance(recent_events, list):
            hints["recentSkips"] = [
                str(item.get("signals", {}).get("practiceType"))
                for item in recent_events
                if isinstance(item, dict)
                and item.get("type") == "practice_skipped"
                and item.get("signals", {}).get("practiceType")
            ][-5:]
            hints["recentCompletions"] = [
                str(item.get("signals", {}).get("practiceType"))
                for item in recent_events
                if isinstance(item, dict)
                and item.get("type") == "practice_completed"
                and item.get("signals", {}).get("practiceType")
            ][-5:]
        if hints.get("preferredModalities"):
            hints["preferredModalities"] = list(dict.fromkeys(hints["preferredModalities"]))[:4]
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
        rhythm_preferences = profile.get("explicitPreferences", {}).get("rhythm", {})
        if isinstance(rhythm_preferences, dict):
            for key in (
                "maxBriefsPerDay",
                "minimumHoursBetweenBriefs",
                "dismissedTriggerCooldownHours",
                "actedOnTriggerCooldownHours",
            ):
                value = rhythm_preferences.get(key)
                if isinstance(value, int) and value > 0:
                    hints[key] = value  # type: ignore[index]
            quiet_hours = rhythm_preferences.get("quietHours")
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

    def _increment_nested(self, store: object, bucket_key: str, stat_key: str) -> None:
        if not isinstance(store, dict):
            return
        bucket = store.get(bucket_key)
        if not isinstance(bucket, dict):
            bucket = {}
            store[bucket_key] = bucket
        bucket[stat_key] = int(bucket.get(stat_key, 0)) + 1
