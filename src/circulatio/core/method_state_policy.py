from __future__ import annotations

from typing import Literal, TypedDict, cast

from ..domain.types import (
    ActiveGoalTensionSummary,
    ContainmentSummary,
    DepthMove,
    DepthReadinessAssessment,
    DepthWorkScope,
    GroundingSummary,
    InterpretationDepthLevel,
    MethodContextSnapshot,
    MethodGateResult,
    MethodStateSummary,
)


class RuntimeMethodStatePolicy(TypedDict, total=False):
    depthLevel: Literal["grounding_only", "gentle", "standard"]
    blockedMoves: list[str]
    preferredMoves: list[str]
    preferredClarificationTargets: list[str]
    questionStyle: str
    witnessTone: str
    witnessVoice: str
    recentLocale: str
    avoidPhrasingPatterns: list[str]
    activeGoalFrame: str
    maxClarifyingQuestions: int
    practiceConstraints: dict[str, object]
    reasons: list[str]


_ALL_SCOPES: tuple[DepthWorkScope, ...] = (
    "shadow_work",
    "projection_language",
    "collective_amplification",
    "active_imagination",
    "somatic_correlation",
    "proactive_briefing",
    "archetypal_patterning",
    "inner_outer_correspondence",
    "living_myth_synthesis",
)

_GROUNDING_BLOCKS = [
    "active_imagination",
    "projection_language",
    "archetypal_patterning",
    "collective_amplification",
    "inner_outer_correspondence",
    "living_myth_synthesis",
]


def get_method_state_summary(
    method_context: MethodContextSnapshot | None,
) -> MethodStateSummary | None:
    if not isinstance(method_context, dict):
        return None
    method_state = method_context.get("methodState")
    if not isinstance(method_state, dict):
        return None
    return cast(MethodStateSummary, method_state)


def get_grounding_summary(
    method_context: MethodContextSnapshot | None,
) -> GroundingSummary | None:
    method_state = get_method_state_summary(method_context)
    if method_state is None:
        return None
    grounding = method_state.get("grounding")
    if not isinstance(grounding, dict):
        return None
    return cast(GroundingSummary, grounding)


def get_containment_summary(
    method_context: MethodContextSnapshot | None,
) -> ContainmentSummary | None:
    method_state = get_method_state_summary(method_context)
    if method_state is None:
        return None
    containment = method_state.get("containment")
    if not isinstance(containment, dict):
        return None
    return cast(ContainmentSummary, containment)


def get_active_goal_tension_summary(
    method_context: MethodContextSnapshot | None,
) -> ActiveGoalTensionSummary | None:
    method_state = get_method_state_summary(method_context)
    if method_state is None:
        return None
    active_goal_tension = method_state.get("activeGoalTension")
    if not isinstance(active_goal_tension, dict):
        return None
    return cast(ActiveGoalTensionSummary, active_goal_tension)


def get_active_goal_tension_items(
    method_context: MethodContextSnapshot | None,
) -> list[dict[str, object]]:
    active_goal_tension = get_active_goal_tension_summary(method_context)
    if active_goal_tension is None:
        return []
    tension_id = str(active_goal_tension.get("goalTensionId") or "").strip()
    if not tension_id:
        return []
    item: dict[str, object] = dict(active_goal_tension)
    item["id"] = tension_id
    return [item]


