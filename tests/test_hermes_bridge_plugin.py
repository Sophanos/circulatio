from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
import unittest
from typing import get_args

sys.path.insert(0, os.path.abspath("src"))

import circulatio_hermes_plugin.commands as plugin_commands
import circulatio_hermes_plugin.tools as plugin_tools
from circulatio.domain.errors import PersistenceError
from circulatio.hermes.agent_bridge_contracts import BridgeOperation
from circulatio.hermes.boot_validation import PluginBootError
from circulatio.hermes.result_renderer import CirculatioResultRenderer
from circulatio.hermes.runtime import (
    build_hermes_circulatio_runtime,
    build_in_memory_circulatio_runtime,
)
from circulatio_hermes_plugin import register
from circulatio_hermes_plugin.commands import (
    build_command_request,
    build_tool_request,
    handle_circulation,
    handle_circulation_sync,
)
from circulatio_hermes_plugin.runtime import get_runtime, reset_runtimes, set_runtime
from circulatio_hermes_plugin.tools import (
    alive_today_tool,
    analysis_packet_tool,
    answer_amplification_tool,
    approve_proposals_tool,
    approve_review_proposals_tool,
    capture_reality_anchors_tool,
    create_journey_tool,
    dashboard_summary_tool,
    delete_entity_tool,
    discovery_tool,
    generate_practice_recommendation_tool,
    generate_rhythmic_briefs_tool,
    get_journey_tool,
    get_material_tool,
    interpret_material_tool,
    journey_page_tool,
    list_journeys_tool,
    list_materials_tool,
    list_pending_review_proposals_tool,
    list_pending_tool,
    living_myth_review_tool,
    memory_kernel_tool,
    method_state_respond_tool,
    plan_ritual_tool,
    query_graph_tool,
    record_interpretation_feedback_tool,
    record_practice_feedback_tool,
    reject_hypotheses_tool,
    reject_proposals_tool,
    reject_review_proposals_tool,
    respond_practice_recommendation_tool,
    respond_rhythmic_brief_tool,
    revise_entity_tool,
    set_journey_status_tool,
    store_body_state_tool,
    store_dream_tool,
    store_event_tool,
    store_reflection_tool,
    store_symbolic_note_tool,
    symbol_get_tool,
    symbol_history_tool,
    symbols_list_tool,
    threshold_review_tool,
    update_journey_tool,
    weekly_review_tool,
)
from tests._helpers import FakeCirculatioLlm


class _FakeHermesContext:
    def __init__(self) -> None:
        self.commands: dict[str, object] = {}
        self.tools: dict[str, object] = {}
        self.skills: dict[str, str] = {}

    def register_command(self, name: str, handler, description: str | None = None) -> None:
        self.commands[name] = {"handler": handler, "description": description}

    def register_tool(self, name: str, handler=None, schema=None) -> None:
        if schema is None and isinstance(handler, dict):
            schema = handler
            handler = None
        self.tools[name] = {"handler": handler, "schema": schema}

    def register_skill(self, name: str, path: str) -> None:
        self.skills[name] = path


class _FakeModernHermesContext(_FakeHermesContext):
    def register_tool(
        self,
        *,
        name: str,
        toolset: str | None = None,
        schema=None,
        handler=None,
        is_async: bool = False,
        description: str | None = None,
    ) -> None:
        self.tools[name] = {
            "handler": handler,
            "schema": schema,
            "toolset": toolset,
            "is_async": is_async,
            "description": description,
        }


class _NarrativeOnlyLlm:
    async def interpret_material(self, input_data: dict[str, object]) -> dict[str, object]:
        del input_data
        return {
            "symbolMentions": [],
            "figureMentions": [],
            "motifMentions": [],
            "lifeContextLinks": [],
            "observations": [],
            "hypotheses": [],
            "practiceRecommendation": {},
            "proposalCandidates": [],
            "userFacingResponse": "A fluent but narrative-only interpretation.",
            "clarifyingQuestion": "",
        }

    async def generate_weekly_review(self, input_data: dict[str, object]) -> dict[str, object]:
        del input_data
        return {"userFacingResponse": "Narrative-only weekly review."}

    async def summarize_life_context(
        self,
        *,
        user_id: str,
        window_start: str,
        window_end: str,
        raw_context: dict[str, object],
    ) -> dict[str, object]:
        del user_id, raw_context
        return {
            "windowStart": window_start,
            "windowEnd": window_end,
            "source": "hermes-life-os",
        }

    async def generate_practice(self, input_data: dict[str, object]) -> dict[str, object]:
        del input_data
        return {"practiceRecommendation": {}, "userFacingResponse": ""}

    async def generate_rhythmic_brief(self, input_data: dict[str, object]) -> dict[str, object]:
        del input_data
        return {"title": "", "summary": "", "userFacingResponse": ""}


class HermesBridgePluginTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_runtimes()

    def _install_fake_runtime(self, *, profile: str = "default", llm: object | None = None):
        tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(tempdir.cleanup)
        runtime = build_hermes_circulatio_runtime(
            db_path=os.path.join(tempdir.name, "circulatio.db"),
            llm=llm if llm is not None else FakeCirculatioLlm(),
        )
        return set_runtime(runtime, profile=profile)

    def _install_in_memory_runtime(self, *, profile: str = "default", llm: object | None = None):
        runtime = build_in_memory_circulatio_runtime(
            llm=llm if llm is not None else FakeCirculatioLlm(),
        )
        return set_runtime(runtime, profile=profile)

    def _kwargs(self, *, message_id: str, session_id: str = "sess_1") -> dict[str, object]:
        return {
            "platform": "cli",
            "profile": "default",
            "session_id": session_id,
            "message_id": message_id,
        }

    def _tool_kwargs(self, *, call_id: str, session_id: str = "sess_1") -> dict[str, object]:
        return {
            **self._kwargs(message_id=call_id, session_id=session_id),
            "tool_call_id": call_id,
        }

    def _rendered_value(self, rendered: str, prefix: str) -> str:
        for line in rendered.splitlines():
            if line.startswith(prefix):
                return line[len(prefix) :].strip()
        self.fail(f"Missing rendered line starting with {prefix!r}")

    def test_tool_dispatch_accepts_payload_fields_as_kwargs(self) -> None:
        async def run() -> None:
            self._install_in_memory_runtime()
            response = json.loads(
                await answer_amplification_tool(
                    canonicalName="bear_attack_dream",
                    surfaceText="A bear attacked me in the forest.",
                    associationText="Fear while running, then a cave.",
                    **self._tool_kwargs(call_id="tool_kwargs_payload"),
                )
            )
            self.assertEqual(response["status"], "ok")
            self.assertEqual(response["message"], "Stored personal amplification.")

        asyncio.run(run())

    def test_plan_ritual_tool_dispatches_to_presentation_operation(self) -> None:
        async def run() -> None:
            self._install_in_memory_runtime()
            response = json.loads(
                await plan_ritual_tool(
                    {
                        "ritualIntent": "weekly_integration",
                        "narrativeMode": "hybrid",
                        "windowStart": "2026-04-12T00:00:00Z",
                        "windowEnd": "2026-04-19T23:59:59Z",
                        "requestedSurfaces": {
                            "breath": {"enabled": True},
                            "meditation": {"enabled": True},
                            "captions": {"enabled": True},
                            "cinema": {"enabled": False},
                        },
                    },
                    **self._tool_kwargs(call_id="tool_plan_ritual"),
                )
            )
            self.assertEqual(response["status"], "ok")
            self.assertEqual(
                response["result"]["plan"]["schemaVersion"],
                "circulatio.presentation.plan.v1",
            )
            self.assertEqual(
                response["result"]["renderRequest"]["rendererVersion"],
                "ritual-renderer.v1",
            )
            self.assertIn("captions", response["result"]["renderRequest"]["allowedSurfaces"])

        asyncio.run(run())

    def test_reflect_command_creates_pending_proposals_and_approval_writes_memory(self) -> None:
        async def run() -> None:
            self._install_fake_runtime()
            rendered = await handle_circulation(
                'reflect "I walked through a house and found a snake image returning after the conflict."',
                **self._kwargs(message_id="msg_1"),
            )
            self.assertIn("LLM schema: structured via llm", rendered)
            self.assertIn("Pending memory proposals - not written yet:", rendered)
            self.assertIn("Approve: /circulation approve", rendered)

            runtime = get_runtime("default")
            user_id = "hermes:default:local"
            self.assertEqual(await runtime.repository.list_symbols(user_id), [])

            approve_request = build_command_request(
                raw_args="approve last p1",
                kwargs=self._kwargs(message_id="msg_2"),
            )
            first_response = await runtime.bridge.dispatch(approve_request)
            second_response = await runtime.bridge.dispatch(approve_request)

            symbols = await runtime.repository.list_symbols(user_id)
            self.assertTrue(symbols)
            self.assertEqual(first_response["status"], "ok")
            self.assertFalse(first_response["replayed"])
            self.assertTrue(second_response["replayed"])

            reject_response = await runtime.bridge.dispatch(
                build_command_request(
                    raw_args='reject last p1 --reason "do not save this"',
                    kwargs=self._kwargs(message_id="msg_3"),
                )
            )
            self.assertEqual(reject_response["status"], "validation_error")
            self.assertIn("cannot transition from approved to rejected", reject_response["message"])

        asyncio.run(run())

    def test_command_render_shows_schema_fallback_when_llm_returns_narrative_only(self) -> None:
        async def run() -> None:
            self._install_fake_runtime(llm=_NarrativeOnlyLlm())
            rendered = await handle_circulation(
                'reflect "A snake crossed the room."',
                **self._kwargs(message_id="msg_schema_fallback"),
            )
            self.assertIn("LLM schema: opened via fallback", rendered)
            self.assertIn("LLM schema reason: collaborative_opening_started", rendered)
            self.assertNotIn("Pending memory proposals - not written yet:", rendered)

        asyncio.run(run())

    def test_interpret_material_tool_normalizes_explicit_question_for_stored_material(self) -> None:
        async def run() -> None:
            runtime = self._install_in_memory_runtime()
            material = await runtime.service.store_material(
                {
                    "userId": "hermes:default:local",
                    "materialType": "dream",
                    "text": "A bear attacked me and I ran through the forest.",
                }
            )
            response = await runtime.bridge.dispatch(
                build_tool_request(
                    operation="circulatio.material.interpret",
                    payload={
                        "materialId": material["id"],
                        "explicitQuestion": "Can we open this collaboratively?",
                    },
                    tool_name="circulatio_interpret_material",
                    kwargs=self._tool_kwargs(call_id="tool_interpret_existing"),
                )
            )
            self.assertEqual(response["status"], "ok")
            self.assertEqual(response["result"]["materialId"], material["id"])
            self.assertEqual(response["result"]["llmInterpretationHealth"]["status"], "structured")

        asyncio.run(run())

    def test_interpret_material_fallback_returns_continuation_state(self) -> None:
        class TimeoutLlm:
            async def interpret_material(self, input_data: dict[str, object]) -> dict[str, object]:
                del input_data
                raise TimeoutError("timed out")

        async def run() -> None:
            self._install_in_memory_runtime(llm=TimeoutLlm())
            interpreted = json.loads(
                await interpret_material_tool(
                    {
                        "materialType": "reflection",
                        "text": "A bear moved through the trees.",
                    },
                    **self._tool_kwargs(call_id="tool_interpret_fallback_state"),
                )
            )
            continuation = interpreted["result"]["continuationState"]
            self.assertEqual(interpreted["status"], "ok")
            self.assertEqual(interpreted["result"]["llmInterpretationHealth"]["source"], "fallback")
            self.assertEqual(continuation["kind"], "waiting_for_follow_up")
            self.assertEqual(continuation["reason"], "fallback_collaborative_opening")
            self.assertEqual(continuation["storagePolicy"], "no_storage_without_confirmation")
            self.assertEqual(continuation["expectedTargets"], ["personal_amplification"])
            self.assertTrue(continuation["doNotRetryInterpretMaterialWithUnchangedMaterial"])
            self.assertEqual(continuation["nextTool"], "circulatio_method_state_respond")
            self.assertEqual(
                continuation["anchorRefs"]["materialId"], interpreted["result"]["materialId"]
            )
            self.assertEqual(continuation["anchorRefs"]["runId"], interpreted["result"]["runId"])

        asyncio.run(run())

    def test_interpret_material_fallback_sanitizes_internal_diagnostics(self) -> None:
        class TimeoutLlm:
            async def interpret_material(self, input_data: dict[str, object]) -> dict[str, object]:
                del input_data
                raise TimeoutError("timed out")

        async def run() -> None:
            self._install_in_memory_runtime(llm=TimeoutLlm())
            interpreted = json.loads(
                await interpret_material_tool(
                    {
                        "materialType": "dream",
                        "text": "A snake moved through my childhood room.",
                    },
                    **self._tool_kwargs(call_id="tool_interpret_fallback_sanitized"),
                )
            )
            llm_health = interpreted["result"]["llmInterpretationHealth"]
            depth_health = interpreted["result"]["depthEngineHealth"]
            self.assertEqual(
                llm_health,
                {
                    "status": "opened",
                    "source": "fallback",
                    "reason": "collaborative_opening_started",
                },
            )
            self.assertEqual(
                depth_health,
                {
                    "status": "opened",
                    "source": "fallback",
                    "reason": "collaborative_opening_started",
                },
            )
            self.assertNotIn("diagnosticReason", llm_health)
            self.assertNotIn("observations", llm_health)
            self.assertNotIn("symbolMentions", llm_health)
            self.assertNotIn("proposalCandidates", llm_health)

        asyncio.run(run())

    def test_method_state_context_only_fallback_returns_terminal_continuation_state(self) -> None:
        class TimeoutLlm:
            async def interpret_material(self, input_data: dict[str, object]) -> dict[str, object]:
                del input_data
                raise TimeoutError("timed out")

            async def route_method_state_response(
                self, input_data: dict[str, object]
            ) -> dict[str, object]:
                del input_data
                raise AssertionError(
                    "Fallback clarification answers should not hit method-state routing."
                )

        async def run() -> None:
            self._install_in_memory_runtime(llm=TimeoutLlm())
            interpreted = json.loads(
                await interpret_material_tool(
                    {
                        "materialType": "reflection",
                        "text": "A wolf stood at the edge of the clearing.",
                    },
                    **self._tool_kwargs(call_id="tool_interpret_fallback_followup"),
                )
            )
            continuation = interpreted["result"]["continuationState"]
            responded = json.loads(
                await method_state_respond_tool(
                    {
                        "source": "clarifying_answer",
                        "responseText": "The wolf at the edge still feels the most alive.",
                        "anchorRefs": continuation["anchorRefs"],
                    },
                    **self._tool_kwargs(call_id="tool_interpret_fallback_followup_answer"),
                )
            )
            next_state = responded["result"]["continuationState"]
            self.assertEqual(responded["status"], "ok")
            self.assertEqual(next_state["kind"], "context_answer_recorded")
            self.assertTrue(next_state["doNotRetryInterpretMaterialWithUnchangedMaterial"])
            self.assertEqual(next_state["nextAction"], "await_user_input")
            self.assertEqual(responded["message"], "I've kept that with the material.")
            self.assertNotIn("backend", responded["message"].lower())
            self.assertNotIn("failed", responded["message"].lower())

        asyncio.run(run())

    def test_fallback_amplification_answer_captures_personal_association(self) -> None:
        class TimeoutInterpretLlm(FakeCirculatioLlm):
            async def interpret_material(self, input_data: dict[str, object]) -> dict[str, object]:
                del input_data
                raise TimeoutError("timed out")

        async def run() -> None:
            runtime = self._install_in_memory_runtime(llm=TimeoutInterpretLlm())
            interpreted = json.loads(
                await interpret_material_tool(
                    {
                        "materialType": "dream",
                        "text": "A bear attacked me in the forest and I ran into a cave.",
                    },
                    **self._tool_kwargs(call_id="tool_fallback_amp_interpret"),
                )
            )
            continuation = interpreted["result"]["continuationState"]
            responded = json.loads(
                await method_state_respond_tool(
                    {
                        "source": "amplification_answer",
                        "responseText": "The fear while running and the cave feel most charged.",
                        "anchorRefs": continuation["anchorRefs"],
                        "expectedTargets": ["personal_amplification"],
                    },
                    **self._tool_kwargs(call_id="tool_fallback_amp_answer"),
                )
            )
            amplifications = await runtime.repository.list_personal_amplifications(
                "hermes:default:local",
                run_id=interpreted["result"]["runId"],
            )
            self.assertEqual(responded["status"], "ok")
            self.assertEqual(responded["result"]["continuationState"]["kind"], "capture_completed")
            self.assertEqual(len(amplifications), 1)
            self.assertEqual(
                amplifications[0]["associationText"],
                "The fear while running and the cave feel most charged.",
            )

        asyncio.run(run())

    def test_safety_block_returns_blocked_without_pending_proposals(self) -> None:
        async def run() -> None:
            runtime = self._install_fake_runtime()
            response = await runtime.bridge.dispatch(
                {
                    "requestId": "req_blocked",
                    "idempotencyKey": "test:block:1",
                    "userId": "hermes:default:local",
                    "source": {
                        "platform": "cli",
                        "sessionId": "sess_1",
                        "messageId": "msg_blocked",
                        "profile": "default",
                        "rawCommand": "/circulation reflect overloaded",
                    },
                    "operation": "circulatio.material.interpret",
                    "payload": {
                        "materialType": "reflection",
                        "text": "Everything feels overloaded and I cannot slow down.",
                        "safetyContext": {"userReportedActivation": "overwhelming"},
                        "options": {"enableTypology": True},
                    },
                }
            )
            self.assertEqual(response["status"], "blocked")
            self.assertEqual(response["pendingProposals"], [])
            self.assertEqual(response["result"]["safetyStatus"], "grounding_only")

        asyncio.run(run())

    def test_tool_endpoints_cover_full_memory_workflow(self) -> None:
        async def run() -> None:
            self._install_fake_runtime()
            interpret = json.loads(
                await interpret_material_tool(
                    {
                        "materialType": "reflection",
                        "text": "I walked through a house and found a snake image returning after the conflict.",
                    },
                    **self._tool_kwargs(call_id="tool_1"),
                )
            )
            self.assertEqual(interpret["status"], "ok")
            run_id = interpret["result"]["runId"]
            pending = interpret["pendingProposals"]
            self.assertTrue(pending)

            listed = json.loads(
                await list_pending_tool(
                    {"runId": run_id},
                    **self._tool_kwargs(call_id="tool_2"),
                )
            )
            self.assertEqual(len(listed["pendingProposals"]), len(pending))

            first_alias = pending[0]["alias"]
            approved = json.loads(
                await approve_proposals_tool(
                    {"runId": run_id, "proposalRefs": [first_alias]},
                    **self._tool_kwargs(call_id="tool_3"),
                )
            )
            self.assertEqual(approved["status"], "ok")

            symbols = json.loads(await symbols_list_tool({}, **self._tool_kwargs(call_id="tool_4")))
            self.assertEqual(symbols["status"], "ok")
            symbol_id = symbols["result"]["symbols"][0]["id"]

            loaded_symbol = json.loads(
                await symbol_get_tool(
                    {"symbolId": symbol_id},
                    **self._tool_kwargs(call_id="tool_5"),
                )
            )
            self.assertEqual(loaded_symbol["result"]["symbols"][0]["canonicalName"], "snake")

            revised = json.loads(
                await revise_entity_tool(
                    {
                        "entityType": "PersonalSymbol",
                        "entityId": symbol_id,
                        "revisionNote": "Use a more explicit label.",
                        "replacement": {"canonicalName": "serpent"},
                    },
                    **self._tool_kwargs(call_id="tool_6"),
                )
            )
            self.assertEqual(revised["status"], "ok")

            history = json.loads(
                await symbol_history_tool(
                    {"symbolId": symbol_id},
                    **self._tool_kwargs(call_id="tool_7"),
                )
            )
            self.assertEqual(history["status"], "ok")
            self.assertTrue(history["result"]["history"])

            review = json.loads(
                await weekly_review_tool(
                    {"windowStart": "2026-04-12T00:00:00Z", "windowEnd": "2026-04-19T23:59:59Z"},
                    **self._tool_kwargs(call_id="tool_8"),
                )
            )
            self.assertEqual(review["status"], "ok")
            self.assertTrue(review["result"]["reviewId"])

            deleted = json.loads(
                await delete_entity_tool(
                    {"entityType": "PersonalSymbol", "entityId": symbol_id},
                    **self._tool_kwargs(call_id="tool_9"),
                )
            )
            self.assertEqual(deleted["status"], "ok")

        asyncio.run(run())

    def test_rejection_tools_cover_proposals_and_hypotheses(self) -> None:
        async def run() -> None:
            self._install_fake_runtime()
            interpreted = json.loads(
                await interpret_material_tool(
                    {"materialType": "reflection", "text": "A snake crossed the room."},
                    **self._tool_kwargs(call_id="tool_10"),
                )
            )
            run_id = interpreted["result"]["runId"]
            proposal_alias = interpreted["pendingProposals"][0]["alias"]
            rejected = json.loads(
                await reject_proposals_tool(
                    {
                        "runId": run_id,
                        "proposalRefs": [proposal_alias],
                        "reason": "do not save this",
                    },
                    **self._tool_kwargs(call_id="tool_11"),
                )
            )
            self.assertEqual(rejected["status"], "ok")

            listed = json.loads(
                await list_pending_tool(
                    {"runId": run_id},
                    **self._tool_kwargs(call_id="tool_12"),
                )
            )
            self.assertEqual(listed["pendingProposals"], [])

            interpreted_again = json.loads(
                await interpret_material_tool(
                    {"materialType": "reflection", "text": "A snake crossed the room again."},
                    **self._tool_kwargs(call_id="tool_13"),
                )
            )
            runtime = get_runtime("default")
            run_record = await runtime.service.repository.get_interpretation_run(
                "hermes:default:local",
                interpreted_again["result"]["runId"],
            )
            hypothesis_id = run_record["result"]["hypotheses"][0]["id"]
            reject_hypothesis = json.loads(
                await reject_hypotheses_tool(
                    {
                        "runId": interpreted_again["result"]["runId"],
                        "feedbackByHypothesisId": {
                            hypothesis_id: {
                                "feedback": "rejected",
                                "note": "This feels like day residue.",
                            }
                        },
                    },
                    **self._tool_kwargs(call_id="tool_14"),
                )
            )
            self.assertEqual(reject_hypothesis["status"], "ok")

        asyncio.run(run())

    def test_method_state_tool_requires_anchor_for_freeform_followup_and_supports_anchored_capture(
        self,
    ) -> None:
        async def run() -> None:
            self._install_in_memory_runtime()
            invalid = json.loads(
                await method_state_respond_tool(
                    {
                        "source": "freeform_followup",
                        "responseText": "It landed hard.",
                    },
                    **self._tool_kwargs(call_id="tool_method_state_invalid"),
                )
            )
            self.assertEqual(invalid["status"], "validation_error")

            stored = json.loads(
                await store_dream_tool(
                    {"text": "A snake stood in the doorway."},
                    **self._tool_kwargs(call_id="tool_method_state_store"),
                )
            )
            interpreted = json.loads(
                await interpret_material_tool(
                    {"materialId": stored["result"]["materialId"]},
                    **self._tool_kwargs(call_id="tool_method_state_interpret"),
                )
            )
            runtime = get_runtime("default")
            prompts = await runtime.repository.list_amplification_prompts(
                "hermes:default:local",
                run_id=interpreted["result"]["runId"],
            )
            captured = json.loads(
                await method_state_respond_tool(
                    {
                        "source": "amplification_answer",
                        "responseText": "It feels ancient and watchful.",
                        "anchorRefs": {
                            "promptId": prompts[0]["id"],
                            "runId": interpreted["result"]["runId"],
                        },
                        "expectedTargets": ["personal_amplification"],
                    },
                    **self._tool_kwargs(call_id="tool_method_state_capture"),
                )
            )
            self.assertEqual(captured["status"], "ok")
            self.assertTrue(captured["result"]["captureRunId"])
            self.assertEqual(
                captured["result"]["appliedEntityRefs"][0]["entityType"],
                "PersonalAmplification",
            )
            amplifications = await runtime.repository.list_personal_amplifications(
                "hermes:default:local",
                run_id=interpreted["result"]["runId"],
            )
            self.assertEqual(len(amplifications), 1)

        asyncio.run(run())

    def test_method_state_capture_proposals_can_be_listed_and_rejected(self) -> None:
        async def run() -> None:
            self._install_in_memory_runtime()
            stored = json.loads(
                await store_reflection_tool(
                    {"text": "I keep reacting to him like he already decided against me."},
                    **self._tool_kwargs(call_id="tool_method_state_projection_store"),
                )
            )
            captured = json.loads(
                await method_state_respond_tool(
                    {
                        "source": "freeform_followup",
                        "responseText": "It may be my own old authority pattern landing on him.",
                        "anchorRefs": {"materialId": stored["result"]["materialId"]},
                        "expectedTargets": ["projection_hypothesis"],
                    },
                    **self._tool_kwargs(call_id="tool_method_state_projection_capture"),
                )
            )
            self.assertEqual(captured["status"], "ok")
            capture_run_id = captured["result"]["captureRunId"]
            proposal_alias = captured["pendingProposals"][0]["alias"]

            listed = json.loads(
                await list_pending_tool(
                    {"captureRunId": capture_run_id},
                    **self._tool_kwargs(call_id="tool_method_state_projection_list"),
                )
            )
            self.assertEqual(listed["status"], "ok")
            self.assertEqual(
                [item["alias"] for item in listed["pendingProposals"]], [proposal_alias]
            )

            rejected = json.loads(
                await reject_proposals_tool(
                    {
                        "captureRunId": capture_run_id,
                        "proposalRefs": [proposal_alias],
                        "reason": "not yet",
                    },
                    **self._tool_kwargs(call_id="tool_method_state_projection_reject"),
                )
            )
            self.assertEqual(rejected["status"], "ok")
            self.assertEqual(rejected["pendingProposals"], [])

        asyncio.run(run())

    def test_phase_8_9_tools_cover_reviews_packets_and_direct_capture(self) -> None:
        async def run() -> None:
            self._install_in_memory_runtime()
            anchors = json.loads(
                await capture_reality_anchors_tool(
                    {
                        "summary": "Work and relationships are intact enough to hold symbolic material.",
                        "anchorSummary": "Outer-life continuity is present, though tender.",
                        "workDailyLifeContinuity": "stable",
                        "sleepBodyRegulation": "mixed",
                        "relationshipContact": "available",
                        "reflectiveCapacity": "present",
                    },
                    **self._tool_kwargs(call_id="tool_phase8_anchors"),
                )
            )
            self.assertEqual(anchors["status"], "ok")
            self.assertTrue(anchors["result"]["individuationRecordId"])

            threshold_review = json.loads(
                await threshold_review_tool(
                    {
                        "windowStart": "2026-04-12T00:00:00Z",
                        "windowEnd": "2026-04-19T23:59:59Z",
                    },
                    **self._tool_kwargs(call_id="tool_phase8_threshold_review"),
                )
            )
            self.assertEqual(threshold_review["status"], "ok")
            self.assertTrue(threshold_review["result"]["reviewId"])

            living_myth_review = json.loads(
                await living_myth_review_tool(
                    {
                        "windowStart": "2026-04-01T00:00:00Z",
                        "windowEnd": "2026-04-19T23:59:59Z",
                    },
                    **self._tool_kwargs(call_id="tool_phase8_living_review"),
                )
            )
            self.assertEqual(living_myth_review["status"], "ok")
            self.assertTrue(living_myth_review["result"]["reviewId"])

            analysis_packet = json.loads(
                await analysis_packet_tool(
                    {
                        "windowStart": "2026-04-12T00:00:00Z",
                        "windowEnd": "2026-04-19T23:59:59Z",
                        "packetFocus": "threshold",
                    },
                    **self._tool_kwargs(call_id="tool_phase8_packet"),
                )
            )
            self.assertEqual(analysis_packet["status"], "ok")
            self.assertTrue(analysis_packet["result"]["packetId"])
            self.assertEqual(analysis_packet["result"]["packetTitle"], "Analysis packet")

        asyncio.run(run())

    def test_analysis_packet_tool_surfaces_readable_function_dynamics_without_recovery_hint(
        self,
    ) -> None:
        async def run() -> None:
            self._install_in_memory_runtime()
            runtime = get_runtime("default")
            await runtime.repository.create_typology_lens(
                {
                    "id": "typology_bridge_1",
                    "userId": "hermes:default:local",
                    "role": "dominant",
                    "function": "thinking",
                    "claim": "Reflection tends to lead.",
                    "confidence": "medium",
                    "status": "candidate",
                    "evidenceIds": ["evidence_1"],
                    "counterevidenceIds": [],
                    "userTestPrompt": "Does reflection lead first?",
                    "linkedMaterialIds": ["material_1"],
                    "createdAt": "2026-04-18T09:00:00Z",
                    "updatedAt": "2026-04-18T09:00:00Z",
                }
            )
            response = json.loads(
                await analysis_packet_tool(
                    {
                        "windowStart": "2026-04-12T00:00:00Z",
                        "windowEnd": "2026-04-19T23:59:59Z",
                        "analyticLens": "typology_function_dynamics",
                    },
                    **self._tool_kwargs(call_id="tool_packet_typology_readable"),
                )
            )
            self.assertEqual(response["status"], "ok")
            self.assertEqual(response["result"]["functionDynamics"]["status"], "readable")
            self.assertNotIn("recoveryHint", response["result"])

        asyncio.run(run())

    def test_analysis_packet_tool_adds_recovery_hint_for_signals_only_function_dynamics(
        self,
    ) -> None:
        async def run() -> None:
            self._install_in_memory_runtime()
            runtime = get_runtime("default")
            await runtime.repository.create_typology_lens(
                {
                    "id": "typology_bridge_2",
                    "userId": "hermes:default:local",
                    "role": "inferior",
                    "function": "sensation",
                    "claim": "Body contact drops out under strain.",
                    "confidence": "low",
                    "status": "user_refined",
                    "evidenceIds": [],
                    "counterevidenceIds": [],
                    "userTestPrompt": "Does sensation fall away first?",
                    "linkedMaterialIds": [],
                    "createdAt": "2026-04-18T09:00:00Z",
                    "updatedAt": "2026-04-18T09:00:00Z",
                }
            )
            response = json.loads(
                await analysis_packet_tool(
                    {
                        "windowStart": "2026-04-12T00:00:00Z",
                        "windowEnd": "2026-04-19T23:59:59Z",
                        "analyticLens": "typology_function_dynamics",
                    },
                    **self._tool_kwargs(call_id="tool_packet_typology_signals"),
                )
            )
            self.assertEqual(response["status"], "ok")
            self.assertEqual(response["result"]["functionDynamics"]["status"], "signals_only")
            self.assertIn("recoveryHint", response["result"])

        asyncio.run(run())

    def test_discovery_tool_preserves_typology_analytic_lens(self) -> None:
        async def run() -> None:
            self._install_in_memory_runtime()
            runtime = get_runtime("default")
            await runtime.repository.create_typology_lens(
                {
                    "id": "typology_bridge_3",
                    "userId": "hermes:default:local",
                    "role": "dominant",
                    "function": "intuition",
                    "claim": "Images stay foregrounded.",
                    "confidence": "medium",
                    "status": "candidate",
                    "evidenceIds": ["evidence_1"],
                    "counterevidenceIds": [],
                    "userTestPrompt": "Do images arrive before analysis?",
                    "linkedMaterialIds": [],
                    "createdAt": "2026-04-18T09:00:00Z",
                    "updatedAt": "2026-04-18T09:00:00Z",
                }
            )
            response = json.loads(
                await discovery_tool(
                    {
                        "windowStart": "2026-04-12T00:00:00Z",
                        "windowEnd": "2026-04-19T23:59:59Z",
                        "analyticLens": "typology_function_dynamics",
                    },
                    **self._tool_kwargs(call_id="tool_discovery_typology_lens"),
                )
            )
            self.assertEqual(response["status"], "ok")
            discovery = response["result"]["discovery"]
            self.assertTrue(
                any(section["key"] == "function_dynamics" for section in discovery["sections"])
            )

        asyncio.run(run())

    def test_review_proposal_tools_cover_living_myth_approval_and_threshold_rejection(self) -> None:
        async def run() -> None:
            self._install_in_memory_runtime()
            runtime = get_runtime("default")
            await runtime.service.create_and_interpret_material(
                {
                    "userId": "hermes:default:local",
                    "materialType": "dream",
                    "text": "A work threshold and authority scene returned in the dream.",
                    "materialDate": "2026-04-18T08:00:00Z",
                }
            )
            approved_review = json.loads(
                await living_myth_review_tool(
                    {},
                    **self._tool_kwargs(call_id="tool_phase8_review_approve"),
                )
            )
            self.assertEqual(approved_review["status"], "ok")
            review_id = approved_review["result"]["reviewId"]
            review_aliases = [item["alias"] for item in approved_review["pendingProposals"]]

            listed = json.loads(
                await list_pending_review_proposals_tool(
                    {"reviewId": review_id},
                    **self._tool_kwargs(call_id="tool_phase8_review_list"),
                )
            )
            self.assertEqual([item["alias"] for item in listed["pendingProposals"]], review_aliases)

            approved = json.loads(
                await approve_review_proposals_tool(
                    {"reviewId": review_id, "proposalRefs": [review_aliases[0]]},
                    **self._tool_kwargs(call_id="tool_phase8_review_apply"),
                )
            )
            self.assertEqual(approved["status"], "ok")
            thresholds = await runtime.repository.list_individuation_records(
                "hermes:default:local",
                record_types=["threshold_process"],
                limit=20,
            )
            self.assertEqual(len(thresholds), 1)

            rejected_review = json.loads(
                await threshold_review_tool(
                    {},
                    **self._tool_kwargs(call_id="tool_phase8_review_reject"),
                )
            )
            self.assertEqual(rejected_review["status"], "ok")
            reject_review_id = rejected_review["result"]["reviewId"]
            reject_alias = rejected_review["pendingProposals"][0]["alias"]

            rejected = json.loads(
                await reject_review_proposals_tool(
                    {
                        "reviewId": reject_review_id,
                        "proposalRefs": [reject_alias],
                        "reason": "do not save this",
                    },
                    **self._tool_kwargs(call_id="tool_phase8_review_reject_apply"),
                )
            )
            self.assertEqual(rejected["status"], "ok")
            self.assertEqual(rejected["pendingProposals"], [])

            listed_after_reject = json.loads(
                await list_pending_review_proposals_tool(
                    {"reviewId": reject_review_id},
                    **self._tool_kwargs(call_id="tool_phase8_review_reject_list"),
                )
            )
            self.assertEqual(listed_after_reject["pendingProposals"], [])

        asyncio.run(run())

    def test_store_tools_and_alive_today_cover_store_first_host_flow(self) -> None:
        async def run() -> None:
            self._install_fake_runtime()
            stored_dream = json.loads(
                await store_dream_tool(
                    {"text": "A serpent moved through the house."},
                    **self._tool_kwargs(call_id="tool_store_1"),
                )
            )
            stored_event = json.loads(
                await store_event_tool(
                    {"text": "The meeting with my manager felt electric."},
                    **self._tool_kwargs(call_id="tool_store_2"),
                )
            )
            stored_reflection = json.loads(
                await store_reflection_tool(
                    {"text": "The image stayed with me all day."},
                    **self._tool_kwargs(call_id="tool_store_3"),
                )
            )
            stored_symbolic = json.loads(
                await store_symbolic_note_tool(
                    {"text": "Snake, stairs, and water keep repeating."},
                    **self._tool_kwargs(call_id="tool_store_4"),
                )
            )
            stored_body = json.loads(
                await store_body_state_tool(
                    {
                        "sensation": "tightness",
                        "bodyRegion": "chest",
                        "noteText": "My chest locked as soon as the email arrived.",
                    },
                    **self._tool_kwargs(call_id="tool_store_5"),
                )
            )
            self.assertEqual(stored_dream["status"], "ok")
            self.assertEqual(stored_event["status"], "ok")
            self.assertEqual(stored_reflection["status"], "ok")
            self.assertEqual(stored_symbolic["status"], "ok")
            self.assertEqual(stored_body["status"], "ok")
            self.assertEqual(
                stored_dream["message"], "Held your dream. If you want, we can open it together."
            )
            self.assertEqual(
                stored_reflection["message"],
                "Held your reflection. Want to explore what comes up?",
            )
            self.assertIn("intakeContext", stored_dream["result"])
            self.assertEqual(stored_dream["result"]["intakeContext"]["visibility"], "host_only")
            self.assertEqual(
                stored_dream["result"]["intakeContext"]["source"], "circulatio-post-store"
            )
            self.assertTrue(stored_dream["result"]["intakeContext"]["hostGuidance"]["holdFirst"])
            self.assertFalse(
                stored_dream["result"]["intakeContext"]["hostGuidance"]["allowAutoInterpretation"]
            )
            self.assertEqual(
                stored_dream["result"]["intakeContext"]["sourceCounts"]["intakeItemCount"],
                len(stored_dream["result"]["intakeContext"]["items"]),
            )
            self.assertIn("material", stored_dream["result"])
            self.assertEqual(
                stored_dream["result"]["material"]["id"],
                stored_dream["result"]["materialId"],
            )
            self.assertIn("continuitySummary", stored_dream["result"])
            self.assertEqual(
                stored_dream["result"]["continuitySummary"]["windowStart"],
                stored_dream["result"]["intakeContext"]["windowStart"],
            )
            self.assertEqual(
                stored_dream["result"]["continuitySummary"]["windowEnd"],
                stored_dream["result"]["intakeContext"]["windowEnd"],
            )
            self.assertGreaterEqual(
                stored_dream["result"]["continuitySummary"]["threadCount"],
                len(stored_dream["result"]["continuitySummary"]["threads"]),
            )
            self.assertNotIn("methodContextSnapshot", stored_dream["result"]["continuitySummary"])
            self.assertEqual(
                stored_dream["result"]["intakeContext"]["materialId"],
                stored_dream["result"]["materialId"],
            )
            self.assertEqual(stored_dream["pendingProposals"], [])
            runtime = get_runtime("default")
            materials = await runtime.service.repository.list_materials("hermes:default:local")
            runs = await runtime.service.repository.list_interpretation_runs("hermes:default:local")
            body_states = await runtime.service.repository.list_body_states("hermes:default:local")
            practices = await runtime.service.repository.list_practice_sessions(
                "hermes:default:local"
            )
            self.assertEqual(len(runs), 0)
            self.assertEqual(len(body_states), 1)
            self.assertEqual(practices, [])
            self.assertEqual(
                {item["materialType"] for item in materials},
                {"dream", "charged_event", "reflection", "symbolic_motif"},
            )

            weave = json.loads(
                await alive_today_tool(
                    {"windowStart": "2026-04-12T00:00:00Z", "windowEnd": "2026-04-19T23:59:59Z"},
                    **self._tool_kwargs(call_id="tool_store_6"),
                )
            )
            self.assertEqual(weave["status"], "ok")
            self.assertTrue(weave["result"]["summaryId"])
            self.assertIn("continuitySummary", weave["result"])
            self.assertIn("threadCount", weave["result"]["continuitySummary"])
            self.assertNotIn("methodContextSnapshot", weave["result"]["continuitySummary"])
            reviews = await runtime.service.repository.list_weekly_reviews("hermes:default:local")
            self.assertEqual(reviews, [])

        asyncio.run(run())

    def test_store_tool_returns_intake_context_without_auto_interpretation(self) -> None:
        async def run() -> None:
            self._install_fake_runtime()
            stored = json.loads(
                await store_dream_tool(
                    {"text": "A fox waited by the gate."},
                    **self._tool_kwargs(call_id="tool_store_intake_context"),
                )
            )

            self.assertEqual(stored["status"], "ok")
            self.assertEqual(
                stored["message"], "Held your dream. If you want, we can open it together."
            )
            self.assertEqual(stored["result"]["materialType"], "dream")
            self.assertEqual(
                stored["result"]["intakeContext"]["materialId"],
                stored["result"]["materialId"],
            )
            self.assertEqual(
                stored["result"]["material"]["id"],
                stored["result"]["materialId"],
            )
            self.assertEqual(stored["result"]["intakeContext"]["visibility"], "host_only")
            self.assertEqual(stored["result"]["intakeContext"]["source"], "circulatio-post-store")
            self.assertTrue(stored["result"]["intakeContext"]["hostGuidance"]["holdFirst"])
            self.assertFalse(
                stored["result"]["intakeContext"]["hostGuidance"]["allowAutoInterpretation"]
            )
            self.assertEqual(
                stored["result"]["intakeContext"]["sourceCounts"]["intakeItemCount"],
                len(stored["result"]["intakeContext"]["items"]),
            )
            self.assertEqual(stored["pendingProposals"], [])

            runtime = get_runtime("default")
            runs = await runtime.service.repository.list_interpretation_runs("hermes:default:local")
            reviews = await runtime.service.repository.list_weekly_reviews("hermes:default:local")
            practices = await runtime.service.repository.list_practice_sessions(
                "hermes:default:local"
            )
            self.assertEqual(runs, [])
            self.assertEqual(reviews, [])
            self.assertEqual(practices, [])

        asyncio.run(run())

    def test_store_dream_tool_preserves_dream_structure_without_interpretation(self) -> None:
        async def run() -> None:
            self._install_fake_runtime()
            stored = json.loads(
                await store_dream_tool(
                    {
                        "text": "A bear waited at the threshold.",
                        "dreamStructure": {
                            "setting": "forest edge",
                            "keyImages": ["bear", "threshold"],
                            "methodDynamics": True,
                        },
                    },
                    **self._tool_kwargs(call_id="tool_store_dream_structure"),
                )
            )

            self.assertEqual(stored["status"], "ok")
            self.assertEqual(
                stored["result"]["material"]["dreamStructure"],
                {
                    "setting": "forest edge",
                    "keyImages": ["bear", "threshold"],
                    "methodDynamics": True,
                },
            )
            runtime = get_runtime("default")
            material = await runtime.service.repository.get_material(
                "hermes:default:local",
                stored["result"]["materialId"],
            )
            self.assertEqual(
                material["dreamStructure"], stored["result"]["material"]["dreamStructure"]
            )
            self.assertEqual(
                await runtime.service.repository.list_interpretation_runs("hermes:default:local"),
                [],
            )

        asyncio.run(run())

    def test_bridge_store_material_accepts_summary_only_payload(self) -> None:
        async def run() -> None:
            runtime = self._install_in_memory_runtime()
            response = await runtime.bridge.dispatch(
                build_tool_request(
                    operation="circulatio.material.store",
                    payload={
                        "materialType": "reflection",
                        "summary": "Keep this brief note without opening it yet.",
                    },
                    tool_name="circulatio_store_reflection",
                    kwargs=self._tool_kwargs(call_id="tool_store_summary_only"),
                )
            )
            self.assertEqual(response["status"], "ok")
            self.assertEqual(
                response["result"]["material"]["summary"],
                "Keep this brief note without opening it yet.",
            )
            self.assertNotIn("text", response["result"]["material"])
            self.assertEqual(
                response["result"]["intakeContext"]["materialId"], response["result"]["materialId"]
            )
            self.assertEqual(
                await runtime.service.repository.list_interpretation_runs("hermes:default:local"),
                [],
            )

        asyncio.run(run())

    def test_interpret_material_supports_material_id_after_store(self) -> None:
        async def run() -> None:
            self._install_fake_runtime()
            stored = json.loads(
                await store_reflection_tool(
                    {"text": "A snake kept appearing in memory after the meeting."},
                    **self._tool_kwargs(call_id="tool_material_id_store"),
                )
            )
            interpreted = json.loads(
                await interpret_material_tool(
                    {"materialId": stored["result"]["materialId"]},
                    **self._tool_kwargs(call_id="tool_material_id_interpret"),
                )
            )
            self.assertEqual(interpreted["status"], "ok")
            self.assertEqual(interpreted["result"]["materialId"], stored["result"]["materialId"])
            self.assertTrue(interpreted["result"]["runId"])

        asyncio.run(run())

    def test_graph_memory_and_dashboard_tools_expose_backend_reads(self) -> None:
        async def run() -> None:
            self._install_fake_runtime()
            stored = json.loads(
                await store_reflection_tool(
                    {"text": "A snake kept appearing in memory after the meeting."},
                    **self._tool_kwargs(call_id="tool_graph_store"),
                )
            )
            interpreted = json.loads(
                await interpret_material_tool(
                    {"materialId": stored["result"]["materialId"]},
                    **self._tool_kwargs(call_id="tool_graph_interpret"),
                )
            )
            approved = json.loads(
                await approve_proposals_tool(
                    {
                        "runId": interpreted["result"]["runId"],
                        "proposalRefs": [
                            item["alias"] for item in interpreted.get("pendingProposals", [])
                        ],
                    },
                    **self._tool_kwargs(call_id="tool_graph_approve"),
                )
            )
            self.assertEqual(approved["status"], "ok")

            graph = json.loads(
                await query_graph_tool(
                    {
                        "rootNodeIds": [stored["result"]["materialId"]],
                        "maxDepth": 2,
                        "includeEvidence": True,
                    },
                    **self._tool_kwargs(call_id="tool_graph_query"),
                )
            )
            self.assertEqual(graph["status"], "ok")
            self.assertGreater(graph["result"]["nodeCount"], 0)
            self.assertGreater(graph["result"]["edgeCount"], 0)

            memory = json.loads(
                await memory_kernel_tool(
                    {"textQuery": "snake", "limit": 5},
                    **self._tool_kwargs(call_id="tool_memory_kernel"),
                )
            )
            self.assertEqual(memory["status"], "ok")
            self.assertGreater(memory["result"]["itemCount"], 0)

            dashboard = json.loads(
                await dashboard_summary_tool(
                    {},
                    **self._tool_kwargs(call_id="tool_dashboard_summary"),
                )
            )
            self.assertEqual(dashboard["status"], "ok")
            self.assertGreaterEqual(dashboard["result"]["recentMaterialCount"], 1)

        asyncio.run(run())

    def test_discovery_tool_builds_read_only_digest_without_writes(self) -> None:
        async def run() -> None:
            self._install_fake_runtime()
            runtime = get_runtime("default")
            stored = json.loads(
                await store_reflection_tool(
                    {"text": "A snake kept appearing in memory after the meeting."},
                    **self._tool_kwargs(call_id="tool_discovery_store"),
                )
            )
            interpreted = json.loads(
                await interpret_material_tool(
                    {"materialId": stored["result"]["materialId"]},
                    **self._tool_kwargs(call_id="tool_discovery_interpret"),
                )
            )
            approved = json.loads(
                await approve_proposals_tool(
                    {
                        "runId": interpreted["result"]["runId"],
                        "proposalRefs": [
                            item["alias"] for item in interpreted.get("pendingProposals", [])
                        ],
                    },
                    **self._tool_kwargs(call_id="tool_discovery_approve"),
                )
            )
            self.assertEqual(approved["status"], "ok")

            before_materials = await runtime.repository.list_materials("hermes:default:local")
            before_runs = await runtime.repository.list_interpretation_runs("hermes:default:local")
            before_reviews = await runtime.repository.list_weekly_reviews("hermes:default:local")

            discovery = json.loads(
                await discovery_tool(
                    {"textQuery": "snake", "maxItems": 4},
                    **self._tool_kwargs(call_id="tool_discovery_read"),
                )
            )
            self.assertEqual(discovery["status"], "ok")
            self.assertEqual(discovery["pendingProposals"], [])
            self.assertTrue(discovery["result"]["discoveryId"])
            self.assertEqual(discovery["result"]["sectionCount"], 8)
            self.assertEqual(
                [section["key"] for section in discovery["result"]["discovery"]["sections"]],
                [
                    "recurring",
                    "dream_body_event_links",
                    "ripe_to_revisit",
                    "conscious_attitude",
                    "body_states",
                    "method_state",
                    "journey_threads",
                    "held_for_now",
                ],
            )
            self.assertGreaterEqual(discovery["result"]["sourceCounts"]["memoryItemCount"], 0)
            self.assertGreaterEqual(discovery["result"]["sourceCounts"]["graphNodeCount"], 0)
            self.assertIn("Discovery digest", discovery["result"]["discovery"]["fallbackText"])

            after_materials = await runtime.repository.list_materials("hermes:default:local")
            after_runs = await runtime.repository.list_interpretation_runs("hermes:default:local")
            after_reviews = await runtime.repository.list_weekly_reviews("hermes:default:local")
            self.assertEqual(len(after_materials), len(before_materials))
            self.assertEqual(len(after_runs), len(before_runs))
            self.assertEqual(len(after_reviews), len(before_reviews))

        asyncio.run(run())

    def test_practice_and_brief_tools_cover_new_runtime_surface(self) -> None:
        async def run() -> None:
            self._install_in_memory_runtime()
            practice = json.loads(
                await generate_practice_recommendation_tool(
                    {},
                    **self._tool_kwargs(call_id="tool_practice_1"),
                )
            )
            self.assertEqual(practice["status"], "ok")
            practice_session_id = practice["result"]["practiceSessionId"]
            accepted = json.loads(
                await respond_practice_recommendation_tool(
                    {"practiceSessionId": practice_session_id, "action": "accepted"},
                    **self._tool_kwargs(call_id="tool_practice_2"),
                )
            )
            self.assertEqual(accepted["status"], "ok")
            briefs = json.loads(
                await generate_rhythmic_briefs_tool(
                    {},
                    **self._tool_kwargs(call_id="tool_brief_1"),
                )
            )
            self.assertEqual(briefs["status"], "ok")
            if briefs["result"]["briefs"]:
                brief_id = briefs["result"]["briefs"][0]["id"]
                dismissed = json.loads(
                    await respond_rhythmic_brief_tool(
                        {"briefId": brief_id, "action": "dismissed"},
                        **self._tool_kwargs(call_id="tool_brief_2"),
                    )
                )
                self.assertEqual(dismissed["status"], "ok")

        asyncio.run(run())

    def test_feedback_tools_cover_interpretation_and_practice_feedback_surface(self) -> None:
        async def run() -> None:
            self._install_fake_runtime()
            stored = json.loads(
                await store_reflection_tool(
                    {"text": "A sharp image stayed after the conflict."},
                    **self._tool_kwargs(call_id="tool_feedback_store"),
                )
            )
            interpreted = json.loads(
                await interpret_material_tool(
                    {"materialId": stored["result"]["materialId"]},
                    **self._tool_kwargs(call_id="tool_feedback_interpret"),
                )
            )
            interpretation_feedback = json.loads(
                await record_interpretation_feedback_tool(
                    {
                        "runId": interpreted["result"]["runId"],
                        "feedback": "too_much",
                        "note": "Zu dicht.",
                        "locale": "de-DE",
                    },
                    **self._tool_kwargs(call_id="tool_feedback_interpretation"),
                )
            )
            self.assertEqual(interpretation_feedback["status"], "ok")

            practice = json.loads(
                await generate_practice_recommendation_tool(
                    {},
                    **self._tool_kwargs(call_id="tool_feedback_practice_seed"),
                )
            )
            practice_feedback = json.loads(
                await record_practice_feedback_tool(
                    {
                        "practiceSessionId": practice["result"]["practiceSessionId"],
                        "feedback": "too_long",
                        "note": "Demasiado largo.",
                        "locale": "es-ES",
                    },
                    **self._tool_kwargs(call_id="tool_feedback_practice"),
                )
            )
            self.assertEqual(practice_feedback["status"], "ok")

        asyncio.run(run())

    def test_command_path_supports_practice_and_brief_subcommands(self) -> None:
        async def run() -> None:
            self._install_in_memory_runtime()
            rendered_practice = await handle_circulation(
                "practice",
                **self._kwargs(message_id="msg_practice"),
            )
            self.assertIn("Practice:", rendered_practice)
            runtime = get_runtime("default")
            practices = await runtime.repository.list_practice_sessions("hermes:default:local")
            self.assertTrue(practices)
            rendered_accept = await handle_circulation(
                f"practice accept {practices[0]['id']}",
                **self._kwargs(message_id="msg_practice_accept"),
            )
            self.assertIn("Practice accepted.", rendered_accept)
            rendered_brief = await handle_circulation(
                "brief",
                **self._kwargs(message_id="msg_brief"),
            )
            self.assertIn("Rhythmic briefs:", rendered_brief)

        asyncio.run(run())

    def test_command_path_supports_discovery_subcommand(self) -> None:
        async def run() -> None:
            self._install_fake_runtime()
            runtime = get_runtime("default")
            stored = json.loads(
                await store_reflection_tool(
                    {"text": "A snake kept appearing in memory after the meeting."},
                    **self._tool_kwargs(call_id="tool_command_discovery_store"),
                )
            )
            interpreted = json.loads(
                await interpret_material_tool(
                    {"materialId": stored["result"]["materialId"]},
                    **self._tool_kwargs(call_id="tool_command_discovery_interpret"),
                )
            )
            approved = json.loads(
                await approve_proposals_tool(
                    {
                        "runId": interpreted["result"]["runId"],
                        "proposalRefs": [
                            item["alias"] for item in interpreted.get("pendingProposals", [])
                        ],
                    },
                    **self._tool_kwargs(call_id="tool_command_discovery_approve"),
                )
            )
            self.assertEqual(approved["status"], "ok")

            before_materials = await runtime.repository.list_materials("hermes:default:local")
            before_runs = await runtime.repository.list_interpretation_runs("hermes:default:local")
            before_reviews = await runtime.repository.list_weekly_reviews("hermes:default:local")

            rendered = await handle_circulation(
                "discovery --query snake",
                **self._kwargs(message_id="msg_discovery"),
            )
            self.assertIn("Discovery digest", rendered)
            self.assertIn("Recurring", rendered)

            after_materials = await runtime.repository.list_materials("hermes:default:local")
            after_runs = await runtime.repository.list_interpretation_runs("hermes:default:local")
            after_reviews = await runtime.repository.list_weekly_reviews("hermes:default:local")
            self.assertEqual(len(after_materials), len(before_materials))
            self.assertEqual(len(after_runs), len(before_runs))
            self.assertEqual(len(after_reviews), len(before_reviews))

        asyncio.run(run())

    def test_scheduled_brief_generation_respects_proactive_consent(self) -> None:
        async def run() -> None:
            self._install_in_memory_runtime()
            runtime = get_runtime("default")
            await runtime.service.set_consent_preference(
                {
                    "userId": "hermes:default:local",
                    "scope": "proactive_briefing",
                    "status": "revoked",
                }
            )
            response = json.loads(
                await generate_rhythmic_briefs_tool(
                    {"source": "scheduled"},
                    **self._tool_kwargs(call_id="tool_brief_scheduled"),
                )
            )
            self.assertEqual(response["status"], "ok")
            self.assertEqual(response["result"]["briefs"], [])

        asyncio.run(run())

    def test_dream_interpretation_returns_llm_method_gate_and_pending_proposals(self) -> None:
        async def run() -> None:
            self._install_fake_runtime()
            stored = json.loads(
                await store_dream_tool(
                    {"text": "There was a snake in the house."},
                    **self._tool_kwargs(call_id="tool_dream_gate_store"),
                )
            )
            interpreted = json.loads(
                await interpret_material_tool(
                    {"materialId": stored["result"]["materialId"]},
                    **self._tool_kwargs(call_id="tool_dream_gate_interpret"),
                )
            )
            self.assertEqual(interpreted["status"], "ok")
            self.assertTrue(interpreted["pendingProposals"])
            self.assertIn("methodGate", interpreted["result"])
            self.assertEqual(
                interpreted["result"]["methodGate"]["depthLevel"],
                "personal_amplification_needed",
            )
            self.assertNotIn(
                "dream_narrative",
                interpreted["result"]["methodGate"]["missingPrerequisites"],
            )
            self.assertIn(
                "conscious_attitude",
                interpreted["result"]["methodGate"]["missingPrerequisites"],
            )

        asyncio.run(run())

    def test_material_lookup_tools_support_interpreting_existing_material(self) -> None:
        async def run() -> None:
            self._install_fake_runtime()
            stored = json.loads(
                await store_dream_tool(
                    {
                        "text": "A bear followed me through the house and I kept hiding.",
                        "title": "Bear dream",
                        "tags": ["bear", "pursuit"],
                    },
                    **self._tool_kwargs(call_id="tool_material_lookup_store"),
                )
            )
            listed = json.loads(
                await list_materials_tool(
                    {"materialTypes": ["dream"], "limit": 5},
                    **self._tool_kwargs(call_id="tool_material_lookup_list"),
                )
            )
            self.assertEqual(listed["status"], "ok")
            self.assertEqual(listed["result"]["materialCount"], 1)
            self.assertEqual(
                listed["result"]["materials"][0]["id"],
                stored["result"]["materialId"],
            )
            self.assertIn("bear", listed["result"]["materials"][0]["text"].lower())

            loaded = json.loads(
                await get_material_tool(
                    {"materialId": stored["result"]["materialId"]},
                    **self._tool_kwargs(call_id="tool_material_lookup_get"),
                )
            )
            self.assertEqual(loaded["status"], "ok")
            self.assertEqual(loaded["result"]["materialType"], "dream")
            self.assertEqual(
                loaded["result"]["material"]["id"],
                stored["result"]["materialId"],
            )

            interpreted = json.loads(
                await interpret_material_tool(
                    {"materialId": loaded["result"]["materialId"]},
                    **self._tool_kwargs(call_id="tool_material_lookup_interpret"),
                )
            )
            self.assertEqual(interpreted["status"], "ok")
            self.assertEqual(interpreted["result"]["materialId"], stored["result"]["materialId"])

        asyncio.run(run())

    def test_plugin_registers_command_tools_and_skill(self) -> None:
        ctx = _FakeHermesContext()
        register(ctx)
        self.assertIn("circulation", ctx.commands)
        self.assertEqual(
            set(ctx.tools),
            {
                "circulatio_store_dream",
                "circulatio_store_event",
                "circulatio_store_reflection",
                "circulatio_store_symbolic_note",
                "circulatio_store_body_state",
                "circulatio_alive_today",
                "circulatio_journey_page",
                "circulatio_query_graph",
                "circulatio_dashboard_summary",
                "circulatio_memory_kernel",
                "circulatio_discovery",
                "circulatio_create_journey",
                "circulatio_list_journeys",
                "circulatio_get_journey",
                "circulatio_update_journey",
                "circulatio_set_journey_status",
                "circulatio_list_materials",
                "circulatio_get_material",
                "circulatio_interpret_material",
                "circulatio_list_pending",
                "circulatio_approve_proposals",
                "circulatio_reject_proposals",
                "circulatio_reject_hypotheses",
                "circulatio_revise_entity",
                "circulatio_delete_entity",
                "circulatio_symbols_list",
                "circulatio_symbol_get",
                "circulatio_symbol_history",
                "circulatio_weekly_review",
                "circulatio_threshold_review",
                "circulatio_living_myth_review",
                "circulatio_analysis_packet",
                "circulatio_list_pending_review_proposals",
                "circulatio_approve_review_proposals",
                "circulatio_reject_review_proposals",
                "circulatio_witness_state",
                "circulatio_capture_conscious_attitude",
                "circulatio_capture_reality_anchors",
                "circulatio_upsert_threshold_process",
                "circulatio_record_relational_scene",
                "circulatio_record_inner_outer_correspondence",
                "circulatio_record_numinous_encounter",
                "circulatio_record_aesthetic_resonance",
                "circulatio_set_consent",
                "circulatio_answer_amplification",
                "circulatio_method_state_respond",
                "circulatio_upsert_goal",
                "circulatio_upsert_goal_tension",
                "circulatio_set_cultural_frame",
                "circulatio_generate_practice_recommendation",
                "circulatio_respond_practice_recommendation",
                "circulatio_record_interpretation_feedback",
                "circulatio_record_practice_feedback",
                "circulatio_plan_ritual",
                "circulatio_generate_rhythmic_briefs",
                "circulatio_respond_rhythmic_brief",
            },
        )
        self.assertIn("circulation", ctx.skills)

    def test_plugin_registers_against_modern_hermes_tool_signature(self) -> None:
        ctx = _FakeModernHermesContext()
        register(ctx)
        self.assertTrue(all(tool["toolset"] == "circulatio" for tool in ctx.tools.values()))
        self.assertTrue(all(tool["is_async"] for tool in ctx.tools.values()))
        self.assertIn("circulatio_alive_today", ctx.tools)
        self.assertIn("circulatio_discovery", ctx.tools)
        self.assertIn("circulatio_weekly_review", ctx.tools)
        self.assertIn("circulatio_method_state_respond", ctx.tools)
        self.assertIn("circulatio_plan_ritual", ctx.tools)
        self.assertIn(
            "one ritual-planning call",
            ctx.tools["circulatio_plan_ritual"]["description"],
        )
        self.assertIn(
            "continuationState.doNotRetryInterpretMaterialWithUnchangedMaterial",
            ctx.tools["circulatio_interpret_material"]["description"],
        )
        self.assertIn(
            "do not call this tool again with unchanged material",
            ctx.tools["circulatio_interpret_material"]["description"],
        )
        self.assertIn(
            "do not frame it as a backend failure",
            ctx.tools["circulatio_interpret_material"]["description"],
        )
        self.assertIn(
            "A bounded recovery retry is allowed",
            ctx.tools["circulatio_interpret_material"]["description"],
        )
        self.assertIn(
            "requests to explain repeated calls or list the errors in English are not permission",
            ctx.tools["circulatio_interpret_material"]["description"],
        )
        self.assertIn(
            "A valid first response may be a single question",
            ctx.tools["circulatio_interpret_material"]["description"],
        )
        self.assertIn(
            "usually 1-3 sentences with exactly one question",
            ctx.tools["circulatio_interpret_material"]["description"],
        )
        self.assertIn(
            "do not present a numbered menu",
            ctx.tools["circulatio_store_dream"]["description"],
        )
        self.assertIn("host-only intakeContext", ctx.tools["circulatio_store_dream"]["description"])
        self.assertIn(
            "summary",
            ctx.tools["circulatio_store_reflection"]["schema"]["parameters"]["properties"],
        )
        self.assertIn(
            "dreamStructure",
            ctx.tools["circulatio_store_dream"]["schema"]["parameters"]["properties"],
        )
        self.assertNotIn(
            "dreamStructure",
            ctx.tools["circulatio_store_event"]["schema"]["parameters"]["properties"],
        )
        self.assertIn("read-only", ctx.tools["circulatio_discovery"]["description"])

    def test_registered_plugin_handlers_smoke_through_modern_context(self) -> None:
        async def run() -> None:
            self._install_in_memory_runtime()
            ctx = _FakeModernHermesContext()
            register(ctx)

            command_handler = ctx.commands["circulation"]["handler"]
            rendered = command_handler(
                'reflect "I walked through a house and found a snake image returning after the conflict."',
                **self._kwargs(message_id="msg_ctx_smoke"),
            )
            self.assertIn("Pending memory proposals - not written yet:", rendered)

            threshold_handler = ctx.tools["circulatio_threshold_review"]["handler"]
            threshold_response = json.loads(
                await threshold_handler(
                    {
                        "windowStart": "2026-04-12T00:00:00Z",
                        "windowEnd": "2026-04-19T23:59:59Z",
                    },
                    **self._tool_kwargs(call_id="tool_ctx_threshold"),
                )
            )
            self.assertEqual(threshold_response["status"], "ok")
            self.assertTrue(threshold_response["result"]["reviewId"])

            packet_handler = ctx.tools["circulatio_analysis_packet"]["handler"]
            packet_response = json.loads(
                await packet_handler(
                    {
                        "windowStart": "2026-04-12T00:00:00Z",
                        "windowEnd": "2026-04-19T23:59:59Z",
                        "packetFocus": "threshold",
                    },
                    **self._tool_kwargs(call_id="tool_ctx_packet"),
                )
            )
            self.assertEqual(packet_response["status"], "ok")
            self.assertTrue(packet_response["result"]["packetId"])

            discovery_handler = ctx.tools["circulatio_discovery"]["handler"]
            discovery_response = json.loads(
                await discovery_handler(
                    {"textQuery": "snake", "maxItems": 4},
                    **self._tool_kwargs(call_id="tool_ctx_discovery"),
                )
            )
            self.assertEqual(discovery_response["status"], "ok")
            self.assertEqual(discovery_response["result"]["sectionCount"], 8)
            self.assertIn("Discovery digest", discovery_response["message"])

            journey_handler = ctx.tools["circulatio_journey_page"]["handler"]
            journey_response = json.loads(
                await journey_handler(
                    {
                        "windowStart": "2026-04-12T00:00:00Z",
                        "windowEnd": "2026-04-19T23:59:59Z",
                    },
                    **self._tool_kwargs(call_id="tool_ctx_journey"),
                )
            )
            self.assertEqual(journey_response["status"], "ok")
            self.assertIn("journeyPageSummary", journey_response["result"])
            self.assertIn("continuitySummary", journey_response["result"])
            self.assertIn("journey overview", journey_response["message"].lower())

        asyncio.run(run())

    def test_journey_page_tool_returns_structured_page_and_message_fallback(self) -> None:
        async def run() -> None:
            self._install_in_memory_runtime()
            response = json.loads(
                await journey_page_tool(
                    {
                        "windowStart": "2026-04-12T00:00:00Z",
                        "windowEnd": "2026-04-19T23:59:59Z",
                    },
                    **self._tool_kwargs(call_id="tool_journey_page"),
                )
            )
            self.assertEqual(response["status"], "ok")
            self.assertIn("journeyPageSummary", response["result"])
            self.assertIn("continuitySummary", response["result"])
            self.assertNotIn("methodContextSnapshot", response["result"]["continuitySummary"])
            self.assertTrue(response["message"])

        asyncio.run(run())

    def test_journey_page_host_sanitizer_preserves_compact_continuity_summary(self) -> None:
        runtime = self._install_in_memory_runtime()
        request = build_tool_request(
            operation="circulatio.journey.page",
            payload={},
            tool_name="circulatio_journey_page",
            kwargs=self._tool_kwargs(call_id="tool_sanitize_journey_page"),
        )
        response = {
            "requestId": "req_1",
            "operation": "circulatio.journey.page",
            "status": "ok",
            "message": "Loaded journey page.",
            "result": {
                "journeyPage": {
                    "windowStart": "2026-04-12T00:00:00Z",
                    "windowEnd": "2026-04-19T23:59:59Z",
                    "title": "Journey page",
                    "aliveToday": {"response": "A bounded opener is available."},
                    "continuity": {
                        "generatedAt": "2026-04-19T23:59:59Z",
                        "windowStart": "2026-04-12T00:00:00Z",
                        "windowEnd": "2026-04-19T23:59:59Z",
                        "threadDigests": [
                            {
                                "threadKey": "journey:1",
                                "kind": "journey",
                                "status": "active",
                                "summary": "A live thread.",
                                "lastTouchedAt": "2026-04-19T20:00:00Z",
                                "journeyIds": ["journey_1", "journey_2", "journey_3", "journey_4"],
                                "surfaceReadiness": {"aliveToday": "ready"},
                            }
                        ],
                        "methodContextSnapshot": {
                            "witnessState": {
                                "stance": "paced_contact",
                                "tone": "gentle",
                                "startingMove": "grounded_question",
                                "maxQuestionsPerTurn": 1,
                                "reasons": ["pace", "containment"],
                            },
                            "coachState": {
                                "selectedMove": {
                                    "loopKey": "coach:1",
                                    "kind": "offer_resource",
                                    "titleHint": "Resource invitation",
                                    "summaryHint": "A grounded resource is available.",
                                }
                            },
                        },
                    },
                }
            },
            "errors": [],
            "pendingProposals": [],
            "affectedEntityIds": [],
            "idempotencyKey": request["idempotencyKey"],
            "replayed": False,
        }

        sanitized = runtime.bridge._sanitize_response_for_host(request=request, response=response)
        self.assertIn("journeyPageSummary", sanitized["result"])
        self.assertIn("continuitySummary", sanitized["result"])
        continuity_summary = sanitized["result"]["continuitySummary"]
        self.assertEqual(continuity_summary["threadCount"], 1)
        self.assertEqual(len(continuity_summary["threads"][0]["journeyIds"]), 3)
        self.assertEqual(continuity_summary["selectedCoachMove"]["title"], "Resource invitation")
        self.assertNotIn("methodContextSnapshot", continuity_summary)

    def test_journey_tools_cover_autonomous_container_lifecycle(self) -> None:
        async def run() -> None:
            self._install_in_memory_runtime()
            stored = json.loads(
                await store_reflection_tool(
                    {"text": "I keep thinking about her when I do my wash."},
                    **self._tool_kwargs(call_id="tool_journey_store"),
                )
            )
            self.assertEqual(stored["status"], "ok")
            material_id = stored["result"]["materialId"]

            created = json.loads(
                await create_journey_tool(
                    {
                        "label": "Laundry return",
                        "currentQuestion": "Why does this return in ordinary rhythm?",
                        "relatedMaterialIds": [material_id],
                    },
                    **self._tool_kwargs(call_id="tool_journey_create"),
                )
            )
            self.assertEqual(created["status"], "ok")
            journey_id = created["result"]["journeyId"]

            listed = json.loads(
                await list_journeys_tool(
                    {"statuses": ["active"]},
                    **self._tool_kwargs(call_id="tool_journey_list"),
                )
            )
            self.assertEqual(listed["status"], "ok")
            self.assertEqual(listed["result"]["journeyCount"], 1)

            loaded = json.loads(
                await get_journey_tool(
                    {"journeyId": journey_id},
                    **self._tool_kwargs(call_id="tool_journey_get"),
                )
            )
            self.assertEqual(loaded["status"], "ok")
            self.assertEqual(loaded["result"]["journey"]["label"], "Laundry return")

            updated = json.loads(
                await update_journey_tool(
                    {
                        "journeyId": journey_id,
                        "label": "Laundry return thread",
                        "currentQuestion": "What keeps looping back here?",
                    },
                    **self._tool_kwargs(call_id="tool_journey_update"),
                )
            )
            self.assertEqual(updated["status"], "ok")
            self.assertEqual(
                updated["result"]["journey"]["currentQuestion"],
                "What keeps looping back here?",
            )

            paused = json.loads(
                await set_journey_status_tool(
                    {"journeyId": journey_id, "status": "paused"},
                    **self._tool_kwargs(call_id="tool_journey_pause"),
                )
            )
            self.assertEqual(paused["status"], "ok")
            self.assertEqual(paused["result"]["journey"]["status"], "paused")

        asyncio.run(run())

    def test_journey_tools_accept_journey_label_payloads(self) -> None:
        async def run() -> None:
            self._install_in_memory_runtime()
            created = json.loads(
                await create_journey_tool(
                    {"label": "Laundry Return"},
                    **self._tool_kwargs(call_id="tool_journey_create_label"),
                )
            )
            self.assertEqual(created["status"], "ok")

            loaded = json.loads(
                await get_journey_tool(
                    {"journeyLabel": "laundry-return"},
                    **self._tool_kwargs(call_id="tool_journey_get_label"),
                )
            )
            self.assertEqual(loaded["status"], "ok")
            self.assertEqual(loaded["result"]["journey"]["id"], created["result"]["journeyId"])

            updated = json.loads(
                await update_journey_tool(
                    {
                        "journeyLabel": "laundry return",
                        "currentQuestion": "What keeps looping back here?",
                    },
                    **self._tool_kwargs(call_id="tool_journey_update_label"),
                )
            )
            self.assertEqual(updated["status"], "ok")
            self.assertEqual(
                updated["result"]["journey"]["currentQuestion"],
                "What keeps looping back here?",
            )

            paused = json.loads(
                await set_journey_status_tool(
                    {"journeyLabel": "laundry_return", "status": "paused"},
                    **self._tool_kwargs(call_id="tool_journey_pause_label"),
                )
            )
            self.assertEqual(paused["status"], "ok")
            self.assertEqual(paused["result"]["journey"]["status"], "paused")

        asyncio.run(run())

    def test_journey_tool_label_ambiguity_returns_conflict(self) -> None:
        async def run() -> None:
            self._install_in_memory_runtime()
            await create_journey_tool(
                {"label": "Contact Pressure"},
                **self._tool_kwargs(call_id="tool_journey_ambiguous_one"),
            )
            await create_journey_tool(
                {"label": "contact-pressure"},
                **self._tool_kwargs(call_id="tool_journey_ambiguous_two"),
            )

            response = json.loads(
                await get_journey_tool(
                    {"journeyLabel": "contact pressure"},
                    **self._tool_kwargs(call_id="tool_journey_ambiguous_get"),
                )
            )
            self.assertEqual(response["status"], "conflict")
            self.assertEqual(response["errors"][0]["code"], "conflict")
            self.assertIn("Ambiguous journey label", response["message"])

        asyncio.run(run())

    def test_explicit_journey_lifecycle_commands_support_manual_qa_surface(self) -> None:
        async def run() -> None:
            self._install_in_memory_runtime()

            created = await handle_circulation(
                'journey create --label "Laundry return" --question "Why does this return in ordinary rhythm?"',
                **self._kwargs(message_id="msg_journey_create"),
            )
            self.assertIn("Journey: Laundry return (active)", created)
            journey_id = self._rendered_value(created, "Journey id: ")

            listed = await handle_circulation(
                "journey list --status active",
                **self._kwargs(message_id="msg_journey_list"),
            )
            self.assertIn("Journeys:", listed)
            self.assertIn(f"Laundry return (active) [{journey_id}]", listed)

            loaded = await handle_circulation(
                'journey get --label "Laundry return"',
                **self._kwargs(message_id="msg_journey_get"),
            )
            self.assertIn(f"Journey id: {journey_id}", loaded)

            updated = await handle_circulation(
                'journey update --label "Laundry return" --new-label "Laundry return thread" --question "What keeps looping back here?"',
                **self._kwargs(message_id="msg_journey_update"),
            )
            self.assertIn("Journey: Laundry return thread (active)", updated)
            self.assertIn("Question: What keeps looping back here?", updated)

            paused = await handle_circulation(
                'journey pause --label "Laundry return thread"',
                **self._kwargs(message_id="msg_journey_pause"),
            )
            self.assertIn("Journey: Laundry return thread (paused)", paused)

            resumed = await handle_circulation(
                'journey resume --label "Laundry return thread"',
                **self._kwargs(message_id="msg_journey_resume"),
            )
            self.assertIn("Journey: Laundry return thread (active)", resumed)

            completed = await handle_circulation(
                f"journey complete {journey_id}",
                **self._kwargs(message_id="msg_journey_complete"),
            )
            self.assertIn("Journey: Laundry return thread (completed)", completed)

            archived = await handle_circulation(
                f"journey archive {journey_id}",
                **self._kwargs(message_id="msg_journey_archive"),
            )
            self.assertIn("Journey: Laundry return thread (archived)", archived)

        asyncio.run(run())

    def test_journey_command_renders_page_fallback(self) -> None:
        async def run() -> None:
            self._install_in_memory_runtime()
            rendered = await handle_circulation(
                "journey --window-start 2026-04-12T00:00:00Z --window-end 2026-04-19T23:59:59Z",
                **self._kwargs(message_id="msg_journey_command"),
            )
            self.assertIn("Journey page", rendered)
            self.assertIn("Alive today:", rendered)
            self.assertIn("Weekly review is available:", rendered)

        asyncio.run(run())

    def test_result_renderer_renders_journey_page_when_message_differs_from_fallback(self) -> None:
        renderer = CirculatioResultRenderer()
        rendered = renderer.render(
            {
                "requestId": "req_1",
                "idempotencyKey": "key_1",
                "replayed": False,
                "status": "ok",
                "message": "Loaded journey page.",
                "result": {
                    "journeyPage": {
                        "pageId": "journey_page_1",
                        "title": "Journey page",
                        "windowStart": "2026-04-12T00:00:00Z",
                        "windowEnd": "2026-04-19T23:59:59Z",
                        "fallbackText": "Journey page fallback.",
                        "cards": [
                            {
                                "id": "card_1",
                                "section": "alive_today",
                                "title": "Alive today",
                                "body": "A bounded opener is available.",
                                "actions": [
                                    {
                                        "label": "Generate weekly review",
                                        "kind": "tool",
                                        "writeIntent": "write",
                                        "requiresExplicitUserAction": True,
                                    }
                                ],
                            }
                        ],
                    }
                },
                "pendingProposals": [],
                "affectedEntityIds": [],
                "errors": [],
            }
        )
        self.assertIn("Journey page", rendered)
        self.assertIn("Alive today:", rendered)
        self.assertIn("Actions: Generate weekly review", rendered)

    def test_result_renderer_renders_discovery_when_message_differs_from_fallback(self) -> None:
        renderer = CirculatioResultRenderer()
        rendered = renderer.render(
            {
                "requestId": "req_discovery",
                "idempotencyKey": "key_discovery",
                "replayed": False,
                "status": "ok",
                "message": "Loaded discovery digest.",
                "result": {
                    "discovery": {
                        "discoveryId": "discovery_1",
                        "windowStart": "2026-04-12T00:00:00Z",
                        "windowEnd": "2026-04-19T23:59:59Z",
                        "sections": [
                            {
                                "key": "recurring",
                                "title": "Recurring",
                                "summary": "Structural recurrences surfaced from dashboard and approved memory.",
                                "items": [
                                    {
                                        "label": "snake",
                                        "criteria": ["dashboard_recurring_symbol"],
                                        "sourceKinds": ["dashboard"],
                                        "entityRefs": {"symbols": ["symbol_1"]},
                                        "evidenceIds": [],
                                    }
                                ],
                            }
                        ],
                    }
                },
                "pendingProposals": [],
                "affectedEntityIds": [],
                "errors": [],
            }
        )
        self.assertIn("Discovery digest", rendered)
        self.assertIn("Recurring", rendered)
        self.assertIn("- snake", rendered)

    def test_no_internal_routing_module_or_capture_any_operation_is_exposed(self) -> None:
        self.assertNotIn("circulatio_capture_any", get_args(BridgeOperation))
        self.assertFalse(any("routing" in operation for operation in get_args(BridgeOperation)))

    def test_command_path_returns_structured_boot_error(self) -> None:
        async def run() -> None:
            original_get_runtime = plugin_commands.get_runtime
            plugin_commands.get_runtime = lambda profile=None: (_ for _ in ()).throw(
                PluginBootError("missing packaged skill asset")
            )
            try:
                rendered = await handle_circulation(
                    'dream "Snake in the cellar"',
                    **self._kwargs(message_id="msg_boot"),
                )
            finally:
                plugin_commands.get_runtime = original_get_runtime
            self.assertIn("missing packaged skill asset", rendered)

        asyncio.run(run())

    def test_sync_command_path_returns_usage_for_empty_args(self) -> None:
        rendered = handle_circulation_sync(**self._kwargs(message_id="msg_help"))
        self.assertIn("Usage: /circulation <subcommand>", rendered)
        self.assertIn(
            '/circulation dream "I walked through a house and found a snake in the cellar."',
            rendered,
        )

    def test_sync_command_path_accepts_user_args_keyword(self) -> None:
        self._install_fake_runtime()
        rendered = handle_circulation_sync(
            user_args='reflect "I walked through a house and found a snake image returning after the conflict."',
            **self._kwargs(message_id="msg_sync_keyword"),
        )
        self.assertIn("Pending memory proposals - not written yet:", rendered)

    def test_tool_path_returns_structured_boot_error_json(self) -> None:
        async def run() -> None:
            original_get_runtime = plugin_tools.get_runtime
            plugin_tools.get_runtime = lambda profile=None: (_ for _ in ()).throw(
                PersistenceError("profile database is locked", retryable=True)
            )
            try:
                response = json.loads(
                    await interpret_material_tool(
                        {"materialType": "dream", "text": "snake"},
                        **self._tool_kwargs(call_id="tool_boot"),
                    )
                )
            finally:
                plugin_tools.get_runtime = original_get_runtime
            self.assertEqual(response["status"], "retryable_error")
            self.assertEqual(response["errors"][0]["code"], "profile_storage_unavailable")

        asyncio.run(run())

    def test_tool_request_prefers_message_and_session_when_tool_call_id_is_missing(self) -> None:
        request = build_tool_request(
            operation="circulatio.symbols.list",
            payload={},
            tool_name="circulatio_symbols_list",
            kwargs=self._kwargs(message_id="msg_fallback", session_id="sess_fallback"),
        )
        self.assertEqual(
            request["idempotencyKey"],
            "tool:circulatio_symbols_list:sess_fallback:msg_fallback:circulatio_symbols_list",
        )


if __name__ == "__main__":
    unittest.main()
