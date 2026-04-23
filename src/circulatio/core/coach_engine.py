from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import Literal, cast

from ..domain.clarifications import ClarificationCaptureTarget
from ..domain.ids import create_id, now_iso
from ..domain.journeys import JourneyRecord
from ..domain.method_state import (
    MethodStateAnchorRefs,
    MethodStateCaptureTargetKind,
    MethodStateResponseSource,
)
from ..domain.practices import PracticeSessionRecord
from ..domain.proactive import ProactiveBriefRecord
from ..domain.reviews import DashboardSummary
from ..domain.timestamps import parse_iso_datetime
from ..domain.types import (
    CoachCaptureContract,
    CoachGlobalConstraints,
    CoachLoopKind,
    CoachLoopSummary,
    CoachMoveContract,
    CoachStateSummary,
    CoachSurface,
    CoachWithheldMoveSummary,
    Id,
    JourneyFollowthroughSummary,
    MethodContextSnapshot,
    MethodStateSourceRef,
    ResourceInvitationSummary,
    UserAdaptationProfileSummary,
    WitnessStateSummary,
)


class CoachEngine:
    def build_witness_state(
        self,
        *,
        method_context: MethodContextSnapshot,
        runtime_policy: dict[str, object],
    ) -> WitnessStateSummary:
        method_state = (
            method_context.get("methodState")
            if isinstance(method_context.get("methodState"), dict)
            else {}
        )
        questioning_preference = (
            method_state.get("questioningPreference")
            if isinstance(method_state.get("questioningPreference"), dict)
            else {}
        )
        typology_state = (
            method_state.get("typologyMethodState")
            if isinstance(method_state.get("typologyMethodState"), dict)
            else {}
        )
        practice_constraints = (
            runtime_policy.get("practiceConstraints")
            if isinstance(runtime_policy.get("practiceConstraints"), dict)
            else {}
        )
        stance = "paced_contact"
        depth_level = str(runtime_policy.get("depthLevel") or "gentle").strip()
        if depth_level == "grounding_only":
            stance = "grounding_first"
        elif depth_level == "standard":
            stance = "symbolic_contact"
        preferred_moves = [
            str(item).strip()
            for item in runtime_policy.get("preferredMoves", [])
            if str(item).strip()
        ]
        preferred_question_styles = [
            str(item).strip()
            for item in questioning_preference.get("preferredQuestionStyles", [])
            if str(item).strip()
        ]
        question_style = str(runtime_policy.get("questionStyle") or "").strip()
        if question_style and question_style not in preferred_question_styles:
            preferred_question_styles.append(question_style)
        avoided_question_styles = [
            str(item).strip()
            for item in questioning_preference.get("avoidedQuestionStyles", [])
            if str(item).strip()
        ]
        allowed_targets = {
            "answer_only",
            "body_state",
            "conscious_attitude",
            "goal",
            "goal_tension",
            "personal_amplification",
            "reality_anchors",
            "threshold_process",
            "relational_scene",
            "inner_outer_correspondence",
            "numinous_encounter",
            "aesthetic_resonance",
            "consent_preference",
            "interpretation_preference",
            "typology_feedback",
        }
        preferred_targets = [
            str(item).strip()
            for item in runtime_policy.get("preferredClarificationTargets", [])
            if str(item).strip() in allowed_targets
        ]
        practice_frame_parts: list[str] = []
        if bool(practice_constraints.get("preferLowIntensity")):
            practice_frame_parts.append("Keep practices low intensity.")
        max_duration = practice_constraints.get("maxDurationMinutes")
        if isinstance(max_duration, int) and max_duration > 0:
            practice_frame_parts.append(f"Keep practices within {max_duration} minutes.")
        compensation_prompt = str(practice_constraints.get("compensationPrompt") or "").strip()
        if compensation_prompt:
            practice_frame_parts.append(compensation_prompt)
        practice_bias = str(practice_constraints.get("practiceBias") or "").strip()
        if practice_bias:
            practice_frame_parts.append(practice_bias.replace("_", " "))
        typology_frame = ""
        prompt_bias = str(typology_state.get("promptBias") or "").strip()
        balancing_function = str(typology_state.get("balancingFunction") or "").strip()
        if prompt_bias or balancing_function:
            fragments = []
            if prompt_bias:
                fragments.append(prompt_bias.replace("_", " "))
            if balancing_function:
                fragments.append(f"balance through {balancing_function}")
            typology_frame = "; ".join(fragments)
        stance_value = cast(
            Literal["grounding_first", "paced_contact", "symbolic_contact"],
            stance,
        )
        tone_value = cast(
            Literal["grounded", "gentle", "direct", "spacious"],
            str(runtime_policy.get("witnessTone") or "gentle").strip() or "gentle",
        )
        preferred_targets_value = cast(list[ClarificationCaptureTarget], preferred_targets)
        updated_at = (
            str(method_state.get("generatedAt") or "").strip()
            or str(method_context.get("windowEnd") or "").strip()
            or now_iso()
        )
        witness_state: WitnessStateSummary = {
            "stance": stance_value,
            "tone": tone_value,
            "startingMove": preferred_moves[0]
            if preferred_moves
            else "grounding"
            if stance == "grounding_first"
            else "grounded_question"
            if stance == "paced_contact"
            else "association",
            "maxQuestionsPerTurn": int(runtime_policy.get("maxClarifyingQuestions", 2) or 2),
            "preferredQuestionStyles": preferred_question_styles,
            "avoidedQuestionStyles": avoided_question_styles,
            "preferredClarificationTargets": preferred_targets_value,
            "blockedMoves": [
                str(item).strip()
                for item in runtime_policy.get("blockedMoves", [])
                if str(item).strip()
            ],
            "avoidPhrasingPatterns": [
                str(item).strip()
                for item in runtime_policy.get("avoidPhrasingPatterns", [])
                if str(item).strip()
            ],
            "reasons": [
                str(item).strip()
                for item in runtime_policy.get("reasons", [])
                if str(item).strip()
            ],
            "updatedAt": updated_at,
        }
        witness_voice = str(runtime_policy.get("witnessVoice") or "").strip()
        if witness_voice:
            witness_state["witnessVoice"] = witness_voice
        active_goal_frame = str(runtime_policy.get("activeGoalFrame") or "").strip()
        if active_goal_frame:
            witness_state["activeGoalFrame"] = active_goal_frame
        if practice_frame_parts:
            witness_state["practiceFrame"] = " ".join(practice_frame_parts[:3])
        if typology_frame:
            witness_state["typologyFrame"] = typology_frame
        recent_locale = str(runtime_policy.get("recentLocale") or "").strip()
        if recent_locale:
            witness_state["recentLocale"] = recent_locale
        return witness_state

    def build_coach_state(
        self,
        *,
        method_context: MethodContextSnapshot | None,
        runtime_policy: dict[str, object],
        surface: CoachSurface,
        existing_briefs: list[ProactiveBriefRecord] | None = None,
        recent_practices: list[PracticeSessionRecord] | None = None,
        journeys: list[JourneyRecord] | None = None,
        journey_followthrough: list[JourneyFollowthroughSummary] | None = None,
        dashboard: DashboardSummary | None = None,
        adaptation_profile: UserAdaptationProfileSummary | None = None,
        now: str,
    ) -> CoachStateSummary:
        snapshot: MethodContextSnapshot = (
            cast(MethodContextSnapshot, dict(method_context))
            if isinstance(method_context, dict)
            else {}
        )
        if adaptation_profile is not None and not isinstance(
            snapshot.get("adaptationProfile"), dict
        ):
            snapshot["adaptationProfile"] = adaptation_profile
        witness = self.build_witness_state(method_context=snapshot, runtime_policy=runtime_policy)
        existing = existing_briefs or []
        practices = recent_practices or []
        journey_items = journeys or []
        loop_candidates: list[CoachLoopSummary] = []
        withheld: list[CoachWithheldMoveSummary] = []

        for builder in (
            self._soma_loop,
            self._goal_guidance_loop,
            self._relational_scene_loop,
            self._practice_integration_loop,
            self._journey_reentry_loop,
            self._resource_support_loop,
        ):
            loop, withheld_move = builder(
                method_context=snapshot,
                runtime_policy=runtime_policy,
                existing_briefs=existing,
                recent_practices=practices,
                journeys=journey_items,
                dashboard=dashboard,
                now=now,
            )
            if loop is not None:
                loop_candidates.append(loop)
            if withheld_move is not None:
                withheld.append(withheld_move)
        loop_candidates = self._integrate_journey_followthrough(
            loop_candidates=loop_candidates,
            journey_followthrough=journey_followthrough or [],
            method_context=snapshot,
            runtime_policy=runtime_policy,
            existing_briefs=existing,
            now=now,
        )

        loop_candidates.sort(key=lambda item: self._loop_sort_key(item, surface=surface))
        active_loops = loop_candidates[:4]
        selected_move = self.select_surface_move(
            coach_state=None,
            surface=surface,
            active_loops=active_loops,
        )
        constraints: CoachGlobalConstraints = {
            "depthLevel": cast(
                Literal["grounding_only", "gentle", "standard"],
                str(runtime_policy.get("depthLevel") or "gentle"),
            ),
            "blockedMoves": self._strings(runtime_policy.get("blockedMoves")),
            "maxQuestionsPerTurn": int(runtime_policy.get("maxClarifyingQuestions", 1) or 1),
            "doNotAskReasons": [
                *(
                    ["coach_state_no_eligible_move"]
                    if selected_move is None and not any(
                        str(loop.get("status") or "").strip() == "eligible" for loop in active_loops
                    )
                    else []
                ),
                *self._strings(runtime_policy.get("reasons")),
            ][:6],
        }
        cooldown_keys = [
            str(loop.get("loopKey") or "")
            for loop in active_loops
            if str(loop.get("status") or "").strip() in {"waiting_for_user", "cooling_down"}
            and str(loop.get("loopKey") or "").strip()
        ]
        source_refs = self._dedupe_refs(
            [
                ref
                for loop in active_loops
                for ref in loop.get("sourceRecordRefs", [])
                if isinstance(ref, dict)
            ]
        )
        evidence_ids = self._dedupe_ids(
            [
                str(value)
                for loop in active_loops
                for value in loop.get("evidenceIds", [])
                if str(value).strip()
            ]
        )
        reasons = self._dedupe_strings(
            [
                *self._strings(runtime_policy.get("reasons")),
                *(
                    ["dashboard_review_present"]
                    if isinstance(dashboard, dict)
                    and isinstance(dashboard.get("latestReview"), dict)
                    else []
                ),
                *(
                    ["coach_state_no_active_loop"]
                    if not active_loops
                    else ["coach_state_surface_selected"]
                ),
            ]
        )
        return {
            "generatedAt": now,
            "surface": surface,
            "runtimePolicyVersion": "coach_state_v1",
            "witness": witness,
            "activeLoops": active_loops,
            "withheldMoves": withheld[:4],
            "globalConstraints": constraints,
            "cooldownKeys": cooldown_keys,
            "sourceRecordRefs": source_refs,
            "evidenceIds": evidence_ids,
            "reasons": reasons,
            **({"selectedMove": selected_move} if selected_move is not None else {}),
        }

    def select_surface_move(
        self,
        *,
        coach_state: CoachStateSummary | None,
        surface: CoachSurface,
        active_loops: list[CoachLoopSummary] | None = None,
    ) -> CoachMoveContract | None:
        loops = active_loops
        if loops is None:
            loops = (
                coach_state.get("activeLoops", [])
                if isinstance(coach_state, dict)
                else []
            )
        eligible = [
            loop
            for loop in loops
            if str(loop.get("status") or "").strip() == "eligible"
        ]
        if not eligible:
            return None
        eligible.sort(key=lambda item: self._loop_sort_key(item, surface=surface))
        selected = eligible[0]
        capture = cast(CoachCaptureContract, dict(selected["capture"]))
        move_id = create_id("coach_move")
        anchor_refs = dict(capture.get("anchorRefs", {}))
        anchor_refs["coachMoveId"] = move_id
        capture["anchorRefs"] = cast(MethodStateAnchorRefs, anchor_refs)
        move: CoachMoveContract = {
            "moveId": move_id,
            "loopKey": selected["loopKey"],
            "kind": selected["moveKind"],
            "titleHint": selected["titleHint"],
            "summaryHint": selected["summaryHint"],
            "promptFrame": dict(selected["promptFrame"]),
            "capture": capture,
            "blockedMoves": list(selected.get("blockedMoves", [])),
            "reasons": list(selected.get("reasons", [])),
        }
        related_resource_ids = selected.get("relatedResourceIds", [])
        if related_resource_ids:
            move["relatedResourceIds"] = list(related_resource_ids)
        if isinstance(selected.get("resourceInvitation"), dict):
            move["resourceInvitation"] = cast(
                dict[str, object],
                dict(selected["resourceInvitation"]),
            )
        return move

    def _integrate_journey_followthrough(
        self,
        *,
        loop_candidates: list[CoachLoopSummary],
        journey_followthrough: list[JourneyFollowthroughSummary],
        method_context: MethodContextSnapshot,
        runtime_policy: dict[str, object],
        existing_briefs: list[ProactiveBriefRecord],
        now: str,
    ) -> list[CoachLoopSummary]:
        if not journey_followthrough:
            return loop_candidates
        goal_tensions = self._dict_list(method_context.get("goalTensions"))
        goal_ids_by_tension: dict[str, list[Id]] = {
            str(item.get("id") or "").strip(): self._ids(item.get("goalIds"))
            for item in goal_tensions
            if str(item.get("id") or "").strip()
        }
        result = [deepcopy(loop) for loop in loop_candidates]
        dominant_journey_ids: set[Id] = set()
        for summary in journey_followthrough:
            if not isinstance(summary, dict):
                continue
            readiness = str(summary.get("readiness") or "").strip()
            if readiness == "quiet":
                continue
            followthrough_loop = self._followthrough_loop(
                summary=summary,
                goal_ids_by_tension=goal_ids_by_tension,
                method_context=method_context,
                runtime_policy=runtime_policy,
                existing_briefs=existing_briefs,
                now=now,
            )
            if followthrough_loop is None:
                continue
            matching_index = self._matching_followthrough_loop_index(
                loop_candidates=result,
                followthrough_loop=followthrough_loop,
                goal_ids_by_tension=goal_ids_by_tension,
            )
            if matching_index is None:
                result.append(followthrough_loop)
            else:
                result[matching_index] = self._merge_followthrough_loop(
                    loop=result[matching_index],
                    followthrough_loop=followthrough_loop,
                )
            dominant_journey_ids.update(self._ids(followthrough_loop.get("relatedJourneyIds")))
        if dominant_journey_ids:
            result = self._suppress_generic_reentry_loops(
                loop_candidates=result,
                dominant_journey_ids=dominant_journey_ids,
            )
        return result

    def _followthrough_loop(
        self,
        *,
        summary: JourneyFollowthroughSummary,
        goal_ids_by_tension: dict[str, list[Id]],
        method_context: MethodContextSnapshot,
        runtime_policy: dict[str, object],
        existing_briefs: list[ProactiveBriefRecord],
        now: str,
    ) -> CoachLoopSummary | None:
        journey_id = str(summary.get("journeyId") or "").strip()
        move_kind = str(summary.get("recommendedMoveKind") or "").strip()
        if not journey_id or not move_kind or move_kind == "track_without_prompt":
            return None
        loop_kind = self._followthrough_loop_kind(summary)
        title_hint, summary_hint, prompt_frame = self._followthrough_prompt(summary=summary)
        related_practice_session_ids = self._ids(summary.get("relatedPracticeSessionIds"))
        related_body_state_ids = self._ids(summary.get("relatedBodyStateIds"))
        related_goal_tension_ids = self._ids(summary.get("relatedGoalTensionIds"))
        related_goal_ids: list[Id] = []
        for tension_id in related_goal_tension_ids:
            related_goal_ids = self._dedupe_ids(
                [*related_goal_ids, *goal_ids_by_tension.get(tension_id, [])]
            )
        anchor_refs: MethodStateAnchorRefs = {"journeyId": journey_id}
        if related_practice_session_ids:
            anchor_refs["practiceSessionId"] = related_practice_session_ids[0]
        if related_goal_ids:
            anchor_refs["goalId"] = related_goal_ids[0]
        capture = self._capture_contract(
            source=self._followthrough_source(loop_kind),
            loop_key=f"coach:{loop_kind}:{journey_id}",
            expected_targets=self._followthrough_expected_targets(
                move_kind=move_kind,
                related_goal_ids=related_goal_ids,
                related_practice_session_ids=related_practice_session_ids,
                related_body_state_ids=related_body_state_ids,
            ),
            answer_mode="choice_then_free_text"
            if move_kind != "return_to_journey"
            else "free_text",
            skip_behavior="cooldown",
            anchor_refs=anchor_refs,
        )
        blocked_moves = self._dedupe_strings(
            [
                *self._strings(runtime_policy.get("blockedMoves")),
                *[
                    str(item)
                    for item in summary.get("blockedEscalations", [])
                    if str(item).strip()
                ],
            ]
        )
        reasons = self._dedupe_strings(
            [
                "journey_followthrough_dominant",
                f"journey_followthrough_family_{summary.get('family', 'cross_family')}",
                f"journey_followthrough_readiness_{summary.get('readiness', 'available')}",
                *[str(item) for item in summary.get("reasons", []) if str(item).strip()],
            ]
        )
        source_record_refs: list[MethodStateSourceRef] = [
            {"recordType": "Journey", "recordId": journey_id, "summary": summary_hint}
        ]
        source_record_refs.extend(
            {"recordType": "PracticeSession", "recordId": practice_id}
            for practice_id in related_practice_session_ids[:2]
        )
        source_record_refs.extend(
            {"recordType": "GoalTension", "recordId": tension_id}
            for tension_id in related_goal_tension_ids[:2]
        )
        loop = self._base_loop(
            loop_key=f"coach:{loop_kind}:{journey_id}",
            kind=loop_kind,
            move_kind=move_kind,
            title=title_hint,
            summary=summary_hint,
            prompt_frame=prompt_frame,
            capture=capture,
            priority=int(summary.get("priority", 0) or 0),
            related_goal_ids=related_goal_ids,
            related_journey_ids=[cast(Id, journey_id)],
            related_practice_session_ids=related_practice_session_ids,
            related_symbol_ids=[],
            related_body_state_ids=related_body_state_ids,
            related_relational_scene_ids=[],
            evidence_ids=related_goal_tension_ids,
            source_record_refs=self._dedupe_refs(source_record_refs),
            blocked_moves=blocked_moves,
            consent_scopes=[],
            reasons=reasons,
            method_context=method_context,
            runtime_policy=runtime_policy,
            existing_briefs=existing_briefs,
            now=now,
        )
        if str(summary.get("readiness") or "").strip() == "available":
            loop["priority"] = max(int(loop.get("priority", 0) or 0), 60)
        return loop

    def _followthrough_loop_kind(self, summary: JourneyFollowthroughSummary) -> CoachLoopKind:
        family = str(summary.get("family") or "cross_family").strip()
        move_kind = str(summary.get("recommendedMoveKind") or "").strip()
        if family == "practice_reentry":
            return "practice_integration"
        if family in {"embodied_recurrence", "symbol_body_life_pressure"}:
            return "soma"
        if family == "relational_scene_recurrence":
            return "relational_scene"
        if family == "thought_loop_typology_restraint":
            return "goal_guidance"
        if move_kind == "offer_resource":
            return "resource_support"
        return "journey_reentry"

    def _followthrough_source(self, loop_kind: CoachLoopKind) -> MethodStateResponseSource:
        if loop_kind == "practice_integration":
            return "practice_feedback"
        if loop_kind == "goal_guidance":
            return "goal_feedback"
        if loop_kind == "relational_scene":
            return "relational_scene"
        if loop_kind in {"soma", "resource_support"}:
            return "body_note"
        return "freeform_followup"

    def _followthrough_expected_targets(
        self,
        *,
        move_kind: str,
        related_goal_ids: list[Id],
        related_practice_session_ids: list[Id],
        related_body_state_ids: list[Id],
    ) -> list[MethodStateCaptureTargetKind]:
        if move_kind == "ask_practice_followup":
            targets: list[MethodStateCaptureTargetKind] = [
                "practice_outcome",
                "practice_preference",
            ]
            if related_body_state_ids:
                targets.append("body_state")
            return targets
        if move_kind == "ask_goal_tension":
            return ["goal_tension", "goal", "conscious_attitude"]
        if move_kind == "ask_relational_scene":
            targets = ["relational_scene"]
            if related_body_state_ids:
                targets.append("body_state")
            return targets
        if move_kind in {"ask_body_checkin", "offer_resource", "offer_practice"}:
            targets = ["body_state"] if related_body_state_ids else []
            if related_goal_ids:
                targets.append("goal_tension")
            if related_practice_session_ids:
                targets.append("practice_outcome")
            return targets or ["body_state"]
        targets = ["conscious_attitude"]
        if related_body_state_ids:
            targets.insert(0, "body_state")
        if related_goal_ids:
            targets.append("goal_tension")
        return list(dict.fromkeys(targets))

    def _followthrough_prompt(
        self,
        *,
        summary: JourneyFollowthroughSummary,
    ) -> tuple[str, str, dict[str, object]]:
        move_kind = str(summary.get("recommendedMoveKind") or "").strip()
        body_first = bool(summary.get("bodyFirst"))
        if move_kind == "ask_practice_followup":
            return (
                "Practice follow-up",
                "A recent journey-linked practice looks ready for a light follow-up.",
                {
                    "stance": "practice_integration",
                    "askAbout": "what shifted, resisted, or changed after the practice",
                    "avoid": ["backlog_dump", "pressure_language", "symbolic_verdict"],
                    "choices": ["note what happened", "body first", "leave it alone"],
                },
            )
        if move_kind == "offer_resource":
            return (
                "Resource support",
                "This journey looks live, but a gentler resource fits better than another push.",
                {
                    "stance": "grounding_first",
                    "askAbout": "whether a gentler resource would help right now",
                    "avoid": ["pressure_language", "symbolic_interpretation", "diagnosis"],
                    "choices": ["try a resource", "not now", "just track it"],
                },
            )
        if move_kind == "ask_body_checkin":
            return (
                "Body check-in",
                "This journey can be met body-first without forcing an explanation.",
                {
                    "stance": "body_first",
                    "askAbout": "what is most noticeable in the body right now",
                    "avoid": ["diagnosis", "causal_claim", "symbolic_pressure"],
                    "choices": ["track it", "name the pressure", "leave it alone"],
                },
            )
        if move_kind == "ask_goal_tension":
            return (
                "Goal tension",
                "A live journey-linked tension can be named without turning it into a plan.",
                {
                    "stance": "hold_tension",
                    "askAbout": "which side feels most charged right now",
                    "avoid": ["optimization_language", "planning_first", "verdict_language"],
                    "choices": ["name both sides", "track it", "leave it alone"],
                },
            )
        if move_kind == "ask_relational_scene":
            return (
                "Relational scene",
                "A relational scene looks active enough for a bounded scene-first check-in.",
                {
                    "stance": "scene_first",
                    "askAbout": "what changed in you after the contact",
                    "avoid": ["diagnosis", "causal_claim", "projection_language"],
                    "choices": ["track the scene", "body first" if body_first else "hold it lightly", "leave it alone"],
                },
            )
        if move_kind == "offer_practice":
            return (
                "Practice option",
                "A bounded practice option may fit this journey now.",
                {
                    "stance": "practice_invitation",
                    "askAbout": "whether a light practice would help or whether silence fits better",
                    "avoid": ["compliance_language", "backlog_pressure", "intensity_escalation"],
                    "choices": ["offer one", "not now", "leave it alone"],
                },
            )
        return (
            "Journey re-entry",
            "An active journey can be picked up from what is already alive.",
            {
                "stance": "journey_reentry",
                "askAbout": "what shifted in this thread since the last touchpoint",
                "avoid": ["backlog_dump", "symbolic_pressure", "certainty_language"],
                "choices": ["track it", "body first" if body_first else "hold it lightly", "leave it alone"],
            },
        )

    def _matching_followthrough_loop_index(
        self,
        *,
        loop_candidates: list[CoachLoopSummary],
        followthrough_loop: CoachLoopSummary,
        goal_ids_by_tension: dict[str, list[Id]],
    ) -> int | None:
        followthrough_kind = str(followthrough_loop.get("kind") or "").strip()
        followthrough_journey_ids = set(self._ids(followthrough_loop.get("relatedJourneyIds")))
        followthrough_practice_ids = set(self._ids(followthrough_loop.get("relatedPracticeSessionIds")))
        followthrough_body_ids = set(self._ids(followthrough_loop.get("relatedBodyStateIds")))
        followthrough_goal_ids = set(self._ids(followthrough_loop.get("relatedGoalIds")))
        del goal_ids_by_tension
        for index, candidate in enumerate(loop_candidates):
            candidate_kind = str(candidate.get("kind") or "").strip()
            if candidate_kind != followthrough_kind:
                continue
            if followthrough_journey_ids.intersection(self._ids(candidate.get("relatedJourneyIds"))):
                return index
            if followthrough_practice_ids.intersection(
                self._ids(candidate.get("relatedPracticeSessionIds"))
            ):
                return index
            if followthrough_body_ids.intersection(self._ids(candidate.get("relatedBodyStateIds"))):
                return index
            if followthrough_goal_ids.intersection(self._ids(candidate.get("relatedGoalIds"))):
                return index
        return None

    def _merge_followthrough_loop(
        self,
        *,
        loop: CoachLoopSummary,
        followthrough_loop: CoachLoopSummary,
    ) -> CoachLoopSummary:
        merged = cast(CoachLoopSummary, deepcopy(loop))
        merged["priority"] = max(
            int(merged.get("priority", 0) or 0),
            int(followthrough_loop.get("priority", 0) or 0),
        )
        for field in (
            "relatedGoalIds",
            "relatedJourneyIds",
            "relatedPracticeSessionIds",
            "relatedSymbolIds",
            "relatedBodyStateIds",
            "relatedRelationalSceneIds",
            "evidenceIds",
        ):
            merged[field] = self._dedupe_ids(
                [
                    *self._ids(merged.get(field)),
                    *self._ids(followthrough_loop.get(field)),
                ]
            )
        merged["sourceRecordRefs"] = self._dedupe_refs(
            [
                *self._dict_list(merged.get("sourceRecordRefs")),
                *self._dict_list(followthrough_loop.get("sourceRecordRefs")),
            ]
        )
        merged["blockedMoves"] = self._dedupe_strings(
            [
                *self._strings(merged.get("blockedMoves")),
                *self._strings(followthrough_loop.get("blockedMoves")),
            ]
        )
        merged["reasons"] = self._dedupe_strings(
            [
                *self._strings(merged.get("reasons")),
                *self._strings(followthrough_loop.get("reasons")),
            ]
        )
        if int(followthrough_loop.get("priority", 0) or 0) >= int(merged.get("priority", 0) or 0):
            for field in ("titleHint", "summaryHint", "promptFrame", "moveKind", "capture"):
                merged[field] = deepcopy(followthrough_loop[field])
        return merged

    def _suppress_generic_reentry_loops(
        self,
        *,
        loop_candidates: list[CoachLoopSummary],
        dominant_journey_ids: set[Id],
    ) -> list[CoachLoopSummary]:
        suppressed: list[CoachLoopSummary] = []
        for loop in loop_candidates:
            reasons = self._strings(loop.get("reasons"))
            if "journey_followthrough_dominant" in reasons:
                suppressed.append(loop)
                continue
            if str(loop.get("kind") or "").strip() != "journey_reentry":
                suppressed.append(loop)
                continue
            if dominant_journey_ids.intersection(self._ids(loop.get("relatedJourneyIds"))):
                continue
            suppressed.append(loop)
        return suppressed

    def _soma_loop(
        self,
        *,
        method_context: MethodContextSnapshot,
        runtime_policy: dict[str, object],
        existing_briefs: list[ProactiveBriefRecord],
        recent_practices: list[PracticeSessionRecord],
        journeys: list[JourneyRecord],
        dashboard: DashboardSummary | None,
        now: str,
    ) -> tuple[CoachLoopSummary | None, CoachWithheldMoveSummary | None]:
        del journeys, dashboard
        body_states = self._dict_list(method_context.get("recentBodyStates"))
        method_state = self._dict(method_context.get("methodState"))
        grounding = self._dict(method_state.get("grounding"))
        containment = self._dict(method_state.get("containment"))
        active_goal_tension = self._dict(method_state.get("activeGoalTension"))
        practice_loop = self._dict(method_state.get("practiceLoop"))
        grounding_recommendation = str(grounding.get("recommendation") or "").strip()
        recent_outcome_trend = str(practice_loop.get("recentOutcomeTrend") or "").strip()
        if (
            not body_states
            and grounding_recommendation not in {"grounding_first", "pace_gently"}
            and recent_outcome_trend not in {"activating", "mixed"}
        ):
            return None, None
        first_body_state = body_states[0] if body_states else {}
        body_state_id = str(first_body_state.get("id") or "current").strip()
        loop_key = f"coach:soma:{body_state_id}"
        move_kind: Literal["ask_body_checkin", "offer_resource"] = (
            "offer_resource"
            if grounding_recommendation == "grounding_first" or recent_outcome_trend == "activating"
            else "ask_body_checkin"
        )
        expected_targets: list[MethodStateCaptureTargetKind] = ["body_state"]
        if active_goal_tension.get("goalTensionId"):
            expected_targets.append("goal_tension")
        if any(
            str(item.get("status") or "").strip() in {"accepted", "completed"}
            for item in recent_practices
        ):
            expected_targets.append("practice_outcome")
        loop = self._base_loop(
            loop_key=loop_key,
            kind="soma",
            move_kind=move_kind,
            title="Body check-in" if move_kind == "ask_body_checkin" else "Grounding support",
            summary=(
                "A recent body signal can be met without forcing interpretation."
                if move_kind == "ask_body_checkin"
                else (
                    "Containment suggests a gentler grounding resource "
                    "instead of more symbolic depth."
                )
            ),
            prompt_frame={
                "stance": "body_first",
                "askAbout": "what changed in the body after contact",
                "avoid": ["diagnosis", "causal_claim", "symbolic_verdict"],
                "choices": ["track it", "ground first", "leave it alone"],
            },
            capture=self._capture_contract(
                source="body_note",
                loop_key=loop_key,
                expected_targets=expected_targets,
                answer_mode="choice_then_free_text",
                skip_behavior="track_only",
            ),
            priority=92 if move_kind == "offer_resource" else 82,
            related_goal_ids=self._ids(active_goal_tension.get("linkedGoalIds"))
            or self._ids(first_body_state.get("linkedGoalIds")),
            related_journey_ids=[],
            related_practice_session_ids=[],
            related_symbol_ids=self._ids(first_body_state.get("linkedSymbolIds")),
            related_body_state_ids=self._ids([body_state_id]) if body_states else [],
            related_relational_scene_ids=[],
            evidence_ids=self._ids(active_goal_tension.get("evidenceIds")),
            source_record_refs=self._dedupe_refs(
                self._dict_list(containment.get("sourceRecordRefs"))  # type: ignore[arg-type]
            ),
            blocked_moves=self._strings(runtime_policy.get("blockedMoves")),
            consent_scopes=[],
            reasons=self._dedupe_strings(
                [
                    *(
                        ["containment_requires_grounding_first"]
                        if grounding_recommendation == "grounding_first"
                        else ["containment_prefers_paced_contact"]
                        if grounding_recommendation == "pace_gently"
                        else []
                    ),
                    *(
                        ["practice_loop_recent_outcome_trend_activating"]
                        if recent_outcome_trend == "activating"
                        else []
                    ),
                    *(
                        ["recent_body_state_available"]
                        if body_states
                        else ["soma_loop_track_only_without_direct_body_state"]
                    ),
                ]
            ),
            method_context=method_context,
            runtime_policy=runtime_policy,
            existing_briefs=existing_briefs,
            now=now,
        )
        if not body_states and loop is not None:
            loop["status"] = "track_only"
        return loop, None

    def _goal_guidance_loop(
        self,
        *,
        method_context: MethodContextSnapshot,
        runtime_policy: dict[str, object],
        existing_briefs: list[ProactiveBriefRecord],
        recent_practices: list[PracticeSessionRecord],
        journeys: list[JourneyRecord],
        dashboard: DashboardSummary | None,
        now: str,
    ) -> tuple[CoachLoopSummary | None, CoachWithheldMoveSummary | None]:
        del recent_practices, journeys, dashboard
        method_state = self._dict(method_context.get("methodState"))
        active_goal_tension = self._dict(method_state.get("activeGoalTension"))
        goal_tension_id = str(active_goal_tension.get("goalTensionId") or "").strip()
        goal_ids = self._ids(active_goal_tension.get("linkedGoalIds"))
        if not goal_tension_id and not goal_ids:
            goal_tensions = self._dict_list(method_context.get("goalTensions"))
            if not goal_tensions:
                return None, None
            goal_tension_id = str(goal_tensions[0].get("id") or "current").strip()
            goal_ids = self._ids(goal_tensions[0].get("goalIds"))
            active_goal_tension = goal_tensions[0]
        loop_key = f"coach:goal_guidance:{goal_tension_id or 'current'}"
        loop = self._base_loop(
            loop_key=loop_key,
            kind="goal_guidance",
            move_kind="ask_goal_tension",
            title="Goal tension",
            summary=(
                str(active_goal_tension.get("balancingDirection") or "").strip()
                or "A live goal tension can be named without forcing resolution."
            ),
            prompt_frame={
                "stance": "hold_tension",
                "askAbout": "which side feels most charged right now",
                "avoid": ["optimization_language", "planning_first", "verdict_language"],
                "choices": ["name both sides", "track it", "leave it alone"],
            },
            capture=self._capture_contract(
                source="goal_feedback",
                loop_key=loop_key,
                expected_targets=["goal_tension", "goal", "conscious_attitude"],
                answer_mode="choice_then_free_text",
                skip_behavior="track_only",
            ),
            priority=78,
            related_goal_ids=goal_ids,
            related_journey_ids=[],
            related_practice_session_ids=[],
            related_symbol_ids=[],
            related_body_state_ids=[],
            related_relational_scene_ids=[],
            evidence_ids=self._ids(active_goal_tension.get("evidenceIds")),
            source_record_refs=[],
            blocked_moves=self._strings(runtime_policy.get("blockedMoves")),
            consent_scopes=[],
            reasons=self._dedupe_strings(["active_goal_tension_present"]),
            method_context=method_context,
            runtime_policy=runtime_policy,
            existing_briefs=existing_briefs,
            now=now,
        )
        return loop, None

    def _relational_scene_loop(
        self,
        *,
        method_context: MethodContextSnapshot,
        runtime_policy: dict[str, object],
        existing_briefs: list[ProactiveBriefRecord],
        recent_practices: list[PracticeSessionRecord],
        journeys: list[JourneyRecord],
        dashboard: DashboardSummary | None,
        now: str,
    ) -> tuple[CoachLoopSummary | None, CoachWithheldMoveSummary | None]:
        del recent_practices, journeys, dashboard
        method_state = self._dict(method_context.get("methodState"))
        relational_field = self._dict(method_state.get("relationalField"))
        individuation = self._dict(method_context.get("individuationContext"))
        scenes = self._dict_list(individuation.get("relationalScenes"))
        active_scene_ids = self._ids(relational_field.get("activeSceneIds")) or self._ids(
            [scene.get("id") for scene in scenes]
        )
        relationship_contact = str(relational_field.get("relationshipContact") or "").strip()
        support_direction = str(relational_field.get("supportDirection") or "").strip()
        if (
            not active_scene_ids
            and relationship_contact not in {"thin", "isolated"}
            and not support_direction
        ):
            return None, None
        loop_key = f"coach:relational_scene:{active_scene_ids[0] if active_scene_ids else 'field'}"
        projection_allowed = bool(relational_field.get("projectionLanguageAllowed"))
        expected_targets: list[MethodStateCaptureTargetKind] = ["relational_scene"]
        blocked_moves = self._strings(runtime_policy.get("blockedMoves"))
        avoid = ["diagnosis", "causal_claim"]
        consent_scopes: list[str] = []
        if projection_allowed and "projection_language" not in blocked_moves:
            expected_targets.append("projection_hypothesis")
            consent_scopes.append("projection_language")
        else:
            avoid.append("projection_language")
            if "projection_language" not in blocked_moves:
                blocked_moves.append("projection_language")
        if relationship_contact in {"thin", "isolated"} or support_direction in {
            "increase_contact",
            "protect_space",
            "hold_contact_lightly",
        }:
            expected_targets.append("reality_anchors")
        loop = self._base_loop(
            loop_key=loop_key,
            kind="relational_scene",
            move_kind="ask_relational_scene",
            title="Relational scene",
            summary=(
                "A relational field is active and can be met scene-first."
                if active_scene_ids
                else "Relational contact looks thin enough that the scene should be held carefully."
            ),
            prompt_frame={
                "stance": "scene_first",
                "askAbout": "what changed in you after the contact",
                "avoid": avoid,
                "choices": ["track the scene", "protect space", "leave it alone"],
            },
            capture=self._capture_contract(
                source="relational_scene",
                loop_key=loop_key,
                expected_targets=expected_targets,
                answer_mode="choice_then_free_text",
                skip_behavior="cooldown",
            ),
            priority=80,
            related_goal_ids=[],
            related_journey_ids=[],
            related_practice_session_ids=[],
            related_symbol_ids=[],
            related_body_state_ids=[],
            related_relational_scene_ids=active_scene_ids,
            evidence_ids=self._dedupe_ids(
                [
                    str(value)
                    for scene in scenes[:2]
                    for value in scene.get("evidenceIds", [])
                    if str(value).strip()
                ]
            ),
            source_record_refs=self._dedupe_refs(
                [
                    ref
                    for ref in self._dict_list(relational_field.get("sourceRecordRefs"))
                    if isinstance(ref, dict)
                ]
            ),
            blocked_moves=blocked_moves,
            consent_scopes=consent_scopes,
            reasons=self._dedupe_strings(
                [
                    *(
                        ["projection_language_not_allowed"]
                        if not projection_allowed
                        else ["projection_language_available_by_contract"]
                    ),
                    *(
                        ["relationship_contact_thin"]
                        if relationship_contact in {"thin", "isolated"}
                        else []
                    ),
                ]
            ),
            method_context=method_context,
            runtime_policy=runtime_policy,
            existing_briefs=existing_briefs,
            now=now,
        )
        return loop, None

    def _practice_integration_loop(
        self,
        *,
        method_context: MethodContextSnapshot,
        runtime_policy: dict[str, object],
        existing_briefs: list[ProactiveBriefRecord],
        recent_practices: list[PracticeSessionRecord],
        journeys: list[JourneyRecord],
        dashboard: DashboardSummary | None,
        now: str,
    ) -> tuple[CoachLoopSummary | None, CoachWithheldMoveSummary | None]:
        del journeys, dashboard
        method_state = self._dict(method_context.get("methodState"))
        practice_loop = self._dict(method_state.get("practiceLoop"))
        if not recent_practices and not practice_loop:
            return None, None
        practice = self._select_recent_practice(recent_practices=recent_practices, now=now)
        recent_outcome_trend = str(practice_loop.get("recentOutcomeTrend") or "").strip()
        skipped_count = sum(
            1
            for item in recent_practices[:3]
            if str(item.get("status") or "").strip() == "skipped"
        )
        if practice is None and recent_outcome_trend not in {"activating", "mixed", "settling"}:
            return None, None
        practice_source_refs = self._practice_loop_source_refs(practice)
        practice_evidence_ids = self._practice_loop_evidence_ids(practice)
        practice_id = (
            str(practice.get("id") or "current").strip()
            if isinstance(practice, dict)
            else "current"
        )
        loop_key = f"coach:practice_integration:{practice_id}"
        if skipped_count >= 2 or recent_outcome_trend == "activating":
            move_kind: Literal["ask_practice_followup", "offer_resource", "offer_practice"] = (
                "offer_resource"
            )
        elif practice is not None and str(practice.get("status") or "").strip() in {
            "recommended",
            "accepted",
            "completed",
            "skipped",
        }:
            move_kind = "ask_practice_followup"
        else:
            move_kind = "offer_practice"
        expected_targets: list[MethodStateCaptureTargetKind] = [
            "practice_outcome",
            "practice_preference",
        ]
        if recent_outcome_trend in {"activating", "mixed"}:
            expected_targets.append("body_state")
        loop = self._base_loop(
            loop_key=loop_key,
            kind="practice_integration",
            move_kind=move_kind,
            title=(
                "Practice follow-up"
                if move_kind == "ask_practice_followup"
                else "Gentler support"
                if move_kind == "offer_resource"
                else "Practice option"
            ),
            summary=(
                "A recent practice looks ready for a light follow-up."
                if move_kind == "ask_practice_followup"
                else "Recent practice signals suggest stepping down intensity."
                if move_kind == "offer_resource"
                else "A lighter practice option may fit the current loop."
            ),
            prompt_frame={
                "stance": "practice_integration",
                "askAbout": "what shifted, resisted, or changed in the body after the practice",
                "avoid": ["pressure_language", "repetition_without_change"],
                "choices": ["shifted", "resisted", "not now"],
            },
            capture=self._capture_contract(
                source="practice_feedback",
                loop_key=loop_key,
                expected_targets=expected_targets,
                answer_mode="choice_then_free_text",
                skip_behavior="cooldown",
                anchor_refs=cast(
                    MethodStateAnchorRefs,
                    (
                        {"practiceSessionId": practice["id"]}
                        if isinstance(practice, dict) and practice.get("id")
                        else {}
                    ),
                ),
            ),
            priority=94 if move_kind == "ask_practice_followup" else 88,
            related_goal_ids=[],
            related_journey_ids=[],
            related_practice_session_ids=self._ids([practice_id]) if practice is not None else [],
            related_symbol_ids=[],
            related_body_state_ids=[],
            related_relational_scene_ids=[],
            evidence_ids=practice_evidence_ids,
            source_record_refs=practice_source_refs,
            blocked_moves=self._strings(runtime_policy.get("blockedMoves")),
            consent_scopes=[],
            reasons=self._dedupe_strings(
                [
                    *(
                        ["practice_repeated_skips"]
                        if skipped_count >= 2
                        else ["practice_due_for_followup"]
                        if practice is not None
                        else []
                    ),
                    *(
                        [f"practice_loop_recent_outcome_trend_{recent_outcome_trend}"]
                        if recent_outcome_trend
                        else []
                    ),
                ]
            ),
            method_context=method_context,
            runtime_policy=runtime_policy,
            existing_briefs=existing_briefs,
            now=now,
        )
        if isinstance(practice, dict):
            self._attach_practice_resource_context(loop=loop, practice=practice)
        return loop, None

    def _journey_reentry_loop(
        self,
        *,
        method_context: MethodContextSnapshot,
        runtime_policy: dict[str, object],
        existing_briefs: list[ProactiveBriefRecord],
        recent_practices: list[PracticeSessionRecord],
        journeys: list[JourneyRecord],
        dashboard: DashboardSummary | None,
        now: str,
    ) -> tuple[CoachLoopSummary | None, CoachWithheldMoveSummary | None]:
        del recent_practices, dashboard
        active_journeys = [
            item
            for item in journeys
            if str(item.get("status") or "").strip() == "active"
        ] or [
            item
            for item in self._dict_list(method_context.get("activeJourneys"))
            if str(item.get("status") or "").strip() == "active"
        ]
        if not active_journeys:
            return None, None
        journey = active_journeys[0]
        journey_id = str(journey.get("id") or "current").strip()
        loop_key = f"coach:journey_reentry:{journey_id}"
        expected_targets: list[MethodStateCaptureTargetKind] = []
        if self._dict(method_context.get("methodState")).get("activeGoalTension"):
            expected_targets.append("goal_tension")
        if self._dict_list(method_context.get("recentBodyStates")):
            expected_targets.append("body_state")
        if not expected_targets:
            expected_targets.append("conscious_attitude")
        loop = self._base_loop(
            loop_key=loop_key,
            kind="journey_reentry",
            move_kind="return_to_journey",
            title="Journey re-entry",
            summary="An active journey can be picked up from the thread that is already alive.",
            prompt_frame={
                "stance": "journey_reentry",
                "askAbout": "what shifted in this thread since the last touchpoint",
                "avoid": ["backlog_dump", "symbolic_pressure"],
                "choices": ["track it", "body first", "leave it alone"],
            },
            capture=self._capture_contract(
                source="freeform_followup",
                loop_key=loop_key,
                expected_targets=expected_targets,
                answer_mode="free_text",
                skip_behavior="cooldown",
                anchor_refs=cast(MethodStateAnchorRefs, {"journeyId": journey_id}),
            ),
            priority=90,
            related_goal_ids=self._ids(journey.get("relatedGoalIds")),
            related_journey_ids=self._ids([journey_id]),
            related_practice_session_ids=[],
            related_symbol_ids=self._ids(journey.get("relatedSymbolIds")),
            related_body_state_ids=[],
            related_relational_scene_ids=[],
            evidence_ids=[],
            source_record_refs=[],
            blocked_moves=self._strings(runtime_policy.get("blockedMoves")),
            consent_scopes=[],
            reasons=self._dedupe_strings(["active_journey_present"]),
            method_context=method_context,
            runtime_policy=runtime_policy,
            existing_briefs=existing_briefs,
            now=now,
        )
        return loop, None

    def _resource_support_loop(
        self,
        *,
        method_context: MethodContextSnapshot,
        runtime_policy: dict[str, object],
        existing_briefs: list[ProactiveBriefRecord],
        recent_practices: list[PracticeSessionRecord],
        journeys: list[JourneyRecord],
        dashboard: DashboardSummary | None,
        now: str,
    ) -> tuple[CoachLoopSummary | None, CoachWithheldMoveSummary | None]:
        del journeys, dashboard
        method_state = self._dict(method_context.get("methodState"))
        grounding = self._dict(method_state.get("grounding"))
        containment = self._dict(method_state.get("containment"))
        practice_loop = self._dict(method_state.get("practiceLoop"))
        depth_level = str(runtime_policy.get("depthLevel") or "").strip()
        grounding_recommendation = str(grounding.get("recommendation") or "").strip()
        recent_outcome_trend = str(practice_loop.get("recentOutcomeTrend") or "").strip()
        skipped_count = sum(
            1
            for item in recent_practices[:3]
            if str(item.get("status") or "").strip() == "skipped"
        )
        if (
            depth_level != "grounding_only"
            and recent_outcome_trend not in {"activating", "mixed"}
            and skipped_count < 2
            and grounding_recommendation != "grounding_first"
        ):
            return None, None
        body_states = self._dict_list(method_context.get("recentBodyStates"))
        practice = self._select_recent_practice(recent_practices=recent_practices, now=now)
        practice_source_refs = self._practice_loop_source_refs(practice)
        practice_evidence_ids = self._practice_loop_evidence_ids(practice)
        loop_key = (
            f"coach:resource_support:{practice['id']}"
            if isinstance(practice, dict) and practice.get("id")
            else f"coach:resource_support:{body_states[0]['id']}"
            if body_states and body_states[0].get("id")
            else "coach:resource_support:current"
        )
        source: MethodStateResponseSource = (
            "practice_feedback"
            if isinstance(practice, dict) and practice.get("id")
            else "body_note"
        )
        expected_targets: list[MethodStateCaptureTargetKind] = (
            ["practice_outcome", "practice_preference"]
            if source == "practice_feedback"
            else ["body_state"]
        )
        if source == "body_note" and recent_outcome_trend in {"activating", "mixed"}:
            expected_targets.append("relational_scene")
        loop = self._base_loop(
            loop_key=loop_key,
            kind="resource_support",
            move_kind="offer_resource",
            title="Resource support",
            summary=(
                "A gentler resource fits the current pacing better "
                "than a stronger symbolic move."
            ),
            prompt_frame={
                "stance": "grounding_first",
                "askAbout": "whether a gentler resource would help right now",
                "avoid": ["diagnosis", "symbolic_interpretation", "pressure_language"],
                "choices": ["try a resource", "not now", "just track it"],
            },
            capture=self._capture_contract(
                source=source,
                loop_key=loop_key,
                expected_targets=expected_targets,
                answer_mode="choice_then_free_text",
                skip_behavior="cooldown",
                anchor_refs=cast(
                    MethodStateAnchorRefs,
                    (
                        {"practiceSessionId": practice["id"]}
                        if source == "practice_feedback"
                        and isinstance(practice, dict)
                        and practice.get("id")
                        else {}
                    ),
                ),
            ),
            priority=96 if depth_level == "grounding_only" else 86,
            related_goal_ids=[],
            related_journey_ids=[],
            related_practice_session_ids=(
                self._ids([practice.get("id")]) if isinstance(practice, dict) else []
            ),
            related_symbol_ids=[],
            related_body_state_ids=self._ids([body_states[0].get("id")]) if body_states else [],
            related_relational_scene_ids=[],
            evidence_ids=self._dedupe_ids(
                [
                    *practice_evidence_ids,
                    *self._ids(containment.get("evidenceIds")),
                ]
            ),
            source_record_refs=self._dedupe_refs(
                practice_source_refs
                + [
                    ref
                    for ref in self._dict_list(containment.get("sourceRecordRefs"))
                    if isinstance(ref, dict)
                ]
            ),
            blocked_moves=self._strings(runtime_policy.get("blockedMoves")),
            consent_scopes=["somatic_correlation"] if source == "body_note" else [],
            reasons=self._dedupe_strings(
                [
                    *(
                        ["runtime_policy_grounding_only"]
                        if depth_level == "grounding_only"
                        else []
                    ),
                    *(
                        ["practice_repeated_skips"]
                        if skipped_count >= 2
                        else []
                    ),
                    *(
                        [f"practice_loop_recent_outcome_trend_{recent_outcome_trend}"]
                        if recent_outcome_trend
                        else []
                    ),
                ]
            ),
            method_context=method_context,
            runtime_policy=runtime_policy,
            existing_briefs=existing_briefs,
            now=now,
        )
        if isinstance(practice, dict):
            self._attach_practice_resource_context(loop=loop, practice=practice)
        return loop, None

    def _base_loop(
        self,
        *,
        loop_key: str,
        kind: CoachLoopKind,
        move_kind: str,
        title: str,
        summary: str,
        prompt_frame: dict[str, object],
        capture: CoachCaptureContract,
        priority: int,
        related_goal_ids: list[Id],
        related_journey_ids: list[Id],
        related_practice_session_ids: list[Id],
        related_symbol_ids: list[Id],
        related_body_state_ids: list[Id],
        related_relational_scene_ids: list[Id],
        evidence_ids: list[Id],
        source_record_refs: list[MethodStateSourceRef],
        blocked_moves: list[str],
        consent_scopes: list[str],
        reasons: list[str],
        method_context: MethodContextSnapshot,
        runtime_policy: dict[str, object],
        existing_briefs: list[ProactiveBriefRecord],
        now: str,
    ) -> CoachLoopSummary:
        loop: CoachLoopSummary = {
            "loopKey": loop_key,
            "kind": kind,
            "status": "eligible",
            "priority": priority,
            "titleHint": title,
            "summaryHint": summary,
            "promptFrame": cast(dict[str, object], dict(prompt_frame)),
            "moveKind": cast(
                Literal[
                    "ask_body_checkin",
                    "ask_goal_tension",
                    "ask_relational_scene",
                    "ask_practice_followup",
                    "offer_resource",
                    "offer_practice",
                    "hold_silence",
                    "track_without_prompt",
                    "return_to_journey",
                ],
                move_kind,
            ),
            "capture": capture,
            "relatedMaterialIds": [],
            "relatedGoalIds": related_goal_ids,
            "relatedJourneyIds": related_journey_ids,
            "relatedPracticeSessionIds": related_practice_session_ids,
            "relatedSymbolIds": related_symbol_ids,
            "relatedBodyStateIds": related_body_state_ids,
            "relatedRelationalSceneIds": related_relational_scene_ids,
            "evidenceIds": evidence_ids,
            "sourceRecordRefs": source_record_refs,
            "blockedMoves": blocked_moves,
            "consentScopes": consent_scopes,
            "reasons": reasons,
        }
        status, cooldown_until = self._cooldown_status(
            loop_key=loop_key,
            existing_briefs=existing_briefs,
            now=now,
        )
        if status:
            loop["status"] = status
        if cooldown_until:
            loop["cooldownUntil"] = cooldown_until
        if (
            str(runtime_policy.get("depthLevel") or "").strip() == "grounding_only"
            and move_kind in {
                "ask_goal_tension",
                "ask_relational_scene",
                "return_to_journey",
            }
        ):
            loop["status"] = "track_only"
        if not isinstance(method_context.get("methodState"), dict):
            loop["status"] = "track_only"
        return loop

    def _capture_contract(
        self,
        *,
        source: MethodStateResponseSource,
        loop_key: str,
        expected_targets: list[MethodStateCaptureTargetKind],
        answer_mode: Literal["free_text", "choice_then_free_text", "skip_only"],
        skip_behavior: Literal["hold_silence", "track_only", "cooldown"],
        anchor_refs: MethodStateAnchorRefs | None = None,
    ) -> CoachCaptureContract:
        refs = dict(anchor_refs or {})
        refs["coachLoopKey"] = loop_key
        return {
            "source": source,
            "anchorRefs": cast(MethodStateAnchorRefs, refs),
            "expectedTargets": list(dict.fromkeys(expected_targets)),
            "maxQuestions": 1,
            "answerMode": answer_mode,
            "skipBehavior": skip_behavior,
        }

    def _practice_loop_source_refs(
        self,
        practice: PracticeSessionRecord | None,
    ) -> list[MethodStateSourceRef]:
        if not isinstance(practice, dict):
            return []
        refs: list[MethodStateSourceRef] = []
        practice_id = str(practice.get("id") or "").strip()
        if practice_id:
            refs.append({"recordType": "PracticeSession", "recordId": practice_id})
        related_brief_id = str(practice.get("relatedBriefId") or "").strip()
        if related_brief_id:
            refs.append({"recordType": "ProactiveBrief", "recordId": related_brief_id})
        material_id = str(practice.get("materialId") or "").strip()
        if material_id:
            refs.append({"recordType": "Material", "recordId": material_id})
        run_id = str(practice.get("runId") or "").strip()
        if run_id:
            refs.append({"recordType": "InterpretationRun", "recordId": run_id})
        invitation = practice.get("resourceInvitation")
        if isinstance(invitation, dict):
            resource = invitation.get("resource")
            resource_id = (
                str(resource.get("id") or "").strip()
                if isinstance(resource, dict)
                else ""
            )
            if resource_id:
                refs.append({"recordType": "EmbodiedResource", "recordId": resource_id})
        return self._dedupe_refs(refs)

    def _practice_loop_evidence_ids(
        self,
        practice: PracticeSessionRecord | None,
    ) -> list[Id]:
        if not isinstance(practice, dict):
            return []
        evidence_ids = self._ids(practice.get("outcomeEvidenceIds"))
        invitation = practice.get("resourceInvitation")
        if isinstance(invitation, dict):
            resource = invitation.get("resource")
            if isinstance(resource, dict):
                evidence_ids = self._dedupe_ids(
                    [
                        *evidence_ids,
                        *self._ids(resource.get("evidenceIds")),
                    ]
                )
        return evidence_ids

    def _attach_practice_resource_context(
        self,
        *,
        loop: CoachLoopSummary | None,
        practice: PracticeSessionRecord | None,
    ) -> None:
        if not isinstance(loop, dict) or not isinstance(practice, dict):
            return
        invitation = practice.get("resourceInvitation")
        if isinstance(invitation, dict):
            loop["resourceInvitation"] = cast(
                ResourceInvitationSummary,
                deepcopy(invitation),
            )
        related_resource_ids = self._ids(practice.get("relatedResourceIds"))
        if not related_resource_ids and isinstance(invitation, dict):
            resource = invitation.get("resource")
            resource_id = (
                str(resource.get("id") or "").strip()
                if isinstance(resource, dict)
                else ""
            )
            if resource_id:
                related_resource_ids = [resource_id]
        if related_resource_ids:
            loop["relatedResourceIds"] = related_resource_ids
        resource_invitation_id = str(practice.get("resourceInvitationId") or "").strip()
        if resource_invitation_id and isinstance(loop.get("capture"), dict):
            capture = cast(CoachCaptureContract, dict(loop["capture"]))
            anchor_refs = dict(capture.get("anchorRefs", {}))
            anchor_refs.setdefault("resourceInvitationId", resource_invitation_id)
            capture["anchorRefs"] = cast(MethodStateAnchorRefs, anchor_refs)
            loop["capture"] = capture

    def _loop_sort_key(
        self,
        loop: CoachLoopSummary,
        *,
        surface: CoachSurface,
    ) -> tuple[int, int, int, int]:
        surface_order = {
            "generic": {
                "practice_integration": 0,
                "goal_guidance": 1,
                "relational_scene": 2,
                "soma": 3,
                "journey_reentry": 4,
                "resource_support": 5,
            },
            "alive_today": {
                "journey_reentry": 0,
                "resource_support": 1,
                "soma": 2,
                "relational_scene": 3,
                "goal_guidance": 4,
                "practice_integration": 5,
            },
            "weekly_review": {
                "goal_guidance": 0,
                "relational_scene": 1,
                "journey_reentry": 2,
                "soma": 3,
                "practice_integration": 4,
                "resource_support": 5,
            },
            "journey_page": {
                "journey_reentry": 0,
                "practice_integration": 1,
                "goal_guidance": 2,
                "relational_scene": 3,
                "soma": 4,
                "resource_support": 5,
            },
            "rhythmic_brief": {
                "practice_integration": 0,
                "resource_support": 1,
                "journey_reentry": 2,
                "soma": 3,
                "goal_guidance": 4,
                "relational_scene": 5,
            },
            "practice_followup": {
                "practice_integration": 0,
                "resource_support": 1,
                "soma": 2,
                "goal_guidance": 3,
                "relational_scene": 4,
                "journey_reentry": 5,
            },
        }
        status_rank = {
            "eligible": 0,
            "waiting_for_user": 1,
            "track_only": 2,
            "cooling_down": 3,
            "withheld": 4,
        }
        kind = str(loop.get("kind") or "").strip()
        dominant_rank = (
            0
            if "journey_followthrough_dominant" in self._strings(loop.get("reasons"))
            else 1
        )
        return (
            dominant_rank,
            surface_order.get(surface, {}).get(kind, 10),
            -int(loop.get("priority", 0)),
            status_rank.get(str(loop.get("status") or "").strip(), 10),
        )

    def _cooldown_status(
        self,
        *,
        loop_key: str,
        existing_briefs: list[ProactiveBriefRecord],
        now: str,
    ) -> tuple[Literal["waiting_for_user", "cooling_down"] | None, str | None]:
        now_dt = parse_iso_datetime(now, default=datetime.now(UTC))
        for brief in existing_briefs:
            brief_key = str(brief.get("coachLoopKey") or brief.get("triggerKey") or "").strip()
            if brief_key != loop_key:
                continue
            status = str(brief.get("status") or "").strip()
            if status in {"candidate", "shown"}:
                return "waiting_for_user", None
            cooldown_until = str(brief.get("cooldownUntil") or "").strip()
            if status in {"dismissed", "acted_on"} and cooldown_until:
                if parse_iso_datetime(cooldown_until, default=datetime.now(UTC)) > now_dt:
                    return "cooling_down", cooldown_until
        return None, None

    def _select_recent_practice(
        self,
        *,
        recent_practices: list[PracticeSessionRecord],
        now: str,
    ) -> PracticeSessionRecord | None:
        if not recent_practices:
            return None
        now_dt = parse_iso_datetime(now, default=datetime.now(UTC))
        due = [
            item
            for item in recent_practices
            if str(item.get("status") or "").strip()
            in {"recommended", "accepted", "completed", "skipped"}
            and (
                not item.get("nextFollowUpDueAt")
                or parse_iso_datetime(
                    str(item.get("nextFollowUpDueAt")),
                    default=datetime.now(UTC),
                )
                <= now_dt
            )
        ]
        pool = due or recent_practices
        pool.sort(
            key=lambda item: str(
                item.get("nextFollowUpDueAt")
                or item.get("updatedAt")
                or item.get("createdAt")
                or ""
            ),
            reverse=True,
        )
        return pool[0] if pool else None

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

    def _strings(self, value: object) -> list[str]:
        if not isinstance(value, list):
            return []
        return self._dedupe_strings([str(item) for item in value if str(item).strip()])

    def _dedupe_ids(self, values: list[str]) -> list[Id]:
        return cast(list[Id], self._dedupe_strings(values))

    def _dedupe_strings(self, values: list[str]) -> list[str]:
        deduped: list[str] = []
        for value in values:
            candidate = str(value).strip()
            if candidate and candidate not in deduped:
                deduped.append(candidate)
        return deduped

    def _dedupe_refs(self, values: list[dict[str, object]]) -> list[MethodStateSourceRef]:
        deduped: list[MethodStateSourceRef] = []
        seen: set[tuple[str, str]] = set()
        for value in values:
            record_type = str(value.get("recordType") or "").strip()
            record_id = str(value.get("recordId") or "").strip()
            if not record_type or not record_id:
                continue
            key = (record_type, record_id)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(
                {
                    "recordType": record_type,
                    "recordId": cast(Id, record_id),
                    **(
                        {"summary": str(value.get("summary")).strip()}
                        if str(value.get("summary") or "").strip()
                        else {}
                    ),
                }
            )
        return deduped
