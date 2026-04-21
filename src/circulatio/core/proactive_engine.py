from __future__ import annotations

from datetime import UTC, datetime, timedelta

from ..domain.adaptation import RhythmCadenceHints
from ..domain.ids import create_id, now_iso
from ..domain.journeys import JourneyRecord
from ..domain.memory import MemoryKernelSnapshot
from ..domain.practices import PracticeSessionRecord
from ..domain.proactive import (
    ProactiveBriefRecord,
    ProactiveBriefStatus,
    RhythmBriefSource,
    RhythmicBriefSeed,
)
from ..domain.reviews import DashboardSummary
from ..domain.types import Id, MethodContextSnapshot, UserAdaptationProfileSummary


class ProactiveEngine:
    def build_candidate_seeds(
        self,
        *,
        user_id: str,
        memory_snapshot: MemoryKernelSnapshot,
        dashboard: DashboardSummary,
        method_context: MethodContextSnapshot | None,
        recent_practices: list[PracticeSessionRecord],
        journeys: list[JourneyRecord],
        existing_briefs: list[ProactiveBriefRecord],
        adaptation_profile: UserAdaptationProfileSummary | None = None,
        source: RhythmBriefSource,
        now: str,
        limit: int = 3,
    ) -> list[RhythmicBriefSeed]:
        del existing_briefs, adaptation_profile
        seeds: list[RhythmicBriefSeed] = []
        seeds.extend(self._practice_followup_seeds(recent_practices=recent_practices, now=now))
        seeds.extend(self._journey_seeds(journeys=journeys, now=now))
        seeds.extend(self._series_seeds(method_context=method_context, now=now))
        seeds.extend(
            self._threshold_invitation_seeds(
                method_context=method_context,
                memory_snapshot=memory_snapshot,
                now=now,
            )
        )
        seeds.extend(
            self._chapter_invitation_seeds(
                method_context=method_context,
                memory_snapshot=memory_snapshot,
                now=now,
            )
        )
        seeds.extend(self._return_invitation_seeds(method_context=method_context, now=now))
        seeds.extend(
            self._bridge_invitation_seeds(
                method_context=method_context,
                memory_snapshot=memory_snapshot,
                now=now,
            )
        )
        seeds.extend(
            self._analysis_packet_invitation_seeds(
                user_id=user_id,
                method_context=method_context,
                memory_snapshot=memory_snapshot,
                now=now,
            )
        )
        seeds.extend(
            self._goal_or_signal_seeds(
                method_context=method_context,
                memory_snapshot=memory_snapshot,
                now=now,
            )
        )
        seeds.extend(self._weekly_review_seed(user_id=user_id, dashboard=dashboard, now=now))
        seeds.sort(key=lambda item: int(item.get("priority", 0)), reverse=True)
        if source == "practice_followup":
            seeds = [item for item in seeds if item["briefType"] == "practice_followup"]
        return seeds[:limit]

    def filter_due_candidates(
        self,
        *,
        seeds: list[RhythmicBriefSeed],
        existing_briefs: list[ProactiveBriefRecord],
        cadence_hints: RhythmCadenceHints,
        source: RhythmBriefSource,
        now: str,
    ) -> list[RhythmicBriefSeed]:
        now_dt = self._parse_datetime(now)
        active_trigger_keys = {
            str(item.get("triggerKey"))
            for item in existing_briefs
            if item.get("status") in {"candidate", "shown"} and item.get("triggerKey")
        }
        suppressed_trigger_keys = {
            str(item.get("triggerKey"))
            for item in existing_briefs
            if item.get("status") == "dismissed"
            and item.get("triggerKey")
            and item.get("cooldownUntil")
            and self._parse_datetime(item["cooldownUntil"]) > now_dt
        }
        if source == "scheduled":
            shown_today = [
                item
                for item in existing_briefs
                if item.get("status") != "deleted"
                and item.get("source") == "scheduled"
                and self._day_bucket(item.get("createdAt", item.get("shownAt", now)))
                == self._day_bucket(now)
            ]
            if len(shown_today) >= int(cadence_hints.get("maxBriefsPerDay", 1)):
                return []
            latest_shown = self._latest_brief_time(existing_briefs)
            if latest_shown is not None:
                minimum_gap = timedelta(
                    hours=int(cadence_hints.get("minimumHoursBetweenBriefs", 20))
                )
                if now_dt - latest_shown < minimum_gap:
                    return []
        due: list[RhythmicBriefSeed] = []
        for seed in seeds:
            trigger_key = seed["triggerKey"]
            if trigger_key in active_trigger_keys or trigger_key in suppressed_trigger_keys:
                continue
            due.append(seed)
        return due

    def validate_transition(
        self,
        *,
        current_status: ProactiveBriefStatus,
        target_status: ProactiveBriefStatus,
    ) -> None:
        allowed: dict[ProactiveBriefStatus, set[ProactiveBriefStatus]] = {
            "candidate": {"shown", "dismissed", "acted_on", "deleted"},
            "shown": {"dismissed", "acted_on", "deleted"},
            "dismissed": {"deleted"},
            "acted_on": {"deleted"},
            "deleted": set(),
        }
        if target_status not in allowed.get(current_status, set()):
            raise ValueError(
                f"Proactive brief cannot transition from {current_status} to {target_status}."
            )

    def build_candidates(
        self,
        *,
        user_id: str,
        memory_snapshot: MemoryKernelSnapshot,
        dashboard: DashboardSummary,
        adaptation_profile: UserAdaptationProfileSummary | None = None,
    ) -> list[ProactiveBriefRecord]:
        seeds = self.build_candidate_seeds(
            user_id=user_id,
            memory_snapshot=memory_snapshot,
            dashboard=dashboard,
            method_context=None,
            recent_practices=[],
            journeys=[],
            existing_briefs=[],
            adaptation_profile=adaptation_profile,
            source="manual",
            now=now_iso(),
        )
        timestamp = now_iso()
        return [
            {
                "id": create_id("proactive_brief"),
                "userId": user_id,
                "briefType": seed["briefType"],
                "status": "candidate",
                "title": seed["titleHint"],
                "summary": seed["summaryHint"],
                "suggestedAction": seed.get("suggestedActionHint"),
                "triggerKey": seed["triggerKey"],
                "priority": seed["priority"],
                "relatedJourneyIds": list(seed["relatedJourneyIds"]),
                "relatedMaterialIds": list(seed["relatedMaterialIds"]),
                "relatedSymbolIds": list(seed["relatedSymbolIds"]),
                "relatedPracticeSessionIds": list(seed["relatedPracticeSessionIds"]),
                "evidenceIds": list(seed["evidenceIds"]),
                "createdAt": timestamp,
                "updatedAt": timestamp,
            }
            for seed in seeds
        ]

    def _practice_followup_seeds(
        self,
        *,
        recent_practices: list[PracticeSessionRecord],
        now: str,
    ) -> list[RhythmicBriefSeed]:
        now_dt = self._parse_datetime(now)
        seeds: list[RhythmicBriefSeed] = []
        sorted_practices = sorted(
            recent_practices,
            key=lambda item: item.get("nextFollowUpDueAt", item.get("createdAt", "")),
            reverse=True,
        )
        for practice in sorted_practices:
            if practice.get("status") not in {"recommended", "accepted"}:
                continue
            due_at = practice.get("nextFollowUpDueAt")
            if due_at:
                if self._parse_datetime(due_at) > now_dt:
                    continue
            else:
                created_at = self._parse_datetime(practice.get("createdAt"))
                if now_dt - created_at < timedelta(hours=24):
                    continue
            date_bucket = self._day_bucket(due_at or now)
            seeds.append(
                {
                    "briefType": "practice_followup",
                    "triggerKey": (
                        f"practice_followup:practice_session:{practice['id']}:{date_bucket}"
                    ),
                    "titleHint": "Practice follow-up",
                    "summaryHint": (
                        "A previously suggested practice may be ready for a light check-in."
                    ),
                    "suggestedActionHint": practice.get("followUpPrompt")
                    or "You can note what happened, or simply leave it for later.",
                    "priority": 100,
                    "relatedJourneyIds": [],
                    "relatedMaterialIds": [practice["materialId"]]
                    if practice.get("materialId")
                    else [],
                    "relatedSymbolIds": [],
                    "relatedPracticeSessionIds": [practice["id"]],
                    "evidenceIds": [],
                    "reason": "practice_session_due",
                }
            )
        return seeds

    def _journey_seeds(self, *, journeys: list[JourneyRecord], now: str) -> list[RhythmicBriefSeed]:
        now_dt = self._parse_datetime(now)
        seeds: list[RhythmicBriefSeed] = []
        for journey in journeys:
            if journey.get("status") != "active":
                continue
            due_at = journey.get("nextReviewDueAt")
            if due_at and self._parse_datetime(due_at) > now_dt:
                continue
            if not due_at and journey.get("lastBriefedAt"):
                continue
            week_bucket = self._week_bucket(due_at or now)
            seeds.append(
                {
                    "briefType": "journey_checkin",
                    "triggerKey": f"journey_checkin:journey:{journey['id']}:{week_bucket}",
                    "titleHint": "Journey check-in",
                    "summaryHint": "An active journey may be ready for a bounded check-in.",
                    "suggestedActionHint": (
                        "You can simply note what shifted, or leave it untouched."
                    ),
                    "priority": 90,
                    "relatedJourneyIds": [journey["id"]],
                    "relatedMaterialIds": [],
                    "relatedSymbolIds": list(journey.get("relatedSymbolIds", [])),
                    "relatedPracticeSessionIds": [],
                    "evidenceIds": [],
                    "reason": "journey_due",
                }
            )
        return seeds

    def _series_seeds(
        self,
        *,
        method_context: MethodContextSnapshot | None,
        now: str,
    ) -> list[RhythmicBriefSeed]:
        if not method_context:
            return []
        now_dt = self._parse_datetime(now)
        seeds: list[RhythmicBriefSeed] = []
        for series in method_context.get("activeDreamSeries", [])[:3]:
            if series.get("status") not in {"active", "integrating"}:
                continue
            if len(series.get("materialIds", [])) < 2:
                continue
            last_seen = series.get("lastSeen")
            if last_seen and now_dt - self._parse_datetime(last_seen) > timedelta(days=14):
                continue
            week_bucket = self._week_bucket(last_seen or now)
            seeds.append(
                {
                    "briefType": "series_followup",
                    "triggerKey": (f"series_followup:dream_series:{series['id']}:{week_bucket}"),
                    "titleHint": "Dream-series follow-up",
                    "summaryHint": (
                        "A dream series has enough recurrence to support a light follow-up."
                    ),
                    "suggestedActionHint": (
                        "You can note what changed in the sequence, or leave it open."
                    ),
                    "priority": 80,
                    "relatedJourneyIds": [],
                    "relatedMaterialIds": list(series.get("materialIds", []))[:3],
                    "relatedSymbolIds": list(series.get("symbolIds", []))[:3],
                    "relatedPracticeSessionIds": [],
                    "evidenceIds": [],
                    "reason": "dream_series_recent",
                }
            )
        return seeds

    def _threshold_invitation_seeds(
        self,
        *,
        method_context: MethodContextSnapshot | None,
        memory_snapshot: MemoryKernelSnapshot,
        now: str,
    ) -> list[RhythmicBriefSeed]:
        if not method_context:
            return []
        individuation = method_context.get("individuationContext") or {}
        thresholds = individuation.get("thresholdProcesses", [])
        seeds: list[RhythmicBriefSeed] = []
        for threshold in thresholds[:3]:
            if threshold.get("invitationReadiness") not in {"ask", "ready"}:
                continue
            related = self._related_refs_for_entity(
                memory_snapshot=memory_snapshot,
                entity_id=str(threshold.get("id") or ""),
            )
            label = str(threshold.get("label") or "Threshold process")
            seeds.append(
                {
                    "briefType": "threshold_invitation",
                    "triggerKey": (
                        f"threshold_invitation:threshold:{threshold['id']}:{self._day_bucket(now)}"
                    ),
                    "titleHint": "Threshold invitation",
                    "summaryHint": f"{label} may be ready for a cautious threshold review.",
                    "suggestedActionHint": (
                        "You can ask for a threshold review, or leave it untouched."
                    ),
                    "priority": 95,
                    "relatedJourneyIds": [],
                    "relatedMaterialIds": related["materialIds"],
                    "relatedSymbolIds": [],
                    "relatedPracticeSessionIds": [],
                    "evidenceIds": list(threshold.get("evidenceIds", [])),
                    "reason": "threshold_process_ready",
                }
            )
        return seeds

    def _chapter_invitation_seeds(
        self,
        *,
        method_context: MethodContextSnapshot | None,
        memory_snapshot: MemoryKernelSnapshot,
        now: str,
    ) -> list[RhythmicBriefSeed]:
        if not method_context:
            return []
        chapter = (method_context.get("livingMythContext") or {}).get("currentLifeChapter")
        if not chapter:
            return []
        related = self._related_refs_for_entity(
            memory_snapshot=memory_snapshot,
            entity_id=str(chapter.get("id") or ""),
        )
        label = str(chapter.get("chapterLabel") or chapter.get("label") or "Current chapter")
        return [
            {
                "briefType": "chapter_invitation",
                "triggerKey": (
                    f"chapter_invitation:chapter:{chapter['id']}:{self._week_bucket(now)}"
                ),
                "titleHint": "Chapter invitation",
                "summaryHint": f"{label} may be ready for a light chapter-level reflection.",
                "suggestedActionHint": (
                    "You can ask for a living myth review, or simply note the chapter."
                ),
                "priority": 88,
                "relatedJourneyIds": [],
                "relatedMaterialIds": related["materialIds"],
                "relatedSymbolIds": [],
                "relatedPracticeSessionIds": [],
                "evidenceIds": list(chapter.get("evidenceIds", [])),
                "reason": "life_chapter_active",
            }
        ]

    def _return_invitation_seeds(
        self,
        *,
        method_context: MethodContextSnapshot | None,
        now: str,
    ) -> list[RhythmicBriefSeed]:
        if not method_context:
            return []
        living_myth = method_context.get("livingMythContext") or {}
        markers = living_myth.get("recentThresholdMarkers", [])
        for marker in markers[:3]:
            if marker.get("markerType") != "return":
                continue
            label = str(marker.get("label") or "Return marker")
            return [
                {
                    "briefType": "return_invitation",
                    "triggerKey": (
                        f"return_invitation:marker:{marker['id']}:{self._week_bucket(now)}"
                    ),
                    "titleHint": "Return invitation",
                    "summaryHint": f"{label} suggests a return may be ready for gentle reflection.",
                    "suggestedActionHint": "You can mark what is returning, or leave it open.",
                    "priority": 86,
                    "relatedJourneyIds": [],
                    "relatedMaterialIds": [],
                    "relatedSymbolIds": [],
                    "relatedPracticeSessionIds": [],
                    "evidenceIds": list(marker.get("evidenceIds", [])),
                    "reason": "threshold_return_marker",
                }
            ]
        individuation = method_context.get("individuationContext") or {}
        for threshold in individuation.get("thresholdProcesses", [])[:3]:
            if threshold.get("phase") != "return":
                continue
            label = str(threshold.get("label") or "Threshold process")
            return [
                {
                    "briefType": "return_invitation",
                    "triggerKey": (
                        f"return_invitation:threshold:{threshold['id']}:{self._week_bucket(now)}"
                    ),
                    "titleHint": "Return invitation",
                    "summaryHint": f"{label} appears to be in a return phase.",
                    "suggestedActionHint": (
                        "You can note what is returning to life, or leave it for later."
                    ),
                    "priority": 84,
                    "relatedJourneyIds": [],
                    "relatedMaterialIds": [],
                    "relatedSymbolIds": [],
                    "relatedPracticeSessionIds": [],
                    "evidenceIds": list(threshold.get("evidenceIds", [])),
                    "reason": "threshold_return_phase",
                }
            ]
        return []

    def _bridge_invitation_seeds(
        self,
        *,
        method_context: MethodContextSnapshot | None,
        memory_snapshot: MemoryKernelSnapshot,
        now: str,
    ) -> list[RhythmicBriefSeed]:
        if not method_context:
            return []
        bridges = (method_context.get("individuationContext") or {}).get("bridgeMoments", [])
        if not bridges:
            return []
        bridge = bridges[0]
        related = self._related_refs_for_entity(
            memory_snapshot=memory_snapshot,
            entity_id=str(bridge.get("id") or ""),
        )
        label = str(bridge.get("label") or "Bridge moment")
        return [
            {
                "briefType": "bridge_invitation",
                "triggerKey": (f"bridge_invitation:bridge:{bridge['id']}:{self._day_bucket(now)}"),
                "titleHint": "Bridge invitation",
                "summaryHint": f"{label} may be ready for a brief bridge reflection.",
                "suggestedActionHint": (
                    "You can note what it seems to connect, or leave it unforced."
                ),
                "priority": 82,
                "relatedJourneyIds": [],
                "relatedMaterialIds": related["materialIds"],
                "relatedSymbolIds": [],
                "relatedPracticeSessionIds": [],
                "evidenceIds": list(bridge.get("evidenceIds", [])),
                "reason": "bridge_moment_active",
            }
        ]

    def _analysis_packet_invitation_seeds(
        self,
        *,
        user_id: str,
        method_context: MethodContextSnapshot | None,
        memory_snapshot: MemoryKernelSnapshot,
        now: str,
    ) -> list[RhythmicBriefSeed]:
        if not method_context:
            return []
        individuation = method_context.get("individuationContext") or {}
        living_myth = method_context.get("livingMythContext") or {}
        if not (
            individuation.get("thresholdProcesses")
            or individuation.get("relationalScenes")
            or living_myth.get("activeMythicQuestions")
            or method_context.get("activeDreamSeries")
        ):
            return []
        related_material_ids: list[Id] = []
        evidence_ids: list[Id] = []
        for item in memory_snapshot.get("items", []):
            if item.get("namespace") not in {"individuation_records", "living_myth_records"}:
                continue
            material_id = item.get("provenance", {}).get("materialId")
            if (
                isinstance(material_id, str)
                and material_id
                and material_id not in related_material_ids
            ):
                related_material_ids.append(material_id)
            for evidence_id in item.get("provenance", {}).get("evidenceIds", []):
                if evidence_id not in evidence_ids:
                    evidence_ids.append(evidence_id)
            if len(related_material_ids) >= 3 and len(evidence_ids) >= 5:
                break
        return [
            {
                "briefType": "analysis_packet_invitation",
                "triggerKey": (
                    f"analysis_packet_invitation:user:{user_id}:{self._week_bucket(now)}"
                ),
                "titleHint": "Analysis-packet invitation",
                "summaryHint": "There is enough approved material for a bounded analysis packet.",
                "suggestedActionHint": (
                    "You can ask for an analysis packet, or leave the material where it is."
                ),
                "priority": 76,
                "relatedJourneyIds": [],
                "relatedMaterialIds": related_material_ids[:3],
                "relatedSymbolIds": [],
                "relatedPracticeSessionIds": [],
                "evidenceIds": evidence_ids[:5],
                "reason": "analysis_packet_ready",
            }
        ]

    def _goal_or_signal_seeds(
        self,
        *,
        method_context: MethodContextSnapshot | None,
        memory_snapshot: MemoryKernelSnapshot,
        now: str,
    ) -> list[RhythmicBriefSeed]:
        if method_context:
            goal_tensions = method_context.get("goalTensions", [])
            if goal_tensions:
                tension = goal_tensions[0]
                return [
                    {
                        "briefType": "daily",
                        "triggerKey": f"daily:goal_tension:{tension['id']}:{self._day_bucket(now)}",
                        "titleHint": "Goal tension",
                        "summaryHint": "An active goal tension may be asking for gentle attention.",
                        "suggestedActionHint": (
                            "You can simply note the tension instead of resolving it."
                        ),
                        "priority": 70,
                        "relatedJourneyIds": [],
                        "relatedMaterialIds": [],
                        "relatedSymbolIds": [],
                        "relatedPracticeSessionIds": [],
                        "evidenceIds": list(tension.get("evidenceIds", [])),
                        "reason": "goal_tension_active",
                    }
                ]
            signals = method_context.get("longitudinalSignals", [])
            if signals:
                signal = signals[0]
                return [
                    {
                        "briefType": "daily",
                        "triggerKey": f"daily:signal:{signal['id']}:{self._day_bucket(now)}",
                        "titleHint": "Longitudinal signal",
                        "summaryHint": "A recurring pattern may be ripe for a short check-in.",
                        "suggestedActionHint": "You can note it without pressing for an answer.",
                        "priority": 65,
                        "relatedJourneyIds": [],
                        "relatedMaterialIds": list(signal.get("materialIds", []))[:3],
                        "relatedSymbolIds": [],
                        "relatedPracticeSessionIds": [],
                        "evidenceIds": [],
                        "reason": "longitudinal_signal_active",
                    }
                ]
        for item in memory_snapshot.get("items", [])[:3]:
            material_id = item.get("provenance", {}).get("materialId")
            if material_id:
                return [
                    {
                        "briefType": "daily",
                        "triggerKey": (
                            f"daily:memory_item:{item['entityId']}:{self._day_bucket(now)}"
                        ),
                        "titleHint": "Daily pattern note",
                        "summaryHint": (
                            "A recent symbolic thread may be ready for a light surfacing."
                        ),
                        "suggestedActionHint": "You can simply note it and move on.",
                        "priority": 60,
                        "relatedJourneyIds": [],
                        "relatedMaterialIds": [material_id],
                        "relatedSymbolIds": [],
                        "relatedPracticeSessionIds": [],
                        "evidenceIds": list(item.get("provenance", {}).get("evidenceIds", [])),
                        "reason": "memory_kernel_recent",
                    }
                ]
        return []

    def _weekly_review_seed(
        self,
        *,
        user_id: str,
        dashboard: DashboardSummary,
        now: str,
    ) -> list[RhythmicBriefSeed]:
        latest_review = dashboard.get("latestReview")
        week_bucket = self._week_bucket(now)
        if latest_review and self._week_bucket(latest_review.get("windowEnd", now)) == week_bucket:
            return []
        return [
            {
                "briefType": "weekly",
                "triggerKey": f"weekly:review_due:{user_id}:{week_bucket}",
                "titleHint": "Weekly review",
                "summaryHint": "A weekly review window appears to be open.",
                "suggestedActionHint": "You can review the week, or let it wait.",
                "priority": 50,
                "relatedJourneyIds": [],
                "relatedMaterialIds": [],
                "relatedSymbolIds": [],
                "relatedPracticeSessionIds": [],
                "evidenceIds": [],
                "reason": "weekly_review_due",
            }
        ]

    def _latest_brief_time(self, briefs: list[ProactiveBriefRecord]) -> datetime | None:
        visible = [
            item for item in briefs if item.get("status") in {"shown", "acted_on", "dismissed"}
        ]
        if not visible:
            return None
        latest = max(
            visible,
            key=lambda item: item.get(
                "shownAt",
                item.get("updatedAt", item.get("createdAt", "1970-01-01T00:00:00Z")),
            ),
        )
        return self._parse_datetime(
            latest.get("shownAt", latest.get("updatedAt", latest.get("createdAt")))
        )

    def _day_bucket(self, value: str) -> str:
        return self._parse_datetime(value).date().isoformat()

    def _week_bucket(self, value: str) -> str:
        parsed = self._parse_datetime(value).date()
        year, week, _ = parsed.isocalendar()
        return f"{year}-W{week:02d}"

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

    def _related_refs_for_entity(
        self,
        *,
        memory_snapshot: MemoryKernelSnapshot,
        entity_id: str,
    ) -> dict[str, list[str]]:
        material_ids: list[str] = []
        evidence_ids: list[str] = []
        if not entity_id:
            return {"materialIds": material_ids, "evidenceIds": evidence_ids}
        for item in memory_snapshot.get("items", []):
            if item.get("entityId") != entity_id:
                continue
            material_id = item.get("provenance", {}).get("materialId")
            if isinstance(material_id, str) and material_id and material_id not in material_ids:
                material_ids.append(material_id)
            for evidence_id in item.get("provenance", {}).get("evidenceIds", []):
                if evidence_id not in evidence_ids:
                    evidence_ids.append(evidence_id)
        return {"materialIds": material_ids[:3], "evidenceIds": evidence_ids[:5]}
