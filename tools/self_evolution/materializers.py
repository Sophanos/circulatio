from __future__ import annotations

import ast
import importlib.util
import re
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

from .constraints import (
    validate_prompt_fragments_module,
    validate_skill_size,
    validate_tool_descriptions,
)
from .targets import EvolutionTarget, get_target

_PROMPT_FRAGMENT_MUTABLE_CONSTANTS = {
    "ACTION_DYNAMICS_POLICY",
    "ANALYSIS_PACKET_BOUNDARY_POLICY",
    "ANALYSIS_PACKET_POLICY",
    "ANALYSIS_PACKET_PROVENANCE_POLICY",
    "ANALYSIS_PACKET_STYLE_POLICY",
    "CLARIFICATION_INTENT_POLICY",
    "CLARIFICATION_ROUTING_POLICY",
    "INTERPRETATION_APPROVAL_BOUNDARY",
    "INTERPRETATION_CONSENT_POLICY",
    "INTERPRETATION_EVIDENCE_POLICY",
    "INTERPRETATION_METHOD_POLICY",
    "INTERPRETATION_PROPOSAL_POLICY",
    "INTERPRETATION_REF_KEY_POLICY",
    "INTERPRETATION_RESPONSE_POLICY",
    "INTERPRETATION_SCHEMA_CONTRACT",
    "INTERPRETATION_SOURCE_POLICY",
    "INTERPRETATION_STYLE_POLICY",
    "LIVING_MYTH_CHAPTER_POLICY",
    "LIVING_MYTH_CONSENT_POLICY",
    "LIVING_MYTH_PROPOSAL_POLICY",
    "LIVING_MYTH_STYLE_POLICY",
    "METHOD_STATE_CLARITY_POLICY",
    "METHOD_STATE_CONSENT_POLICY",
    "METHOD_STATE_EXTRACTION_POLICY",
    "METHOD_STATE_STORAGE_POLICY",
    "PRACTICE_CONSENT_POLICY",
    "PRACTICE_DYNAMICS_POLICY",
    "PRACTICE_PACING_POLICY",
    "PRACTICE_STYLE_POLICY",
    "PROJECTION_HANDLING_POLICY",
    "RUNTIME_HINT_POLICY",
    "THRESHOLD_CONSENT_POLICY",
    "THRESHOLD_PROCESS_POLICY",
    "THRESHOLD_PROPOSAL_POLICY",
    "THRESHOLD_STYLE_POLICY",
    "TYPOLOGY_RESTRAINT_POLICY",
    "WITNESS_METHOD_POLICY",
}


@dataclass(frozen=True)
class MaterializedCandidate:
    candidate_id: str
    target_name: str
    candidate_path: Path
    relative_path: str
    rationale: str
    source_trace_ids: list[str]
    edit_summary: list[str]


