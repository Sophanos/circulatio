from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.abspath("src"))
sys.path.insert(0, os.path.abspath("."))

from tests.self_evolution_helpers import FakeEvolutionLlmClient
from tools.self_evolution.dataset_builder import load_case_set
from tools.self_evolution.execution import ExecutionOptions, run_execution_cases
from tools.self_evolution.targets import get_target
from tools.self_evolution.traces import JsonlTraceSink


class SelfEvolutionExecutionTests(unittest.TestCase):
    def _dataset_path(self, name: str) -> Path:
        return Path(__file__).resolve().parents[1] / "tests" / "evals" / "circulatio_method" / name

    def test_prompt_execution_harness_records_sanitized_trace(self) -> None:
        cases = load_case_set([self._dataset_path("execution_prompt_behavior.jsonl")])
        client = FakeEvolutionLlmClient(
            handler=lambda schema_name, messages, metadata: {
                "clarifyingQuestion": "Which image feels most alive to you right now?",
                "methodGate": {"depthLevel": "personal_amplification_needed"},
                "proposalCandidates": [],
            }
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            sink = JsonlTraceSink(Path(tmp_dir))
            results, outputs = asyncio.run(
                run_execution_cases(
                    target=get_target("prompt_fragments"),
                    candidate_path=None,
                    cases=cases,
                    llm_client=client,
                    options=ExecutionOptions(
                        enabled=True,
                        candidate_id="prompt_fragments_cand_0001",
                        stage_name="test",
                    ),
                    trace_sink=sink,
                )
            )
            trace_text = (Path(tmp_dir) / "sanitized_traces.jsonl").read_text()
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].passed)
        self.assertIn("execution_interpretation_next_question_001", outputs)
        self.assertIn('"outputSummary"', trace_text)
        self.assertIn('"prompt_fragments_cand_0001"', trace_text)

    def test_skill_routing_harness_scores_store_first_case(self) -> None:
        cases = load_case_set([self._dataset_path("execution_skill_routing.jsonl")])
        client = FakeEvolutionLlmClient(
            responses={
                "circulatio_execution_skill_routing": {
                    "selectedTool": "circulatio_store_dream",
                    "toolArgsSummary": {"materialType": "dream"},
                    "askedClarification": False,
                    "performedHostInterpretation": False,
                    "stoppedOnFallback": False,
                    "hostReply": "I stored the dream.",
                    "rationale": "Store-first routing applies.",
                }
            }
        )
        results, _ = asyncio.run(
            run_execution_cases(
                target=get_target("skill"),
                candidate_path=None,
                cases=cases,
                llm_client=client,
                options=ExecutionOptions(enabled=True),
            )
        )
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].passed)

    def test_tool_choice_harness_uses_full_schema_set(self) -> None:
        cases = load_case_set([self._dataset_path("execution_tool_choice.jsonl")])
        client = FakeEvolutionLlmClient(
            responses={
                "circulatio_execution_tool_choice": {
                    "selectedTool": "circulatio_record_interpretation_feedback",
                    "argumentPlan": {"runId": "run_123", "feedback": "rejected"},
                    "hostReply": "I can record that feedback directly.",
                    "rationale": "This is explicit interpretation feedback, not a new reflection.",
                }
            }
        )
        results, _ = asyncio.run(
            run_execution_cases(
                target=get_target("tool_descriptions"),
                candidate_path=None,
                cases=cases,
                llm_client=client,
                options=ExecutionOptions(enabled=True),
            )
        )
        payload = json.loads(client.calls[0].messages[1]["content"])
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].passed)
        self.assertGreater(len(payload["toolSchemas"]), 10)


if __name__ == "__main__":
    unittest.main()
