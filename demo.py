from __future__ import annotations

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.abspath("src"))

from circulatio.hermes.runtime import build_in_memory_circulatio_runtime
from circulatio_hermes_plugin import register
from circulatio_hermes_plugin.runtime import reset_runtimes, set_runtime
from tests._helpers import FakeCirculatioLlm

_PROFILE = "demo"
_SESSION_ID = "roadmap_demo"
_WINDOW_START = "2026-04-12T00:00:00Z"
_WINDOW_END = "2026-04-21T23:59:59Z"
_REFLECTION_TEXT = "I was thinking why I always think about her when Im doing my wash."
_SYMBOLIC_REFLECTION_TEXT = (
    "I walked through a house and found a snake image returning after the conflict."
)


class _DemoHermesContext:
    def __init__(self) -> None:
        self.commands: dict[str, dict[str, object]] = {}
        self.tools: dict[str, dict[str, object]] = {}
        self.skills: dict[str, dict[str, object]] = {}

    def register_command(self, name: str, handler, description: str | None = None) -> None:
        self.commands[name] = {"handler": handler, "description": description}

    def register_tool(
        self,
        *,
        name: str,
        toolset: str | None = None,
        schema: dict[str, object] | None = None,
        handler=None,
        is_async: bool = False,
        description: str | None = None,
    ) -> None:
        self.tools[name] = {
            "toolset": toolset,
            "schema": schema,
            "handler": handler,
            "is_async": is_async,
            "description": description,
        }

    def register_skill(
        self,
        name: str,
        path: str,
        description: str | None = None,
    ) -> None:
        self.skills[name] = {"path": path, "description": description}


def _command_kwargs(*, message_id: str) -> dict[str, object]:
    return {
        "platform": "cli",
        "profile": _PROFILE,
        "session_id": _SESSION_ID,
        "message_id": message_id,
    }


def _tool_kwargs(*, call_id: str) -> dict[str, object]:
    return {
        **_command_kwargs(message_id=call_id),
        "tool_call_id": call_id,
    }


async def _call_tool(
    ctx: _DemoHermesContext,
    *,
    name: str,
    arguments: dict[str, object],
    call_id: str,
) -> dict[str, object]:
    handler = ctx.tools[name]["handler"]
    response = await handler(arguments, **_tool_kwargs(call_id=call_id))
    return json.loads(response)


def _call_command(
    ctx: _DemoHermesContext,
    *,
    raw_args: str,
    message_id: str,
) -> str:
    handler = ctx.commands["circulation"]["handler"]
    return str(handler(raw_args, **_command_kwargs(message_id=message_id)))


