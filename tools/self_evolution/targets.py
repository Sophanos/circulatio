from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
DOCS_ROOT = REPO_ROOT / "docs"
EVAL_DATASETS_ROOT = REPO_ROOT / "tests" / "evals" / "circulatio_method"

REVIEW_ONLY_REFERENCE_ARTIFACTS = (
    DOCS_ROOT / "RUNBOOK.md",
    DOCS_ROOT / "ENGINEERING_GUIDE.md",
    DOCS_ROOT / "INTERPRETATION_ENGINE_SPEC.md",
)

IMMUTABLE_GUARDRAIL_ARTIFACTS = (
    SRC_ROOT / "circulatio" / "application" / "circulatio_service.py",
    SRC_ROOT / "circulatio" / "core" / "interpretation_mapping.py",
    SRC_ROOT / "circulatio" / "core" / "method_state_policy.py",
    SRC_ROOT / "circulatio" / "core" / "safety_gate.py",
    SRC_ROOT / "circulatio" / "llm" / "json_schema.py",
)

ALL_IMMUTABLE_ARTIFACTS = IMMUTABLE_GUARDRAIL_ARTIFACTS + REVIEW_ONLY_REFERENCE_ARTIFACTS


@dataclass(frozen=True)
class EvolutionTarget:
    name: str
    kind: str
    baseline_path: Path
    dataset_paths: tuple[Path, ...]
    description: str
    mutation_scope: str
    mutable_sections: tuple[str, ...]
    immutable_dependencies: tuple[Path, ...]
    constraint_profile: str
    owner: str

    @property
    def baseline_relative_path(self) -> str:
        return str(self.baseline_path.relative_to(REPO_ROOT))


TARGETS = {
    "prompt_fragments": EvolutionTarget(
        name="prompt_fragments",
        kind="prompt_fragments",
        baseline_path=REPO_ROOT / "src" / "circulatio" / "llm" / "prompt_fragments.py",
        dataset_paths=(
            EVAL_DATASETS_ROOT / "clarification_routing.jsonl",
            EVAL_DATASETS_ROOT / "projection_restraint.jsonl",
            EVAL_DATASETS_ROOT / "grounding_pacing.jsonl",
            EVAL_DATASETS_ROOT / "typology_restraint.jsonl",
            EVAL_DATASETS_ROOT / "memory_write_boundary.jsonl",
            EVAL_DATASETS_ROOT / "adaptation_precedence.jsonl",
            EVAL_DATASETS_ROOT / "consent_boundary.jsonl",
            EVAL_DATASETS_ROOT / "evidence_integrity.jsonl",
            EVAL_DATASETS_ROOT / "review_packet_boundaries.jsonl",
            EVAL_DATASETS_ROOT / "safety_grounding_boundary.jsonl",
            EVAL_DATASETS_ROOT / "execution_prompt_behavior.jsonl",
        ),
        description=(
            "Evaluate prompt-policy fragments used by Circulatio prompt_builder across "
            "clarification, restraint, pacing, consent, evidence, and approval-boundary rules."
        ),
        mutation_scope="text_policy",
        mutable_sections=(
            "interpretation_instruction_block",
            "practice_instruction_block",
            "threshold_review_instruction_block",
            "living_myth_instruction_block",
            "method_state_routing_instruction_block",
            "analysis_packet_instruction_block",
        ),
        immutable_dependencies=ALL_IMMUTABLE_ARTIFACTS,
        constraint_profile="prompt_policy",
        owner="circulatio",
    ),
    "skill": EvolutionTarget(
        name="skill",
        kind="skill",
        baseline_path=(
            REPO_ROOT / "src" / "circulatio_hermes_plugin" / "skills" / "circulation" / "SKILL.md"
        ),
        dataset_paths=(
            EVAL_DATASETS_ROOT / "skill_routing.jsonl",
            EVAL_DATASETS_ROOT / "hermes_hold_first_routing.jsonl",
            EVAL_DATASETS_ROOT / "execution_skill_routing.jsonl",
        ),
        description=(
            "Evaluate the Hermes Circulatio skill for hold-first routing, collaborative "
            "interpretation, lookup-before-repeat, and explicit feedback handling."
        ),
        mutation_scope="host_skill",
        mutable_sections=(
            "Routing",
            "Host Tone",
            "Collaborative Interpretation",
            "Guardrails",
        ),
        immutable_dependencies=ALL_IMMUTABLE_ARTIFACTS,
        constraint_profile="host_skill",
        owner="hermes_contract",
    ),
    "tool_descriptions": EvolutionTarget(
        name="tool_descriptions",
        kind="tool_descriptions",
        baseline_path=REPO_ROOT / "src" / "circulatio_hermes_plugin" / "schemas.py",
        dataset_paths=(
            EVAL_DATASETS_ROOT / "tool_description_routing.jsonl",
            EVAL_DATASETS_ROOT / "method_state_connector.jsonl",
            EVAL_DATASETS_ROOT / "execution_tool_choice.jsonl",
        ),
        description=(
            "Evaluate Circulatio tool descriptions for routing clarity, read-only boundaries, "
            "and contract-safe wording."
        ),
        mutation_scope="tool_description",
        mutable_sections=(
            "description",
            "non-breaking schema metadata",
        ),
        immutable_dependencies=ALL_IMMUTABLE_ARTIFACTS,
        constraint_profile="tool_description_routing",
        owner="hermes_contract",
    ),
}

DEFAULT_TARGET_ORDER = tuple(TARGETS.keys())


def get_target(name: str) -> EvolutionTarget:
    try:
        return TARGETS[name]
    except KeyError as exc:
        known = ", ".join(sorted(TARGETS))
        raise ValueError(f"Unknown self-evolution target '{name}'. Known targets: {known}") from exc
