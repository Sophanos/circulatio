from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.abspath("src"))
sys.path.insert(0, os.path.abspath("."))

from circulatio.llm import prompt_builder
from tools.self_evolution import evaluate_candidate_bundle, evaluate_target


class MethodSelfEvolutionTests(unittest.TestCase):
    def test_prompt_fragment_baseline_passes_default_eval_sets(self) -> None:
        report = evaluate_target("prompt_fragments")
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["failedCases"], 0)

    def test_skill_baseline_passes_default_eval_set(self) -> None:
        report = evaluate_target("skill")
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["failedCases"], 0)

    def test_tool_description_baseline_passes_default_eval_set(self) -> None:
        report = evaluate_target("tool_descriptions")
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["failedCases"], 0)

    def test_candidate_prompt_override_surfaces_regression(self) -> None:
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
            report = evaluate_target(
                "prompt_fragments",
                candidate_path=candidate_path,
                dataset_paths=[
                    repo_root
                    / "tests"
                    / "evals"
                    / "circulatio_method"
                    / "clarification_routing.jsonl"
                ],
            )
        self.assertEqual(report["status"], "fail")
        self.assertGreater(report["failedCases"], 0)
        self.assertEqual(report["regressionStatus"], "same")

    def test_candidate_prompt_override_does_not_mutate_global_prompt_fragment_provider(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        baseline = (repo_root / "src" / "circulatio" / "llm" / "prompt_fragments.py").read_text()
        marker = "TEST_RUNTIME_HINT_TOKEN"
        candidate_text = (
            baseline
            + "\nRUNTIME_HINT_POLICY = (\n"
            + f"    {repr(prompt_builder.prompt_fragments.RUNTIME_HINT_POLICY + ' ' + marker)}\n"
            + ")\n"
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            candidate_path = Path(tmp_dir) / "prompt_fragments.py"
            candidate_path.write_text(candidate_text)
            report = evaluate_target(
                "prompt_fragments",
                candidate_path=candidate_path,
                dataset_paths=[
                    repo_root
                    / "tests"
                    / "evals"
                    / "circulatio_method"
                    / "adaptation_precedence.jsonl"
                ],
            )
        self.assertEqual(report["status"], "pass")
        self.assertNotIn(marker, prompt_builder.prompt_fragments.RUNTIME_HINT_POLICY)

    def test_split_filter_preserves_case_metadata(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        report = evaluate_target(
            "prompt_fragments",
            dataset_paths=[
                repo_root
                / "tests"
                / "evals"
                / "circulatio_method"
                / "safety_grounding_boundary.jsonl"
            ],
            split_filter=["redteam"],
        )
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["caseCount"], 1)
        case = report["cases"][0]
        self.assertEqual(case["split"], "redteam")
        self.assertEqual(case["severity"], "blocking")
        self.assertEqual(case["gate_type"], "deterministic")

    def test_candidate_bundle_rejects_immutable_artifact(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        baseline = (repo_root / "src" / "circulatio" / "llm" / "prompt_fragments.py").read_text()
        with tempfile.TemporaryDirectory() as tmp_dir:
            candidate_root = Path(tmp_dir) / "candidates"
            candidate_root.mkdir()
            (candidate_root / "prompt_fragments.py").write_text(baseline)
            immutable_path = candidate_root / "src" / "circulatio" / "core"
            immutable_path.mkdir(parents=True)
            (immutable_path / "safety_gate.py").write_text("# should not be here\n")
            reports = evaluate_candidate_bundle(
                ["prompt_fragments"],
                candidate_dir=Path(tmp_dir),
                split_filter=["dev", "redteam", "regression", "holdout"],
            )
        self.assertEqual(reports[0]["status"], "fail")
        self.assertTrue(
            any(
                "Immutable artifact cannot be optimized" in finding
                for finding in reports[0]["constraintFindings"]
            )
        )


if __name__ == "__main__":
    unittest.main()