async def run_demo() -> dict[str, object]:
    reset_runtimes()
    runtime = build_in_memory_circulatio_runtime(llm=FakeCirculatioLlm())
    set_runtime(runtime, profile=_PROFILE)
    ctx = _DemoHermesContext()
    register(ctx)

    try:
        tool_scenarios: list[dict[str, object]] = []
        command_scenarios: list[dict[str, object]] = []

        stored = await _call_tool(
            ctx,
            name="circulatio_store_reflection",
            arguments={"text": _REFLECTION_TEXT, "materialDate": _WINDOW_END},
            call_id="demo_store_reflection",
        )
        tool_scenarios.append(
            {
                "label": "Hold-first reflection capture via Hermes tool intent",
                "toolName": "circulatio_store_reflection",
                "arguments": {"text": _REFLECTION_TEXT},
                "response": stored,
            }
        )

        journey = await _call_tool(
            ctx,
            name="circulatio_create_journey",
            arguments={
                "label": "Laundry return",
                "currentQuestion": "Why does this thought return in ordinary rhythm?",
                "relatedMaterialIds": [stored["result"]["materialId"]],
            },
            call_id="demo_create_journey",
        )
        tool_scenarios.append(
            {
                "label": "Autonomous journey container created from a recurring held thread",
                "toolName": "circulatio_create_journey",
                "arguments": {
                    "label": "Laundry return",
                    "currentQuestion": "Why does this thought return in ordinary rhythm?",
                    "relatedMaterialIds": [stored["result"]["materialId"]],
                },
                "response": journey,
            }
        )

        alive_today = await _call_tool(
            ctx,
            name="circulatio_alive_today",
            arguments={"windowStart": _WINDOW_START, "windowEnd": _WINDOW_END},
            call_id="demo_alive_today",
        )
        tool_scenarios.append(
            {
                "label": "Alive-today weave across recent approved and held context",
                "toolName": "circulatio_alive_today",
                "arguments": {"windowStart": _WINDOW_START, "windowEnd": _WINDOW_END},
                "response": alive_today,
            }
        )

        journey_page = await _call_tool(
            ctx,
            name="circulatio_journey_page",
            arguments={"windowStart": _WINDOW_START, "windowEnd": _WINDOW_END},
            call_id="demo_journey_page",
        )
        tool_scenarios.append(
            {
                "label": "Journey page assembles a read-mostly host surface",
                "toolName": "circulatio_journey_page",
                "arguments": {"windowStart": _WINDOW_START, "windowEnd": _WINDOW_END},
                "response": journey_page,
            }
        )

        symbolic_reflection = await _call_tool(
            ctx,
            name="circulatio_store_reflection",
            arguments={"text": _SYMBOLIC_REFLECTION_TEXT, "materialDate": _WINDOW_END},
            call_id="demo_store_symbolic_reflection",
        )
        tool_scenarios.append(
            {
                "label": "Store a charged reflection before asking for meaning",
                "toolName": "circulatio_store_reflection",
                "arguments": {"text": _SYMBOLIC_REFLECTION_TEXT},
                "response": symbolic_reflection,
            }
        )

        interpreted = await _call_tool(
            ctx,
            name="circulatio_interpret_material",
            arguments={"materialId": symbolic_reflection["result"]["materialId"]},
            call_id="demo_interpret_material",
        )
        tool_scenarios.append(
            {
                "label": "Deliberate interpretation after explicit meaning request",
                "toolName": "circulatio_interpret_material",
                "arguments": {"materialId": symbolic_reflection["result"]["materialId"]},
                "response": interpreted,
            }
        )

        proposal_refs = [item["alias"] for item in interpreted.get("pendingProposals", [])]
        approved = await _call_tool(
            ctx,
            name="circulatio_approve_proposals",
            arguments={"runId": interpreted["result"]["runId"], "proposalRefs": proposal_refs},
            call_id="demo_approve_proposals",
        )
        tool_scenarios.append(
            {
                "label": "Explicit approval applies LLM-derived memory writes",
                "toolName": "circulatio_approve_proposals",
                "arguments": {
                    "runId": interpreted["result"]["runId"],
                    "proposalRefs": proposal_refs,
                },
                "response": approved,
            }
        )

        threshold_review = await _call_tool(
            ctx,
            name="circulatio_threshold_review",
            arguments={"windowStart": _WINDOW_START, "windowEnd": _WINDOW_END},
            call_id="demo_threshold_review",
        )
        tool_scenarios.append(
            {
                "label": "Threshold review for a liminal period",
                "toolName": "circulatio_threshold_review",
                "arguments": {"windowStart": _WINDOW_START, "windowEnd": _WINDOW_END},
                "response": threshold_review,
            }
        )

        living_myth_review = await _call_tool(
            ctx,
            name="circulatio_living_myth_review",
            arguments={"windowStart": _WINDOW_START, "windowEnd": _WINDOW_END},
            call_id="demo_living_myth_review",
        )
        tool_scenarios.append(
            {
                "label": "Living myth review for chapter-scale synthesis",
                "toolName": "circulatio_living_myth_review",
                "arguments": {"windowStart": _WINDOW_START, "windowEnd": _WINDOW_END},
                "response": living_myth_review,
            }
        )

        analysis_packet = await _call_tool(
            ctx,
            name="circulatio_analysis_packet",
            arguments={
                "windowStart": _WINDOW_START,
                "windowEnd": _WINDOW_END,
                "packetFocus": "threshold",
            },
            call_id="demo_analysis_packet",
        )
        tool_scenarios.append(
            {
                "label": "Bounded analysis packet for journaling or analysis prep",
                "toolName": "circulatio_analysis_packet",
                "arguments": {
                    "windowStart": _WINDOW_START,
                    "windowEnd": _WINDOW_END,
                    "packetFocus": "threshold",
                },
                "response": analysis_packet,
            }
        )

        practice = await _call_tool(
            ctx,
            name="circulatio_generate_practice_recommendation",
            arguments={},
            call_id="demo_practice",
        )
        tool_scenarios.append(
            {
                "label": "Practice generation remains a separate explicit step",
                "toolName": "circulatio_generate_practice_recommendation",
                "arguments": {},
                "response": practice,
            }
        )

        briefs = await _call_tool(
            ctx,
            name="circulatio_generate_rhythmic_briefs",
            arguments={"source": "manual", "windowStart": _WINDOW_START, "windowEnd": _WINDOW_END},
            call_id="demo_briefs",
        )
        tool_scenarios.append(
            {
                "label": "Rhythmic briefs stay bounded and consent-aware",
                "toolName": "circulatio_generate_rhythmic_briefs",
                "arguments": {
                    "source": "manual",
                    "windowStart": _WINDOW_START,
                    "windowEnd": _WINDOW_END,
                },
                "response": briefs,
            }
        )

        command_scenarios.append(
            {
                "label": "Explicit slash command reflection path",
                "rawArgs": (
                    'reflect "I keep circling the same thought about her '
                    'whenever I do the wash."'
                ),
                "rendered": _call_command(
                    ctx,
                    raw_args=(
                        'reflect "I keep circling the same thought about her '
                        'whenever I do the wash."'
                    ),
                    message_id="demo_command_reflect",
                ),
            }
        )
        command_scenarios.append(
            {
                "label": "Explicit slash command journey page path",
                "rawArgs": (
                    "journey --window-start "
                    f"{_WINDOW_START} --window-end {_WINDOW_END}"
                ),
                "rendered": _call_command(
                    ctx,
                    raw_args=(
                        "journey --window-start "
                        f"{_WINDOW_START} --window-end {_WINDOW_END}"
                    ),
                    message_id="demo_command_journey",
                ),
            }
        )
        command_scenarios.append(
            {
                "label": "Explicit slash command packet path",
                "rawArgs": (
                    "packet --focus threshold --window-start "
                    f"{_WINDOW_START} --window-end {_WINDOW_END}"
                ),
                "rendered": _call_command(
                    ctx,
                    raw_args=(
                        "packet --focus threshold --window-start "
                        f"{_WINDOW_START} --window-end {_WINDOW_END}"
                    ),
                    message_id="demo_command_packet",
                ),
            }
        )

        return {
            "profile": _PROFILE,
            "toolScenarios": tool_scenarios,
            "commandScenarios": command_scenarios,
        }
    finally:
        reset_runtimes()


