from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from circulatio_hermes_plugin import schemas as plugin_schemas

from .output_schema import OUTPUT_SCHEMA

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL_PATH = REPO_ROOT / "src" / "circulatio_hermes_plugin" / "skills" / "circulation" / "SKILL.md"
JOURNEY_FAMILIES_PATH = REPO_ROOT / "tests" / "evals" / "journey_cli" / "JOURNEY_FAMILIES.md"

_FAMILY_HEADINGS = {
    "EmbodiedRecurrence": "### 1. Embodied Recurrence",
    "SymbolBodyPressure": "### 2. Symbol / Body / Life Pressure",
    "ThoughtLoopTypology": "### 3. Thought Loop / Typology Restraint",
    "RelationalSceneRecurrence": "### 4. Relational Scene Recurrence",
    "PracticeReentry": "### 5. Practice / Re-entry Journey",
    "CrossFamilyUmbrella": "## Canonical E2E Cases",
}


@dataclass
class PromptPackage:
    prompt_text: str
    skill_text: str
    tool_schemas_json: str
    journey_excerpt: str


def _extract_section(text: str, heading: str) -> str:
    lines = text.splitlines()
    collected: list[str] = []
    recording = False
    for line in lines:
        if line.strip() == heading:
            recording = True
        elif recording and line.startswith("## ") and not heading.startswith("## "):
            break
        elif (
            recording
            and line.startswith("### ")
            and heading.startswith("### ")
            and line.strip() != heading
        ):
            break
        if recording:
            collected.append(line)
    return "\n".join(collected).strip()


def _tool_names_from_case(case: dict[str, object]) -> list[str]:
    names: list[str] = []
    for turn in list(case.get("turns", [])):
        if not isinstance(turn, dict):
            continue
        expected = turn.get("expected") if isinstance(turn.get("expected"), dict) else {}
        matcher = expected.get("toolSequence") if isinstance(expected, dict) else None
        if isinstance(matcher, dict):
            for key in ("equals", "contains", "prefix", "notContains"):
                value = matcher.get(key)
                if isinstance(value, list):
                    names.extend(str(item) for item in value if str(item))
                elif value is not None:
                    names.append(str(value))
            options = matcher.get("oneOf")
            if isinstance(options, list):
                for option in options:
                    if isinstance(option, list):
                        names.extend(str(item) for item in option if str(item))
                    elif option is not None:
                        names.append(str(option))
        names.extend(str(item) for item in expected.get("forbiddenTools", []) if str(item))
    deduped: list[str] = []
    seen: set[str] = set()
    for name in names:
        if name and name not in seen:
            seen.add(name)
            deduped.append(name)
    return deduped


def _compact_tool_schemas(case: dict[str, object]) -> list[dict[str, str]]:
    selected = set(_tool_names_from_case(case))
    if not selected:
        selected = {
            "circulatio_store_dream",
            "circulatio_store_reflection",
            "circulatio_store_body_state",
            "circulatio_alive_today",
            "circulatio_journey_page",
            "circulatio_interpret_material",
            "circulatio_method_state_respond",
            "circulatio_generate_practice_recommendation",
            "circulatio_record_interpretation_feedback",
            "circulatio_record_practice_feedback",
        }
    compact = []
    for schema in plugin_schemas.TOOL_SCHEMAS:
        name = str(schema.get("name") or "")
        if name not in selected:
            continue
        compact.append(
            {
                "name": name,
                "description": str(schema.get("description") or ""),
            }
        )
    return compact


def build_prompt_package(
    case: dict[str, object], *, max_prompt_bytes: int = 48_000
) -> PromptPackage:
    skill_text = SKILL_PATH.read_text()
    tool_schemas = _compact_tool_schemas(case)
    tool_schemas_json = json.dumps(tool_schemas, indent=2, sort_keys=True)
    families_text = JOURNEY_FAMILIES_PATH.read_text()
    family_heading = _FAMILY_HEADINGS.get(str(case.get("journeyFamily") or ""))
    family_excerpt = _extract_section(families_text, family_heading) if family_heading else ""
    priority_excerpt = _extract_section(families_text, "## Cross-Signal Priority For Evals")
    journey_excerpt = "\n\n".join(
        excerpt for excerpt in (family_excerpt, priority_excerpt) if excerpt
    ).strip()
    case_packet = json.dumps(case, indent=2, sort_keys=True)
    prompt_parts = [
        "You are simulating Hermes routing for Circulatio. You are not the Circulatio backend.",
        "",
        "Hard boundaries:",
        "- Hermes routes; Circulatio owns state and interpretation.",
        "- Store first for ambient material and body-state logging.",
        "- No host-side Jungian or symbolic interpretation.",
        "- No hidden capture-any ingress.",
        "- circulatio_method_state_respond is for anchored follow-up only.",
        "- Feedback routes to feedback tools, not new stored reflections.",
        "- Read-mostly surfaces must not invent writes.",
        "- Ritual planning is read-only and may return an artifact URL for the host/frontend.",
        "- Frontend artifact completion routes to ritual completion only, without interpretation.",
        "- Scheduled cron may create ritual_invitation rhythmic briefs only; no scheduled ritual planning or rendering.",
        "",
        "Available tools:",
        tool_schemas_json,
        "",
        "Relevant skill instructions:",
        skill_text,
        "",
        "Relevant journey-family excerpt:",
        journey_excerpt,
        "",
        "Case packet:",
        case_packet,
        "",
        "Output contract:",
        json.dumps(OUTPUT_SCHEMA, indent=2, sort_keys=True),
        "",
        "Return JSON only. Do not wrap the result in markdown fences.",
        "Do not edit files or run project-changing commands.",
    ]
    prompt_text = "\n".join(prompt_parts)
    if len(prompt_text.encode("utf-8")) > max_prompt_bytes:
        truncated_skill = skill_text[: max_prompt_bytes // 3]
        prompt_parts[14] = truncated_skill
        prompt_parts.insert(15, "[SKILL TRUNCATED FOR PROMPT SIZE]")
        prompt_text = "\n".join(prompt_parts)
    return PromptPackage(
        prompt_text=prompt_text,
        skill_text=skill_text,
        tool_schemas_json=tool_schemas_json,
        journey_excerpt=journey_excerpt,
    )
