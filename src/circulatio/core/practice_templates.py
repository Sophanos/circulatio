from __future__ import annotations

from ..domain.types import PracticeScriptStep

PRACTICE_TEMPLATES: dict[str, dict[str, object]] = {
    "grounding_5_4_3_2_1": {
        "type": "grounding",
        "modality": "somatic",
        "intensity": "low",
        "durationMinutes": 3,
        "instructions": [
            "Name five things you can see.",
            "Notice four things you can feel touching your body.",
            "Track three sounds without analyzing them.",
            "Take two slower exhales.",
            "Name one thing that feels steady right now.",
        ],
        "script": [
            {
                "instruction": "Look around the room and name five things you can see.",
                "pauseSeconds": 20,
            },
            {"instruction": "Feel the surface beneath your feet or body.", "pauseSeconds": 20},
            {"instruction": "Lengthen your exhale for two breaths.", "pauseSeconds": 15},
        ],
    },
    "image_journaling": {
        "type": "journaling",
        "modality": "writing",
        "intensity": "low",
        "durationMinutes": 8,
        "instructions": [
            "Write the strongest image in one sentence.",
            "Write what feeling came with it.",
            "Write one waking-life echo without forcing a conclusion.",
        ],
        "script": [
            {"instruction": "Write the image exactly as it appeared.", "pauseSeconds": 30},
            {"instruction": "Write the feeling that comes with it now.", "pauseSeconds": 30},
        ],
    },
    "active_imagination_symbol_dialogue": {
        "type": "active_imagination",
        "modality": "imaginal",
        "intensity": "moderate",
        "durationMinutes": 6,
        "instructions": [
            "Return to the image slowly.",
            "Ask what it wants you to notice.",
            "Write the first response without arguing with it.",
            "Stop if activation rises sharply.",
        ],
        "script": [
            {
                "instruction": "Close your eyes and let the image appear without forcing it.",
                "pauseSeconds": 25,
            },
            {"instruction": "Ask the image: what do you want me to notice?", "pauseSeconds": 30},
            {
                "instruction": "Write the first response you receive.",
                "pauseSeconds": 45,
                "safetyNote": "Stop if the image becomes overwhelming.",
            },
        ],
    },
    "somatic_tracking_sensation": {
        "type": "somatic_tracking",
        "modality": "somatic",
        "intensity": "low",
        "durationMinutes": 5,
        "instructions": [
            "Stay with one body sensation for a few breaths.",
            "Notice whether it shifts, spreads, or softens.",
            "Stop if activation increases.",
        ],
        "script": [
            {
                "instruction": "Notice the sensation without trying to change it.",
                "pauseSeconds": 20,
            },
            {"instruction": "Track whether it moves, tightens, or eases.", "pauseSeconds": 25},
        ],
    },
    "amplification_journaling": {
        "type": "amplification_journaling",
        "modality": "writing",
        "intensity": "low",
        "durationMinutes": 7,
        "instructions": [
            "Write your own association to the image before using any symbolic frame.",
            "Add one memory, one feeling, and one body cue.",
            "Leave the image open rather than solving it.",
        ],
        "script": [
            {
                "instruction": "Write your first personal association to the image.",
                "pauseSeconds": 30,
            },
            {
                "instruction": "Add the feeling and body sensation that come with it.",
                "pauseSeconds": 30,
            },
        ],
    },
}


def template_script(template_id: str) -> list[PracticeScriptStep]:
    return list(PRACTICE_TEMPLATES.get(template_id, {}).get("script", []))
