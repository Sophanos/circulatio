from __future__ import annotations

import importlib.util
import sys
import unittest
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def _load_harness_module():
    repo_root = Path(__file__).resolve().parents[1]
    module_path = repo_root / "scripts" / "evaluate_hermes_real_host.py"
    spec = importlib.util.spec_from_file_location("evaluate_hermes_real_host", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class EvaluateHermesRealHostTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.harness = _load_harness_module()

    def test_allowed_tool_sequences_match_exact_full_sequence(self) -> None:
        findings = self.harness.evaluate_expectations(
            expected={
                "allowedToolSequences": [
                    ["circulatio_analysis_packet"],
                    ["circulatio_analysis_packet", "circulatio_discovery"],
                ]
            },
            tool_calls=["circulatio_analysis_packet", "circulatio_discovery"],
            host_reply="Typologisch wirkt Denken im Vordergrund.",
            timed_out=False,
            return_code=0,
        )
        self.assertEqual(findings, [])

    def test_allowed_tool_sequences_fail_on_non_matching_sequence(self) -> None:
        findings = self.harness.evaluate_expectations(
            expected={
                "allowedToolSequences": [
                    ["circulatio_analysis_packet"],
                    ["circulatio_analysis_packet", "circulatio_discovery"],
                ]
            },
            tool_calls=["circulatio_discovery"],
            host_reply="Typologisch wirkt Denken im Vordergrund.",
            timed_out=False,
            return_code=0,
        )
        self.assertIn("tool sequence did not match any allowed exact sequence", findings[0])

    def test_reply_regex_expectations_use_multiline_case_insensitive_matching(self) -> None:
        findings = self.harness.evaluate_expectations(
            expected={
                "requiredReplyRegexes": [r"denken.*vordergrund", r"fühlen.*problem"],
                "forbiddenReplyRegexes": [r"du bist.*denktyp"],
            },
            tool_calls=["circulatio_interpret_material"],
            host_reply=(
                "Denken wirkt hier eher im Vordergrund.\n"
                "Fühlen erscheint unter Druck eher als Problemzone."
            ),
            timed_out=False,
            return_code=0,
        )
        self.assertEqual(findings, [])

    def test_reply_regex_expectations_fail_on_forbidden_match(self) -> None:
        findings = self.harness.evaluate_expectations(
            expected={
                "forbiddenReplyRegexes": [r"du bist.*denktyp"],
            },
            tool_calls=["circulatio_interpret_material"],
            host_reply="Du bist hier eindeutig ein Denktyp.",
            timed_out=False,
            return_code=0,
        )
        self.assertEqual(
            findings,
            ["reply matched forbidden regex: du bist.*denktyp"],
        )

    def test_resume_from_case_id_dependency_resolution(self) -> None:
        turn_spec = self.harness.TurnSpec(
            case_id="story_turn_002",
            turn_id=None,
            title="Story turn 2",
            session_label=None,
            story_id="story_alpha",
            story_title="Story Alpha",
            turn_index=2,
            resume_from_case_id="story_turn_001",
            user_turn="Bitte fahre damit fort.",
            expected={},
            max_turns=None,
            dataset_path="tests/evals/hermes_real_host/typology_journeys.jsonl",
            line_number=2,
        )
        session_id, finding = self.harness.resolve_resume_session_id(
            turn_spec,
            sessions_by_label={},
            session_ids_by_case_id={},
        )
        self.assertIsNone(session_id)
        self.assertEqual(
            finding,
            "resume dependency unavailable: case story_turn_001 produced no session id in this run",
        )

        session_id, finding = self.harness.resolve_resume_session_id(
            turn_spec,
            sessions_by_label={},
            session_ids_by_case_id={"story_turn_001": "session_123"},
        )
        self.assertEqual(session_id, "session_123")
        self.assertIsNone(finding)

    def test_legacy_tool_sequence_prefix_behavior_still_works(self) -> None:
        findings = self.harness.evaluate_expectations(
            expected={"toolSequencePrefix": ["circulatio_store_reflection"]},
            tool_calls=["circulatio_store_reflection", "circulatio_interpret_material"],
            host_reply="Ich habe das festgehalten.",
            timed_out=False,
            return_code=0,
        )
        self.assertEqual(findings, [])

        findings = self.harness.evaluate_expectations(
            expected={"toolSequencePrefix": ["circulatio_store_reflection"]},
            tool_calls=["circulatio_store_event"],
            host_reply="Ich habe das festgehalten.",
            timed_out=False,
            return_code=0,
        )
        self.assertEqual(
            findings,
            [
                "tool sequence prefix mismatch: expected ['circulatio_store_reflection'], "
                "got ['circulatio_store_event']"
            ],
        )

    def test_sanitize_output_accepts_timeout_bytes(self) -> None:
        sanitized = self.harness.sanitize_output(b"session_id: abc123\r\nLine 1\r\n")
        self.assertEqual(sanitized, "session_id: abc123\nLine 1")


if __name__ == "__main__":
    unittest.main()
