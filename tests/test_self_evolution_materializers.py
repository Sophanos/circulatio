from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.abspath("src"))
sys.path.insert(0, os.path.abspath("."))

from circulatio.llm import prompt_fragments
from circulatio_hermes_plugin import schemas as plugin_schemas
from tools.self_evolution import evaluate_candidate_bundle
from tools.self_evolution.materializers import (
    PromptFragmentsMaterializer,
    SkillMaterializer,
    ToolDescriptionMaterializer,
)
from tools.self_evolution.targets import get_target


def _load_module(path: Path, *, module_name: str) -> object:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"Unable to load module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SelfEvolutionMaterializerTests(unittest.TestCase):
    def test_prompt_materializer_rewrites_allowed_constant(self) -> None:
        materializer = PromptFragmentsMaterializer(get_target("prompt_fragments"))
        proposal = {
            "editSet": {
                "prompt_constant_replacements": [
                    {
                        "constantName": "RUNTIME_HINT_POLICY",
                        "newText": (
                            f"{prompt_fragments.RUNTIME_HINT_POLICY} "
                            "Keep the runtime hint explicit for the host."
                        ),
                        "reason": "Preserve the existing guardrail while sharpening wording.",
                    }
                ]
            },
            "rationale": "Tighten runtime-guidance wording without changing the contract.",
            "sourceTraceIds": ["trace_runtime_hint"],
        }
        with tempfile.TemporaryDirectory() as tmp_dir:
            candidate = materializer.materialize(
                candidate_id="prompt_fragments_cand_0001",
                proposal=proposal,
                output_dir=Path(tmp_dir),
            )
            text = candidate.candidate_path.read_text()
        self.assertIn("Keep the runtime hint explicit for the host.", text)
        self.assertEqual(candidate.source_trace_ids, ["trace_runtime_hint"])
        self.assertEqual(candidate.edit_summary, ["RUNTIME_HINT_POLICY"])

    def test_skill_materializer_enforces_byte_limit(self) -> None:
        materializer = SkillMaterializer(get_target("skill"))
        proposal = {
            "editSet": {
                "skill_section_replacements": [
                    {
                        "heading": "Guardrails",
                        "newMarkdown": "x" * 20000,
                        "reason": "Too large on purpose.",
                    }
                ]
            },
            "rationale": "This should fail size validation.",
        }
        with tempfile.TemporaryDirectory() as tmp_dir:
            with self.assertRaises(ValueError):
                materializer.materialize(
                    candidate_id="skill_cand_0001",
                    proposal=proposal,
                    output_dir=Path(tmp_dir),
                )

    def test_tool_materializer_only_changes_description_text(self) -> None:
        materializer = ToolDescriptionMaterializer(get_target("tool_descriptions"))
        proposal = {
            "editSet": {
                "tool_description_replacements": [
                    {
                        "toolName": "circulatio_record_interpretation_feedback",
                        "newDescription": (
                            "Record explicit user feedback about a Circulatio interpretation "
                            "without parsing free-text notes into new symbolic material."
                        ),
                        "reason": "Tighten the routing boundary.",
                    }
                ]
            },
            "rationale": "Clarify that feedback capture is not a new reflection write.",
        }
        baseline_tool = next(
            schema
            for schema in plugin_schemas.TOOL_SCHEMAS
            if schema["name"] == "circulatio_record_interpretation_feedback"
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            candidate = materializer.materialize(
                candidate_id="tool_descriptions_cand_0001",
                proposal=proposal,
                output_dir=Path(tmp_dir),
            )
            module = _load_module(
                candidate.candidate_path,
                module_name="candidate_tool_descriptions",
            )
        candidate_tool = next(
            schema
            for schema in module.TOOL_SCHEMAS
            if schema["name"] == "circulatio_record_interpretation_feedback"
        )
        self.assertNotEqual(candidate_tool["description"], baseline_tool["description"])
        self.assertEqual(
            candidate_tool["parameters"]["properties"],
            baseline_tool["parameters"]["properties"],
        )
        self.assertEqual(
            candidate_tool["parameters"].get("required"),
            baseline_tool["parameters"].get("required"),
        )

    def test_candidate_bundle_rejects_extra_artifact(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        baseline = (repo_root / "src" / "circulatio" / "llm" / "prompt_fragments.py").read_text()
        with tempfile.TemporaryDirectory() as tmp_dir:
            candidate_root = Path(tmp_dir) / "candidates"
            candidate_root.mkdir()
            (candidate_root / "prompt_fragments.py").write_text(baseline)
            (candidate_root / "notes.txt").write_text("unsupported artifact\n")
            reports = evaluate_candidate_bundle(
                ["prompt_fragments"],
                candidate_dir=Path(tmp_dir),
            )
        self.assertEqual(reports[0]["status"], "fail")
        self.assertTrue(
            any(
                "Candidate bundle includes unsupported artifact" in finding
                for finding in reports[0]["constraintFindings"]
            )
        )


if __name__ == "__main__":
    unittest.main()
