from __future__ import annotations

import json
from typing import Any

CLARIFICATION_PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "questionText": {"type": "string"},
        "questionKey": {"type": "string"},
        "intent": {"type": "string"},
        "captureTarget": {"type": "string"},
        "expectedAnswerKind": {"type": "string"},
        "answerSlots": {"type": "object"},
        "routingHints": {"type": "object"},
        "supportingRefs": {"type": "array"},
        "anchorRefs": {"type": "object"},
        "consentScopes": {"type": "array"},
    },
    "required": ["questionText", "intent", "captureTarget", "expectedAnswerKind"],
}

TYPOLOGY_ASSESSMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {
            "type": "string",
            "enum": ["insufficient_evidence", "signals_only", "hypotheses_available"],
        },
        "typologySignals": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "category": {"type": "string"},
                    "function": {"type": "string"},
                    "orientation": {
                        "type": "string",
                        "enum": [
                            "conscious_adaptation",
                            "support",
                            "compensatory_pressure",
                            "overuse",
                            "unknown",
                        ],
                    },
                    "statement": {"type": "string"},
                    "strength": {"type": "string"},
                    "evidenceIds": {"type": "array", "items": {"type": "string"}},
                },
                "required": [
                    "category",
                    "function",
                    "orientation",
                    "statement",
                    "strength",
                    "evidenceIds",
                ],
            },
        },
        "typologyHypotheses": {"type": "array"},
        "userTestPrompt": {"type": "string"},
    },
    "required": ["status"],
}

ANALYSIS_PACKET_FUNCTION_DYNAMICS_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {
            "type": "string",
            "enum": ["insufficient_evidence", "signals_only", "readable"],
        },
        "summary": {"type": "string"},
        "foregroundFunctions": {"type": "array", "items": {"type": "string"}},
        "compensatoryFunctions": {"type": "array", "items": {"type": "string"}},
        "backgroundFunctions": {"type": "array", "items": {"type": "string"}},
        "ambiguityNotes": {"type": "array", "items": {"type": "string"}},
        "supportingRefs": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "status",
        "summary",
        "foregroundFunctions",
        "compensatoryFunctions",
        "backgroundFunctions",
        "supportingRefs",
    ],
}

INTERPRETATION_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "symbolMentions": {"type": "array"},
        "figureMentions": {"type": "array"},
        "motifMentions": {"type": "array"},
        "lifeContextLinks": {"type": "array"},
        "observations": {"type": "array"},
        "hypotheses": {"type": "array"},
        "depthReadiness": {"type": "object"},
        "methodGate": {"type": "object"},
        "amplificationPrompts": {"type": "array"},
        "dreamSeriesSuggestions": {"type": "array"},
        "typologyAssessment": TYPOLOGY_ASSESSMENT_SCHEMA,
        "individuation": {"type": "object"},
        "practiceRecommendation": {"type": "object"},
        "proposalCandidates": {"type": "array"},
        "userFacingResponse": {"type": "string"},
        "clarifyingQuestion": {"type": "string"},
        "clarificationPlan": CLARIFICATION_PLAN_SCHEMA,
        "clarificationIntent": {"type": "object"},
    },
    "required": [
        "symbolMentions",
        "figureMentions",
        "motifMentions",
        "lifeContextLinks",
        "observations",
        "hypotheses",
        "practiceRecommendation",
        "proposalCandidates",
        "userFacingResponse",
    ],
}

WEEKLY_REVIEW_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "userFacingResponse": {"type": "string"},
        "activeThemes": {"type": "array"},
        "practiceRecommendation": {"type": "object"},
        "longitudinalObservations": {"type": "array"},
    },
    "required": ["userFacingResponse"],
}