def derive_runtime_method_state_policy(
    method_context: MethodContextSnapshot | None,
) -> RuntimeMethodStatePolicy:
    policy: RuntimeMethodStatePolicy = {
        "depthLevel": "standard",
        "blockedMoves": [],
        "preferredMoves": [],
        "preferredClarificationTargets": [],
        "questionStyle": "reflective",
        "witnessTone": "gentle",
        "avoidPhrasingPatterns": [],
        "maxClarifyingQuestions": 2,
        "practiceConstraints": {},
        "reasons": [],
    }
    if not isinstance(method_context, dict):
        return policy

    method_state = get_method_state_summary(method_context)
    if method_state is not None:
        containment = get_containment_summary(method_context)
        grounding = get_grounding_summary(method_context)
        grounding_need = (
            str(containment.get("groundingNeed") or "").strip()
            if isinstance(containment, dict)
            else ""
        )
        if not grounding_need and isinstance(grounding, dict):
            grounding_need = str(grounding.get("recommendation") or "").strip()
        if grounding_need == "grounding_first":
            policy["depthLevel"] = "grounding_only"
            policy["blockedMoves"] = list(_GROUNDING_BLOCKS)
            policy["preferredMoves"] = ["grounding", "body_orientation", "reality_anchors"]
            policy["preferredClarificationTargets"] = ["body_state", "reality_anchors"]
            policy["questionStyle"] = "body_first"
            policy["witnessTone"] = "grounded"
            policy["practiceConstraints"] = {
                **policy["practiceConstraints"],
                "requireGroundingCompatible": True,
            }
            policy["reasons"].append("Containment currently requires grounding first.")
        elif grounding_need == "pace_gently":
            policy["depthLevel"] = "gentle"
            policy["blockedMoves"] = ["active_imagination"]
            policy["preferredMoves"] = ["grounded_question", "body_orientation"]
            policy["preferredClarificationTargets"] = ["body_state", "conscious_attitude"]
            policy["practiceConstraints"] = {
                **policy["practiceConstraints"],
                "preferLowIntensity": True,
            }
            policy["reasons"].append(
                "Containment suggests symbolic work should stay paced and concrete."
            )
        elif grounding_need == "clear_for_depth":
            policy["depthLevel"] = "standard"
            policy["blockedMoves"] = []
            policy["reasons"].append("Reality anchors suggest depth work can be held.")

        if isinstance(containment, dict):
            status = str(containment.get("status") or "").strip()
            if status == "thin":
                policy["practiceConstraints"] = {
                    **policy["practiceConstraints"],
                    "requireGroundingCompatible": True,
                }
            elif status == "strained":
                policy["practiceConstraints"] = {
                    **policy["practiceConstraints"],
                    "preferLowIntensity": True,
                }

        ego_capacity = method_state.get("egoCapacity")
        if isinstance(ego_capacity, dict) and ego_capacity.get("reflectiveCapacity") == "fragile":
            policy["maxClarifyingQuestions"] = 1
            if policy["depthLevel"] == "standard":
                policy["depthLevel"] = "gentle"
            if "Fragile reflective capacity favors one-step pacing." not in policy["reasons"]:
                policy["reasons"].append("Fragile reflective capacity favors one-step pacing.")

        relational_field = method_state.get("relationalField")
        if isinstance(relational_field, dict):
            relationship_contact = str(relational_field.get("relationshipContact") or "").strip()
            isolation_risk = str(relational_field.get("isolationRisk") or "").strip()
            support_direction = str(relational_field.get("supportDirection") or "").strip()
            if relationship_contact in {"thin", "isolated"} or isolation_risk in {
                "moderate",
                "high",
            }:
                policy["preferredClarificationTargets"] = list(
                    dict.fromkeys(
                        [
                            *policy["preferredClarificationTargets"],
                            "relational_scene",
                            "reality_anchors",
                        ]
                    )
                )
                if "projection_language" not in policy["blockedMoves"] and not bool(
                    relational_field.get("projectionLanguageAllowed")
                ):
                    policy["blockedMoves"].append("projection_language")
                policy["reasons"].append(
                    "Relational field suggests starting with support and contact."
                )
            if support_direction == "protect_space":
                policy["practiceConstraints"] = {
                    **policy["practiceConstraints"],
                    "preferLowIntensity": True,
                    "protectRelationalSpace": True,
                }
                if policy["witnessTone"] == "direct":
                    policy["witnessTone"] = "gentle"
            dependency_pressure = str(relational_field.get("dependencyPressure") or "").strip()
            if dependency_pressure == "high":
                policy["preferredMoves"] = list(
                    dict.fromkeys([*policy["preferredMoves"], "boundary_support"])
                )

        questioning_preference = method_state.get("questioningPreference")
        if isinstance(questioning_preference, dict):
            depth_pacing = str(questioning_preference.get("depthPacing") or "").strip()
            if depth_pacing == "one_step":
                policy["maxClarifyingQuestions"] = 1
                if policy["depthLevel"] == "standard":
                    policy["depthLevel"] = "gentle"
                policy["reasons"].append("Recent questioning feedback asks for one step at a time.")
                policy["questionStyle"] = "choice_based"
            preferred_targets = questioning_preference.get("preferredCaptureTargets")
            if isinstance(preferred_targets, list):
                policy["preferredClarificationTargets"] = list(
                    dict.fromkeys(
                        [
                            *policy["preferredClarificationTargets"],
                            *[str(item) for item in preferred_targets if str(item).strip()],
                        ]
                    )
                )[:4]
            preferred_styles = _string_list(questioning_preference.get("preferredQuestionStyles"))
            if preferred_styles:
                policy["questionStyle"] = preferred_styles[0]

        compensation = method_state.get("compensationTendencies")
        if isinstance(compensation, list) and compensation:
            policy["preferredMoves"] = list(
                dict.fromkeys([*policy["preferredMoves"], "tentative_user_test_prompt"])
            )
            first_compensation = compensation[0] if isinstance(compensation[0], dict) else None
            if isinstance(first_compensation, dict):
                compensation_prompt = str(first_compensation.get("userTestPrompt") or "").strip()
                if compensation_prompt:
                    policy["practiceConstraints"] = {
                        **policy["practiceConstraints"],
                        "compensationPrompt": compensation_prompt,
                    }

        active_goal_tension = method_state.get("activeGoalTension")
        if isinstance(active_goal_tension, dict):
            balancing_direction = str(active_goal_tension.get("balancingDirection") or "").strip()
            if balancing_direction:
                policy["activeGoalFrame"] = balancing_direction
                policy["preferredClarificationTargets"] = list(
                    dict.fromkeys([*policy["preferredClarificationTargets"], "goal_tension"])
                )
                policy["preferredMoves"] = list(
                    dict.fromkeys([*policy["preferredMoves"], "goal_tension_language"])
                )
                policy["reasons"].append("An active goal tension should stay in frame.")

        practice_loop = method_state.get("practiceLoop")
        if isinstance(practice_loop, dict):
            preferred_modalities = _string_list(practice_loop.get("preferredModalities"))
            avoided_modalities = _string_list(practice_loop.get("avoidedModalities"))
            if preferred_modalities:
                policy["practiceConstraints"] = {
                    **policy["practiceConstraints"],
                    "preferredModalities": preferred_modalities,
                }
            if avoided_modalities:
                policy["practiceConstraints"] = {
                    **policy["practiceConstraints"],
                    "avoidedModalities": avoided_modalities,
                }
            max_duration = practice_loop.get("maxDurationMinutes")
            if isinstance(max_duration, int) and max_duration > 0:
                policy["practiceConstraints"] = {
                    **policy["practiceConstraints"],
                    "maxDurationMinutes": max_duration,
                }
            recommended_intensity = str(practice_loop.get("recommendedIntensity") or "").strip()
            if recommended_intensity == "low":
                policy["practiceConstraints"] = {
                    **policy["practiceConstraints"],
                    "preferLowIntensity": True,
                }
                policy["preferredMoves"] = list(
                    dict.fromkeys([*policy["preferredMoves"], "grounding", "body_orientation"])
                )
            recent_outcome_trend = str(practice_loop.get("recentOutcomeTrend") or "").strip()
            if recent_outcome_trend == "activating":
                policy["reasons"].append(
                    "Recent practice outcomes suggest keeping work low intensity."
                )
                if policy["depthLevel"] == "standard":
                    policy["depthLevel"] = "gentle"

        typology_method_state = method_state.get("typologyMethodState")
        if isinstance(typology_method_state, dict):
            prompt_bias = str(typology_method_state.get("promptBias") or "").strip()
            practice_bias = str(typology_method_state.get("practiceBias") or "").strip()
            if prompt_bias in {"body_first", "image_first", "relational_first", "reflection_first"}:
                if policy["questionStyle"] == "reflective":
                    policy["questionStyle"] = prompt_bias
                prompt_targets = {
                    "body_first": "body_state",
                    "image_first": "personal_amplification",
                    "relational_first": "relational_scene",
                    "reflection_first": "conscious_attitude",
                }
                target = prompt_targets.get(prompt_bias)
                if target:
                    policy["preferredClarificationTargets"] = list(
                        dict.fromkeys([*policy["preferredClarificationTargets"], target])
                    )
            if practice_bias and practice_bias != "neutral":
                policy["practiceConstraints"] = {
                    **policy["practiceConstraints"],
                    "practiceBias": practice_bias,
                }
                policy["reasons"].append(
                    "Typology remains advisory, but it can shape pacing and framing."
                )

    _apply_adaptation_overlay(policy, method_context.get("adaptationProfile"))

    if policy.get("depthLevel") == "gentle" and "active_imagination" not in policy.get(
        "blockedMoves", []
    ):
        policy["blockedMoves"] = list(
            dict.fromkeys([*policy.get("blockedMoves", []), "active_imagination"])
        )

    policy["blockedMoves"] = list(dict.fromkeys(str(item) for item in policy["blockedMoves"]))
    policy["preferredMoves"] = list(dict.fromkeys(str(item) for item in policy["preferredMoves"]))
    policy["preferredClarificationTargets"] = list(
        dict.fromkeys(str(item) for item in policy["preferredClarificationTargets"])
    )[:5]
    policy["avoidPhrasingPatterns"] = list(
        dict.fromkeys(
            str(item) for item in policy.get("avoidPhrasingPatterns", []) if str(item).strip()
        )
    )[:5]
    policy["reasons"] = list(
        dict.fromkeys(str(item) for item in policy["reasons"] if str(item).strip())
    )

    return policy


