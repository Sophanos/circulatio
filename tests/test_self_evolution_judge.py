from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.abspath("src"))
sys.path.insert(0, os.path.abspath("."))

from tests.self_evolution_helpers import FakeEvolutionLlmClient
from tools.self_evolution import evaluate_target
from tools.self_evolution.execution import ExecutionOptions
from tools.self_evolution.judge import JudgeOptions, pairwise_order


class SelfEvolutionJudgeTests(unittest.TestCase):
    def _dataset_path(self, name: str) -> Path:
        return (
            Path(__file__).resolve().parents[1]
            / "tests"
            / "evals"
            / "circulatio_method"
            / name
        )

    def test_judge_score_is_recorded_but_does_not_flip_pass_status(self) -> None:
        client = FakeEvolutionLlmClient(
            handler=lambda schema_name, messages, metadata: (
                {
                    "clarifyingQuestion": "Which image feels most alive to you right now?",
                    "methodGate": {"depthLevel": "personal_amplification_needed"},
                    "proposalCandidates": [],
                }
                if schema_name.startswith("circulatio_execution_")
                else {
                    "dimensions": {"restraint": 0.25, "pacing": 0.2},
                    "overallScore": 0.25,
                    "confidence": "medium",
                    "failureTags": ["overreach"],
                    "feedback": "The response still feels broader than necessary.",
                    "criticalConcerns": ["Tighten the pacing."],
                }
            )
        )
        report = evaluate_target(
            "prompt_fragments",
            dataset_paths=[self._dataset_path("execution_prompt_behavior.jsonl")],
            execution_options=ExecutionOptions(enabled=True, candidate_id="prompt_fragments_cand_0001"),
            judge_options=JudgeOptions(enabled=True, candidate_id="prompt_fragments_cand_0001"),
            llm_client=client,
        )
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["judgeCaseCount"], 1)
        self.assertEqual(report["judgeConcernCount"], 1)
        self.assertEqual(report["criticalJudgeConcernCount"], 1)
        self.assertGreater(report["judgeScorePercent"], 0.0)

    def test_pairwise_judge_uses_neutral_labels_and_baseline_outputs(self) -> None:
        client = FakeEvolutionLlmClient(
            handler=lambda schema_name, messages, metadata: (
                {
                    "clarifyingQuestion": "Which image feels most alive to you right now?",
                    "methodGate": {"depthLevel": "personal_amplification_needed"},
                    "proposalCandidates": [],
                }
                if schema_name.startswith("circulatio_execution_")
                else {
                    "dimensions": {"restraint": 0.9},
                    "overallScore": 0.9,
                    "confidence": "high",
                    "failureTags": [],
                    "feedback": "",
                    "criticalConcerns": [],
                }
            )
        )
        baseline_execution_outputs: dict[str, object] = {}
        evaluate_target(
            "prompt_fragments",
            dataset_paths=[self._dataset_path("execution_prompt_behavior.jsonl")],
            execution_options=ExecutionOptions(enabled=True),
            judge_options=JudgeOptions(enabled=False),
            llm_client=client,
            captured_execution_outputs=baseline_execution_outputs,
        )
        client.calls.clear()
        report = evaluate_target(
            "prompt_fragments",
            dataset_paths=[self._dataset_path("execution_prompt_behavior.jsonl")],
            execution_options=ExecutionOptions(enabled=True, candidate_id="prompt_fragments_cand_0001"),
            judge_options=JudgeOptions(
                enabled=True,
                mode="pairwise",
                candidate_id="prompt_fragments_cand_0001",
            ),
            llm_client=client,
            baseline_execution_outputs=baseline_execution_outputs,
        )
        judge_call = next(
            call for call in client.calls if call.schema_name == "circulatio_judge_prompt_fragments"
        )
        payload = json.loads(judge_call.messages[1]["content"])
        serialized_payload = json.dumps(payload, sort_keys=True)
        self.assertEqual(report["status"], "pass")
        self.assertEqual(set(payload["outputs"].keys()), {"responseA", "responseB"})
        self.assertIn(payload["targetResponseId"], {"responseA", "responseB"})
        self.assertNotIn('"baseline"', serialized_payload)
        self.assertNotIn('"candidate"', serialized_payload)

    def test_pairwise_judge_alternates_candidate_order(self) -> None:
        seen_orders: set[tuple[str, str]] = set()
        for index in range(1, 500):
            seen_orders.add(pairwise_order(f"pairwise_case_{index}"))
            if len(seen_orders) == 2:
                break
        self.assertEqual(
            seen_orders,
            {("baseline", "candidate"), ("candidate", "baseline")},
        )


if __name__ == "__main__":
    unittest.main()