class BaseMaterializer:
    def __init__(self, target: EvolutionTarget) -> None:
        self._target = target

    def materialize(
        self,
        *,
        candidate_id: str,
        proposal: dict[str, object],
        output_dir: Path,
    ) -> MaterializedCandidate:
        raise NotImplementedError

    def _candidate_path(self, output_dir: Path, *, candidate_id: str) -> Path:
        candidate_dir = output_dir / "candidates" / candidate_id
        candidate_dir.mkdir(parents=True, exist_ok=True)
        return candidate_dir / self._target.baseline_path.name

    def _load_module(self, path: Path, *, module_name: str) -> ModuleType:
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            raise ValueError(f"Unable to load Python module from {path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module


class PromptFragmentsMaterializer(BaseMaterializer):
    def materialize(
        self,
        *,
        candidate_id: str,
        proposal: dict[str, object],
        output_dir: Path,
    ) -> MaterializedCandidate:
        replacements = proposal.get("editSet") or {}
        constant_replacements = replacements.get("prompt_constant_replacements")
        if not isinstance(constant_replacements, list) or not constant_replacements:
            raise ValueError("Prompt-fragment candidate requires prompt_constant_replacements.")
        baseline_text = self._target.baseline_path.read_text()
        baseline_module = self._load_module(
            self._target.baseline_path,
            module_name="baseline_prompt_fragments_materializer",
        )
        updated_text = baseline_text
        summary: list[str] = []
        for entry in constant_replacements:
            if not isinstance(entry, dict):
                continue
            constant_name = str(entry.get("constantName") or "").strip()
            new_text = str(entry.get("newText") or "").strip()
            if not constant_name or not new_text:
                continue
            self._validate_constant_name(baseline_module, constant_name)
            updated_text = self._replace_assignment(updated_text, constant_name, new_text)
            summary.append(constant_name)
        candidate_path = self._candidate_path(output_dir, candidate_id=candidate_id)
        candidate_path.write_text(updated_text)
        module = self._load_module(candidate_path, module_name=f"candidate_{candidate_id}_prompt")
        findings = validate_prompt_fragments_module(module)
        if findings:
            raise ValueError("; ".join(findings))
        return MaterializedCandidate(
            candidate_id=candidate_id,
            target_name=self._target.name,
            candidate_path=candidate_path,
            relative_path=self._target.baseline_relative_path,
            rationale=str(proposal.get("rationale") or ""),
            source_trace_ids=[
                str(item) for item in proposal.get("sourceTraceIds", []) if str(item)
            ],
            edit_summary=summary,
        )

    def _validate_constant_name(self, baseline_module: ModuleType, constant_name: str) -> None:
        if constant_name not in _PROMPT_FRAGMENT_MUTABLE_CONSTANTS:
            raise ValueError(
                "Prompt fragment edits must stay inside the mutable instruction-block constants. "
                f"'{constant_name}' is outside the allowed mutation boundary."
            )
        if not isinstance(getattr(baseline_module, constant_name, None), str):
            raise ValueError(
                f"Prompt fragment constant '{constant_name}' is not a mutable string policy."
            )

    def _replace_assignment(self, source_text: str, constant_name: str, new_text: str) -> str:
        tree = ast.parse(source_text)
        lines = source_text.splitlines(keepends=True)
        for node in tree.body:
            if not isinstance(node, ast.Assign):
                continue
            if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
                continue
            if node.targets[0].id != constant_name:
                continue
            if node.end_lineno is None:
                raise ValueError(f"Unable to rewrite assignment for {constant_name}.")
            replacement = f"{constant_name} = {new_text!r}\n"
            return "".join(lines[: node.lineno - 1] + [replacement] + lines[node.end_lineno :])
        raise ValueError(f"Prompt fragment constant '{constant_name}' was not found.")


class SkillMaterializer(BaseMaterializer):
    def materialize(
        self,
        *,
        candidate_id: str,
        proposal: dict[str, object],
        output_dir: Path,
    ) -> MaterializedCandidate:
        replacements = proposal.get("editSet") or {}
        section_replacements = replacements.get("skill_section_replacements")
        if not isinstance(section_replacements, list) or not section_replacements:
            raise ValueError("Skill candidate requires skill_section_replacements.")
        text = self._target.baseline_path.read_text()
        summary: list[str] = []
        for entry in section_replacements:
            if not isinstance(entry, dict):
                continue
            heading = str(entry.get("heading") or "").strip()
            new_markdown = str(entry.get("newMarkdown") or "").rstrip()
            if not heading or not new_markdown:
                continue
            text = self._replace_section(text, heading, new_markdown)
            summary.append(heading)
        findings = validate_skill_size(text)
        if findings:
            raise ValueError("; ".join(findings))
        candidate_path = self._candidate_path(output_dir, candidate_id=candidate_id)
        candidate_path.write_text(text)
        return MaterializedCandidate(
            candidate_id=candidate_id,
            target_name=self._target.name,
            candidate_path=candidate_path,
            relative_path=self._target.baseline_relative_path,
            rationale=str(proposal.get("rationale") or ""),
            source_trace_ids=[
                str(item) for item in proposal.get("sourceTraceIds", []) if str(item)
            ],
            edit_summary=summary,
        )

    def _replace_section(self, text: str, heading: str, new_markdown: str) -> str:
        pattern = re.compile(
            rf"(^## {re.escape(heading)}\n)(.*?)(?=^## |\Z)",
            re.MULTILINE | re.DOTALL,
        )
        match = pattern.search(text)
        if match is None:
            raise ValueError(f"Skill section '{heading}' was not found.")
        replacement = f"{match.group(1)}{new_markdown.strip()}\n\n"
        return text[: match.start()] + replacement + text[match.end() :]


class ToolDescriptionMaterializer(BaseMaterializer):
    def materialize(
        self,
        *,
        candidate_id: str,
        proposal: dict[str, object],
        output_dir: Path,
    ) -> MaterializedCandidate:
        replacements = proposal.get("editSet") or {}
        description_replacements = replacements.get("tool_description_replacements")
        if not isinstance(description_replacements, list) or not description_replacements:
            raise ValueError("Tool-description candidate requires tool_description_replacements.")
        source_text = self._target.baseline_path.read_text()
        updated_text = source_text
        summary: list[str] = []
        for entry in description_replacements:
            if not isinstance(entry, dict):
                continue
            tool_name = str(entry.get("toolName") or "").strip()
            new_description = str(entry.get("newDescription") or "").strip()
            if not tool_name or not new_description:
                continue
            updated_text = self._replace_description(updated_text, tool_name, new_description)
            summary.append(tool_name)
        candidate_path = self._candidate_path(output_dir, candidate_id=candidate_id)
        candidate_path.write_text(updated_text)
        module = self._load_module(candidate_path, module_name=f"candidate_{candidate_id}_schemas")
        tool_schemas = list(getattr(module, "TOOL_SCHEMAS", []))
        findings = validate_tool_descriptions(tool_schemas, profile=self._target.constraint_profile)
        if findings:
            raise ValueError("; ".join(findings))
        return MaterializedCandidate(
            candidate_id=candidate_id,
            target_name=self._target.name,
            candidate_path=candidate_path,
            relative_path=self._target.baseline_relative_path,
            rationale=str(proposal.get("rationale") or ""),
            source_trace_ids=[
                str(item) for item in proposal.get("sourceTraceIds", []) if str(item)
            ],
            edit_summary=summary,
        )

    def _replace_description(self, source_text: str, tool_name: str, new_description: str) -> str:
        tree = ast.parse(source_text)
        lines = source_text.splitlines(keepends=True)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Name) or node.func.id != "_schema":
                continue
            if len(node.args) < 2:
                continue
            name_arg = node.args[0]
            description_arg = node.args[1]
            if not isinstance(name_arg, ast.Constant) or name_arg.value != tool_name:
                continue
            if description_arg.end_lineno is None or description_arg.lineno is None:
                raise ValueError(f"Unable to rewrite description for {tool_name}.")
            indent = " " * description_arg.col_offset
            replacement = f"{indent}{new_description!r},\n"
            return "".join(
                lines[: description_arg.lineno - 1]
                + [replacement]
                + lines[description_arg.end_lineno :]
            )
        raise ValueError(f"Tool description '{tool_name}' was not found.")


class MaterializerRegistry:
    def __init__(self) -> None:
        self._materializers = {
            "prompt_fragments": PromptFragmentsMaterializer(get_target("prompt_fragments")),
            "skill": SkillMaterializer(get_target("skill")),
            "tool_descriptions": ToolDescriptionMaterializer(get_target("tool_descriptions")),
        }

    def for_target(self, target_name: str) -> BaseMaterializer:
        try:
            return self._materializers[target_name]
        except KeyError as exc:
            raise ValueError(f"No materializer registered for target '{target_name}'.") from exc


def materializer_for_target(target_name: str) -> BaseMaterializer:
    return MaterializerRegistry().for_target(target_name)