def _apply_adaptation_overlay(
    policy: RuntimeMethodStatePolicy,
    adaptation_profile: object | None,
) -> None:
    communication_preferences = _adaptation_scope_dict(
        adaptation_profile,
        explicit_scope="communication",
        learned_scope="communicationPolicy",
    )
    interpretation_preferences = _adaptation_scope_dict(
        adaptation_profile,
        explicit_scope="interpretation",
        learned_scope="interpretationPolicy",
    )
    interpretation_stats = _adaptation_nested_dict(adaptation_profile, "interpretationStats")
    interaction_feedback = _adaptation_nested_dict(adaptation_profile, "interactionFeedbackStats")

    preferred_voice = _last_string(interpretation_stats.get("preferredWitnessVoice"))
    if preferred_voice:
        policy["witnessVoice"] = preferred_voice
    rejected_patterns = _string_list(interpretation_stats.get("rejectedPhrasingPatterns"))
    if rejected_patterns:
        policy["avoidPhrasingPatterns"] = list(
            dict.fromkeys([*policy.get("avoidPhrasingPatterns", []), *rejected_patterns])
        )[:5]
    interpretation_feedback = (
        interaction_feedback.get("interpretation")
        if isinstance(interaction_feedback, dict)
        else None
    )
    recent_locale = (
        _last_string(interpretation_feedback.get("recentLocales"))
        if isinstance(interpretation_feedback, dict)
        else ""
    )
    if recent_locale:
        policy["recentLocale"] = recent_locale

    if policy.get("depthLevel") != "grounding_only":
        communication_tone = str(communication_preferences.get("tone") or "").strip()
        if (
            communication_tone in {"gentle", "direct", "spacious"}
            and policy.get("witnessTone") != "grounded"
        ):
            if policy.get("witnessTone") == "gentle" or communication_tone == "gentle":
                policy["witnessTone"] = communication_tone

        communication_question_style = str(
            communication_preferences.get("questioningStyle") or ""
        ).strip()
        mapped_question_style = {
            "soma_first": "body_first",
            "image_first": "image_first",
            "feeling_first": "relational_first",
            "reflective": "reflection_first",
        }.get(communication_question_style)
        if mapped_question_style and policy.get("questionStyle") == "reflective":
            policy["questionStyle"] = mapped_question_style

        depth_preference = str(interpretation_preferences.get("depthPreference") or "").strip()
        if depth_preference == "brief_pattern_notes":
            if policy["depthLevel"] == "standard":
                policy["depthLevel"] = "gentle"
            policy["preferredMoves"] = list(
                dict.fromkeys([*policy["preferredMoves"], "brief_pattern_notes"])
            )
            policy["reasons"].append("Interpretation preference favors brief pattern notes.")
        elif depth_preference == "deep_amplification" and policy["depthLevel"] == "standard":
            policy["preferredMoves"] = list(
                dict.fromkeys([*policy["preferredMoves"], "deepen_when_held"])
            )
            policy["reasons"].append(
                "Interpretation preference leaves room for deeper amplification."
            )

        modality_bias = str(interpretation_preferences.get("modalityBias") or "").strip()
        if modality_bias == "body":
            if policy["questionStyle"] == "reflective":
                policy["questionStyle"] = "body_first"
            policy["preferredMoves"] = list(
                dict.fromkeys([*policy["preferredMoves"], "body_orientation"])
            )
            policy["preferredClarificationTargets"] = list(
                dict.fromkeys([*policy["preferredClarificationTargets"], "body_state"])
            )
        elif modality_bias == "image":
            if policy["questionStyle"] == "reflective":
                policy["questionStyle"] = "image_first"
            policy["preferredMoves"] = list(
                dict.fromkeys([*policy["preferredMoves"], "image_association"])
            )
            policy["preferredClarificationTargets"] = list(
                dict.fromkeys([*policy["preferredClarificationTargets"], "personal_amplification"])
            )
        elif modality_bias == "emotion":
            if policy["questionStyle"] == "reflective":
                policy["questionStyle"] = "relational_first"
            policy["preferredClarificationTargets"] = list(
                dict.fromkeys([*policy["preferredClarificationTargets"], "relational_scene"])
            )
        elif modality_bias == "narrative":
            if policy["questionStyle"] == "reflective":
                policy["questionStyle"] = "choice_based"
            policy["preferredClarificationTargets"] = list(
                dict.fromkeys([*policy["preferredClarificationTargets"], "conscious_attitude"])
            )


