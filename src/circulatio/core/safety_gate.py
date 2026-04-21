from __future__ import annotations

import re

from ..domain.types import (
    CrisisSupportResource,
    MaterialInterpretationInput,
    SafetyDisposition,
    SafetyFlag,
)

DEFAULT_SUPPORT: list[CrisisSupportResource] = [
    {
        "label": "Local emergency services",
        "note": "Use your local emergency number if there is immediate danger.",
    }
]


class SafetyGate:
    """Minimal deterministic safety floor. Runs before LLM as a fast screen,
    and after LLM as a reconciliation layer. The gate wins over the LLM."""

    def assess(self, input_data: MaterialInterpretationInput) -> SafetyDisposition:
        session = input_data.get("sessionContext", {})
        safety_context = input_data.get("safetyContext", {})
        state_text = " ".join(
            [
                input_data.get("explicitQuestion", ""),
                " ".join(session.get("contextNotes", [])),
                " ".join(session.get("recentEventNotes", [])),
                " ".join(session.get("currentStateNotes", [])),
                safety_context.get("userReportedActivation", ""),
            ]
        ).lower()
        material_text = input_data.get("materialText", "").lower()

        flags: list[SafetyFlag] = []
        if re.search(
            r"\b(kill myself|suicide|end my life|self harm|hurt myself)\b", state_text, re.I
        ):
            flags.append("self_harm_or_suicide")
        if re.search(r"\b(kill them|hurt someone|harm others|attack them)\b", state_text, re.I):
            flags.append("harm_to_others")
        if re.search(r"\b(kill myself|suicide|hurt myself)\b", material_text, re.I) and re.search(
            r"\b(i want|i will|i need to)\b", material_text, re.I
        ):
            flags.append("self_harm_or_suicide")
        if re.search(
            r"\b(message from god|chosen one|they control my thoughts|implanted thoughts)\b",
            state_text,
            re.I,
        ):
            flags.append("psychosis_like_certainty")
        if re.search(
            r"\b(haven't slept|no sleep for days|unstoppable energy|invincible)\b", state_text, re.I
        ):
            flags.append("mania_like_activation")
        if re.search(
            r"\b(not real|outside my body|can't feel my body|dissociating)\b", state_text, re.I
        ):
            flags.append("severe_dissociation")
        if safety_context.get("userReportedActivation") == "overwhelming":
            flags.append("panic_or_overwhelm")
        if safety_context.get("intoxicationReported"):
            flags.append("intoxication")
        if safety_context.get("userIsMinor"):
            flags.append("minor_policy_sensitive")

        unique_flags = list(dict.fromkeys(flags))
        support = safety_context.get("crisisSupportResources", DEFAULT_SUPPORT)
        if any(flag in unique_flags for flag in ("self_harm_or_suicide", "harm_to_others")):
            return {
                "status": "crisis_handoff",
                "flags": unique_flags,
                "depthWorkAllowed": False,
                "message": (
                    "This is not a moment for symbolic depth work. Please seek "
                    "immediate human support and use emergency or crisis "
                    "resources if there is any risk of harm."
                ),
                "suggestedSupport": support,
            }
        if any(
            flag in unique_flags
            for flag in (
                "psychosis_like_certainty",
                "mania_like_activation",
                "severe_dissociation",
                "panic_or_overwhelm",
                "intoxication",
            )
        ):
            return {
                "status": "grounding_only",
                "flags": unique_flags,
                "depthWorkAllowed": False,
                "message": (
                    "Depth interpretation should pause here. The safer route "
                    "is grounding, orienting to the present, and involving "
                    "trusted human support if needed."
                ),
                "suggestedSupport": support,
            }
        return {
            "status": "clear",
            "flags": unique_flags,
            "depthWorkAllowed": True,
            "message": (
                "Hermes-Circulation supports reflection and symbolic "
                "interpretation. It does not provide therapy, diagnosis, "
                "crisis counseling, or medical advice."
            ),
        }
