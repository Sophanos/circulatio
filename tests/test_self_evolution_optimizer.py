from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.abspath("src"))
sys.path.insert(0, os.path.abspath("."))

from circulatio.llm import prompt_fragments
from tests.self_evolution_helpers import FakeEvolutionLlmClient
from tools.self_evolution import (
    EvolutionGenerationConfig,
    ExecutionOptions,
    JudgeOptions,
    evolve_candidates,
)


class SelfEvolutionOptimizerTests(unittest.TestCase):
    def _automatic_client(
        self,
        *,
        broken: bool = False,
        multi_candidate: bool = False,
    ) -> FakeEvolutionLlmClient:
        def handler(
            schema_name: str,
            messages: list[dict[str, str]],
            metadata: dict[str, object],
        ) -> dict[str, object]:
            if schema_name == "circulatio_evolution_generation_prompt_fragments":
                if broken:
                    return {
                        "candidates": [
                            {
                                "editSet": {
                                    "prompt_constant_replacements": [
                                        {
                                            "constantName": "CLARIFICATION_ROUTING_POLICY",
                                            "newText": (
                                                "When you ask a clarifyingQuestion, answer_only is "
                                                "acceptable even when no durable typed routing is available."
                                            ),
                                            "reason": "Intentionally broken for regression coverage.",
                                        }
                                    ]
                                },
                                "rationale": "Break the clarification-routing contract.",
                            }
                        ]
                    }
                if multi_candidate:
                    return {
                        "candidates": [
                            {
                                "editSet": {
                                    "prompt_constant_replacements": [
                                        {
                                            "constantName": "RUNTIME_HINT_POLICY",
                                            "newText": (
                                                f"{prompt_fragments.RUNTIME_HINT_POLICY} "
                                                "Keep the runtime hint explicit."
                                            ),
                                            "reason": "Shorter safe refinement.",
                                        }
                                    ]
                                },
                                "rationale": "Tighten runtime wording without changing the guardrail.",
                            },
                            {
                                "editSet": {
                                    "prompt_constant_replacements": [
                                        {
                                            "constantName": "RUNTIME_HINT_POLICY",
                                            "newText": (
                                                f"{prompt_fragments.RUNTIME_HINT_POLICY} "
                                                "Keep the runtime hint explicit for the host, the adapter, "
                                                "and the reflective search loop."
                                            ),
                                            "reason": "Longer safe refinement.",
                                        }
                                    ]
                                },
                                "rationale": "A longer candidate that should lose on size cost.",
                            },
                        ]
                    }
                return {
                    "candidates": [
                        {
                            "editSet": {
                                "prompt_constant_replacements": [
                                    {
                                        "constantName": "RUNTIME_HINT_POLICY",
                                        "newText": (
                                            f"{prompt_fragments.RUNTIME_HINT_POLICY} "
                                            "Keep the runtime hint explicit."
                                        ),
                                        "reason": "Preserve the contract while refining the text.",
                                    }
                                ]
                            },
                            "rationale": "Tighten runtime wording without changing the guardrail.",
                        }
                    ]
                }
            if schema_name.startswith("circulatio_execution_"):
                return {
                    "clarifyingQuestion": "Which image feels most alive to you right now?",
                    "methodGate": {"depthLevel": "personal_amplification_needed"},
                    "proposalCandidates": [],
                }
            if schema_name == "circulatio_judge_prompt_fragments":
                return {
                    "dimensions": {"restraint": 0.95, "pacing": 0.9},
                    "overallScore": 0.95,
                    "confidence": "high",
                    "failureTags": [],
                    "feedback": "",
                    "criticalConcerns": [],
                }
            raise AssertionError(f"Unexpected schema request: {schema_name}")

        return FakeEvolutionLlmClient(handler=handler)

    def test_manual_candidate_flow_writes_review_package(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        baseline_path = repo_root / "src" / "circulatio" / "llm" / "prompt_fragments.py"
        with tempfile.TemporaryDirectory() as tmp_dir:
            candidate_path = Path(tmp_dir) / "prompt_fragments.py"
            candidate_path.write_text(baseline_path.read_text())
            result = evolve_candidates(
                target_names=["prompt_fragments"],
                strategy="manual",
                candidate_paths={"prompt_fragments": candidate_path},
                out_dir=Path(tmp_dir) / "runs",
            )
            manifest_text = Path(result["paths"]["manifest"]).read_text()
            report_text = Path(result["paths"]["report_json"]).read_text()
            self.assertEqual(result["status"], "pass")
            self.assertEqual(result["promotionStatus"], "holdout_passed")
            self.assertIn('"status": "holdout_passed"', manifest_text)
            self.assertIn('"evaluationStatus": "pass"', manifest_text)
            self.assertIn('"promotionStatus": "holdout_passed"', report_text)
            self.assertTrue(Path(result["paths"]["manifest"]).exists())
            self.assertTrue(Path(result["paths"]["report_json"]).exists())
            self.assertTrue(Path(result["paths"]["report_md"]).exists())
            self.assertTrue(Path(result["paths"]["diff_patch"]).exists())

    def test_manual_candidate_flow_records_failure_report(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        baseline = (repo_root / "src" / "circulatio" / "llm" / "prompt_fragments.py").read_text()
        broken = (
            baseline
            + "\nCLARIFICATION_ROUTING_POLICY = (\n"
            + '    "When you ask a clarifyingQuestion, answer_only is acceptable even when "\n'
            + '    "no durable typed routing is available."\n'
            + ")\n"
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            candidate_path = Path(tmp_dir) / "prompt_fragments.py"
            candidate_path.write_text(broken)
            result = evolve_candidates(
                target_names=["prompt_fragments"],
                strategy="manual",
                candidate_paths={"prompt_fragments": candidate_path},
                out_dir=Path(tmp_dir) / "runs",
            )
            report_json = Path(result["paths"]["report_json"]).read_text()
            manifest_text = Path(result["paths"]["manifest"]).read_text()
        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["promotionStatus"], "failed")
        self.assertIn("\"status\": \"fail\"", report_json)
        self.assertIn('"status": "failed"', manifest_text)

    def test_reflection_strategy_writes_review_package(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            result = evolve_candidates(
                target_names=["prompt_fragments"],
                strategy="reflection",
                candidate_paths={},
                out_dir=Path(tmp_dir) / "runs",
                generation_config=EvolutionGenerationConfig(
                    iterations=1,
                    population_size=1,
                    max_generated_candidates=1,
                ),
                execution_options=ExecutionOptions(enabled=True),
                judge_options=JudgeOptions(enabled=True),
                llm_client=self._automatic_client(),
            )
            manifest = Path(result["paths"]["manifest"]).read_text()
            report_json = Path(result["paths"]["report_json"]).read_text()
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["promotionStatus"], "holdout_passed")
        self.assertIn('"selectedCandidateId": "prompt_fragments_cand_0001"', manifest)
        self.assertIn('"candidateCount": 1', manifest)
        self.assertIn('"selectedCandidateId": "prompt_fragments_cand_0001"', report_json)

    def test_pareto_reflection_records_multiple_candidates_and_selects_one(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            result = evolve_candidates(
                target_names=["prompt_fragments"],
                strategy="pareto_reflection",
                candidate_paths={},
                out_dir=Path(tmp_dir) / "runs",
                generation_config=EvolutionGenerationConfig(
                    iterations=1,
                    population_size=2,
                    max_generated_candidates=2,
                ),
                execution_options=ExecutionOptions(enabled=True),
                judge_options=JudgeOptions(enabled=True),
                llm_client=self._automatic_client(multi_candidate=True),
            )
            candidate_index = Path(result["paths"]["candidate_index"]).read_text()
            report_json = Path(result["paths"]["report_json"]).read_text()
        self.assertEqual(result["status"], "pass")
        self.assertIn("prompt_fragments_cand_0001", candidate_index)
        self.assertIn("prompt_fragments_cand_0002", candidate_index)
        self.assertIn('"selectedCandidateId": "prompt_fragments_cand_0001"', report_json)

    def test_automatic_strategy_blocks_promotion_on_deterministic_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            result = evolve_candidates(
                target_names=["prompt_fragments"],
                strategy="reflection",
                candidate_paths={},
                out_dir=Path(tmp_dir) / "runs",
                generation_config=EvolutionGenerationConfig(
                    iterations=1,
                    population_size=1,
                    max_generated_candidates=1,
                ),
                execution_options=ExecutionOptions(enabled=True),
                judge_options=JudgeOptions(enabled=True),
                llm_client=self._automatic_client(broken=True),
            )
            report_json = Path(result["paths"]["report_json"]).read_text()
        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["promotionStatus"], "failed")
        self.assertTrue(
            any(
                stage["name"] == "selection" and stage["status"] == "failed"
                for stage in result["stageHistory"]
            )
        )
        self.assertIn('"selectedCandidateId": null', report_json)


if __name__ == "__main__":
    unittest.main()