def merge_method_gate_with_policy(
    llm_gate: MethodGateResult | None,
    policy: RuntimeMethodStatePolicy,
) -> MethodGateResult | None:
    if llm_gate is None and not policy.get("reasons") and not policy.get("blockedMoves"):
        return None
    gate: MethodGateResult = {
        "depthLevel": _policy_depth_to_gate_level(policy.get("depthLevel") or "standard"),
        "missingPrerequisites": [],
        "blockedMoves": [],
        "requiredPrompts": [],
        "responseConstraints": [],
    }
    if isinstance(llm_gate, dict):
        gate["depthLevel"] = _stricter_depth_level(gate["depthLevel"], llm_gate["depthLevel"])
        gate["missingPrerequisites"] = [str(item) for item in llm_gate["missingPrerequisites"]]
        gate["blockedMoves"] = [str(item) for item in llm_gate["blockedMoves"]]
        gate["requiredPrompts"] = [str(item) for item in llm_gate["requiredPrompts"]]
        gate["responseConstraints"] = [str(item) for item in llm_gate["responseConstraints"]]
    policy_blocked_moves = [str(item) for item in policy.get("blockedMoves", [])]
    gate["blockedMoves"] = list(dict.fromkeys([*gate["blockedMoves"], *policy_blocked_moves]))
    gate["requiredPrompts"] = list(
        dict.fromkeys(
            [
                *gate["requiredPrompts"],
                *(
                    ["Ask at most one clarifying question."]
                    if int(policy.get("maxClarifyingQuestions", 2)) <= 1
                    else []
                ),
            ]
        )
    )
    response_constraints = list(gate["responseConstraints"])
    if policy.get("depthLevel") == "grounding_only":
        response_constraints.append("Stay with grounding and concrete embodied language.")
    elif policy.get("depthLevel") == "gentle":
        response_constraints.append("Prefer short, concrete, body-near language.")
    gate["responseConstraints"] = list(dict.fromkeys(response_constraints))
    policy_reasons = [str(item) for item in policy.get("reasons", [])]
    gate["missingPrerequisites"] = list(
        dict.fromkeys([*gate["missingPrerequisites"], *policy_reasons])
    )
    return gate


