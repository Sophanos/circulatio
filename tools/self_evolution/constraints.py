from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from types import ModuleType

from .targets import ALL_IMMUTABLE_ARTIFACTS, REPO_ROOT, get_target

MAX_SKILL_BYTES = 20 * 1024
MAX_TOOL_DESCRIPTION_CHARS = 1800
REQUIRED_PROMPT_FRAGMENT_FUNCTIONS = (
    "analysis_packet_instruction_block",
    "interpretation_instruction_block",
    "life_context_instruction_block",
    "living_myth_instruction_block",
    "method_state_routing_instruction_block",
    "practice_instruction_block",
    "rhythmic_brief_instruction_block",
    "threshold_review_instruction_block",
    "weekly_review_instruction_block",
)

_TOOL_DESCRIPTION_PROFILE_REQUIRED_NAMES = {
    "tool_description_routing": {
        "circulatio_answer_amplification",
        "circulatio_discovery",
        "circulatio_generate_practice_recommendation",
        "circulatio_interpret_material",
        "circulatio_method_state_respond",
        "circulatio_record_interpretation_feedback",
        "circulatio_record_practice_feedback",
        "circulatio_set_consent",
    }
}


def _repo_relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve()))
    except ValueError:
        return str(path)


def validate_prompt_fragments_module(module: ModuleType) -> list[str]:
    findings: list[str] = []
    for name in REQUIRED_PROMPT_FRAGMENT_FUNCTIONS:
        value = getattr(module, name, None)
        if not callable(value):
            findings.append(f"Prompt-fragment module is missing callable '{name}'.")
    return findings


def validate_skill_size(skill_text: str, *, limit_bytes: int = MAX_SKILL_BYTES) -> list[str]:
    findings: list[str] = []
    size_bytes = len(skill_text.encode("utf-8"))
    if size_bytes > limit_bytes:
        findings.append(f"Skill text exceeds {limit_bytes} bytes ({size_bytes}).")
    return findings


def skill_contract_text(
    skill_text: str,
    *,
    section_headings: Sequence[str] | None = None,
) -> str:
    headings = [str(heading).strip() for heading in section_headings or () if str(heading).strip()]
    if not headings:
        return skill_text

    sections: list[str] = []
    for heading in headings:
        pattern = re.compile(
            rf"(^## {re.escape(heading)}\n)(.*?)(?=^## |\Z)",
            re.MULTILINE | re.DOTALL,
        )
        match = pattern.search(skill_text)
        if match is None:
            continue
        sections.append(f"{match.group(1)}{match.group(2).strip()}\n")
    return "\n".join(sections) if sections else skill_text


def validate_tool_descriptions(
    tool_schemas: list[dict[str, object]],
    *,
    max_chars: int = MAX_TOOL_DESCRIPTION_CHARS,
    profile: str = "default",
) -> list[str]:
    findings: list[str] = []
    by_name: dict[str, dict[str, object]] = {}
    for schema in tool_schemas:
        name = str(schema.get("name") or "<unknown>")
        description = str(schema.get("description") or "")
        if name in by_name:
            findings.append(f"Duplicate tool schema name '{name}'.")
        by_name[name] = schema
        if not description.strip():
            findings.append(f"Tool description '{name}' must not be empty.")
        if len(description) > max_chars:
            findings.append(
                f"Tool description '{name}' exceeds {max_chars} chars ({len(description)})."
            )
    for required_name in sorted(_TOOL_DESCRIPTION_PROFILE_REQUIRED_NAMES.get(profile, set())):
        if required_name not in by_name:
            findings.append(f"Tool description profile '{profile}' requires '{required_name}'.")
    return findings


def validate_candidate_path(candidate_path: Path | None) -> list[str]:
    if candidate_path is None:
        return []
    if not candidate_path.exists():
        return [f"Candidate path does not exist: {candidate_path}"]
    if not candidate_path.is_file():
        return [f"Candidate path must be a file: {candidate_path}"]
    return []


def validate_dataset_coverage(
    cases: list[dict[str, object]],
    dataset_paths: Iterable[Path],
    *,
    allow_empty: bool = False,
) -> list[str]:
    dataset_list = list(dataset_paths)
    findings: list[str] = []
    if not dataset_list:
        findings.append("At least one dataset path is required.")
    elif not cases and not allow_empty:
        names = ", ".join(path.name for path in dataset_list)
        findings.append(f"No eval cases were loaded from dataset selection: {names}.")
    return findings


def validate_candidate_bundle_paths(
    *,
    target_names: Iterable[str],
    candidate_relative_paths: Mapping[str, str],
    extra_relative_paths: Iterable[str],
) -> list[str]:
    findings: list[str] = []
    selected_targets = tuple(target_names)
    if not selected_targets:
        return ["At least one target is required for candidate bundle validation."]

    allowed_relative_paths: set[str] = set()
    immutable_relative_paths = {_repo_relative(path) for path in ALL_IMMUTABLE_ARTIFACTS}

    for target_name in selected_targets:
        target = get_target(target_name)
        allowed_relative_paths.add(target.baseline_relative_path)
        immutable_relative_paths.update(
            _repo_relative(path) for path in target.immutable_dependencies
        )

    for target_name, relative_path in candidate_relative_paths.items():
        if relative_path not in allowed_relative_paths:
            findings.append(
                "Candidate for target "
                f"'{target_name}' resolves to disallowed path '{relative_path}'."
            )
        if (
            relative_path in immutable_relative_paths
            and relative_path not in allowed_relative_paths
        ):
            findings.append(f"Immutable artifact cannot be optimized: {relative_path}")

    for relative_path in extra_relative_paths:
        if relative_path in immutable_relative_paths:
            findings.append(f"Immutable artifact cannot be optimized: {relative_path}")
        else:
            findings.append(f"Candidate bundle includes unsupported artifact: {relative_path}")
    return findings
