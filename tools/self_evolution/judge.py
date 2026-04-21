from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from .dataset_builder import case_judge_config
from .execution import ExecutionCaseOutput
from .fitness import CaseResult, build_advisory_case_result
from .llm_client import EvolutionLlmClient
from .targets import EvolutionTarget
from .traces import JsonlTraceSink

DEFAULT_RUBRICS = {
    "prompt_fragments": [
        "next-question specificity",
        "symbolic restraint",
        "consent and method-gate respect",
        "grounding and pacing",
        "evidence provenance",
        "schema usefulness",
    ],
    "skill": [
        "correct tool routing",
        "store-first behavior",
        "lookup-before-repeat behavior",
        "fallback-stop behavior",
        "host non-interpretation",
        "collaborative facilitation",
    ],
    "tool_descriptions": [
        "correct tool choice",
        "description factuality",
        "boundary clarity",
        "non-overlapping routing",
        "concision",
    ],
}

JUDGE_RESULT_SCHEMA = {
    "type": "object",
    "properties": {
        "dimensions": {"type": "object"},
        "overallScore": {"type": "number"},
        "confidence": {"type": "string"},
        "failureTags": {"type": "array", "items": {"type": "string"}},
        "feedback": {"type": "string"},
        "criticalConcerns": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["dimensions", "overallScore", "confidence", "feedback"],
}


@dataclass(frozen=True)
class JudgeOptions:
    enabled: bool = False
    temperature: float = 0.0
    max_tokens: int = 900
    timeout_seconds: float | None = None
    mode: str | None = None
    candidate_id: str | None = None


@dataclass(frozen=True)
class JudgeResult:
    case_id: str
    overall_score: float
    confidence: str
    feedback: str
    critical_concerns: list[str]
    failure_tags: list[str]
    dimensions: dict[str, float]
    trace_id: str | None = None


async def run_judge_cases(
    *,
    target: EvolutionTarget,
    execution_outputs: dict[str, ExecutionCaseOutput],
    llm_client: EvolutionLlmClient,
    options: JudgeOptions,
    trace_sink: JsonlTraceSink | None = None,
    baseline_outputs: dict[str, ExecutionCaseOutput] | None = None,
) -> tuple[list[CaseResult], dict[str, JudgeResult]]:
    case_results: list[CaseResult] = []
    judge_results: dict[str, JudgeResult] = {}
    for case_id, execution_output in execution_outputs.items():
        judge_config = case_judge_config(execution_output.case) or {}
        mode = str(
            options.mode
            if options.mode is not None
            else judge_config.get("mode") or "absolute"
        )
        rubric = [str(item) for item in judge_config.get("rubric", []) if str(item)]
        if not rubric:
            rubric = list(DEFAULT_RUBRICS[target.kind])
        baseline_output = (baseline_outputs or {}).get(case_id)
        messages = _judge_messages(
            target=target,
            case=execution_output.case,
            execution_output=execution_output,
            baseline_output=baseline_output,
            rubric=rubric,
            mode=mode,
        )
        response = await llm_client.complete_json(
            messages=messages,
            schema=JUDGE_RESULT_SCHEMA,
            schema_name=f"circulatio_judge_{target.name}",
            max_tokens=int(judge_config.get("maxTokens") or options.max_tokens),
            temperature=options.temperature,
            timeout_seconds=options.timeout_seconds,
            metadata={"target": target.name, "caseId": case_id, "mode": mode},
        )
        payload = response.payload
        trace_id = None
        if trace_sink is not None:
            trace_id = trace_sink.record(
                "judge_trace",
                {
                    "candidateId": options.candidate_id,
                    "target": target.name,
                    "caseId": case_id,
                    "mode": mode,
                    "parsedOutput": payload,
                    "rawText": response.raw_text,
                },
            )
        result = JudgeResult(
            case_id=case_id,
            overall_score=float(payload.get("overallScore") or 0.0),
            confidence=str(payload.get("confidence") or "low"),
            feedback=str(payload.get("feedback") or ""),
            critical_concerns=[
                str(item) for item in payload.get("criticalConcerns", []) if str(item)
            ],
            failure_tags=[str(item) for item in payload.get("failureTags", []) if str(item)],
            dimensions={
                str(key): float(value)
                for key, value in dict(payload.get("dimensions") or {}).items()
                if isinstance(value, (int, float))
            },
            trace_id=trace_id,
        )
        judge_results[case_id] = result
        findings = []
        if result.feedback:
            findings.append(result.feedback)
        findings.extend(result.critical_concerns)
        case_results.append(
            build_advisory_case_result(
                execution_output.case,
                score=int(round(result.overall_score * 100)),
                max_score=100,
                findings=findings,
                candidate_id=options.candidate_id,
                trace_id=trace_id,
                signals={
                    "confidence": result.confidence,
                    "criticalConcerns": list(result.critical_concerns),
                    "failureTags": list(result.failure_tags),
                    "dimensions": dict(result.dimensions),
                    "mode": mode,
                },
            )
        )
    return case_results, judge_results



def pairwise_order(case_id: str) -> tuple[str, str]:
    digest = hashlib.sha256(case_id.encode("utf-8")).hexdigest()
    return ("baseline", "candidate") if int(digest[:2], 16) % 2 == 0 else ("candidate", "baseline")



def _judge_messages(
    *,
    target: EvolutionTarget,
    case: dict[str, object],
    execution_output: ExecutionCaseOutput,
    baseline_output: ExecutionCaseOutput | None,
    rubric: list[str],
    mode: str,
) -> list[dict[str, str]]:
    system = (
        "You are an advisory judge for Circulatio Evolution OS. Return JSON only. "
        "Judge qualitative behavior, but do not override deterministic safety gates."
    )
    payload: dict[str, object] = {
        "target": target.name,
        "caseId": case.get("caseId"),
        "rubric": rubric,
        "mode": mode,
    }
    if mode == "pairwise" and baseline_output is not None:
        first, second = pairwise_order(str(case.get("caseId") or ""))
        response_a = baseline_output.payload if first == "baseline" else execution_output.payload
        response_b = execution_output.payload if second == "candidate" else baseline_output.payload
        payload["outputs"] = {
            "responseA": response_a,
            "responseB": response_b,
        }
        payload["targetResponseId"] = "responseA" if first == "candidate" else "responseB"
        payload["comparisonPolicy"] = (
            "Score only targetResponseId while using the other response as blinded comparison "
            "context. Do not infer provenance or preference from either neutral label."
        )
    else:
        payload["output"] = execution_output.payload
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(payload, indent=2, sort_keys=True)},
    ]
