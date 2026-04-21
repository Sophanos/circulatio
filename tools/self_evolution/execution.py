from __future__ import annotations

import importlib.util
import json
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

from circulatio.llm import prompt_builder
from circulatio.llm.json_schema import (
    ANALYSIS_PACKET_OUTPUT_SCHEMA,
    INTERPRETATION_OUTPUT_SCHEMA,
    LIVING_MYTH_REVIEW_OUTPUT_SCHEMA,
    METHOD_STATE_ROUTING_OUTPUT_SCHEMA,
    PRACTICE_OUTPUT_SCHEMA,
    RHYTHMIC_BRIEF_OUTPUT_SCHEMA,
    THRESHOLD_REVIEW_OUTPUT_SCHEMA,
    WEEKLY_REVIEW_OUTPUT_SCHEMA,
)
from circulatio_hermes_plugin import schemas as plugin_schemas

from .dataset_builder import case_execution_config
from .fitness import CaseResult, evaluate_execution_output_case
from .llm_client import EvolutionLlmClient
from .targets import EvolutionTarget
from .traces import JsonlTraceSink, summarize_trace_findings

PROMPT_OUTPUT_SCHEMAS = {
    "analysis_packet": ANALYSIS_PACKET_OUTPUT_SCHEMA,
    "interpretation": INTERPRETATION_OUTPUT_SCHEMA,
    "living_myth_review": LIVING_MYTH_REVIEW_OUTPUT_SCHEMA,
    "method_state_routing": METHOD_STATE_ROUTING_OUTPUT_SCHEMA,
    "practice": PRACTICE_OUTPUT_SCHEMA,
    "rhythmic_brief": RHYTHMIC_BRIEF_OUTPUT_SCHEMA,
    "threshold_review": THRESHOLD_REVIEW_OUTPUT_SCHEMA,
    "weekly_review": WEEKLY_REVIEW_OUTPUT_SCHEMA,
}

ROUTING_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "selectedTool": {"type": "string"},
        "toolArgsSummary": {"type": "object"},
        "argumentPlan": {"type": "object"},
        "askedClarification": {"type": "boolean"},
        "performedHostInterpretation": {"type": "boolean"},
        "stoppedOnFallback": {"type": "boolean"},
        "hostReply": {"type": "string"},
        "confidence": {"type": "number"},
        "rationale": {"type": "string"},
    },
    "required": ["selectedTool", "hostReply", "rationale"],
}


@dataclass(frozen=True)
class ExecutionOptions:
    enabled: bool = False
    temperature: float = 0.2
    max_tokens: int = 1600
    timeout_seconds: float | None = None
    candidate_id: str | None = None
    stage_name: str = "deterministic"


@dataclass(frozen=True)
class ExecutionCaseOutput:
    case: dict[str, object]
    payload: dict[str, object]
    trace_id: str | None


async def run_execution_cases(
    *,
    target: EvolutionTarget,
    candidate_path: Path | None,
    cases: list[dict[str, object]],
    llm_client: EvolutionLlmClient,
    options: ExecutionOptions,
    trace_sink: JsonlTraceSink | None = None,
) -> tuple[list[CaseResult], dict[str, ExecutionCaseOutput]]:
    results: list[CaseResult] = []
    outputs: dict[str, ExecutionCaseOutput] = {}
    prompt_fragments_module = (
        _load_python_module(candidate_path, module_name="execution_prompt_fragments")
        if target.kind == "prompt_fragments" and candidate_path is not None
        else None
    )
    tool_schemas = (
        list(
            getattr(
                _load_python_module(candidate_path, module_name="execution_schemas"),
                "TOOL_SCHEMAS",
                [],
            )
        )
        if target.kind == "tool_descriptions" and candidate_path is not None
        else list(plugin_schemas.TOOL_SCHEMAS)
    )
    skill_text = (
        candidate_path.read_text()
        if target.kind == "skill" and candidate_path is not None
        else None
    )

    for case in cases:
        execution_config = case_execution_config(case) or {}
        payload = await _execute_case(
            target=target,
            case=case,
            execution_config=execution_config,
            llm_client=llm_client,
            options=options,
            prompt_fragments_module=prompt_fragments_module,
            skill_text=skill_text,
            tool_schemas=tool_schemas,
        )
        trace_id = None
        if trace_sink is not None:
            trace_id = trace_sink.record(
                "execution_trace",
                {
                    "candidateId": options.candidate_id,
                    "target": target.name,
                    "caseId": case.get("caseId"),
                    "split": case.get("split"),
                    "stage": options.stage_name,
                    "executionMode": execution_config.get("mode") or target.kind,
                    "inputSummary": {
                        "promptKind": case.get("promptKind"),
                        "toolName": case.get("toolName"),
                    },
                    "parsedOutput": payload,
                },
            )
        result = evaluate_execution_output_case(
            case,
            payload,
            candidate_id=options.candidate_id,
            trace_id=trace_id,
            signals={
                "mode": execution_config.get("mode") or target.kind,
                "outputKeys": sorted(payload.keys()),
            },
        )
        if trace_sink is not None and not result.passed:
            trace_sink.record(
                "candidate_event",
                {
                    "candidateId": options.candidate_id,
                    "target": target.name,
                    "caseId": case.get("caseId"),
                    "eventType": "execution_failure",
                    "failureTags": summarize_trace_findings(result.findings),
                },
            )
        results.append(result)
        outputs[str(case.get("caseId") or "")] = ExecutionCaseOutput(
            case=case,
            payload=payload,
            trace_id=trace_id,
        )
    return results, outputs


