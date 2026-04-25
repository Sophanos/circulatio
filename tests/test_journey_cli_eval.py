from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.journey_cli_eval.dataset import load_journey_cases
from tools.journey_cli_eval.normalization import normalize_journey_output
from tools.journey_cli_eval.runner import run_journey_cli_eval
from tools.journey_cli_eval.scoring import score_journey_output

REPO_ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = REPO_ROOT / "tests" / "evals" / "journey_cli" / "baseline.jsonl"
COMPOUND_PATH = REPO_ROOT / "tests" / "evals" / "journey_cli" / "compound.jsonl"
REDTEAM_PATH = REPO_ROOT / "tests" / "evals" / "journey_cli" / "redteam.jsonl"


class JourneyCliEvalTests(unittest.TestCase):
    def test_schema_validation_accepts_committed_datasets(self) -> None:
        cases = load_journey_cases([BASELINE_PATH, COMPOUND_PATH, REDTEAM_PATH])
        self.assertGreaterEqual(len(cases), 10)
        case_ids = {case["caseId"] for case in cases}
        self.assertIn("embodied_recurrence_001", case_ids)
        self.assertIn("ritual_artifact_chat_website_cron_001", case_ids)

    def test_invalid_case_reports_field_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "invalid.jsonl"
            path.write_text(
                json.dumps(
                    {
                        "schemaVersion": 1,
                        "caseId": "bad_case",
                        "title": "Bad",
                        "journeyFamily": "EmbodiedRecurrence",
                        "caseKind": "single_turn_route",
                        "split": "dev",
                        "severity": "blocking",
                        "gateType": "deterministic",
                        "testLayers": ["cli_comparison"],
                        "turns": [
                            {
                                "turnId": "t1",
                                "turnKind": "ambient_intake",
                                "userTurn": "hello",
                                "expected": {"toolSequence": {"unsupported": ["x"]}},
                            }
                        ],
                    }
                )
            )
            with self.assertRaisesRegex(ValueError, r"turns\[0\]\.expected\.toolSequence"):
                load_journey_cases([path])

    def test_fake_adapter_success_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            summary = run_journey_cli_eval(
                adapters_requested=["fake"],
                dataset_paths=[BASELINE_PATH],
                case_ids=["embodied_recurrence_001"],
                cache_root=Path(temp_dir) / "cache",
                use_cache=False,
            )
        self.assertEqual(summary["missingRequiredAdapters"], [])
        self.assertEqual(len(summary["results"]), 1)
        self.assertTrue(summary["results"][0]["passed"])

    def test_ritual_artifact_flow_fake_adapter_success_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            summary = run_journey_cli_eval(
                adapters_requested=["fake"],
                dataset_paths=[COMPOUND_PATH],
                case_ids=["ritual_artifact_chat_website_cron_001"],
                cache_root=Path(temp_dir) / "cache",
                use_cache=False,
            )
        self.assertEqual(summary["missingRequiredAdapters"], [])
        self.assertEqual(len(summary["results"]), 1)
        result = summary["results"][0]
        self.assertTrue(result["passed"], result["findings"])

    def test_fake_adapter_malformed_json_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            adapter_config = Path(temp_dir) / "adapters.local.yaml"
            adapter_config.write_text(
                json.dumps(
                    {
                        "adapters": {
                            "fake": {
                                "binary": "",
                                "enabledByDefault": False,
                                "promptTransport": "stdin",
                                "command": [],
                                "outputMode": "text",
                                "timeoutSeconds": 5,
                                "versionCommand": [],
                                "mode": "malformed_json",
                            }
                        }
                    }
                )
            )
            summary = run_journey_cli_eval(
                adapters_requested=["fake"],
                adapter_config_path=adapter_config,
                dataset_paths=[BASELINE_PATH],
                case_ids=["embodied_recurrence_001"],
                cache_root=Path(temp_dir) / "cache",
                use_cache=False,
            )
        self.assertEqual(len(summary["results"]), 1)
        self.assertFalse(summary["results"][0]["passed"])
        self.assertIn("output was not valid JSON", summary["results"][0]["findings"][0])

    def test_tool_alias_normalization(self) -> None:
        case = load_journey_cases([BASELINE_PATH], case_ids=["embodied_recurrence_001"])[0]
        normalized = normalize_journey_output(
            json.dumps(
                {
                    "caseId": "embodied_recurrence_001",
                    "turnResults": [
                        {
                            "turnId": "t1",
                            "selectedToolSequence": ["body_state_store"],
                            "askedClarification": False,
                            "performedHostInterpretation": False,
                            "hostReply": "I held that.",
                            "rationale": "store first",
                        }
                    ],
                }
            ),
            case=case,
            adapter="fake",
        )
        self.assertEqual(
            normalized.payload["turnResults"][0]["selectedToolSequence"],
            ["circulatio_store_body_state"],
        )

    def test_nested_jsonl_event_extraction_for_real_adapter_formats(self) -> None:
        case = load_journey_cases([BASELINE_PATH], case_ids=["embodied_recurrence_001"])[0]
        codex_raw = "\n".join(
            [
                json.dumps({"type": "turn.started"}),
                json.dumps(
                    {
                        "type": "item.completed",
                        "item": {
                            "id": "item_1",
                            "type": "agent_message",
                            "text": json.dumps(
                                {
                                    "caseId": "embodied_recurrence_001",
                                    "turnResults": [
                                        {
                                            "turnId": "t1",
                                            "selectedToolSequence": ["circulatio_store_body_state"],
                                            "askedClarification": False,
                                            "performedHostInterpretation": False,
                                            "hostReply": "I held that.",
                                            "rationale": "store first",
                                        }
                                    ],
                                }
                            ),
                        },
                    }
                ),
            ]
        )
        opencode_raw = "\n".join(
            [
                json.dumps({"type": "step_start"}),
                json.dumps(
                    {
                        "type": "text",
                        "part": {
                            "type": "text",
                            "text": json.dumps(
                                {
                                    "caseId": "embodied_recurrence_001",
                                    "turnResults": [
                                        {
                                            "turnId": "t1",
                                            "selectedToolSequence": ["circulatio_store_body_state"],
                                            "askedClarification": False,
                                            "performedHostInterpretation": False,
                                            "hostReply": "I held that.",
                                            "rationale": "store first",
                                        }
                                    ],
                                }
                            ),
                        },
                    }
                ),
            ]
        )
        for adapter, raw_text in (("codex", codex_raw), ("opencode", opencode_raw)):
            with self.subTest(adapter=adapter):
                normalized = normalize_journey_output(raw_text, case=case, adapter=adapter)
                self.assertEqual(normalized.parse_status, "parsed")
                self.assertEqual(
                    normalized.payload["turnResults"][0]["selectedToolSequence"],
                    ["circulatio_store_body_state"],
                )

    def test_forbidden_escalation_detection(self) -> None:
        case = load_journey_cases([BASELINE_PATH], case_ids=["embodied_recurrence_003"])[0]
        normalized = normalize_journey_output(
            json.dumps(
                {
                    "caseId": "embodied_recurrence_003",
                    "turnResults": [
                        {
                            "turnId": "t1",
                            "selectedToolSequence": ["circulatio_store_body_state"],
                            "askedClarification": False,
                            "performedHostInterpretation": False,
                            "hostReply": "This is your shadow breaking through.",
                            "rationale": "bad reply",
                        }
                    ],
                }
            ),
            case=case,
            adapter="fake",
        )
        self.assertEqual(
            normalized.payload["turnResults"][0]["forbiddenEscalationsPresent"],
            ["archetypal_patterning"],
        )

    def test_write_budget_scoring(self) -> None:
        case = load_journey_cases([BASELINE_PATH], case_ids=["journey_page_read_only_001"])[0]
        normalized = normalize_journey_output(
            json.dumps(
                {
                    "caseId": "journey_page_read_only_001",
                    "turnResults": [
                        {
                            "turnId": "t1",
                            "selectedToolSequence": ["circulatio_journey_page"],
                            "writeActions": [
                                {"kind": "journey", "tool": "circulatio_create_journey"}
                            ],
                            "askedClarification": False,
                            "performedHostInterpretation": False,
                            "hostReply": "I created a new journey for you.",
                            "rationale": "bad write",
                        }
                    ],
                }
            ),
            case=case,
            adapter="fake",
        )
        result = score_journey_output(case, normalized)
        self.assertFalse(result.passed)
        self.assertTrue(any("read-mostly surface" in finding for finding in result.findings))

    def test_baseline_comparison_flags_regression(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            baseline_path = temp_path / "baseline.json"
            first = run_journey_cli_eval(
                adapters_requested=["fake"],
                dataset_paths=[BASELINE_PATH],
                case_ids=["embodied_recurrence_001"],
                cache_root=temp_path / "cache1",
                use_cache=False,
                write_baseline_path=baseline_path,
            )
            self.assertTrue(first["results"][0]["passed"])
            adapter_config = temp_path / "adapters.local.yaml"
            adapter_config.write_text(
                json.dumps(
                    {
                        "adapters": {
                            "fake": {
                                "binary": "",
                                "enabledByDefault": False,
                                "promptTransport": "stdin",
                                "command": [],
                                "outputMode": "text",
                                "timeoutSeconds": 5,
                                "versionCommand": [],
                                "mode": "malformed_json",
                            }
                        }
                    }
                )
            )
            second = run_journey_cli_eval(
                adapters_requested=["fake"],
                adapter_config_path=adapter_config,
                dataset_paths=[BASELINE_PATH],
                case_ids=["embodied_recurrence_001"],
                cache_root=temp_path / "cache2",
                use_cache=False,
                compare_baseline_path=baseline_path,
            )
        baseline = second["baselineComparison"]
        self.assertTrue(baseline["hasRegression"])
        self.assertEqual(baseline["regressions"][0]["caseId"], "embodied_recurrence_001")


if __name__ == "__main__":
    unittest.main()
