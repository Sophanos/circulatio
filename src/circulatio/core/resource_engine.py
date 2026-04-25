from __future__ import annotations

from copy import deepcopy
from typing import cast

from ..domain.ids import create_id
from ..domain.types import (
    CoachLoopSummary,
    CoachStateSummary,
    EmbodiedResourceSummary,
    ResourceInvitationSummary,
)
from .resource_catalog import CATALOG


class ResourceEngine:
    def select_resource_for_loop(
        self,
        *,
        loop: CoachLoopSummary,
        coach_state: CoachStateSummary,
        runtime_policy: dict[str, object],
        safety_context: dict[str, object] | None,
        now: str,
    ) -> ResourceInvitationSummary | None:
        del safety_context
        existing_invitation = loop.get("resourceInvitation")
        if isinstance(existing_invitation, dict) and isinstance(
            existing_invitation.get("resource"), dict
        ):
            return cast(ResourceInvitationSummary, deepcopy(existing_invitation))
        candidates = [
            resource
            for resource in CATALOG
            if self.resource_allowed(
                resource=resource,
                loop=loop,
                runtime_policy=runtime_policy,
                consent_preferences=coach_state.get("witness", {}).get(
                    "preferredClarificationTargets", []
                ),
            )
        ]
        if not candidates:
            return None
        preferred_modalities = self._preferred_modalities(loop=loop, coach_state=coach_state)
        candidates.sort(
            key=lambda item: (
                0 if item["modality"] in preferred_modalities else 1,
                0 if self._matches_activation_band(resource=item, coach_state=coach_state) else 1,
                int(item.get("durationMinutes", 99)),
                item["id"],
            )
        )
        resource = candidates[0]
        presentation_policy = {
            "allowNotNow": True,
            "preserveHostChoice": True,
            "renderAs": "resource_card",
        }
        return {
            "id": create_id("resource_invitation"),
            "resource": cast(EmbodiedResourceSummary, dict(resource)),
            "triggerLoopKey": loop["loopKey"],
            "reason": str(loop.get("summaryHint") or "A gentler resource fits the current pacing."),
            "activationRationale": self._activation_rationale(loop=loop, coach_state=coach_state),
            "capture": cast(dict[str, object], dict(loop["capture"])),
            "presentationPolicy": presentation_policy,
            "createdAt": now,
        }

    def resource_allowed(
        self,
        *,
        resource: EmbodiedResourceSummary,
        loop: CoachLoopSummary,
        runtime_policy: dict[str, object],
        consent_preferences: list[object],
    ) -> bool:
        del consent_preferences
        blocked_moves = {
            str(item).strip() for item in loop.get("blockedMoves", []) if str(item).strip()
        }
        depth_level = str(runtime_policy.get("depthLevel") or "").strip()
        modality = str(resource.get("modality") or "").strip()
        if (
            modality in {"breath", "body_scan", "somatic_tracking"}
            and "somatic_correlation" in blocked_moves
        ):
            return False
        if depth_level == "grounding_only" and modality not in {
            "grounding",
            "breath",
            "body_scan",
            "somatic_tracking",
        }:
            return False
        return True

    def _preferred_modalities(
        self,
        *,
        loop: CoachLoopSummary,
        coach_state: CoachStateSummary,
    ) -> list[str]:
        kind = str(loop.get("kind") or "").strip()
        move_kind = str(loop.get("moveKind") or "").strip()
        if kind == "practice_integration" and move_kind == "offer_resource":
            return ["journaling", "breath", "body_scan"]
        if kind in {"soma", "resource_support"}:
            return ["breath", "body_scan", "somatic_tracking"]
        if kind == "relational_scene":
            return ["breath", "journaling"]
        if coach_state.get("globalConstraints", {}).get("depthLevel") == "grounding_only":
            return ["breath", "body_scan", "somatic_tracking"]
        return ["journaling", "somatic_tracking", "breath"]

    def _matches_activation_band(
        self,
        *,
        resource: EmbodiedResourceSummary,
        coach_state: CoachStateSummary,
    ) -> bool:
        depth_level = str(coach_state.get("globalConstraints", {}).get("depthLevel") or "").strip()
        band = str(resource.get("activationBand") or "").strip()
        if depth_level == "grounding_only":
            return band in {"high", "overwhelming"}
        return band in {"low", "moderate", "high"}

    def _activation_rationale(
        self,
        *,
        loop: CoachLoopSummary,
        coach_state: CoachStateSummary,
    ) -> str:
        depth_level = str(coach_state.get("globalConstraints", {}).get("depthLevel") or "").strip()
        if depth_level == "grounding_only":
            return "Grounding comes before stronger symbolic or reflective depth right now."
        if str(loop.get("kind") or "").strip() == "practice_integration":
            return "Recent practice signals suggest a gentler modality."
        return "This loop benefits from a paced, embodied support option."
