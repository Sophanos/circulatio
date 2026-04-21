from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field

from .llm_client import EvolutionLlmClient
from .targets import EvolutionTarget
from .traces import JsonlTraceSink

METHOD_PRIORITIES = [
    "ask the right next question",
    "avoid over-interpretation",
    "respect consent gates",
    "choose the right tool",
    "pace depth better",
    "preserve evidence boundaries",
    "preserve fallback-stop behavior",
]


@dataclass(frozen=True)
class GenerationContext:
    target_name: str
    baseline_text: str
    mutable_sections: tuple[str, ...]
    immutable_dependencies_summary: list[str]
    deterministic_failures: list[str] = field(default_factory=list)
    execution_trace_summaries: list[str] = field(default_factory=list)
    judge_feedback_summaries: list[str] = field(default_factory=list)
    previous_candidate_summaries: list[str] = field(default_factory=list)
    hard_constraints: list[str] = field(default_factory=list)
    method_priorities: list[str] = field(default_factory=lambda: list(METHOD_PRIORITIES))


@dataclass(frozen=True)
class CandidateProposal:
    candidate_id: str
    target_name: str
    edit_set: dict[str, object]
    rationale: str
    expected_behavior_impact: list[str]
    risk_notes: list[str]
    source_trace_ids: list[str]
    preserved_guardrails: list[str]
    rejected_alternatives: list[str]

    def as_dict(self) -> dict[str, object]:
        return {
            "candidateId": self.candidate_id,
            "targetName": self.target_name,
            "editSet": self.edit_set,
            "rationale": self.rationale,
            "expectedBehaviorImpact": list(self.expected_behavior_impact),
            "riskNotes": list(self.risk_notes),
            "sourceTraceIds": list(self.source_trace_ids),
            "preservedGuardrails": list(self.preserved_guardrails),
            "rejectedAlternatives": list(self.rejected_alternatives),
        }


class ReflectionGenerationEngine:
    def __init__(
        self,
        llm_client: EvolutionLlmClient,
        *,
        trace_sink: JsonlTraceSink | None = None,
        temperature: float = 0.2,
        max_tokens: int = 2200,
        timeout_seconds: float | None = None,
    ) -> None:
        self._llm_client = llm_client
        self._trace_sink = trace_sink
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._timeout_seconds = timeout_seconds

    async def generate_candidates(
        self,
        *,
        target: EvolutionTarget,
        context: GenerationContext,
        max_candidates: int,
        candidate_offset: int = 0,
    ) -> list[CandidateProposal]:
        schema = _proposal_schema(target.kind)
        response = await self._llm_client.complete_json(
            messages=self._messages(target=target, context=context, max_candidates=max_candidates),
            schema=schema,
            schema_name=f"circulatio_evolution_generation_{target.name}",
            max_tokens=self._max_tokens,
            temperature=self._temperature,
            timeout_seconds=self._timeout_seconds,
            metadata={
                "target": target.name,
                "maxCandidates": max_candidates,
                "candidateOffset": candidate_offset,
            },
        )
        proposals = _normalize_candidate_payload(
            target_name=target.name,
            target_kind=target.kind,
            payload=response.payload,
            candidate_offset=candidate_offset,
        )
        if self._trace_sink is not None:
            self._trace_sink.record(
                "generation_trace",
                {
                    "target": target.name,
                    "candidateIds": [proposal.candidate_id for proposal in proposals],
                    "contextSummary": {
                        "mutableSections": list(context.mutable_sections),
                        "deterministicFailures": list(context.deterministic_failures),
                        "executionTraceSummaries": list(context.execution_trace_summaries),
                        "judgeFeedbackSummaries": list(context.judge_feedback_summaries),
                    },
                    "parsedOutput": response.payload,
                    "rawText": response.raw_text,
                },
            )
        return proposals

    def _messages(
        self,
        *,
        target: EvolutionTarget,
        context: GenerationContext,
        max_candidates: int,
    ) -> list[dict[str, str]]:
        system = (
            "You generate offline Circulatio Evolution OS candidate edits. Return JSON only. "
            "Preserve immutable boundaries, never add runtime mutation APIs, and only "
            "propose edits inside the target's mutable sections."
        )
        user = json.dumps(
            {
                "target": {
                    "name": target.name,
                    "kind": target.kind,
                    "description": target.description,
                    "mutationScope": target.mutation_scope,
                    "mutableSections": list(target.mutable_sections),
                },
                "generationContext": asdict(context),
                "maxCandidates": max_candidates,
            },
            indent=2,
            sort_keys=True,
        )
        return [{"role": "system", "content": system}, {"role": "user", "content": user}]



def _proposal_schema(target_kind: str) -> dict[str, object]:
    edit_field = {
        "prompt_fragments": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "constantName": {"type": "string"},
                    "newText": {"type": "string"},
                    "reason": {"type": "string"},
                },
                "required": ["constantName", "newText", "reason"],
            },
        },
        "skill": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "heading": {"type": "string"},
                    "newMarkdown": {"type": "string"},
                    "reason": {"type": "string"},
                },
                "required": ["heading", "newMarkdown", "reason"],
            },
        },
        "tool_descriptions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "toolName": {"type": "string"},
                    "newDescription": {"type": "string"},
                    "reason": {"type": "string"},
                },
                "required": ["toolName", "newDescription", "reason"],
            },
        },
    }[target_kind]
    edit_key = {
        "prompt_fragments": "prompt_constant_replacements",
        "skill": "skill_section_replacements",
        "tool_descriptions": "tool_description_replacements",
    }[target_kind]
    return {
        "type": "object",
        "properties": {
            "candidates": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "editSet": {
                            "type": "object",
                            "properties": {edit_key: edit_field},
                            "required": [edit_key],
                        },
                        "rationale": {"type": "string"},
                        "expectedBehaviorImpact": {"type": "array", "items": {"type": "string"}},
                        "riskNotes": {"type": "array", "items": {"type": "string"}},
                        "sourceTraceIds": {"type": "array", "items": {"type": "string"}},
                        "preservedGuardrails": {"type": "array", "items": {"type": "string"}},
                        "rejectedAlternatives": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["editSet", "rationale"],
                },
            }
        },
        "required": ["candidates"],
    }



def _normalize_candidate_payload(
    *,
    target_name: str,
    target_kind: str,
    payload: dict[str, object],
    candidate_offset: int,
) -> list[CandidateProposal]:
    raw_candidates = payload.get("candidates")
    if not isinstance(raw_candidates, list):
        return []
    normalized: list[CandidateProposal] = []
    for index, item in enumerate(raw_candidates, start=1):
        if not isinstance(item, dict):
            continue
        edit_set = item.get("editSet")
        if not isinstance(edit_set, dict):
            continue
        candidate_number = candidate_offset + index
        normalized.append(
            CandidateProposal(
                candidate_id=f"{target_name}_cand_{candidate_number:04d}",
                target_name=target_name,
                edit_set={str(key): value for key, value in edit_set.items()},
                rationale=str(item.get("rationale") or "").strip(),
                expected_behavior_impact=[
                    str(value) for value in item.get("expectedBehaviorImpact", []) if str(value)
                ],
                risk_notes=[str(value) for value in item.get("riskNotes", []) if str(value)],
                source_trace_ids=[
                    str(value) for value in item.get("sourceTraceIds", []) if str(value)
                ],
                preserved_guardrails=[
                    str(value) for value in item.get("preservedGuardrails", []) if str(value)
                ],
                rejected_alternatives=[
                    str(value) for value in item.get("rejectedAlternatives", []) if str(value)
                ],
            )
        )
    return normalized
