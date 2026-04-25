from __future__ import annotations

CANONICAL_SURFACES = (
    "alive_today",
    "journey_page",
    "practice_followup",
    "method_state_response",
    "analysis_packet",
    "threshold_review",
    "living_myth_review",
    "weekly_review",
    "ritual_artifact",
    "artifact_completion",
    "ritual_invitation",
    "rhythmic_brief",
    "discovery",
    "none",
)

CANONICAL_MOVE_KINDS = (
    "ask_body_checkin",
    "offer_resource",
    "track_without_prompt",
    "hold_silence",
    "return_to_journey",
    "ask_goal_tension",
    "ask_relational_scene",
    "ask_practice_followup",
    "offer_practice",
    "offer_ritual",
    "record_completion",
    "scheduled_invitation",
)

CANONICAL_WRITE_KINDS = (
    "material",
    "body_state",
    "relational_scene",
    "journey",
    "practice_session",
    "practice_response",
    "feedback",
    "review",
    "proposal",
    "proactive_brief",
    "proactive_brief_response",
    "ritual_completion",
    "unknown",
)

REQUIRED_OUTPUT_FIELDS = ("caseId", "turnResults")
REQUIRED_TURN_FIELDS = (
    "turnId",
    "selectedToolSequence",
    "askedClarification",
    "performedHostInterpretation",
    "hostReply",
    "rationale",
)

OUTPUT_SCHEMA: dict[str, object] = {
    "type": "object",
    "required": ["caseId", "turnResults", "globalNotes"],
    "additionalProperties": False,
    "properties": {
        "caseId": {"type": "string"},
        "turnResults": {
            "type": "array",
            "items": {
                "type": "object",
                "required": [
                    "turnId",
                    "selectedToolSequence",
                    "toolArgsSummary",
                    "selectedSurface",
                    "selectedMoveKind",
                    "depthLevel",
                    "captureTargets",
                    "readActions",
                    "writeActions",
                    "askedClarification",
                    "performedHostInterpretation",
                    "forbiddenEscalationsPresent",
                    "hostReply",
                    "confidence",
                    "rationale",
                ],
                "additionalProperties": False,
                "properties": {
                    "turnId": {"type": "string"},
                    "selectedToolSequence": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "toolArgsSummary": {
                        "type": ["object", "null"],
                        "additionalProperties": False,
                        "properties": {},
                    },
                    "selectedSurface": {"type": ["string", "null"]},
                    "selectedMoveKind": {"type": ["string", "null"]},
                    "depthLevel": {"type": ["string", "null"]},
                    "captureTargets": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "readActions": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "writeActions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": [
                                "kind",
                                "tool",
                                "requiresApproval",
                                "autonomous",
                            ],
                            "additionalProperties": False,
                            "properties": {
                                "kind": {"type": "string"},
                                "tool": {"type": ["string", "null"]},
                                "requiresApproval": {"type": ["boolean", "null"]},
                                "autonomous": {"type": ["boolean", "null"]},
                            },
                        },
                    },
                    "askedClarification": {"type": "boolean"},
                    "performedHostInterpretation": {"type": "boolean"},
                    "forbiddenEscalationsPresent": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "hostReply": {"type": "string"},
                    "confidence": {"type": ["number", "null"]},
                    "rationale": {"type": "string"},
                },
            },
        },
        "globalNotes": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
}