def reconcile_depth_readiness_with_policy(
    readiness: DepthReadinessAssessment | None,
    policy: RuntimeMethodStatePolicy,
) -> DepthReadinessAssessment | None:
    if (
        readiness is None
        and policy.get("depthLevel") == "standard"
        and not policy.get("blockedMoves")
    ):
        return None
    allowed_moves: dict[DepthWorkScope, DepthMove] = {scope: "allow" for scope in _ALL_SCOPES}
    status: Literal["grounding_only", "limited", "ready"] = "ready"
    reasons = [str(item) for item in policy.get("reasons", [])]
    required_user_action: str | None = None
    evidence_ids: list[str] = []
    if isinstance(readiness, dict):
        status = readiness["status"]
        allowed_moves.update(readiness["allowedMoves"])
        reasons = list(dict.fromkeys([*reasons, *readiness["reasons"]]))
        required_user_action = readiness.get("requiredUserAction")
        evidence_ids = [str(item) for item in readiness["evidenceIds"]]
    if policy.get("depthLevel") == "grounding_only":
        status = "grounding_only"
        required_user_action = "Grounding first."
        for scope in _ALL_SCOPES:
            allowed_moves[scope] = "withhold" if scope in _GROUNDING_BLOCKS else "mirror_only"
    elif policy.get("depthLevel") == "gentle":
        if status == "ready":
            status = "limited"
        for scope in _ALL_SCOPES:
            if scope in {"active_imagination", "shadow_work", "archetypal_patterning"}:
                allowed_moves[scope] = "soften"
    for move in policy.get("blockedMoves", []):
        blocked_scope = _as_depth_scope(move)
        if blocked_scope is not None:
            allowed_moves[blocked_scope] = "withhold"
    result: DepthReadinessAssessment = {
        "status": status,
        "allowedMoves": allowed_moves,
        "reasons": reasons,
        "evidenceIds": evidence_ids,
    }
    if required_user_action is not None:
        result["requiredUserAction"] = required_user_action
    return result


