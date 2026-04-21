from __future__ import annotations

import asyncio
import json
import os
import sys
import types
import unittest
from contextlib import contextmanager
from unittest import mock

sys.path.insert(0, os.path.abspath("src"))

from circulatio.hermes.runtime import build_in_memory_circulatio_runtime
from circulatio.llm.hermes_model_adapter import HermesModelAdapter


@contextmanager
def auxiliary_client_modules(*, async_call_llm=None, extract_content_or_reasoning=None):
    agent_module = types.ModuleType("agent")
    modules = {"agent": agent_module}
    if async_call_llm is not None or extract_content_or_reasoning is not None:
        auxiliary_module = types.ModuleType("agent.auxiliary_client")
        if async_call_llm is not None:
            auxiliary_module.async_call_llm = async_call_llm
        if extract_content_or_reasoning is not None:
            auxiliary_module.extract_content_or_reasoning = extract_content_or_reasoning
        agent_module.auxiliary_client = auxiliary_module
        modules["agent.auxiliary_client"] = auxiliary_module
    with mock.patch.dict(sys.modules, modules):
        yield


class HermesModelAdapterTests(unittest.TestCase):
    def test_missing_auxiliary_client_returns_unavailable_and_core_falls_back(self) -> None:
        async def run() -> None:
            adapter = HermesModelAdapter()
            with auxiliary_client_modules():
                probe = await adapter.verify_model_path(perform_call=False)
                self.assertEqual(probe["status"], "unavailable")
                runtime = build_in_memory_circulatio_runtime(llm=adapter)
                workflow = await runtime.service.create_and_interpret_material(
                    {
                        "userId": "user_missing_aux",
                        "materialType": "reflection",
                        "text": "A snake crossed the room.",
                    }
                )
                self.assertEqual(workflow["pendingProposals"], [])
                self.assertIn(
                    "did not return usable structured output",
                    workflow["interpretation"]["userFacingResponse"],
                )

        asyncio.run(run())

    def test_fake_auxiliary_client_drives_real_adapter_path(self) -> None:
        async def run() -> None:
            response_payload = {
                "symbolMentions": [
                    {
                        "refKey": "sym_snake",
                        "surfaceText": "snake",
                        "canonicalName": "snake",
                        "category": "animal",
                        "salience": 0.9,
                    }
                ],
                "figureMentions": [],
                "motifMentions": [],
                "lifeContextLinks": [],
                "observations": [
                    {
                        "kind": "image",
                        "statement": "The snake is central.",
                        "supportingRefs": ["sym_snake"],
                    }
                ],
                "hypotheses": [
                    {
                        "claim": "The snake may mark a recurring tension.",
                        "hypothesisType": "theme",
                        "confidence": "medium",
                        "supportingRefs": ["sym_snake"],
                        "userTestPrompt": "Does the snake feel recurrent?",
                        "phrasingPolicy": "tentative",
                    }
                ],
                "practiceRecommendation": {},
                "proposalCandidates": [
                    {
                        "action": "upsert_personal_symbol",
                        "entityType": "PersonalSymbol",
                        "payload": {"canonicalName": "snake", "category": "animal"},
                        "reason": "The snake looks central enough to remember if approved.",
                        "supportingRefs": ["sym_snake"],
                    }
                ],
                "userFacingResponse": "LLM interpretation available.",
                "clarifyingQuestion": "What stands out?",
            }

            async def async_call_llm(**kwargs):
                return {"text": json.dumps(response_payload)}

            def extract_content_or_reasoning(response):
                return response["text"]

            with auxiliary_client_modules(
                async_call_llm=async_call_llm,
                extract_content_or_reasoning=extract_content_or_reasoning,
            ):
                adapter = HermesModelAdapter()
                runtime = build_in_memory_circulatio_runtime(llm=adapter)
                workflow = await runtime.service.create_and_interpret_material(
                    {
                        "userId": "user_fake_aux",
                        "materialType": "reflection",
                        "text": "A snake crossed the room.",
                    }
                )
                self.assertEqual(
                    workflow["interpretation"]["symbolMentions"][0]["canonicalName"], "snake"
                )
                self.assertEqual(len(workflow["pendingProposals"]), 1)
                self.assertEqual(
                    workflow["pendingProposals"][0]["action"], "upsert_personal_symbol"
                )

        asyncio.run(run())

    def test_malformed_model_fields_are_sanitized_before_reaching_core(self) -> None:
        async def run() -> None:
            response_payload = {
                "symbolMentions": "snake",
                "figureMentions": ["shadow"],
                "motifMentions": [{"canonicalName": "descent"}],
                "lifeContextLinks": "none",
                "observations": ["The bear is intense."],
                "hypotheses": "threat",
                "practiceRecommendation": "breathe",
                "proposalCandidates": ["store snake"],
                "userFacingResponse": "LLM interpretation available.",
                "clarifyingQuestion": "What stayed with you?",
            }

            async def async_call_llm(**kwargs):
                return {"text": json.dumps(response_payload)}

            def extract_content_or_reasoning(response):
                return response["text"]

            with auxiliary_client_modules(
                async_call_llm=async_call_llm,
                extract_content_or_reasoning=extract_content_or_reasoning,
            ):
                adapter = HermesModelAdapter()
                runtime = build_in_memory_circulatio_runtime(llm=adapter)
                workflow = await runtime.service.create_and_interpret_material(
                    {
                        "userId": "user_sanitized_aux",
                        "materialType": "reflection",
                        "text": "A bear attacked me while I walked.",
                    }
                )
                self.assertEqual(workflow["interpretation"]["symbolMentions"], [])
                self.assertTrue(workflow["interpretation"]["observations"])
                self.assertEqual(workflow["pendingProposals"], [])
                self.assertIn(
                    "did not return usable structured output",
                    workflow["interpretation"]["userFacingResponse"],
                )
                self.assertEqual(
                    workflow["interpretation"]["llmInterpretationHealth"]["status"], "fallback"
                )

        asyncio.run(run())

    def test_clarifying_question_only_payload_is_accepted_as_first_pass_structure(self) -> None:
        async def run() -> None:
            calls = []
            response_payload = {
                "symbolMentions": [],
                "figureMentions": [],
                "motifMentions": [],
                "lifeContextLinks": [],
                "observations": [],
                "hypotheses": [],
                "practiceRecommendation": {},
                "proposalCandidates": [],
                "userFacingResponse": "",
                "clarifyingQuestion": "What felt strongest in the chase?",
                "clarificationIntent": {
                    "refKey": "clarify_chase_body",
                    "questionText": "What felt strongest in the chase?",
                    "expectedTargets": ["body_state", "personal_amplification"],
                    "anchorRefs": {},
                    "consentScopes": ["somatic_correlation"],
                    "storagePolicy": "direct_if_explicit",
                    "expiresAt": "2026-12-31T00:00:00Z",
                },
            }

            async def async_call_llm(**kwargs):
                calls.append(kwargs)
                return {"text": json.dumps(response_payload)}

            def extract_content_or_reasoning(response):
                return response["text"]

            with auxiliary_client_modules(
                async_call_llm=async_call_llm,
                extract_content_or_reasoning=extract_content_or_reasoning,
            ):
                adapter = HermesModelAdapter()
                runtime = build_in_memory_circulatio_runtime(llm=adapter)
                workflow = await runtime.service.create_and_interpret_material(
                    {
                        "userId": "user_clarifying_first_pass",
                        "materialType": "dream",
                        "text": "A bear chased me through the forest.",
                    }
                )
                self.assertEqual(len(calls), 1)
                self.assertEqual(
                    workflow["interpretation"]["userFacingResponse"],
                    "What felt strongest in the chase?",
                )
                self.assertEqual(
                    workflow["interpretation"]["clarifyingQuestion"],
                    "What felt strongest in the chase?",
                )
                self.assertEqual(
                    workflow["interpretation"]["clarificationIntent"]["refKey"],
                    "clarify_chase_body",
                )
                self.assertEqual(
                    workflow["interpretation"]["llmInterpretationHealth"]["status"], "structured"
                )

        asyncio.run(run())

    def test_route_method_state_response_uses_json_schema_and_returns_structured_candidates(
        self,
    ) -> None:
        async def run() -> None:
            calls = []
            response_payload = {
                "answerSummary": "Jaw tightness came up with the image.",
                "evidenceSpans": [
                    {
                        "refKey": "resp_1",
                        "quote": "My jaw tightened when I pictured the door.",
                        "summary": "Jaw tightness appeared with the image.",
                        "targetKinds": ["body_state"],
                    }
                ],
                "captureCandidates": [
                    {
                        "targetKind": "body_state",
                        "application": "direct_write",
                        "confidence": "high",
                        "payload": {
                            "sensation": "tightness",
                            "bodyRegion": "jaw",
                            "activation": "moderate",
                        },
                        "supportingEvidenceRefs": ["resp_1"],
                        "consentScopes": [],
                        "reason": "The user directly reported a body response.",
                    }
                ],
                "followUpPrompts": [],
                "routingWarnings": [],
            }

            async def async_call_llm(**kwargs):
                calls.append(kwargs)
                return {"text": json.dumps(response_payload)}

            def extract_content_or_reasoning(response):
                return response["text"]

            with auxiliary_client_modules(
                async_call_llm=async_call_llm,
                extract_content_or_reasoning=extract_content_or_reasoning,
            ):
                adapter = HermesModelAdapter()
                output = await adapter.route_method_state_response(
                    {
                        "userId": "user_route_method_state",
                        "responseText": "My jaw tightened when I pictured the door.",
                        "source": "clarifying_answer",
                        "anchorRefs": {"runId": "run_1", "clarificationRefKey": "clarify_door"},
                        "expectedTargets": ["body_state"],
                        "consentPreferences": [],
                    }
                )
                self.assertEqual(output["captureCandidates"][0]["targetKind"], "body_state")
                self.assertEqual(output["evidenceSpans"][0]["refKey"], "resp_1")
                self.assertEqual(
                    calls[0]["response_format"]["json_schema"]["name"],
                    "circulatio_method_state_routing",
                )

        asyncio.run(run())

    def test_narrative_only_json_gets_structure_repair_pass(self) -> None:
        async def run() -> None:
            calls = []
            narrative_only_payload = {
                "symbolMentions": [],
                "figureMentions": [],
                "motifMentions": [],
                "lifeContextLinks": [],
                "observations": [],
                "hypotheses": [],
                "practiceRecommendation": {},
                "proposalCandidates": [],
                "userFacingResponse": "A snake in the room may suggest a charged tension moving through familiar space.",
                "clarifyingQuestion": "",
            }
            repaired_payload = {
                "symbolMentions": [
                    {
                        "refKey": "sym_snake",
                        "surfaceText": "snake",
                        "canonicalName": "snake",
                        "category": "animal",
                        "salience": 0.91,
                    }
                ],
                "figureMentions": [],
                "motifMentions": [],
                "lifeContextLinks": [],
                "observations": [
                    {
                        "kind": "image",
                        "statement": "The snake is the dominant image in the material.",
                        "supportingRefs": ["sym_snake"],
                    }
                ],
                "hypotheses": [
                    {
                        "claim": "The snake may be carrying a recurring tension rather than a one-off image.",
                        "hypothesisType": "theme",
                        "confidence": "medium",
                        "supportingRefs": ["sym_snake"],
                        "userTestPrompt": "Does the snake feel recurrent or specific to this scene?",
                        "phrasingPolicy": "tentative",
                    }
                ],
                "practiceRecommendation": {},
                "proposalCandidates": [
                    {
                        "action": "upsert_personal_symbol",
                        "entityType": "PersonalSymbol",
                        "payload": {"canonicalName": "snake", "category": "animal"},
                        "reason": "The central image is strong enough to save if approved.",
                        "supportingRefs": ["sym_snake"],
                    }
                ],
                "userFacingResponse": "LLM interpretation available.",
                "clarifyingQuestion": "What about the snake felt most charged?",
            }

            async def async_call_llm(**kwargs):
                calls.append(kwargs)
                payload = narrative_only_payload if len(calls) == 1 else repaired_payload
                return {"text": json.dumps(payload)}

            def extract_content_or_reasoning(response):
                return response["text"]

            with auxiliary_client_modules(
                async_call_llm=async_call_llm,
                extract_content_or_reasoning=extract_content_or_reasoning,
            ):
                adapter = HermesModelAdapter()
                runtime = build_in_memory_circulatio_runtime(llm=adapter)
                workflow = await runtime.service.create_and_interpret_material(
                    {
                        "userId": "user_contract_repair",
                        "materialType": "reflection",
                        "text": "A snake crossed the room.",
                    }
                )
                self.assertEqual(len(calls), 2)
                self.assertEqual(
                    workflow["interpretation"]["symbolMentions"][0]["canonicalName"], "snake"
                )
                self.assertEqual(len(workflow["pendingProposals"]), 1)
                self.assertEqual(
                    workflow["interpretation"]["llmInterpretationHealth"]["status"], "structured"
                )

        asyncio.run(run())

    def test_interpretation_requests_json_schema_when_client_accepts_it(self) -> None:
        async def run() -> None:
            calls = []
            response_payload = {
                "symbolMentions": [],
                "figureMentions": [],
                "motifMentions": [],
                "lifeContextLinks": [],
                "observations": [],
                "hypotheses": [],
                "practiceRecommendation": {},
                "proposalCandidates": [],
                "userFacingResponse": "",
                "clarifyingQuestion": "What image stayed with you?",
            }

            async def async_call_llm(**kwargs):
                calls.append(kwargs)
                return {"text": json.dumps(response_payload)}

            def extract_content_or_reasoning(response):
                return response["text"]

            with auxiliary_client_modules(
                async_call_llm=async_call_llm,
                extract_content_or_reasoning=extract_content_or_reasoning,
            ):
                adapter = HermesModelAdapter()
                runtime = build_in_memory_circulatio_runtime(llm=adapter)
                await runtime.service.create_and_interpret_material(
                    {
                        "userId": "user_json_schema_aux",
                        "materialType": "dream",
                        "text": "A bear chased me through the forest.",
                    }
                )
                self.assertEqual(
                    calls[0]["response_format"]["json_schema"]["name"],
                    "circulatio_interpretation",
                )
                self.assertEqual(calls[0]["json_schema"]["type"], "object")

        asyncio.run(run())

    def test_timeout_returns_unavailable_and_core_falls_back(self) -> None:
        async def run() -> None:
            async def async_call_llm(**kwargs):
                del kwargs
                await asyncio.sleep(0.05)
                return {"text": "{}"}

            def extract_content_or_reasoning(response):
                return response["text"]

            with auxiliary_client_modules(
                async_call_llm=async_call_llm,
                extract_content_or_reasoning=extract_content_or_reasoning,
            ):
                adapter = HermesModelAdapter(request_timeout_seconds=0.01)
                runtime = build_in_memory_circulatio_runtime(llm=adapter)
                workflow = await runtime.service.create_and_interpret_material(
                    {
                        "userId": "user_timeout_aux",
                        "materialType": "reflection",
                        "text": "A bear attacked me in the forest.",
                    }
                )
                self.assertEqual(workflow["pendingProposals"], [])
                self.assertIn(
                    "did not return usable structured output",
                    workflow["interpretation"]["userFacingResponse"],
                )
                self.assertEqual(
                    workflow["interpretation"]["llmInterpretationHealth"]["status"], "fallback"
                )

        asyncio.run(run())

    def test_debug_logging_emits_raw_and_parsed_shape_when_enabled(self) -> None:
        async def run() -> None:
            response_payload = {
                "symbolMentions": [],
                "figureMentions": [],
                "motifMentions": [],
                "lifeContextLinks": [],
                "observations": [],
                "hypotheses": [],
                "practiceRecommendation": {},
                "proposalCandidates": [],
                "userFacingResponse": "LLM interpretation available.",
            }

            async def async_call_llm(**kwargs):
                return {"text": json.dumps(response_payload)}

            def extract_content_or_reasoning(response):
                return response["text"]

            with auxiliary_client_modules(
                async_call_llm=async_call_llm,
                extract_content_or_reasoning=extract_content_or_reasoning,
            ):
                with mock.patch.dict(os.environ, {"CIRCULATIO_DEBUG_LLM": "1"}, clear=False):
                    adapter = HermesModelAdapter()
                    with self.assertLogs(
                        "circulatio.llm.hermes_model_adapter", level="WARNING"
                    ) as logs:
                        await adapter.verify_model_path(perform_call=True)
                combined = "\n".join(logs.output)
                self.assertIn('"stage": "initial_raw"', combined)
                self.assertIn('"stage": "initial_parsed"', combined)
                self.assertIn('"parsedShape"', combined)
                self.assertIn('"userFacingResponse"', combined)

        asyncio.run(run())

    def test_json_repair_path_is_used_when_first_response_is_invalid(self) -> None:
        async def run() -> None:
            calls = []

            async def async_call_llm(**kwargs):
                calls.append(kwargs)
                if len(calls) == 1:
                    return {"text": "not-json"}
                return {"text": '{"ok": true}'}

            def extract_content_or_reasoning(response):
                return response["text"]

            with auxiliary_client_modules(
                async_call_llm=async_call_llm,
                extract_content_or_reasoning=extract_content_or_reasoning,
            ):
                adapter = HermesModelAdapter()
                probe = await adapter.verify_model_path(perform_call=True)
                self.assertEqual(probe["status"], "ok")
                self.assertEqual(len(calls), 2)

        asyncio.run(run())

    def test_optional_real_model_path_probe(self) -> None:
        if os.environ.get("CIRCULATIO_REAL_HERMES_MODEL") != "1":
            self.skipTest(
                "Set CIRCULATIO_REAL_HERMES_MODEL=1 to probe the real Hermes auxiliary client."
            )

        async def run() -> None:
            adapter = HermesModelAdapter()
            probe = await adapter.verify_model_path(perform_call=True)
            self.assertNotEqual(probe["status"], "unavailable")

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