async def _execute_case(
    *,
    target: EvolutionTarget,
    case: dict[str, object],
    execution_config: dict[str, object],
    llm_client: EvolutionLlmClient,
    options: ExecutionOptions,
    prompt_fragments_module: ModuleType | None,
    skill_text: str | None,
    tool_schemas: list[dict[str, object]],
) -> dict[str, object]:
    if target.kind == "prompt_fragments":
        prompt_kind = str(case.get("promptKind") or "")
        input_data = case.get("input")
        if not isinstance(input_data, dict):
            raise ValueError(f"Execution case {case.get('caseId')} requires object input.")
        messages = _prompt_messages(prompt_kind, input_data, fragments=prompt_fragments_module)
        return (
            await llm_client.complete_json(
                messages=messages,
                schema=PROMPT_OUTPUT_SCHEMAS[prompt_kind],
                schema_name=f"circulatio_execution_{prompt_kind}",
                max_tokens=int(execution_config.get("maxTokens") or options.max_tokens),
                temperature=options.temperature,
                timeout_seconds=options.timeout_seconds,
                metadata={
                    "target": target.name,
                    "caseId": case.get("caseId"),
                    "mode": execution_config.get("mode") or "prompt_json",
                },
            )
        ).payload

    if target.kind == "skill":
        active_skill_text = skill_text or target.baseline_path.read_text()
        messages = _skill_routing_messages(case=case, skill_text=active_skill_text)
        return (
            await llm_client.complete_json(
                messages=messages,
                schema=ROUTING_OUTPUT_SCHEMA,
                schema_name="circulatio_execution_skill_routing",
                max_tokens=int(execution_config.get("maxTokens") or options.max_tokens),
                temperature=options.temperature,
                timeout_seconds=options.timeout_seconds,
                metadata={
                    "target": target.name,
                    "caseId": case.get("caseId"),
                    "mode": "skill_routing",
                },
            )
        ).payload

    if target.kind == "tool_descriptions":
        messages = _tool_choice_messages(case=case, tool_schemas=tool_schemas)
        return (
            await llm_client.complete_json(
                messages=messages,
                schema=ROUTING_OUTPUT_SCHEMA,
                schema_name="circulatio_execution_tool_choice",
                max_tokens=int(execution_config.get("maxTokens") or options.max_tokens),
                temperature=options.temperature,
                timeout_seconds=options.timeout_seconds,
                metadata={
                    "target": target.name,
                    "caseId": case.get("caseId"),
                    "mode": "tool_choice",
                },
            )
        ).payload

    raise ValueError(f"Unsupported execution target kind: {target.kind}")



def _prompt_messages(
    prompt_kind: str,
    input_data: dict[str, object],
    *,
    fragments: ModuleType | None,
) -> list[dict[str, str]]:
    if prompt_kind == "analysis_packet":
        return prompt_builder.build_analysis_packet_messages(input_data, fragments=fragments)
    if prompt_kind == "interpretation":
        return prompt_builder.build_interpretation_messages(input_data, fragments=fragments)
    if prompt_kind == "living_myth_review":
        return prompt_builder.build_living_myth_review_messages(input_data, fragments=fragments)
    if prompt_kind == "method_state_routing":
        return prompt_builder.build_method_state_routing_messages(input_data, fragments=fragments)
    if prompt_kind == "practice":
        return prompt_builder.build_practice_messages(input_data, fragments=fragments)
    if prompt_kind == "rhythmic_brief":
        return prompt_builder.build_rhythmic_brief_messages(input_data, fragments=fragments)
    if prompt_kind == "threshold_review":
        return prompt_builder.build_threshold_review_messages(input_data, fragments=fragments)
    if prompt_kind == "weekly_review":
        return prompt_builder.build_weekly_review_messages(input_data, fragments=fragments)
    raise ValueError(f"Unknown prompt execution kind: {prompt_kind}")



def _skill_routing_messages(*, case: dict[str, object], skill_text: str) -> list[dict[str, str]]:
    execution = case_execution_config(case) or {}
    payload = {
        "skillText": skill_text,
        "userTurn": execution.get("userTurn") or case.get("userTurn"),
        "availableTools": execution.get("availableTools") or [
            schema.get("name") for schema in plugin_schemas.TOOL_SCHEMAS
        ],
        "expectationHints": execution.get("expectationHints") or {},
    }
    system = (
        "You simulate Hermes reading the Circulatio skill and choosing the next tool action. "
        "Return JSON only. Select one tool, then state whether the reply asks an "
        "unnecessary clarification, performs host interpretation, or stops on fallback."
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(payload, indent=2, sort_keys=True)},
    ]



def _tool_choice_messages(
    *,
    case: dict[str, object],
    tool_schemas: list[dict[str, object]],
) -> list[dict[str, str]]:
    execution = case_execution_config(case) or {}
    payload = {
        "userTurn": execution.get("userTurn") or case.get("userTurn"),
        "toolSchemas": tool_schemas,
        "expectationHints": execution.get("expectationHints") or {},
    }
    system = (
        "You simulate Hermes choosing among Circulatio tools using only tool descriptions "
        "and parameter contracts. Return JSON only. Pick exactly one tool and summarize "
        "the intended arguments without inventing writes outside the tool boundary."
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(payload, indent=2, sort_keys=True)},
    ]



def _load_python_module(path: Path, *, module_name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ValueError(f"Unable to load Python module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