ALIVE_TODAY_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "userFacingResponse": {"type": "string"},
        "activeThemes": {"type": "array"},
        "selectedCoachLoopKey": {"type": "string"},
        "coachMoveKind": {"type": "string"},
        "followUpQuestion": {"type": "string"},
        "suggestedAction": {"type": "string"},
        "practiceRecommendation": {"type": "object"},
        "resourceInvitation": {"type": "object"},
        "withheldReason": {"type": "string"},
    },
    "required": ["userFacingResponse"],
}

PRACTICE_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "practiceRecommendation": {"type": "object"},
        "userFacingResponse": {"type": "string"},
        "followUpPrompt": {"type": "string"},
        "adaptationNotes": {"type": "array"},
        "resourceInvitation": {"type": "object"},
    },
    "required": ["practiceRecommendation", "userFacingResponse"],
}

RHYTHMIC_BRIEF_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "summary": {"type": "string"},
        "suggestedAction": {"type": "string"},
        "userFacingResponse": {"type": "string"},
        "supportingRefs": {"type": "array"},
        "resourceInvitation": {"type": "object"},
    },
    "required": ["title", "summary", "userFacingResponse"],
}

THRESHOLD_REVIEW_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "userFacingResponse": {"type": "string"},
        "thresholdProcesses": {"type": "array"},
        "realityAnchors": {"type": "array"},
        "invitations": {"type": "array"},
        "practiceRecommendation": {"type": "object"},
        "proposalCandidates": {"type": "array"},
    },
    "required": ["userFacingResponse", "thresholdProcesses"],
}

LIVING_MYTH_REVIEW_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "userFacingResponse": {"type": "string"},
        "lifeChapter": {"type": "object"},
        "mythicQuestions": {"type": "array"},
        "thresholdMarkers": {"type": "array"},
        "complexEncounters": {"type": "array"},
        "integrationContour": {"type": "object"},
        "symbolicWellbeing": {"type": "object"},
        "practiceRecommendation": {"type": "object"},
        "proposalCandidates": {"type": "array"},
    },
    "required": ["userFacingResponse", "mythicQuestions", "thresholdMarkers", "complexEncounters"],
}

METHOD_STATE_ROUTING_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "answerSummary": {"type": "string"},
        "evidenceSpans": {"type": "array"},
        "captureCandidates": {"type": "array"},
        "followUpPrompts": {"type": "array"},
        "routingWarnings": {"type": "array"},
    },
    "required": [
        "answerSummary",
        "evidenceSpans",
        "captureCandidates",
        "followUpPrompts",
        "routingWarnings",
    ],
}

ANALYSIS_PACKET_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "packetTitle": {"type": "string"},
        "sections": {"type": "array"},
        "includedMaterialIds": {"type": "array"},
        "includedRecordRefs": {"type": "array"},
        "evidenceIds": {"type": "array"},
        "functionDynamics": ANALYSIS_PACKET_FUNCTION_DYNAMICS_SCHEMA,
        "userFacingResponse": {"type": "string"},
        "supportingRefs": {"type": "array"},
    },
    "required": [
        "packetTitle",
        "sections",
        "includedMaterialIds",
        "includedRecordRefs",
        "evidenceIds",
        "userFacingResponse",
        "supportingRefs",
    ],
}

LIFE_CONTEXT_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "windowStart": {"type": "string"},
        "windowEnd": {"type": "string"},
        "lifeEventRefs": {"type": "array"},
        "moodSummary": {"type": "string"},
        "energySummary": {"type": "string"},
        "focusSummary": {"type": "string"},
        "mentalStateSummary": {"type": "string"},
        "habitSummary": {"type": "string"},
        "notableChanges": {"type": "array"},
        "source": {"type": "string"},
    },
    "required": ["windowStart", "windowEnd", "source"],
}


def schema_text(schema: dict[str, Any]) -> str:
    return json.dumps(schema, indent=2, sort_keys=True)


def extract_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:].strip()
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("No JSON object found in model output.")
        value = json.loads(cleaned[start : end + 1])
    if not isinstance(value, dict):
        raise ValueError("Model output must be a JSON object.")
    return value