def render_demo(run: dict[str, object]) -> str:
    lines = [
        "# Circulatio Hermes ROADMAP Demo",
        "",
        "This runs the real Circulatio Hermes plugin surface against an in-memory runtime.",
        "It demonstrates both host-LLM tool use by intent and explicit `/circulation` commands.",
        "",
        "## Tool Scenarios",
    ]
    for index, scenario in enumerate(run["toolScenarios"], start=1):
        response = scenario["response"]
        lines.extend(
            [
                "",
                f"### {index}. {scenario['label']}",
                f"Tool: {scenario['toolName']}",
                f"Arguments: {json.dumps(scenario['arguments'], sort_keys=True)}",
                f"Status: {response['status']}",
                f"Message: {response['message']}",
            ]
        )
        for highlight in _response_highlights(response):
            lines.append(highlight)

    lines.extend(["", "## Command Scenarios"])
    for index, scenario in enumerate(run["commandScenarios"], start=1):
        lines.extend(
            [
                "",
                f"### {index}. {scenario['label']}",
                f"Command: /circulation {scenario['rawArgs']}",
                scenario["rendered"],
            ]
        )
    return "\n".join(lines)


def _response_highlights(response: dict[str, object]) -> list[str]:
    result = response.get("result", {})
    highlights: list[str] = []
    if isinstance(result, dict):
        labels = (
            ("materialId", "Material"),
            ("runId", "Run"),
            ("integrationId", "Integration"),
            ("reviewId", "Review"),
            ("packetId", "Packet"),
            ("packetTitle", "Packet title"),
            ("journeyId", "Journey"),
            ("journeyPageId", "Journey page"),
        )
        for key, label in labels:
            value = result.get(key)
            if value:
                highlights.append(f"{label}: {value}")
        journey = result.get("journey")
        if isinstance(journey, dict):
            highlights.append(
                "Journey label: "
                f"{journey.get('label', 'unknown')} "
                f"({journey.get('status', 'unknown')})"
            )
        journey_page = result.get("journeyPage")
        if isinstance(journey_page, dict):
            cards = journey_page.get("cards")
            if isinstance(cards, list):
                highlights.append(f"Journey cards: {len(cards)}")
        journeys = result.get("journeys")
        if isinstance(journeys, list):
            highlights.append(f"Journey count: {len(journeys)}")
        symbols = result.get("symbols")
        if isinstance(symbols, list) and symbols:
            highlights.append(f"Symbols: {len(symbols)}")
        practice_session = result.get("practiceSession")
        if isinstance(practice_session, dict):
            highlights.append(
                "Practice session: "
                f"{practice_session.get('id', 'unknown')} "
                f"({practice_session.get('status', 'unknown')})"
            )
        briefs = result.get("briefs")
        if isinstance(briefs, list):
            highlights.append(f"Brief count: {len(briefs)}")
    pending = response.get("pendingProposals", [])
    if isinstance(pending, list) and pending:
        rendered = ", ".join(
            f"{item.get('alias', '?')}:{item.get('action', '?')}" for item in pending[:5]
        )
        highlights.append(f"Pending proposals: {rendered}")
    return highlights


def main() -> None:
    print(render_demo(asyncio.run(run_demo())))


if __name__ == "__main__":
    main()
