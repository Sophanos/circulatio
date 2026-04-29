from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from typing import cast

from ..domain.adaptation import RhythmCadenceHints
from ..domain.ids import create_id, now_iso
from ..domain.journeys import JourneyRecord
from ..domain.memory import MemoryKernelSnapshot
from ..domain.practices import PracticeSessionRecord
from ..domain.presentation import (
    PresentationSourceRef,
    RitualInvitationPlanDraft,
    RitualInvitationSummary,
)
from ..domain.proactive import (
    ProactiveBriefRecord,
    ProactiveBriefStatus,
    ProactiveBriefType,
    RhythmBriefSource,
    RhythmicBriefSeed,
)
from ..domain.reviews import DashboardSummary
from ..domain.types import (
    CoachCaptureContract,
    CoachLoopKind,
    CoachMoveKind,
    Id,
    MethodContextSnapshot,
    ResourceInvitationSummary,
    ThreadDigest,
    UserAdaptationProfileSummary,
)
from .method_state_policy import (
    derive_runtime_method_state_policy,
    get_active_goal_tension_summary,
)


class ProactiveEngine:
    def build_candidate_seeds(
        self,
        *,
        user_id: str,
        memory_snapshot: MemoryKernelSnapshot,
        dashboard: DashboardSummary,
        method_context: MethodContextSnapshot | None,
        thread_digests: list[ThreadDigest] | None,
        recent_practices: list[PracticeSessionRecord],
        journeys: list[JourneyRecord],
        existing_briefs: list[ProactiveBriefRecord],
        adaptation_profile: UserAdaptationProfileSummary | None = None,
        source: RhythmBriefSource,
        now: str,
        limit: int = 3,
    ) -> list[RhythmicBriefSeed]:
        runtime_policy = self._effective_runtime_policy(
            method_context=method_context,
            adaptation_profile=adaptation_profile,
        )
        seeds: list[RhythmicBriefSeed] = []
        if source != "manual":
            seeds.extend(
                self._coach_loop_seeds(
                    coach_state=(
                        cast(dict[str, object] | None, (method_context or {}).get("coachState"))
                        if isinstance(method_context, dict)
                        else None
                    ),
                    existing_briefs=existing_briefs,
                    source=source,
                    now=now,
                )
            )
        seeds.extend(self._practice_followup_seeds(recent_practices=recent_practices, now=now))
        seeds.extend(self._journey_seeds(journeys=journeys, now=now))
        seeds.extend(
            self._series_seeds(
                method_context=method_context,
                thread_digests=thread_digests,
                now=now,
            )
        )
        seeds.extend(
            self._threshold_invitation_seeds(
                method_context=method_context,
                memory_snapshot=memory_snapshot,
                thread_digests=thread_digests,
                now=now,
            )
        )
        seeds.extend(
            self._chapter_invitation_seeds(
                method_context=method_context,
                memory_snapshot=memory_snapshot,
                thread_digests=thread_digests,
                now=now,
            )
        )
        seeds.extend(
            self._return_invitation_seeds(
                method_context=method_context,
                thread_digests=thread_digests,
                now=now,
            )
        )
        seeds.extend(
            self._bridge_invitation_seeds(
                method_context=method_context,
                memory_snapshot=memory_snapshot,
                thread_digests=thread_digests,
                now=now,
            )
        )
        seeds.extend(
            self._analysis_packet_invitation_seeds(
                user_id=user_id,
                method_context=method_context,
                memory_snapshot=memory_snapshot,
                thread_digests=thread_digests,
                now=now,
            )
        )
        seeds.extend(
            self._goal_or_signal_seeds(
                method_context=method_context,
                memory_snapshot=memory_snapshot,
                thread_digests=thread_digests,
                now=now,
            )
        )
        if source == "scheduled":
            seeds.extend(
                self._ritual_invitation_seed(
                    user_id=user_id,
                    dashboard=dashboard,
                    method_context=method_context,
                    now=now,
                )
            )
        seeds.extend(self._weekly_review_seed(user_id=user_id, dashboard=dashboard, now=now))
        seeds = self._apply_runtime_policy_to_seeds(
            seeds=seeds,
            runtime_policy=runtime_policy,
        )
        seeds = self._dedupe_seeds(seeds)
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
        active_coach_loop_keys = {
            str(item.get("coachLoopKey"))
            for item in existing_briefs
            if item.get("status") in {"candidate", "shown"} and item.get("coachLoopKey")
        }
        suppressed_trigger_keys = {
            str(item.get("triggerKey"))
            for item in existing_briefs
            if item.get("status") == "dismissed"
            and item.get("triggerKey")
            and item.get("cooldownUntil")
            and self._parse_datetime(item["cooldownUntil"]) > now_dt
        }
        suppressed_coach_loop_keys = {
            str(item.get("coachLoopKey"))
            for item in existing_briefs
            if item.get("status") in {"dismissed", "acted_on"}
            and item.get("coachLoopKey")
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
            coach_loop_key = str(seed.get("coachLoopKey") or "").strip()
            if (
                trigger_key in active_trigger_keys
                or trigger_key in suppressed_trigger_keys
                or (coach_loop_key and coach_loop_key in active_coach_loop_keys)
                or (coach_loop_key and coach_loop_key in suppressed_coach_loop_keys)
            ):
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
            thread_digests=None,
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

    def _dedupe_seeds(self, seeds: list[RhythmicBriefSeed]) -> list[RhythmicBriefSeed]:
        deduped: list[RhythmicBriefSeed] = []
        seen_trigger_keys: set[str] = set()
        seen_loop_keys: set[str] = set()
        for seed in seeds:
            trigger_key = str(seed.get("triggerKey") or "").strip()
            coach_loop_key = str(seed.get("coachLoopKey") or "").strip()
            if trigger_key and trigger_key in seen_trigger_keys:
                continue
            if coach_loop_key and coach_loop_key in seen_loop_keys:
                continue
            if trigger_key:
                seen_trigger_keys.add(trigger_key)
            if coach_loop_key:
                seen_loop_keys.add(coach_loop_key)
            deduped.append(seed)
        return deduped

    def _merge_ids(self, existing: list[str], additions: list[str]) -> list[str]:
        merged = list(existing)
        for value in additions:
            candidate = str(value).strip()
            if candidate and candidate not in merged:
                merged.append(candidate)
        return merged

    def _thread_seed_links(
        self,
        *,
        thread_digests: list[ThreadDigest] | None,
        candidate_ids: list[str],
    ) -> dict[str, list[str]]:
        normalized_candidate_ids = {
            str(value).strip() for value in candidate_ids if str(value).strip()
        }
        if not normalized_candidate_ids:
            return {
                "relatedJourneyIds": [],
                "relatedMaterialIds": [],
                "relatedSymbolIds": [],
                "relatedPracticeSessionIds": [],
                "evidenceIds": [],
            }
        related_journey_ids: list[str] = []
        related_material_ids: list[str] = []
        related_symbol_ids: list[str] = []
        related_practice_ids: list[str] = []
        evidence_ids: list[str] = []
        for digest in thread_digests or []:
            if not isinstance(digest, dict):
                continue
            digest_candidate_ids: set[str] = set()
            entity_refs = (
                digest.get("entityRefs") if isinstance(digest.get("entityRefs"), dict) else {}
            )
            for ref_ids in entity_refs.values():
                if not isinstance(ref_ids, list):
                    continue
                digest_candidate_ids.update(
                    str(ref_id).strip() for ref_id in ref_ids if str(ref_id).strip()
                )
            digest_candidate_ids.update(
                str(ref_id).strip()
                for ref_id in digest.get("journeyIds", [])
                if isinstance(ref_id, str) and ref_id.strip()
            )
            for source_ref in digest.get("sourceRecordRefs", []):
                if not isinstance(source_ref, dict):
                    continue
                record_id = str(source_ref.get("recordId") or "").strip()
                if record_id:
                    digest_candidate_ids.add(record_id)
            if not normalized_candidate_ids.intersection(digest_candidate_ids):
                continue
            related_journey_ids = self._merge_ids(
                related_journey_ids,
                [
                    str(ref_id)
                    for ref_id in digest.get("journeyIds", [])
                    if isinstance(ref_id, str) and ref_id.strip()
                ],
            )
            related_material_ids = self._merge_ids(
                related_material_ids,
                [
                    str(ref_id)
                    for ref_id in entity_refs.get("materials", [])
                    if isinstance(ref_id, str) and ref_id.strip()
                ],
            )
            related_symbol_ids = self._merge_ids(
                related_symbol_ids,
                [
                    str(ref_id)
                    for ref_id in entity_refs.get("symbols", [])
                    if isinstance(ref_id, str) and ref_id.strip()
                ],
            )
            related_practice_ids = self._merge_ids(
                related_practice_ids,
                [
                    str(ref_id)
                    for ref_id in entity_refs.get("practiceSessions", [])
                    if isinstance(ref_id, str) and ref_id.strip()
                ],
            )
            evidence_ids = self._merge_ids(
                evidence_ids,
                [
                    str(ref_id)
                    for ref_id in digest.get("evidenceIds", [])
                    if isinstance(ref_id, str) and ref_id.strip()
                ],
            )
        return {
            "relatedJourneyIds": related_journey_ids,
            "relatedMaterialIds": related_material_ids,
            "relatedSymbolIds": related_symbol_ids,
            "relatedPracticeSessionIds": related_practice_ids,
            "evidenceIds": evidence_ids,
        }

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

    def _coach_loop_seeds(
        self,
        *,
        coach_state: dict[str, object] | None,
        existing_briefs: list[ProactiveBriefRecord],
        source: RhythmBriefSource,
        now: str,
    ) -> list[RhythmicBriefSeed]:
        del existing_briefs
        if source == "manual" or not isinstance(coach_state, dict):
            return []
        seeds: list[RhythmicBriefSeed] = []
        for loop in coach_state.get("activeLoops", []):
            if not isinstance(loop, dict):
                continue
            if str(loop.get("status") or "").strip() != "eligible":
                continue
            loop_key = str(loop.get("loopKey") or "").strip()
            if not loop_key:
                continue
            move_kind = str(loop.get("moveKind") or "").strip()
            kind = str(loop.get("kind") or "").strip()
            if move_kind == "track_without_prompt":
                continue
            brief_type = "daily"
            if move_kind == "offer_resource":
                brief_type = "resource_invitation"
            elif kind == "practice_integration":
                brief_type = "practice_followup"
            elif kind in {"journey_reentry", "relational_scene"} and loop.get("relatedJourneyIds"):
                brief_type = "journey_checkin"
            elif kind == "goal_guidance":
                brief_type = "weekly"
            bucket = (
                self._week_bucket(now)
                if brief_type in {"weekly", "journey_checkin"}
                else self._day_bucket(now)
            )
            seed: RhythmicBriefSeed = {
                "briefType": cast(ProactiveBriefType, brief_type),
                "triggerKey": f"coach_loop:{loop_key}:{brief_type}:{bucket}",
                "titleHint": str(loop.get("titleHint") or "Coach loop"),
                "summaryHint": str(loop.get("summaryHint") or "A live thread may be ready."),
                "priority": int(loop.get("priority", 0) or 0),
                "relatedJourneyIds": [
                    str(item) for item in loop.get("relatedJourneyIds", []) if str(item).strip()
                ],
                "relatedMaterialIds": [
                    str(item) for item in loop.get("relatedMaterialIds", []) if str(item).strip()
                ],
                "relatedSymbolIds": [
                    str(item) for item in loop.get("relatedSymbolIds", []) if str(item).strip()
                ],
                "relatedPracticeSessionIds": [
                    str(item)
                    for item in loop.get("relatedPracticeSessionIds", [])
                    if str(item).strip()
                ],
                "evidenceIds": [
                    str(item) for item in loop.get("evidenceIds", []) if str(item).strip()
                ],
                "reason": f"coach_loop:{kind}",
                "coachLoopKey": loop_key,
                "coachLoopKind": cast(CoachLoopKind, kind),
                "coachMoveKind": cast(CoachMoveKind, move_kind),
            }
            resource_invitation = (
                loop.get("resourceInvitation")
                if isinstance(loop.get("resourceInvitation"), dict)
                else {}
            )
            suggested_action_hint = str(
                resource_invitation.get("resource", {}).get("followUpQuestion") or ""
            ).strip()
            if not suggested_action_hint:
                prompt_frame = loop.get("promptFrame")
                if isinstance(prompt_frame, dict):
                    suggested_action_hint = str(prompt_frame.get("askAbout") or "").strip()
            if suggested_action_hint:
                seed["suggestedActionHint"] = suggested_action_hint
            if isinstance(loop.get("capture"), dict):
                seed["capture"] = cast(CoachCaptureContract, dict(loop["capture"]))
            if isinstance(resource_invitation, dict) and resource_invitation:
                seed["resourceInvitation"] = cast(
                    ResourceInvitationSummary, dict(resource_invitation)
                )
                resource = resource_invitation.get("resource")
                if isinstance(resource, dict) and str(resource.get("id") or "").strip():
                    seed["relatedResourceIds"] = [str(resource["id"])]
            seeds.append(seed)
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
        thread_digests: list[ThreadDigest] | None,
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
            thread_links = self._thread_seed_links(
                thread_digests=thread_digests,
                candidate_ids=[
                    str(series["id"]),
                    *[str(item) for item in series.get("materialIds", [])],
                ],
            )
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
                    "relatedJourneyIds": list(thread_links["relatedJourneyIds"]),
                    "relatedMaterialIds": self._merge_ids(
                        list(series.get("materialIds", []))[:3],
                        thread_links["relatedMaterialIds"],
                    )[:3],
                    "relatedSymbolIds": self._merge_ids(
                        list(series.get("symbolIds", []))[:3],
                        thread_links["relatedSymbolIds"],
                    )[:3],
                    "relatedPracticeSessionIds": list(thread_links["relatedPracticeSessionIds"]),
                    "evidenceIds": list(thread_links["evidenceIds"]),
                    "reason": "dream_series_recent",
                }
            )
        return seeds

    def _threshold_invitation_seeds(
        self,
        *,
        method_context: MethodContextSnapshot | None,
        memory_snapshot: MemoryKernelSnapshot,
        thread_digests: list[ThreadDigest] | None,
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
            thread_links = self._thread_seed_links(
                thread_digests=thread_digests,
                candidate_ids=[
                    str(threshold.get("id") or ""),
                    *related["materialIds"],
                ],
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
                    "relatedJourneyIds": list(thread_links["relatedJourneyIds"]),
                    "relatedMaterialIds": self._merge_ids(
                        related["materialIds"],
                        thread_links["relatedMaterialIds"],
                    )[:3],
                    "relatedSymbolIds": list(thread_links["relatedSymbolIds"]),
                    "relatedPracticeSessionIds": list(thread_links["relatedPracticeSessionIds"]),
                    "evidenceIds": self._merge_ids(
                        [
                            str(item)
                            for item in threshold.get("evidenceIds", [])
                            if str(item).strip()
                        ],
                        thread_links["evidenceIds"],
                    )[:5],
                    "reason": "threshold_process_ready",
                }
            )
        return seeds

    def _chapter_invitation_seeds(
        self,
        *,
        method_context: MethodContextSnapshot | None,
        memory_snapshot: MemoryKernelSnapshot,
        thread_digests: list[ThreadDigest] | None,
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
        thread_links = self._thread_seed_links(
            thread_digests=thread_digests,
            candidate_ids=[str(chapter.get("id") or ""), *related["materialIds"]],
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
                "relatedJourneyIds": list(thread_links["relatedJourneyIds"]),
                "relatedMaterialIds": self._merge_ids(
                    related["materialIds"],
                    thread_links["relatedMaterialIds"],
                )[:3],
                "relatedSymbolIds": list(thread_links["relatedSymbolIds"]),
                "relatedPracticeSessionIds": list(thread_links["relatedPracticeSessionIds"]),
                "evidenceIds": self._merge_ids(
                    [str(item) for item in chapter.get("evidenceIds", []) if str(item).strip()],
                    thread_links["evidenceIds"],
                )[:5],
                "reason": "life_chapter_active",
            }
        ]

    def _return_invitation_seeds(
        self,
        *,
        method_context: MethodContextSnapshot | None,
        thread_digests: list[ThreadDigest] | None,
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
            thread_links = self._thread_seed_links(
                thread_digests=thread_digests,
                candidate_ids=[str(marker.get("id") or "")],
            )
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
                    "relatedJourneyIds": list(thread_links["relatedJourneyIds"]),
                    "relatedMaterialIds": list(thread_links["relatedMaterialIds"]),
                    "relatedSymbolIds": list(thread_links["relatedSymbolIds"]),
                    "relatedPracticeSessionIds": list(thread_links["relatedPracticeSessionIds"]),
                    "evidenceIds": self._merge_ids(
                        [str(item) for item in marker.get("evidenceIds", []) if str(item).strip()],
                        thread_links["evidenceIds"],
                    )[:5],
                    "reason": "threshold_return_marker",
                }
            ]
        individuation = method_context.get("individuationContext") or {}
        for threshold in individuation.get("thresholdProcesses", [])[:3]:
            if threshold.get("phase") != "return":
                continue
            label = str(threshold.get("label") or "Threshold process")
            thread_links = self._thread_seed_links(
                thread_digests=thread_digests,
                candidate_ids=[str(threshold.get("id") or "")],
            )
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
                    "relatedJourneyIds": list(thread_links["relatedJourneyIds"]),
                    "relatedMaterialIds": list(thread_links["relatedMaterialIds"]),
                    "relatedSymbolIds": list(thread_links["relatedSymbolIds"]),
                    "relatedPracticeSessionIds": list(thread_links["relatedPracticeSessionIds"]),
                    "evidenceIds": self._merge_ids(
                        [
                            str(item)
                            for item in threshold.get("evidenceIds", [])
                            if str(item).strip()
                        ],
                        thread_links["evidenceIds"],
                    )[:5],
                    "reason": "threshold_return_phase",
                }
            ]
        return []

    def _bridge_invitation_seeds(
        self,
        *,
        method_context: MethodContextSnapshot | None,
        memory_snapshot: MemoryKernelSnapshot,
        thread_digests: list[ThreadDigest] | None,
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
        thread_links = self._thread_seed_links(
            thread_digests=thread_digests,
            candidate_ids=[str(bridge.get("id") or ""), *related["materialIds"]],
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
                "relatedJourneyIds": list(thread_links["relatedJourneyIds"]),
                "relatedMaterialIds": self._merge_ids(
                    related["materialIds"],
                    thread_links["relatedMaterialIds"],
                )[:3],
                "relatedSymbolIds": list(thread_links["relatedSymbolIds"]),
                "relatedPracticeSessionIds": list(thread_links["relatedPracticeSessionIds"]),
                "evidenceIds": self._merge_ids(
                    [str(item) for item in bridge.get("evidenceIds", []) if str(item).strip()],
                    thread_links["evidenceIds"],
                )[:5],
                "reason": "bridge_moment_active",
            }
        ]

    def _analysis_packet_invitation_seeds(
        self,
        *,
        user_id: str,
        method_context: MethodContextSnapshot | None,
        memory_snapshot: MemoryKernelSnapshot,
        thread_digests: list[ThreadDigest] | None,
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
        thread_links = self._thread_seed_links(
            thread_digests=thread_digests,
            candidate_ids=[user_id, *related_material_ids],
        )
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
                "relatedJourneyIds": list(thread_links["relatedJourneyIds"]),
                "relatedMaterialIds": self._merge_ids(
                    related_material_ids[:3],
                    thread_links["relatedMaterialIds"],
                )[:3],
                "relatedSymbolIds": list(thread_links["relatedSymbolIds"]),
                "relatedPracticeSessionIds": list(thread_links["relatedPracticeSessionIds"]),
                "evidenceIds": self._merge_ids(evidence_ids[:5], thread_links["evidenceIds"])[:5],
                "reason": "analysis_packet_ready",
            }
        ]

    def _goal_or_signal_seeds(
        self,
        *,
        method_context: MethodContextSnapshot | None,
        memory_snapshot: MemoryKernelSnapshot,
        thread_digests: list[ThreadDigest] | None,
        now: str,
    ) -> list[RhythmicBriefSeed]:
        if method_context:
            active_goal_tension = get_active_goal_tension_summary(method_context) or {}
            active_goal_tension_id = str(active_goal_tension.get("goalTensionId") or "").strip()
            if active_goal_tension_id:
                balancing_direction = str(
                    active_goal_tension.get("balancingDirection") or ""
                ).strip()
                reason = (
                    balancing_direction
                    or "An active goal tension may be asking for gentle attention."
                )
                thread_links = self._thread_seed_links(
                    thread_digests=thread_digests,
                    candidate_ids=[active_goal_tension_id],
                )
                return [
                    {
                        "briefType": "daily",
                        "triggerKey": (
                            f"daily:goal_tension:{active_goal_tension_id}:{self._day_bucket(now)}"
                        ),
                        "titleHint": "Goal tension",
                        "summaryHint": reason,
                        "suggestedActionHint": (
                            "You can name the live tension without forcing resolution."
                        ),
                        "priority": 74,
                        "relatedJourneyIds": list(thread_links["relatedJourneyIds"]),
                        "relatedMaterialIds": list(thread_links["relatedMaterialIds"]),
                        "relatedSymbolIds": list(thread_links["relatedSymbolIds"]),
                        "relatedPracticeSessionIds": list(
                            thread_links["relatedPracticeSessionIds"]
                        ),
                        "evidenceIds": self._merge_ids(
                            [
                                str(item)
                                for item in active_goal_tension.get("evidenceIds", [])
                                if str(item).strip()
                            ],
                            thread_links["evidenceIds"],
                        )[:5],
                        "reason": "goal_tension_active_method_state",
                    }
                ]
            signals = method_context.get("longitudinalSignals", [])
            if signals:
                signal = signals[0]
                thread_links = self._thread_seed_links(
                    thread_digests=thread_digests,
                    candidate_ids=[
                        str(signal.get("id") or ""),
                        *[str(item) for item in signal.get("materialIds", [])],
                    ],
                )
                return [
                    {
                        "briefType": "daily",
                        "triggerKey": f"daily:signal:{signal['id']}:{self._day_bucket(now)}",
                        "titleHint": "Longitudinal signal",
                        "summaryHint": "A recurring pattern may be ripe for a short check-in.",
                        "suggestedActionHint": "You can note it without pressing for an answer.",
                        "priority": 65,
                        "relatedJourneyIds": list(thread_links["relatedJourneyIds"]),
                        "relatedMaterialIds": self._merge_ids(
                            list(signal.get("materialIds", []))[:3],
                            thread_links["relatedMaterialIds"],
                        )[:3],
                        "relatedSymbolIds": list(thread_links["relatedSymbolIds"]),
                        "relatedPracticeSessionIds": list(
                            thread_links["relatedPracticeSessionIds"]
                        ),
                        "evidenceIds": list(thread_links["evidenceIds"]),
                        "reason": "longitudinal_signal_active",
                    }
                ]
        for item in memory_snapshot.get("items", [])[:3]:
            material_id = item.get("provenance", {}).get("materialId")
            if material_id:
                thread_links = self._thread_seed_links(
                    thread_digests=thread_digests,
                    candidate_ids=[str(item.get("entityId") or ""), str(material_id)],
                )
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
                        "relatedJourneyIds": list(thread_links["relatedJourneyIds"]),
                        "relatedMaterialIds": self._merge_ids(
                            [str(material_id)],
                            thread_links["relatedMaterialIds"],
                        )[:3],
                        "relatedSymbolIds": list(thread_links["relatedSymbolIds"]),
                        "relatedPracticeSessionIds": list(
                            thread_links["relatedPracticeSessionIds"]
                        ),
                        "evidenceIds": self._merge_ids(
                            [
                                str(evidence_id)
                                for evidence_id in item.get("provenance", {}).get("evidenceIds", [])
                                if str(evidence_id).strip()
                            ],
                            thread_links["evidenceIds"],
                        )[:5],
                        "reason": "memory_kernel_recent",
                    }
                ]
        return []

    def _ritual_invitation_seed(
        self,
        *,
        user_id: str,
        dashboard: DashboardSummary,
        method_context: MethodContextSnapshot | None,
        now: str,
    ) -> list[RhythmicBriefSeed]:
        week_bucket = self._week_bucket(now)
        source_refs = self._ritual_invitation_source_refs(dashboard=dashboard)
        safety_context = cast(dict[str, object] | None, (method_context or {}).get("safetyContext"))
        requested_surfaces = {
            "text": {"enabled": True},
            "audio": {"enabled": False},
            "captions": {"enabled": True, "format": "webvtt"},
            "breath": {"enabled": True, "request": {"pattern": "steadying"}},
            "meditation": {"enabled": True, "request": {"fieldType": "coherence_convergence"}},
            "image": {"enabled": False},
            "music": {"enabled": False},
            "cinema": {"enabled": False},
        }
        render_policy = {
            "mode": "dry_run_manifest",
            "externalProvidersAllowed": False,
            "videoAllowed": False,
            "providerAllowlist": ["mock", "local"],
            "maxCost": {"currency": "USD", "amount": 0},
            "sourceDataPolicy": {
                "allowRawMaterialTextInPlan": False,
                "allowRawMaterialTextToProviders": False,
                "providerPromptPolicy": "none",
            },
        }
        completion_policy = {
            "captureReflection": True,
            "capturePracticeFeedback": True,
            "returnMode": "frontend_callback",
        }
        plan_draft: RitualInvitationPlanDraft = {
            "sourceRefs": source_refs,
            "ritualIntent": "weekly_integration",
            "narrativeMode": "hybrid",
            "requestedSurfaces": requested_surfaces,
            "privacyClass": "private",
            "renderPolicy": render_policy,
            "completionPolicy": completion_policy,
            "locale": "en-US",
        }
        if safety_context:
            plan_draft["safetyContext"] = deepcopy(safety_context)
        acceptance_payload: dict[str, object] = {
            "ritualIntent": "weekly_integration",
            "narrativeMode": "hybrid",
            "sourceRefs": source_refs,
            "requestedSurfaces": requested_surfaces,
            "renderPolicy": render_policy,
            "completionPolicy": completion_policy,
            "privacyClass": "private",
            "locale": "en-US",
        }
        if safety_context:
            acceptance_payload["safetyContext"] = deepcopy(safety_context)
        invitation: RitualInvitationSummary = {
            "invitationId": create_id("ritual_invitation"),
            "userId": user_id,
            "sourceRefs": source_refs,
            "title": "Weekly ritual invitation",
            "summary": (
                "A weekly ritual can be prepared from approved summaries and recent "
                "continuity if you accept it."
            ),
            "suggestedIntent": "weekly_integration",
            "suggestedSurfaces": ["text", "captions", "breath", "meditation"],
            "privacyClass": "private",
            "cadence": "weekly",
            "generatedAt": now,
            "expiresAt": (self._parse_datetime(now) + timedelta(days=7))
            .isoformat()
            .replace("+00:00", "Z"),
            "planDraft": plan_draft,
            "acceptancePayload": acceptance_payload,
        }
        material_ids = [
            str(ref.get("recordId"))
            for ref in source_refs
            if ref.get("sourceType") == "material" and ref.get("recordId")
        ]
        evidence_ids = [
            str(evidence_id)
            for ref in source_refs
            for evidence_id in ref.get("evidenceIds", [])
            if str(evidence_id).strip()
        ]
        return [
            {
                "briefType": "ritual_invitation",
                "triggerKey": f"ritual_invitation:weekly:{user_id}:{week_bucket}",
                "titleHint": invitation["title"],
                "summaryHint": invitation["summary"],
                "suggestedActionHint": (
                    "Accept to prepare the plan; ignore it and nothing is rendered."
                ),
                "priority": 55,
                "relatedJourneyIds": [],
                "relatedMaterialIds": material_ids,
                "relatedSymbolIds": [],
                "relatedPracticeSessionIds": [],
                "evidenceIds": list(dict.fromkeys(evidence_ids)),
                "reason": "weekly_ritual_invitation_due",
                "ritualInvitation": invitation,
            }
        ]

    def _ritual_invitation_source_refs(
        self,
        *,
        dashboard: DashboardSummary,
    ) -> list[PresentationSourceRef]:
        refs: list[PresentationSourceRef] = []
        latest_review = dashboard.get("latestReview")
        if isinstance(latest_review, dict):
            refs.append(
                {
                    "sourceType": "weekly_review",
                    "recordId": str(latest_review.get("id") or ""),
                    "role": "primary",
                    "title": "Latest weekly review",
                    "evidenceIds": [str(item) for item in latest_review.get("evidenceIds", [])],
                    "approvalState": "read_only_generated",
                }
            )
        for material in dashboard.get("recentMaterials", [])[:3]:
            if not isinstance(material, dict):
                continue
            material_id = str(material.get("id") or "").strip()
            if not material_id:
                continue
            title = str(material.get("title") or material.get("summary") or "Recent material")
            refs.append(
                {
                    "sourceType": "material",
                    "recordId": material_id,
                    "role": "supporting" if refs else "primary",
                    "title": self._sanitize_text(title, avoid_patterns=[]),
                    "evidenceIds": [],
                    "approvalState": "read_only_generated",
                }
            )
        if not refs:
            refs.append(
                {
                    "sourceType": "surface_result",
                    "recordId": "weekly_continuity",
                    "role": "primary",
                    "title": "Weekly continuity",
                    "evidenceIds": [],
                    "approvalState": "read_only_generated",
                }
            )
        return refs

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

    def _effective_runtime_policy(
        self,
        *,
        method_context: MethodContextSnapshot | None,
        adaptation_profile: UserAdaptationProfileSummary | None,
    ) -> dict[str, object]:
        snapshot: MethodContextSnapshot | None = None
        if isinstance(method_context, dict):
            snapshot = cast(MethodContextSnapshot, dict(method_context))
        elif adaptation_profile is not None:
            snapshot = cast(MethodContextSnapshot, {"adaptationProfile": adaptation_profile})
        if (
            isinstance(snapshot, dict)
            and adaptation_profile is not None
            and not isinstance(snapshot.get("adaptationProfile"), dict)
        ):
            snapshot["adaptationProfile"] = adaptation_profile
        return dict(derive_runtime_method_state_policy(snapshot))

    def _apply_runtime_policy_to_seeds(
        self,
        *,
        seeds: list[RhythmicBriefSeed],
        runtime_policy: dict[str, object],
    ) -> list[RhythmicBriefSeed]:
        filtered: list[RhythmicBriefSeed] = []
        for seed in seeds:
            if self._seed_blocked_by_policy(seed=seed, runtime_policy=runtime_policy):
                continue
            personalized = dict(seed)
            self._personalize_seed_copy(seed=personalized, runtime_policy=runtime_policy)
            filtered.append(personalized)
        return filtered

    def _seed_blocked_by_policy(
        self,
        *,
        seed: RhythmicBriefSeed,
        runtime_policy: dict[str, object],
    ) -> bool:
        depth_level = str(runtime_policy.get("depthLevel") or "").strip()
        brief_type = str(seed.get("briefType") or "").strip()
        if depth_level == "grounding_only" and brief_type not in {
            "practice_followup",
            "resource_invitation",
        }:
            return True
        return False

    def _personalize_seed_copy(
        self,
        *,
        seed: RhythmicBriefSeed,
        runtime_policy: dict[str, object],
    ) -> None:
        tone = str(runtime_policy.get("witnessTone") or "").strip()
        question_style = str(runtime_policy.get("questionStyle") or "").strip()
        practice_constraints = (
            runtime_policy.get("practiceConstraints")
            if isinstance(runtime_policy.get("practiceConstraints"), dict)
            else {}
        )
        avoid_patterns = [
            str(item).strip()
            for item in runtime_policy.get("avoidPhrasingPatterns", [])
            if str(item).strip()
        ]
        active_goal_frame = str(runtime_policy.get("activeGoalFrame") or "").strip()
        brief_type = str(seed.get("briefType") or "").strip()
        if question_style and brief_type != "practice_followup":
            action_hint = self._question_style_action_hint(question_style)
            if action_hint:
                seed["suggestedActionHint"] = action_hint
        if tone == "direct":
            seed["summaryHint"] = self._sanitize_text(
                "A live thread looks ready for a plain, bounded check-in.",
                avoid_patterns=avoid_patterns,
            )
        elif tone == "spacious":
            seed["summaryHint"] = self._sanitize_text(
                "A live thread may be ready for a light check-in with room around it.",
                avoid_patterns=avoid_patterns,
            )
        elif tone == "grounded":
            seed["summaryHint"] = self._sanitize_text(
                "Keep this concrete and close to lived contact before making meaning.",
                avoid_patterns=avoid_patterns,
            )
        elif seed.get("summaryHint"):
            seed["summaryHint"] = self._sanitize_text(
                str(seed.get("summaryHint") or ""),
                avoid_patterns=avoid_patterns,
            )
        if seed.get("suggestedActionHint"):
            seed["suggestedActionHint"] = self._sanitize_text(
                str(seed.get("suggestedActionHint") or ""),
                avoid_patterns=avoid_patterns,
            )
        if seed.get("titleHint"):
            seed["titleHint"] = self._sanitize_text(
                str(seed.get("titleHint") or ""),
                avoid_patterns=avoid_patterns,
            )
        if active_goal_frame and str(seed.get("reason") or "").startswith("goal_tension_active"):
            seed["summaryHint"] = self._sanitize_text(
                active_goal_frame,
                avoid_patterns=avoid_patterns,
            )
        prefer_low_intensity = bool(practice_constraints.get("preferLowIntensity"))
        protect_relational_space = bool(practice_constraints.get("protectRelationalSpace"))
        if prefer_low_intensity and brief_type in {
            "threshold_invitation",
            "chapter_invitation",
            "analysis_packet_invitation",
            "return_invitation",
            "bridge_invitation",
        }:
            seed["priority"] = max(int(seed.get("priority", 0)) - 18, 1)
        if protect_relational_space and brief_type in {
            "threshold_invitation",
            "analysis_packet_invitation",
        }:
            seed["priority"] = max(int(seed.get("priority", 0)) - 12, 1)

    def _question_style_action_hint(self, question_style: str) -> str:
        mapping = {
            "body_first": "You can notice what your body does around this before naming meaning.",
            "image_first": "You can name the image that returns before explaining it.",
            "relational_first": "You can notice the contact pattern before deciding what it means.",
            "choice_based": (
                "You can name the next small choice instead of solving the whole story."
            ),
            "reflection_first": "You can say what feels most true in plain language.",
        }
        return mapping.get(question_style, "")

    def _sanitize_text(self, text: str, *, avoid_patterns: list[str]) -> str:
        sanitized = text
        lowered = sanitized.lower()
        for pattern in avoid_patterns:
            if not pattern:
                continue
            pattern_lower = pattern.lower()
            if pattern_lower not in lowered:
                continue
            start = lowered.find(pattern_lower)
            end = start + len(pattern_lower)
            sanitized = sanitized[:start].rstrip(" ,.;:") + sanitized[end:]
            lowered = sanitized.lower()
        return " ".join(sanitized.split()).strip() or text

    def _merge_adaptation_preferences(
        self,
        *,
        runtime_policy: dict[str, object],
        adaptation_profile: UserAdaptationProfileSummary | None,
    ) -> None:
        communication_preferences = self._adaptation_scope(
            adaptation_profile,
            explicit_scope="communication",
            learned_scope="communicationPolicy",
        )
        interpretation_preferences = self._adaptation_scope(
            adaptation_profile,
            explicit_scope="interpretation",
            learned_scope="interpretationPolicy",
        )
        interpretation_stats = self._adaptation_nested(adaptation_profile, "interpretationStats")
        interaction_feedback = self._adaptation_nested(
            adaptation_profile, "interactionFeedbackStats"
        )
        tone = str(communication_preferences.get("tone") or "").strip()
        if tone and not runtime_policy.get("witnessTone"):
            runtime_policy["witnessTone"] = tone
        question_style = str(communication_preferences.get("questioningStyle") or "").strip()
        question_style_map = {
            "soma_first": "body_first",
            "image_first": "image_first",
            "feeling_first": "relational_first",
            "reflective": "reflection_first",
        }
        mapped_style = question_style_map.get(question_style)
        if mapped_style and not runtime_policy.get("questionStyle"):
            runtime_policy["questionStyle"] = mapped_style
        depth_preference = str(interpretation_preferences.get("depthPreference") or "").strip()
        if depth_preference == "brief_pattern_notes" and not runtime_policy.get("depthLevel"):
            runtime_policy["depthLevel"] = "gentle"
        preferred_voice = self._last_string(interpretation_stats.get("preferredWitnessVoice"))
        if preferred_voice and not runtime_policy.get("witnessVoice"):
            runtime_policy["witnessVoice"] = preferred_voice
        rejected_patterns = self._strings(interpretation_stats.get("rejectedPhrasingPatterns"))
        if rejected_patterns and not runtime_policy.get("avoidPhrasingPatterns"):
            runtime_policy["avoidPhrasingPatterns"] = rejected_patterns[:5]
        interpretation_feedback = (
            interaction_feedback.get("interpretation")
            if isinstance(interaction_feedback.get("interpretation"), dict)
            else {}
        )
        recent_locale = self._last_string(interpretation_feedback.get("recentLocales"))
        if recent_locale and not runtime_policy.get("recentLocale"):
            runtime_policy["recentLocale"] = recent_locale

    def _adaptation_scope(
        self,
        adaptation_profile: UserAdaptationProfileSummary | None,
        *,
        explicit_scope: str,
        learned_scope: str,
    ) -> dict[str, object]:
        if not isinstance(adaptation_profile, dict):
            return {}
        explicit_preferences = (
            adaptation_profile.get("explicitPreferences")
            if isinstance(adaptation_profile.get("explicitPreferences"), dict)
            else {}
        )
        learned_signals = (
            adaptation_profile.get("learnedSignals")
            if isinstance(adaptation_profile.get("learnedSignals"), dict)
            else {}
        )
        result: dict[str, object] = {}
        explicit = explicit_preferences.get(explicit_scope)
        learned = learned_signals.get(learned_scope)
        if isinstance(learned, dict):
            result.update(learned)
        if isinstance(explicit, dict):
            result.update(explicit)
        return result

    def _adaptation_nested(
        self,
        adaptation_profile: UserAdaptationProfileSummary | None,
        key: str,
    ) -> dict[str, object]:
        if not isinstance(adaptation_profile, dict):
            return {}
        learned_signals = (
            adaptation_profile.get("learnedSignals")
            if isinstance(adaptation_profile.get("learnedSignals"), dict)
            else {}
        )
        nested = learned_signals.get(key)
        return dict(nested) if isinstance(nested, dict) else {}

    def _strings(self, value: object) -> list[str]:
        if not isinstance(value, list):
            return []
        return list(dict.fromkeys(str(item).strip() for item in value if str(item).strip()))

    def _last_string(self, value: object) -> str:
        if not isinstance(value, list):
            return ""
        values = [str(item).strip() for item in value if str(item).strip()]
        return values[-1] if values else ""