def _policy_depth_to_gate_level(value: str) -> InterpretationDepthLevel:
    mapping: dict[str, InterpretationDepthLevel] = {
        "grounding_only": "grounding_only",
        "gentle": "observations_only",
        "standard": "depth_interpretation_allowed",
    }
    return mapping.get(value, "depth_interpretation_allowed")


def _stricter_depth_level(
    left: InterpretationDepthLevel,
    right: object,
) -> InterpretationDepthLevel:
    ranking: dict[InterpretationDepthLevel, int] = {
        "grounding_only": 0,
        "observations_only": 1,
        "personal_amplification_needed": 2,
        "cautious_pattern_note": 3,
        "depth_interpretation_allowed": 4,
    }
    candidate = _as_depth_level(right)
    if candidate is None:
        return left
    return left if ranking[left] <= ranking[candidate] else candidate


def _as_depth_level(value: object) -> InterpretationDepthLevel | None:
    candidate = str(value or "").strip()
    if candidate in {
        "grounding_only",
        "observations_only",
        "personal_amplification_needed",
        "cautious_pattern_note",
        "depth_interpretation_allowed",
    }:
        return cast(InterpretationDepthLevel, candidate)
    return None


def _as_depth_scope(value: object) -> DepthWorkScope | None:
    candidate = str(value or "").strip()
    if candidate in _ALL_SCOPES:
        return cast(DepthWorkScope, candidate)
    return None


def _adaptation_scope_dict(
    adaptation_profile: object | None,
    *,
    explicit_scope: str,
    learned_scope: str,
) -> dict[str, object]:
    if not isinstance(adaptation_profile, dict):
        return {}
    explicit = adaptation_profile.get("explicitPreferences")
    learned = adaptation_profile.get("learnedSignals")
    explicit_value = explicit.get(explicit_scope) if isinstance(explicit, dict) else None
    learned_value = learned.get(learned_scope) if isinstance(learned, dict) else None
    if isinstance(explicit_value, dict) and explicit_value:
        return explicit_value
    return learned_value if isinstance(learned_value, dict) else {}


def _adaptation_nested_dict(
    adaptation_profile: object | None,
    key: str,
) -> dict[str, object]:
    if not isinstance(adaptation_profile, dict):
        return {}
    learned = adaptation_profile.get("learnedSignals")
    if not isinstance(learned, dict):
        return {}
    value = learned.get(key)
    return value if isinstance(value, dict) else {}


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [candidate for item in value if (candidate := str(item or "").strip())]


def _last_string(value: object) -> str:
    if not isinstance(value, list):
        return ""
    for item in reversed(value):
        candidate = str(item or "").strip()
        if candidate:
            return candidate
    return ""
