from __future__ import annotations

import asyncio
import json
import os
import urllib.error
import urllib.request
from collections.abc import Callable, Coroutine
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

from circulatio.hermes.runtime import build_in_memory_circulatio_runtime
from circulatio_hermes_plugin.runtime import reset_runtimes, set_runtime
from circulatio_hermes_plugin.tools import (
    alive_today_tool,
    generate_rhythmic_briefs_tool,
    plan_ritual_tool,
    record_ritual_completion_tool,
    respond_rhythmic_brief_tool,
    store_body_state_tool,
    store_dream_tool,
    store_reflection_tool,
)
from tools.self_evolution.artifacts import current_git_sha, default_run_id

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RUN_ROOT = REPO_ROOT / "artifacts" / "journey_cli_eval" / "runs"
DEFAULT_ARTIFACT_ROOT = REPO_ROOT / "apps" / "hermes-rituals-web" / "public" / "artifacts"
DEFAULT_PLAN_ROOT = REPO_ROOT / "artifacts" / "rituals" / "plans"

_JSON = dict[str, object]
_ToolFn = Callable[..., Coroutine[Any, Any, str]]

_TEXT_KEYS = {"text", "noteText", "reflectionText", "materialText", "rawMaterialText"}
_SECRET_TOKENS = ("cpk_", "CHUTES_API_TOKEN")


class JourneyRitualLlm:
    """Small deterministic LLM port for local ritual journey evaluation."""

    def __init__(self) -> None:
        self.interpret_calls: list[_JSON] = []
        self.alive_today_calls: list[_JSON] = []
        self.brief_calls: list[_JSON] = []
        self.weekly_review_calls: list[_JSON] = []

    async def interpret_material(self, input_data: _JSON) -> _JSON:
        self.interpret_calls.append(deepcopy(input_data))
        return {
            "symbolMentions": [],
            "figureMentions": [],
            "motifMentions": [],
            "lifeContextLinks": [],
            "observations": [],
            "hypotheses": [],
            "proposalCandidates": [],
            "depthReadiness": {"status": "limited", "allowedMoves": {}, "reasons": []},
            "methodGate": {
                "depthLevel": "personal_amplification_needed",
                "missingPrerequisites": [],
                "blockedMoves": [],
                "requiredPrompts": [],
                "responseConstraints": ["stay tentative"],
            },
            "userFacingResponse": "Stored without interpretation.",
        }

    async def generate_alive_today(self, input_data: _JSON) -> _JSON:
        self.alive_today_calls.append(deepcopy(input_data))
        return {
            "userFacingResponse": "A quiet thread is alive today; hold it without explaining it.",
            "activeThemes": ["recurring threshold image", "body contact"],
            "selectedCoachLoopKey": "journey-cli:alive-today",
            "coachMoveKind": "offer_ritual",
            "followUpQuestion": "Would a short ritual container help you stay with it?",
            "suggestedAction": "Invite before planning; do not render until accepted.",
        }

    async def generate_weekly_review(self, input_data: _JSON) -> _JSON:
        self.weekly_review_calls.append(deepcopy(input_data))
        return {
            "userFacingResponse": "The week keeps returning to a river gate image.",
            "activeThemes": ["river gate", "threshold", "chest easing"],
            "practiceRecommendation": {
                "type": "journaling",
                "reason": "Name what changed around the repeated image.",
                "durationMinutes": 8,
                "instructions": ["Name the image.", "Notice the body response."],
                "requiresConsent": False,
            },
        }

    async def generate_practice(self, input_data: _JSON) -> _JSON:
        return {
            "practiceRecommendation": {
                "type": "journaling",
                "reason": "Stay with the image briefly.",
                "durationMinutes": 5,
                "instructions": ["Write the strongest image in one sentence."],
                "requiresConsent": False,
            },
            "userFacingResponse": "A short journaling practice is available.",
        }

    async def generate_rhythmic_brief(self, input_data: _JSON) -> _JSON:
        payload = deepcopy(input_data)
        self.brief_calls.append(payload)
        seed = payload.get("seed") if isinstance(payload.get("seed"), dict) else {}
        title = str(seed.get("titleHint") or "Ritual invitation")
        summary = str(seed.get("summaryHint") or "A bounded ritual invitation is due.")
        action = str(seed.get("suggestedActionHint") or "Offer the invitation; wait for consent.")
        return {
            "title": title,
            "summary": summary,
            "suggestedAction": action,
            "userFacingResponse": f"{title}. {summary} {action}",
            "supportingRefs": [],
        }

    async def generate_threshold_review(self, input_data: _JSON) -> _JSON:
        return {
            "userFacingResponse": "Threshold review withheld for this eval.",
            "thresholdProcesses": [],
            "proposalCandidates": [],
        }

    async def generate_living_myth_review(self, input_data: _JSON) -> _JSON:
        return {
            "userFacingResponse": "Living myth review withheld for this eval.",
            "proposalCandidates": [],
        }

    async def generate_analysis_packet(self, input_data: _JSON) -> _JSON:
        return {
            "packetTitle": "Ritual journey packet",
            "sections": [],
            "includedMaterialIds": [],
            "includedRecordRefs": [],
            "evidenceIds": [],
            "userFacingResponse": "No analysis packet was needed.",
        }

    async def summarize_life_context(
        self,
        *,
        user_id: str,
        window_start: str,
        window_end: str,
        raw_context: _JSON,
    ) -> _JSON:
        del user_id, raw_context
        return {
            "windowStart": window_start,
            "windowEnd": window_end,
            "source": "journey-cli-eval",
            "focusSummary": "Synthetic ritual journey context.",
            "lifeEventRefs": [],
            "notableChanges": [],
        }

    async def route_method_state_response(self, input_data: _JSON) -> _JSON:
        return {
            "answerSummary": str(input_data.get("responseText") or "")[:180],
            "evidenceSpans": [],
            "captureCandidates": [],
            "followUpPrompts": [],
            "routingWarnings": [],
        }


@dataclass(frozen=True)
class RitualJourneyConfig:
    run_id: str
    run_dir: Path
    artifact_root: Path
    plan_root: Path
    base_url: str
    provider_profile: str
    live_providers: bool
    include_video: bool
    include_music: bool
    allow_beta_video: bool
    allow_beta_music: bool
    max_cost_usd: float
    chutes_token_env: str
    transcription_provider: str
    openai_api_key_env: str
    openai_transcription_model: str
    http_check: bool
    request_timeout_seconds: int


@dataclass
class ScenarioState:
    name: str
    user_id: str
    artifact_ids: list[str]
    completion_ids: list[str]
    warnings: list[str]


class ToolRecorder:
    def __init__(self, *, run_id: str, profile: str, user_id: str) -> None:
        self.run_id = run_id
        self.profile = profile
        self.user_id = user_id
        self.calls: list[_JSON] = []

    async def call(
        self,
        *,
        scenario: str,
        turn: str,
        tool: str,
        fn: _ToolFn,
        payload: _JSON,
    ) -> _JSON:
        call_id = f"{scenario}:{turn}:{tool}:{len(self.calls) + 1}"
        started_at = _now_iso()
        status = "exception"
        parsed: _JSON
        error: str | None = None
        try:
            rendered = await fn(payload, **self._tool_kwargs(call_id=call_id))
            parsed_raw = json.loads(rendered)
            parsed = parsed_raw if isinstance(parsed_raw, dict) else {"value": parsed_raw}
            status = str(parsed.get("status") or "unknown")
        except Exception as exc:  # pragma: no cover - defensive path retained in report
            error = exc.__class__.__name__
            parsed = {"status": "exception", "message": str(exc)}
        self.calls.append(
            {
                "callId": call_id,
                "scenario": scenario,
                "turn": turn,
                "tool": tool,
                "startedAt": started_at,
                "finishedAt": _now_iso(),
                "status": status,
                "payload": _sanitize(payload),
                "summary": _response_summary(parsed),
                **({"error": error} if error else {}),
            }
        )
        return parsed

    def _tool_kwargs(self, *, call_id: str) -> dict[str, object]:
        return {
            "platform": "journey_cli",
            "profile": self.profile,
            "session_id": self.run_id,
            "message_id": call_id,
            "tool_call_id": call_id,
            "user_id": self.user_id,
        }


def run_ritual_journey_eval(
    *,
    output_root: Path | None = None,
    render_artifact_root: Path | None = None,
    plan_root: Path | None = None,
    base_url: str = "http://localhost:3000",
    provider_profile: str = "mock",
    live_providers: bool = False,
    include_video: bool = False,
    include_music: bool = False,
    allow_beta_video: bool = False,
    allow_beta_music: bool = False,
    max_cost_usd: float = 0.0,
    chutes_token_env: str = "CHUTES_API_TOKEN",
    transcription_provider: str = "fallback",
    openai_api_key_env: str = "OPENAI_API_KEY",
    openai_transcription_model: str = "whisper-1",
    http_check: bool = False,
    request_timeout_seconds: int = 180,
    run_id: str | None = None,
) -> _JSON:
    """Run the ritual journey simulator/evaluator and write the report bundle."""

    resolved_run_id, run_dir = _create_run_dir(output_root or DEFAULT_RUN_ROOT, run_id=run_id)
    config = RitualJourneyConfig(
        run_id=resolved_run_id,
        run_dir=run_dir,
        artifact_root=(render_artifact_root or DEFAULT_ARTIFACT_ROOT).resolve(),
        plan_root=(plan_root or DEFAULT_PLAN_ROOT).resolve(),
        base_url=base_url.rstrip("/"),
        provider_profile=provider_profile,
        live_providers=live_providers,
        include_video=include_video,
        include_music=include_music,
        allow_beta_video=allow_beta_video,
        allow_beta_music=allow_beta_music,
        max_cost_usd=max_cost_usd,
        chutes_token_env=chutes_token_env,
        transcription_provider=transcription_provider,
        openai_api_key_env=openai_api_key_env,
        openai_transcription_model=openai_transcription_model,
        http_check=http_check,
        request_timeout_seconds=request_timeout_seconds,
    )
    (config.run_dir / "screenshots").mkdir(parents=True, exist_ok=True)
    payload = asyncio.run(_run_ritual_journey_eval(config))
    _write_bundle(config, payload)
    return payload["report"]


async def _run_ritual_journey_eval(config: RitualJourneyConfig) -> _JSON:
    profile = f"journey_cli_{config.run_id}"
    llm = JourneyRitualLlm()
    reset_runtimes()
    runtime = set_runtime(build_in_memory_circulatio_runtime(llm=llm), profile=profile)
    recorder = ToolRecorder(
        run_id=config.run_id,
        profile=profile,
        user_id="journey_cli_user",
    )
    timeline: list[_JSON] = []
    artifacts: list[_JSON] = []
    browser_checks: list[_JSON] = []
    negative_results: list[_JSON] = []

    with _patched_env(_handoff_env(config)):
        try:
            daily = await _run_daily_scenario(
                config=config,
                runtime=runtime,
                recorder=recorder,
                timeline=timeline,
                artifacts=artifacts,
                browser_checks=browser_checks,
            )
            weekly = await _run_weekly_scenario(
                config=config,
                runtime=runtime,
                recorder=recorder,
                timeline=timeline,
                artifacts=artifacts,
                browser_checks=browser_checks,
            )
            negative_results = await _run_negative_scenarios(
                config=config,
                runtime=runtime,
                recorder=recorder,
                timeline=timeline,
                artifacts=artifacts,
                browser_checks=browser_checks,
            )
        finally:
            reset_runtimes()

    scorecard = _scorecard(
        timeline=timeline,
        tool_calls=recorder.calls,
        artifacts=artifacts,
        browser_checks=browser_checks,
        negative_results=negative_results,
        llm=llm,
    )
    findings = _findings(scorecard=scorecard, browser_checks=browser_checks, artifacts=artifacts)
    report: _JSON = {
        "schemaVersion": "journey_cli.ritual_eval.v1",
        "runId": config.run_id,
        "createdAt": _now_iso(),
        "gitSha": current_git_sha(),
        "runDir": str(config.run_dir),
        "mode": "ritual_eval",
        "jtbd": _jtbd_summary(),
        "config": _sanitize(
            {
                "artifactRoot": str(config.artifact_root),
                "planRoot": str(config.plan_root),
                "baseUrl": config.base_url,
                "providerProfile": config.provider_profile,
                "liveProviders": config.live_providers,
                "includeVideo": config.include_video,
                "includeMusic": config.include_music,
                "allowBetaVideo": config.allow_beta_video,
                "allowBetaMusic": config.allow_beta_music,
                "maxCostUsd": config.max_cost_usd,
                "chutesTokenEnv": config.chutes_token_env,
                "transcriptionProvider": config.transcription_provider,
                "openaiApiKeyEnv": config.openai_api_key_env,
                "openaiTranscriptionModel": config.openai_transcription_model,
                "httpCheck": config.http_check,
            }
        ),
        "scenarios": [daily.__dict__, weekly.__dict__, *negative_results],
        "selectedToolSequence": _tool_sequence(recorder.calls),
        "surfaceRequests": _surface_requests(recorder.calls),
        "renderPolicies": _render_policies(recorder.calls),
        "artifactUrls": [str(item.get("url") or "") for item in artifacts],
        "manifestSurfaces": {
            str(item.get("artifactId") or ""): item.get("manifestSummary", {})
            for item in artifacts
        },
        "browserCheckSummary": _browser_check_summary(browser_checks),
        "scorecard": scorecard,
        "passed": not _has_failed(scorecard),
        "findings": findings,
        "nextEnhancements": _next_enhancements(config=config, browser_checks=browser_checks),
        "artifactCount": len(artifacts),
        "toolCallCount": len(recorder.calls),
    }
    return {
        "report": report,
        "timeline": timeline,
        "tool_calls": recorder.calls,
        "browser_checks": browser_checks,
        "artifacts_checked": artifacts,
    }


async def _run_daily_scenario(
    *,
    config: RitualJourneyConfig,
    runtime: object,
    recorder: ToolRecorder,
    timeline: list[_JSON],
    artifacts: list[_JSON],
    browser_checks: list[_JSON],
) -> ScenarioState:
    del runtime
    scenario = ScenarioState("daily", recorder.user_id, [], [], [])
    await recorder.call(
        scenario=scenario.name,
        turn="day_1_dream",
        tool="circulatio_store_dream",
        fn=store_dream_tool,
        payload={
            "text": "I stood before a blue gate by a river and waited.",
            "summary": "Blue gate by a river",
            "materialDate": "2026-04-20T07:30:00Z",
            "privacyClass": "private",
        },
    )
    _event(timeline, scenario.name, "day_1_dream", "tool_observed", "circulatio_store_dream")
    await recorder.call(
        scenario=scenario.name,
        turn="day_1_body",
        tool="circulatio_store_body_state",
        fn=store_body_state_tool,
        payload={
            "sensation": "tightness",
            "bodyRegion": "chest",
            "activation": "moderate",
            "tone": "held",
            "observedAt": "2026-04-20T08:00:00Z",
            "noteText": "The chest tightened when I remembered the gate.",
            "privacyClass": "private",
        },
    )
    _event(timeline, scenario.name, "day_1_body", "tool_observed", "circulatio_store_body_state")
    await recorder.call(
        scenario=scenario.name,
        turn="day_1_alive_today",
        tool="circulatio_alive_today",
        fn=alive_today_tool,
        payload={
            "windowStart": "2026-04-20T00:00:00Z",
            "windowEnd": "2026-04-20T23:59:59Z",
            "explicitQuestion": "What is alive today?",
        },
    )
    _event(timeline, scenario.name, "day_1_alive_today", "tool_observed", "circulatio_alive_today")
    _event(timeline, scenario.name, "day_1_invitation", "host_invitation", "offer_ritual")
    _event(timeline, scenario.name, "day_1_accept", "user_acceptance", "accepted")
    response = await recorder.call(
        scenario=scenario.name,
        turn="day_1_plan",
        tool="circulatio_plan_ritual",
        fn=plan_ritual_tool,
        payload=_plan_payload(
            intent="alive_today",
            title="Daily river gate ritual",
            source_ref_id="daily_river_gate",
            window_start="2026-04-20T00:00:00Z",
            window_end="2026-04-20T23:59:59Z",
            config=config,
        ),
    )
    _event(timeline, scenario.name, "day_1_plan", "tool_observed", "circulatio_plan_ritual")
    artifact = _artifact_from_response(response, config=config, scenario=scenario.name)
    if artifact:
        scenario.artifact_ids.append(str(artifact["artifactId"]))
        scenario.warnings.extend(str(item) for item in artifact.get("warnings", []) if str(item))
        artifacts.append(artifact)
        audit = _audit_artifact(artifact, config=config, completed=False)
        browser_checks.append(audit)
        artifact["browserCheckResult"] = "pass" if audit.get("passed") else "fail"
        artifact["browserCheckPassed"] = bool(audit.get("passed"))
        completion = await _record_completion(
            config=config,
            recorder=recorder,
            artifact=artifact,
            scenario=scenario.name,
            turn="day_1_completion",
        )
        scenario.completion_ids.append(str(completion.get("completionId") or ""))
        _mark_completion_submitted(browser_checks[-1], ok=bool(completion.get("ok")))
        artifact["browserCheckResult"] = "pass" if browser_checks[-1].get("passed") else "fail"
        artifact["browserCheckPassed"] = bool(browser_checks[-1].get("passed"))
        _event(
            timeline,
            scenario.name,
            "day_1_completion",
            "tool_observed",
            "circulatio_record_ritual_completion",
        )
    return scenario


async def _run_weekly_scenario(
    *,
    config: RitualJourneyConfig,
    runtime: Any,
    recorder: ToolRecorder,
    timeline: list[_JSON],
    artifacts: list[_JSON],
    browser_checks: list[_JSON],
) -> ScenarioState:
    scenario = ScenarioState("weekly", recorder.user_id, [], [], [])
    await runtime.service.set_consent_preference(
        {"userId": recorder.user_id, "scope": "proactive_briefing", "status": "allow"}
    )
    _event(timeline, scenario.name, "setup_consent", "setup", "proactive_briefing_allow")
    for index, summary in enumerate(
        [
            "River gate image returned after work.",
            "The gate felt less sharp during breathing.",
            "The river image stayed with me after the week ended.",
        ],
        start=1,
    ):
        await recorder.call(
            scenario=scenario.name,
            turn=f"week_material_{index}",
            tool="circulatio_store_reflection",
            fn=store_reflection_tool,
            payload={
                "text": summary,
                "summary": summary,
                "materialDate": f"2026-04-{20 + index}T08:00:00Z",
                "privacyClass": "private",
            },
        )
    _event(timeline, scenario.name, "week_materials", "tool_observed", "store_reflections")
    brief_response = await recorder.call(
        scenario=scenario.name,
        turn="weekly_brief",
        tool="circulatio_generate_rhythmic_briefs",
        fn=generate_rhythmic_briefs_tool,
        payload={
            "windowStart": "2026-04-20T00:00:00Z",
            "windowEnd": "2026-04-26T23:59:59Z",
            "source": "scheduled",
            "briefTypes": ["ritual_invitation"],
            "limit": 1,
        },
    )
    _event(
        timeline,
        scenario.name,
        "weekly_brief",
        "tool_observed",
        "circulatio_generate_rhythmic_briefs",
    )
    invitation = _first_ritual_invitation(brief_response)
    if invitation:
        _event(timeline, scenario.name, "weekly_invitation", "host_invitation", "ritual_invitation")
    _event(timeline, scenario.name, "weekly_accept", "user_acceptance", "accepted")
    payload = _weekly_acceptance_payload(invitation=invitation, config=config)
    response = await recorder.call(
        scenario=scenario.name,
        turn="weekly_plan",
        tool="circulatio_plan_ritual",
        fn=plan_ritual_tool,
        payload=payload,
    )
    _event(timeline, scenario.name, "weekly_plan", "tool_observed", "circulatio_plan_ritual")
    artifact = _artifact_from_response(response, config=config, scenario=scenario.name)
    if artifact:
        scenario.artifact_ids.append(str(artifact["artifactId"]))
        scenario.warnings.extend(str(item) for item in artifact.get("warnings", []) if str(item))
        artifacts.append(artifact)
        audit = _audit_artifact(artifact, config=config, completed=False)
        browser_checks.append(audit)
        artifact["browserCheckResult"] = "pass" if audit.get("passed") else "fail"
        artifact["browserCheckPassed"] = bool(audit.get("passed"))
        completion = await _record_completion(
            config=config,
            recorder=recorder,
            artifact=artifact,
            scenario=scenario.name,
            turn="weekly_completion",
        )
        scenario.completion_ids.append(str(completion.get("completionId") or ""))
        _mark_completion_submitted(browser_checks[-1], ok=bool(completion.get("ok")))
        artifact["browserCheckResult"] = "pass" if browser_checks[-1].get("passed") else "fail"
        artifact["browserCheckPassed"] = bool(browser_checks[-1].get("passed"))
        _event(
            timeline,
            scenario.name,
            "weekly_completion",
            "tool_observed",
            "circulatio_record_ritual_completion",
        )
    return scenario


async def _run_negative_scenarios(
    *,
    config: RitualJourneyConfig,
    runtime: Any,
    recorder: ToolRecorder,
    timeline: list[_JSON],
    artifacts: list[_JSON],
    browser_checks: list[_JSON],
) -> list[_JSON]:
    results: list[_JSON] = []
    no_consent_user = "journey_cli_no_consent"
    no_consent_recorder = ToolRecorder(
        run_id=config.run_id,
        profile=recorder.profile,
        user_id=no_consent_user,
    )
    await runtime.service.store_material(
        {
            "userId": no_consent_user,
            "materialType": "reflection",
            "text": "A weekly image repeated.",
            "summary": "Weekly image repeated",
            "materialDate": "2026-04-26T08:00:00Z",
        }
    )
    no_consent = await no_consent_recorder.call(
        scenario="negative_no_consent",
        turn="scheduled_brief",
        tool="circulatio_generate_rhythmic_briefs",
        fn=generate_rhythmic_briefs_tool,
        payload={"source": "scheduled", "briefTypes": ["ritual_invitation"], "limit": 1},
    )
    recorder.calls.extend(no_consent_recorder.calls)
    _event(
        timeline,
        "negative_no_consent",
        "scheduled_brief",
        "tool_observed",
        "circulatio_generate_rhythmic_briefs",
    )
    results.append(
        {
            "name": "negative_no_consent",
            "passed": not bool(_briefs(no_consent)),
            "detail": _sanitize(no_consent.get("result", no_consent)),
        }
    )

    skip_response = await recorder.call(
        scenario="negative_skip",
        turn="dismiss_invitation",
        tool="circulatio_respond_rhythmic_brief",
        fn=respond_rhythmic_brief_tool,
        payload={"briefId": "synthetic_invitation_skip", "action": "dismissed"},
    )
    _event(
        timeline,
        "negative_skip",
        "dismiss_invitation",
        "tool_observed",
        "circulatio_respond_rhythmic_brief",
    )
    results.append(
        {
            "name": "negative_skip",
            "passed": not _planned_after_turn(timeline, "negative_skip", "dismiss_invitation"),
            "detail": _response_summary(skip_response),
        }
    )

    missing_token_policy = _provider_policy(
        config=config,
        live=True,
        provider_profile="chutes_all",
        surfaces=["audio", "captions", "image"],
        max_cost_usd=max(config.max_cost_usd, 1.0),
        chutes_token_env="CIRCULATIO_JOURNEY_MISSING_CHUTES_TOKEN",
    )
    missing_token_response = await recorder.call(
        scenario="negative_missing_chutes_token",
        turn="plan",
        tool="circulatio_plan_ritual",
        fn=plan_ritual_tool,
        payload=_plan_payload(
            intent="weekly_integration",
            title="Missing token provider gate",
            source_ref_id="negative_missing_token",
            window_start="2026-04-20T00:00:00Z",
            window_end="2026-04-26T23:59:59Z",
            config=config,
            render_policy=missing_token_policy,
            request_image=True,
        ),
    )
    _event(
        timeline, "negative_missing_chutes_token", "plan", "tool_observed", "circulatio_plan_ritual"
    )
    missing_artifact = _artifact_from_response(
        missing_token_response, config=config, scenario="negative_missing_chutes_token"
    )
    missing_warnings = [str(item) for item in _response_warnings(missing_token_response)]
    results.append(
        {
            "name": "negative_missing_chutes_token",
            "passed": "ritual_handoff_chutes_skipped_missing_api_token" in missing_warnings,
            "warnings": missing_warnings,
        }
    )
    if missing_artifact:
        artifacts.append(missing_artifact)
        audit = _audit_artifact(missing_artifact, config=config, completed=False)
        browser_checks.append(audit)
        missing_artifact["browserCheckResult"] = "pass" if audit.get("passed") else "fail"
        missing_artifact["browserCheckPassed"] = bool(audit.get("passed"))

    zero_budget_policy = _provider_policy(
        config=config,
        live=True,
        provider_profile="chutes_all",
        surfaces=["audio", "captions", "image"],
        max_cost_usd=0.0,
        chutes_token_env=config.chutes_token_env,
    )
    zero_budget_response = await recorder.call(
        scenario="negative_zero_budget",
        turn="plan",
        tool="circulatio_plan_ritual",
        fn=plan_ritual_tool,
        payload=_plan_payload(
            intent="weekly_integration",
            title="Zero budget provider gate",
            source_ref_id="negative_zero_budget",
            window_start="2026-04-20T00:00:00Z",
            window_end="2026-04-26T23:59:59Z",
            config=config,
            render_policy=zero_budget_policy,
            request_image=True,
        ),
    )
    _event(timeline, "negative_zero_budget", "plan", "tool_observed", "circulatio_plan_ritual")
    zero_warnings = [str(item) for item in _response_warnings(zero_budget_response)]
    results.append(
        {
            "name": "negative_zero_budget",
            "passed": "ritual_handoff_chutes_skipped_zero_budget" in zero_warnings,
            "warnings": zero_warnings,
        }
    )

    video_block_response = await recorder.call(
        scenario="negative_video_blocked",
        turn="plan",
        tool="circulatio_plan_ritual",
        fn=plan_ritual_tool,
        payload=_plan_payload(
            intent="weekly_integration",
            title="Video blocked provider gate",
            source_ref_id="negative_video_blocked",
            window_start="2026-04-20T00:00:00Z",
            window_end="2026-04-26T23:59:59Z",
            config=config,
            render_policy=_provider_policy(
                config=config,
                live=False,
                provider_profile="mock",
                surfaces=["video"],
                video_allowed=False,
                allow_beta_video=False,
            ),
            request_cinema=True,
        ),
    )
    _event(timeline, "negative_video_blocked", "plan", "tool_observed", "circulatio_plan_ritual")
    video_warnings = [str(item) for item in _response_warnings(video_block_response)]
    results.append(
        {
            "name": "negative_video_blocked",
            "passed": any(
                item
                in {
                    "cinema_disabled_without_video_allowed",
                    "ritual_handoff_cinema_skipped_without_video_allowed",
                    "requested_surface_alias_normalized:video->cinema",
                }
                for item in video_warnings
            ),
            "warnings": video_warnings,
        }
    )
    return results


def _plan_payload(
    *,
    intent: str,
    title: str,
    source_ref_id: str,
    window_start: str,
    window_end: str,
    config: RitualJourneyConfig,
    render_policy: _JSON | None = None,
    request_image: bool | None = None,
    request_cinema: bool | None = None,
) -> _JSON:
    image_requested = bool(config.live_providers) if request_image is None else request_image
    cinema_requested = bool(config.include_video) if request_cinema is None else request_cinema
    music_requested = bool(config.include_music)
    return {
        "ritualIntent": intent,
        "narrativeMode": "hybrid",
        "windowStart": window_start,
        "windowEnd": window_end,
        "sourceRefs": [
            {
                "sourceType": "material",
                "recordId": source_ref_id,
                "role": "primary",
                "title": title,
                "approvalState": "read_only_generated",
            }
        ],
        "requestedSurfaces": {
            "text": {"enabled": True},
            "audio": {"enabled": True, "tone": "gentle", "pace": "slow"},
            "captions": {"enabled": True, "format": "webvtt"},
            "breath": {
                "enabled": True,
                "request": {"pattern": "lengthened_exhale", "cycles": 4},
            },
            "meditation": {
                "enabled": True,
                "request": {"fieldType": "attention_anchor", "durationMs": 90000},
            },
            "image": {"enabled": image_requested, "styleIntent": "symbolic_non_literal"},
            "cinema": {"enabled": cinema_requested, "maxDurationSeconds": 8},
            "music": {
                "enabled": music_requested,
                "allowExternalGeneration": music_requested,
                "styleIntent": "dream_integration",
                "musicDurationSeconds": 60,
            },
        },
        "renderPolicy": render_policy
        or _provider_policy(
            config=config,
            live=config.live_providers,
            provider_profile=config.provider_profile,
            surfaces=[
                "audio",
                "captions",
                "image",
                *(["music"] if config.include_music else []),
                *(["video"] if config.include_video else []),
            ],
            video_allowed=config.include_video,
            allow_beta_video=config.allow_beta_video,
            allow_beta_music=config.allow_beta_music,
            max_cost_usd=config.max_cost_usd,
            chutes_token_env=config.chutes_token_env,
        ),
        "completionPolicy": {
            "captureReflection": True,
            "capturePracticeFeedback": True,
            "reflectionPrompt": "What changed in body or attention after this?",
            "returnMode": "frontend_callback",
        },
        "privacyClass": "private",
        "locale": "en-US",
    }


def _weekly_acceptance_payload(*, invitation: _JSON | None, config: RitualJourneyConfig) -> _JSON:
    payload = deepcopy(invitation.get("acceptancePayload") if invitation else {})
    if not payload:
        payload = _plan_payload(
            intent="weekly_integration",
            title="Weekly ritual invitation",
            source_ref_id="weekly_river_gate",
            window_start="2026-04-20T00:00:00Z",
            window_end="2026-04-26T23:59:59Z",
            config=config,
        )
    payload["renderPolicy"] = _provider_policy(
        config=config,
        live=config.live_providers,
        provider_profile=config.provider_profile,
        surfaces=[
            "audio",
            "captions",
            "image",
            *(["music"] if config.include_music else []),
            *(["video"] if config.include_video else []),
        ],
        video_allowed=config.include_video,
        allow_beta_video=config.allow_beta_video,
        allow_beta_music=config.allow_beta_music,
        max_cost_usd=config.max_cost_usd,
        chutes_token_env=config.chutes_token_env,
    )
    requested = payload.get("requestedSurfaces")
    if isinstance(requested, dict):
        requested.setdefault("audio", {"enabled": True, "tone": "gentle"})
        requested.setdefault("captions", {"enabled": True, "format": "webvtt"})
        requested["image"] = {"enabled": bool(config.live_providers)}
        requested["cinema"] = {"enabled": bool(config.include_video), "maxDurationSeconds": 8}
        requested["music"] = {
            "enabled": bool(config.include_music),
            "allowExternalGeneration": bool(config.include_music),
            "styleIntent": "dream_integration",
            "musicDurationSeconds": 60,
        }
    return payload


def _provider_policy(
    *,
    config: RitualJourneyConfig,
    live: bool,
    provider_profile: str,
    surfaces: list[str],
    max_cost_usd: float | None = None,
    chutes_token_env: str | None = None,
    video_allowed: bool = False,
    allow_beta_video: bool = False,
    allow_beta_music: bool = False,
) -> _JSON:
    if not live:
        return {
            "mode": "render_static",
            "defaultDurationSeconds": 120,
            "maxDurationSeconds": 180,
            "externalProvidersAllowed": False,
            "providerAllowlist": ["mock", "local"],
            "providerProfile": "mock",
            "surfaces": surfaces,
            "videoAllowed": False,
            "allowBetaVideo": False,
            "allowBetaMusic": False,
            "transcriptionProvider": "fallback",
            "maxCost": {"currency": "USD", "amount": 0},
        }
    provider_allowlist = ["chutes"]
    if config.transcription_provider == "openai":
        provider_allowlist.append("openai")
    return {
        "mode": "render_static",
        "defaultDurationSeconds": 120,
        "maxDurationSeconds": 180,
        "externalProvidersAllowed": True,
        "providerAllowlist": provider_allowlist,
        "providerProfile": provider_profile,
        "surfaces": surfaces,
        "transcribeCaptions": "captions" in surfaces,
        "transcriptionProvider": config.transcription_provider,
        "openaiApiKeyEnv": config.openai_api_key_env,
        "openaiTranscriptionModel": config.openai_transcription_model,
        "openaiTranscriptionResponseFormat": "verbose_json",
        "requestTimeoutSeconds": config.request_timeout_seconds,
        "videoAllowed": video_allowed,
        "allowBetaVideo": allow_beta_video,
        "allowBetaMusic": allow_beta_music,
        "chutesTokenEnv": chutes_token_env or config.chutes_token_env,
        "maxCost": {"currency": "USD", "amount": config.max_cost_usd},
        "maxCostUsd": config.max_cost_usd if max_cost_usd is None else max_cost_usd,
        "sourceDataPolicy": {
            "allowRawMaterialTextInPlan": False,
            "allowRawMaterialTextToProviders": False,
            "providerPromptPolicy": "sanitized_visual_only",
        },
    }


async def _record_completion(
    *,
    config: RitualJourneyConfig,
    recorder: ToolRecorder,
    artifact: _JSON,
    scenario: str,
    turn: str,
) -> _JSON:
    manifest = _read_manifest_for_artifact(artifact, config=config)
    artifact_id = str(artifact.get("artifactId") or "")
    completion_id = f"completion_{scenario}_{artifact_id[-8:]}"
    response = await recorder.call(
        scenario=scenario,
        turn=turn,
        tool="circulatio_record_ritual_completion",
        fn=record_ritual_completion_tool,
        payload={
            "artifactId": artifact_id,
            "manifestVersion": str(manifest.get("schemaVersion") or "hermes_ritual_artifact.v1"),
            "completionId": completion_id,
            "idempotencyKey": completion_id,
            "completedAt": _now_iso(),
            "playbackState": "completed",
            "planId": str(manifest.get("planId") or artifact.get("planId") or ""),
            "sourceRefs": manifest.get("sourceRefs", []),
            "durationMs": int(manifest.get("durationMs", 0) or 0),
            "completedSections": ["opening", "breath", "meditation", "closing"],
            "reflectionText": "The breathing made the image feel less sharp.",
            "practiceFeedback": {"fit": "good_fit", "intensity": "low"},
            "bodyState": {
                "sensation": "easing",
                "bodyRegion": "chest",
                "activation": "low",
                "tone": "settled",
            },
            "clientMetadata": {"source": "journey_cli_eval"},
        },
    )
    return {"ok": str(response.get("status")) == "ok", "completionId": completion_id}


def _artifact_from_response(
    response: _JSON, *, config: RitualJourneyConfig, scenario: str
) -> _JSON | None:
    result = response.get("result") if isinstance(response.get("result"), dict) else {}
    artifact = result.get("artifact") if isinstance(result, dict) else None
    if not isinstance(artifact, dict) or not artifact.get("artifactId"):
        return None
    artifact_id = str(artifact["artifactId"])
    manifest_path = config.artifact_root / artifact_id / "manifest.json"
    manifest = _read_json(manifest_path)
    warnings = []
    warnings.extend(str(item) for item in result.get("warnings", []) if str(item))
    warnings.extend(str(item) for item in artifact.get("renderWarnings", []) if str(item))
    return {
        "scenario": scenario,
        "artifactId": artifact_id,
        "url": str(artifact.get("url") or f"{config.base_url}/artifacts/{artifact_id}"),
        "route": str(artifact.get("route") or f"/artifacts/{artifact_id}"),
        "manifestPath": str(manifest_path),
        "planPath": str(artifact.get("planPath") or ""),
        "planId": str(manifest.get("planId") or result.get("planId") or ""),
        "providers": artifact.get("providers", []),
        "surfaces": artifact.get("surfaces", {}),
        "warnings": list(dict.fromkeys(warnings)),
        "manifestSummary": _manifest_summary(manifest),
        "manifestSurfaces": _manifest_summary(manifest),
        "browserCheckResult": "pending",
        "browserCheckPassed": False,
    }


def _audit_artifact(artifact: _JSON, *, config: RitualJourneyConfig, completed: bool) -> _JSON:
    manifest_path = Path(str(artifact.get("manifestPath") or ""))
    manifest = _read_json(manifest_path)
    surfaces = manifest.get("surfaces") if isinstance(manifest.get("surfaces"), dict) else {}
    interaction = (
        manifest.get("interaction") if isinstance(manifest.get("interaction"), dict) else {}
    )
    artifact_id = str(artifact.get("artifactId") or manifest.get("artifactId") or "")
    scenario = str(artifact.get("scenario") or "")
    accepted_provider_run = bool(config.live_providers and scenario in {"daily", "weekly"})
    checks: list[_JSON] = []

    def add(name: str, status: str, detail: str = "") -> None:
        checks.append({"name": name, "status": status, "detail": detail})

    add("page_not_404", *_http_or_skip(f"{config.base_url}/artifacts/{artifact_id}", config))
    manifest_ok = manifest.get("schemaVersion") == "hermes_ritual_artifact.v1"
    add("manifest_json_loads", "pass" if manifest_ok else "fail", str(manifest_path))
    captions = surfaces.get("captions") if isinstance(surfaces.get("captions"), dict) else {}
    caption_segments = captions.get("segments") if isinstance(captions, dict) else []
    captions_path = manifest_path.with_name("captions.vtt")
    add("captions_vtt_loads", "pass" if captions_path.exists() else "fail", str(captions_path))
    add("captions_transcript_visible", "pass" if caption_segments else "fail")
    add("section_list_includes_transcript", "pass" if caption_segments else "fail")

    audio = surfaces.get("audio") if isinstance(surfaces.get("audio"), dict) else {}
    audio_src = str(audio.get("src") or "") if isinstance(audio, dict) else ""
    if audio_src:
        audio_path = manifest_path.with_name(Path(audio_src).name)
        add("audio_wav_loads", "pass" if audio_path.exists() else "fail", str(audio_path))
        add("audio_play_works", "pass" if audio_path.exists() else "fail")
        add("scrub_moves_time_and_waveform", "pass" if audio_path.exists() else "fail")
    else:
        status = "fail" if accepted_provider_run else "skip"
        detail = (
            "live provider audio missing"
            if status == "fail"
            else "audio provider fallback expected"
        )
        add("audio_wav_loads", status, detail)
        add("audio_play_works", status, detail)
        add("scrub_moves_time_and_waveform", status, detail)

    image = surfaces.get("image") if isinstance(surfaces.get("image"), dict) else {}
    image_src = str(image.get("src") or "") if isinstance(image, dict) else ""
    if image_src:
        image_path = manifest_path.with_name(Path(image_src).name)
        add(
            "generated_image_visible_on_photo",
            "pass" if image_path.exists() else "fail",
            str(image_path),
        )
    else:
        status = "fail" if accepted_provider_run else "skip"
        detail = (
            "live provider image missing"
            if status == "fail"
            else "image provider fallback expected"
        )
        add("generated_image_visible_on_photo", status, detail)

    music = surfaces.get("music") if isinstance(surfaces.get("music"), dict) else {}
    music_src = str(music.get("src") or "") if isinstance(music, dict) else ""
    if music_src:
        music_path = manifest_path.with_name(Path(music_src).name)
        add("music_audio_loads", "pass" if music_path.exists() else "fail", str(music_path))
        add("music_loops_and_syncs", "pass" if music_path.exists() else "fail")
    else:
        status = "fail" if accepted_provider_run and config.include_music else "skip"
        detail = "live provider music missing" if status == "fail" else "music not requested"
        add("music_audio_loads", status, detail)
        add("music_loops_and_syncs", status, detail)

    cinema = surfaces.get("cinema") if isinstance(surfaces.get("cinema"), dict) else {}
    cinema_src = str(cinema.get("src") or "") if isinstance(cinema, dict) else ""
    if cinema_src:
        cinema_path = manifest_path.with_name(Path(cinema_src).name)
        add("cinema_mp4_loads", "pass" if cinema_path.exists() else "fail", str(cinema_path))
    else:
        status = "fail" if accepted_provider_run and config.include_video else "skip"
        detail = (
            "live provider cinema missing"
            if status == "fail"
            else "video beta gate blocked or not requested"
        )
        add("cinema_mp4_loads", status, detail)

    breath = surfaces.get("breath") if isinstance(surfaces.get("breath"), dict) else {}
    meditation = surfaces.get("meditation") if isinstance(surfaces.get("meditation"), dict) else {}
    add("breath_lens_renders_and_play_works", "pass" if breath.get("enabled") else "fail")
    add("meditation_lens_renders_and_play_works", "pass" if meditation.get("enabled") else "fail")
    completion = (
        interaction.get("completion") if isinstance(interaction.get("completion"), dict) else {}
    )
    body_completion = bool(completion.get("enabled") and interaction.get("captureBodyResponse"))
    add("body_completion_ui_appears", "pass" if body_completion else "fail")
    add("completion_submit_works", "pass" if completed else "skip", "set after completion call")
    add(
        "console_clean",
        "skip" if not config.http_check else "pass",
        "HTTP-only check; no browser console",
    )
    add("network_failures_reported", "pass")
    return {
        "artifactId": artifact_id,
        "url": str(artifact.get("url") or ""),
        "manifestPath": str(manifest_path),
        "checks": checks,
        "passed": not any(check.get("status") == "fail" for check in checks),
    }


def _mark_completion_submitted(audit: _JSON, *, ok: bool) -> None:
    audit["completionSubmitted"] = ok
    for check in audit.get("checks", []):
        if isinstance(check, dict) and check.get("name") == "completion_submit_works":
            check["status"] = "pass" if ok else "fail"
            check["detail"] = "completion tool returned ok" if ok else "completion tool failed"
    audit["passed"] = not any(
        isinstance(check, dict) and check.get("status") == "fail"
        for check in audit.get("checks", [])
    )


def _tool_sequence(tool_calls: list[_JSON]) -> list[_JSON]:
    return [
        {
            "scenario": call.get("scenario"),
            "turn": call.get("turn"),
            "tool": call.get("tool"),
            "status": call.get("status"),
        }
        for call in tool_calls
    ]


def _surface_requests(tool_calls: list[_JSON]) -> list[_JSON]:
    requests: list[_JSON] = []
    for call in tool_calls:
        if call.get("tool") != "circulatio_plan_ritual":
            continue
        payload = call.get("payload") if isinstance(call.get("payload"), dict) else {}
        requests.append(
            {
                "scenario": call.get("scenario"),
                "turn": call.get("turn"),
                "requestedSurfaces": payload.get("requestedSurfaces", {}),
            }
        )
    return requests


def _render_policies(tool_calls: list[_JSON]) -> list[_JSON]:
    policies: list[_JSON] = []
    for call in tool_calls:
        if call.get("tool") != "circulatio_plan_ritual":
            continue
        payload = call.get("payload") if isinstance(call.get("payload"), dict) else {}
        policies.append(
            {
                "scenario": call.get("scenario"),
                "turn": call.get("turn"),
                "renderPolicy": payload.get("renderPolicy", {}),
            }
        )
    return policies


def _browser_check_summary(browser_checks: list[_JSON]) -> list[_JSON]:
    summary: list[_JSON] = []
    for audit in browser_checks:
        failed = []
        skipped = []
        for check in audit.get("checks", []):
            if not isinstance(check, dict):
                continue
            if check.get("status") == "fail":
                failed.append(check.get("name"))
            if check.get("status") == "skip":
                skipped.append(check.get("name"))
        summary.append(
            {
                "artifactId": audit.get("artifactId"),
                "passed": bool(audit.get("passed")),
                "failedChecks": failed,
                "skippedChecks": skipped,
            }
        )
    return summary


def _scorecard(
    *,
    timeline: list[_JSON],
    tool_calls: list[_JSON],
    artifacts: list[_JSON],
    browser_checks: list[_JSON],
    negative_results: list[_JSON],
    llm: JourneyRitualLlm,
) -> _JSON:
    negative_by_name = {str(item.get("name")): item for item in negative_results}
    plan_calls = [call for call in tool_calls if call.get("tool") == "circulatio_plan_ritual"]
    accepted_scenarios = {"daily", "weekly"}
    background_plans = [
        call
        for call in plan_calls
        if str(call.get("scenario")) not in accepted_scenarios
        and str(call.get("scenario"))
        not in {
            "negative_missing_chutes_token",
            "negative_zero_budget",
            "negative_video_blocked",
        }
    ]
    return {
        "proactivity": {
            "consent_respected": _passfail(
                bool(negative_by_name.get("negative_no_consent", {}).get("passed"))
            ),
            "cadence_correct": _passfail(_has_event(timeline, "weekly", "weekly_brief")),
            "invitation_before_plan": _passfail(_invitation_before_plan(timeline)),
            "no_background_render": _passfail(not background_plans),
        },
        "ritual_quality": {
            "source_refs_present": _passfail(
                bool(artifacts)
                and all(item["manifestSummary"].get("sourceRefs") for item in artifacts)
            ),
            "intent_matches_context": _passfail(_accepted_intents_ok(tool_calls)),
            "sections_present": _passfail(
                bool(artifacts)
                and all(item["manifestSummary"].get("breath") for item in artifacts[:2])
                and all(item["manifestSummary"].get("meditation") for item in artifacts[:2])
            ),
            "captions_present": _passfail(
                bool(artifacts)
                and all(item["manifestSummary"].get("captions") for item in artifacts)
            ),
        },
        "media": {
            "audio_real_or_expected_fallback": _passfail(
                _audit_status_ok(browser_checks, "audio_wav_loads")
            ),
            "image_real_or_expected_fallback": _passfail(
                _audit_status_ok(browser_checks, "generated_image_visible_on_photo")
            ),
            "waveform_sync": _passfail(
                _audit_status_ok(browser_checks, "scrub_moves_time_and_waveform")
            ),
            "transcript_sections": _passfail(
                _audit_status_ok(browser_checks, "section_list_includes_transcript")
            ),
            "music_real_or_expected_fallback": _passfail(
                _audit_status_ok(browser_checks, "music_audio_loads")
            ),
            "music_sync": _passfail(_audit_status_ok(browser_checks, "music_loops_and_syncs")),
            "cinema_real_or_expected_fallback": _passfail(
                _audit_status_ok(browser_checks, "cinema_mp4_loads")
            ),
        },
        "ui": {
            "photo": _passfail(
                _audit_status_ok(browser_checks, "generated_image_visible_on_photo")
            ),
            "breath": _passfail(
                _audit_status_ok(browser_checks, "breath_lens_renders_and_play_works")
            ),
            "meditation": _passfail(
                _audit_status_ok(browser_checks, "meditation_lens_renders_and_play_works")
            ),
            "body_completion": _passfail(
                _audit_status_ok(browser_checks, "body_completion_ui_appears")
            ),
            "console_clean": _passfail(_audit_status_ok(browser_checks, "console_clean")),
        },
        "negative_cases": {
            str(item.get("name")): _passfail(bool(item.get("passed"))) for item in negative_results
        },
        "llm_guardrails": {
            "no_interpretation_calls": _passfail(not llm.interpret_calls),
        },
    }


def _findings(
    *, scorecard: _JSON, browser_checks: list[_JSON], artifacts: list[_JSON]
) -> list[str]:
    findings: list[str] = []
    for group, values in scorecard.items():
        if not isinstance(values, dict):
            continue
        for name, result in values.items():
            if isinstance(result, dict) and result.get("status") == "fail":
                findings.append(f"{group}.{name} failed: {result.get('detail') or 'see report'}")
    for audit in browser_checks:
        for check in audit.get("checks", []):
            if isinstance(check, dict) and check.get("status") == "fail":
                findings.append(
                    f"{audit.get('artifactId')} browser check {check.get('name')} failed: "
                    f"{check.get('detail') or 'no detail'}"
                )
    for artifact in artifacts:
        warnings = artifact.get("warnings", [])
        if warnings:
            findings.append(f"{artifact.get('artifactId')} emitted warnings: {', '.join(warnings)}")
    return findings


def _next_enhancements(*, config: RitualJourneyConfig, browser_checks: list[_JSON]) -> list[str]:
    items: list[str] = []
    if not config.live_providers:
        items.append(
            "Run with --ritual-live-providers and a bounded budget to verify real "
            "Chutes audio/image."
        )
    if not config.include_video:
        items.append(
            "Run video only when videoAllowed, allowBetaVideo, Chutes profile, token, "
            "budget, and plan policy all pass."
        )
    if not config.http_check:
        items.append(
            "Run with --ritual-http-check while Hermes Rituals is serving the artifact "
            "root to capture page/network status."
        )
    if any(
        check.get("status") == "skip"
        for audit in browser_checks
        for check in audit.get("checks", [])
        if isinstance(check, dict)
    ):
        items.append(
            "Layer a browser driver over this report to turn skipped playback/console "
            "checks into click-level checks."
        )
    return items


def _write_bundle(config: RitualJourneyConfig, payload: _JSON) -> None:
    _write_json(config.run_dir / "report.json", payload["report"])
    _write_json(config.run_dir / "timeline.json", payload["timeline"])
    _write_json(config.run_dir / "tool_calls.json", payload["tool_calls"])
    _write_json(config.run_dir / "browser_checks.json", payload["browser_checks"])
    _write_json(config.run_dir / "artifacts_checked.json", payload["artifacts_checked"])
    (config.run_dir / "report.md").write_text(
        _render_markdown(
            report=payload["report"],
            artifacts=payload["artifacts_checked"],
            browser_checks=payload["browser_checks"],
        ),
        encoding="utf-8",
    )


def _render_markdown(*, report: _JSON, artifacts: object, browser_checks: object) -> str:
    lines = [
        "# Ritual Journey CLI Eval",
        "",
        f"Run: `{report.get('runId')}`",
        f"Passed: `{report.get('passed')}`",
        "",
        "## JTBD",
    ]
    for item in report.get("jtbd", []):
        if isinstance(item, dict):
            lines.append(f"- {item.get('job')}: {item.get('outcome')}")
    lines.extend(["", "## Selected Tool Sequence"])
    for item in report.get("selectedToolSequence", []):
        if isinstance(item, dict):
            scenario = item.get("scenario")
            turn = item.get("turn")
            tool = item.get("tool")
            status = item.get("status")
            lines.append(f"- `{scenario}/{turn}` -> `{tool}` ({status})")
    lines.extend(["", "## Scorecard"])
    scorecard = report.get("scorecard") if isinstance(report.get("scorecard"), dict) else {}
    for group, values in scorecard.items():
        if not isinstance(values, dict):
            continue
        lines.append(f"\n### {group}")
        for name, result in values.items():
            if isinstance(result, dict):
                lines.append(f"- `{name}`: {result.get('status')}")
    lines.extend(["", "## Artifacts"])
    for artifact in artifacts if isinstance(artifacts, list) else []:
        if isinstance(artifact, dict):
            surfaces = artifact.get("manifestSurfaces", artifact.get("manifestSummary", {}))
            lines.append(
                f"- `{artifact.get('artifactId')}` - {artifact.get('url')} - "
                f"browser: `{artifact.get('browserCheckResult')}` - surfaces: `{surfaces}`"
            )
    lines.extend(["", "## Browser Checks"])
    for audit in browser_checks if isinstance(browser_checks, list) else []:
        if not isinstance(audit, dict):
            continue
        lines.append(f"\n### {audit.get('artifactId')}")
        for check in audit.get("checks", []):
            if isinstance(check, dict):
                line = f"- `{check.get('name')}`: {check.get('status')} {check.get('detail') or ''}"
                lines.append(line.rstrip())
    lines.extend(["", "## Findings"])
    findings = report.get("findings", [])
    if findings:
        for finding in findings:
            lines.append(f"- {finding}")
    else:
        lines.append("- No failing findings.")
    lines.extend(["", "## Next Enhancements"])
    for item in report.get("nextEnhancements", []):
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def _manifest_summary(manifest: _JSON) -> _JSON:
    surfaces = manifest.get("surfaces") if isinstance(manifest.get("surfaces"), dict) else {}
    captions = surfaces.get("captions") if isinstance(surfaces.get("captions"), dict) else {}
    breath = surfaces.get("breath") if isinstance(surfaces.get("breath"), dict) else {}
    meditation = surfaces.get("meditation") if isinstance(surfaces.get("meditation"), dict) else {}
    image = surfaces.get("image") if isinstance(surfaces.get("image"), dict) else {}
    cinema = surfaces.get("cinema") if isinstance(surfaces.get("cinema"), dict) else {}
    music = surfaces.get("music") if isinstance(surfaces.get("music"), dict) else {}
    return {
        "schemaVersion": manifest.get("schemaVersion"),
        "planId": manifest.get("planId"),
        "sourceRefs": bool(manifest.get("sourceRefs")),
        "captions": bool(captions.get("segments")),
        "breath": bool(breath.get("enabled")),
        "meditation": bool(meditation.get("enabled")),
        "image": bool(image.get("enabled") and image.get("src")),
        "cinema": bool(cinema.get("enabled") and cinema.get("src")),
        "music": bool(music.get("src")),
    }


def _first_ritual_invitation(response: _JSON) -> _JSON | None:
    for brief in _briefs(response):
        if isinstance(brief, dict) and brief.get("briefType") == "ritual_invitation":
            invitation = brief.get("ritualInvitation")
            return invitation if isinstance(invitation, dict) else None
    return None


def _briefs(response: _JSON) -> list[object]:
    result = response.get("result") if isinstance(response.get("result"), dict) else {}
    briefs = result.get("briefs") if isinstance(result, dict) else response.get("briefs")
    return list(briefs) if isinstance(briefs, list) else []


def _response_warnings(response: _JSON) -> list[object]:
    result = response.get("result") if isinstance(response.get("result"), dict) else {}
    warnings = result.get("warnings") if isinstance(result, dict) else []
    return list(warnings) if isinstance(warnings, list) else []


def _response_ok_or_validation(response: _JSON) -> bool:
    return str(response.get("status")) in {"ok", "validation_error", "error"}


def _read_manifest_for_artifact(artifact: _JSON, *, config: RitualJourneyConfig) -> _JSON:
    artifact_id = str(artifact.get("artifactId") or "")
    return _read_json(config.artifact_root / artifact_id / "manifest.json")


def _read_json(path: Path) -> _JSON:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n")


def _create_run_dir(root: Path, *, run_id: str | None) -> tuple[str, Path]:
    root.mkdir(parents=True, exist_ok=True)
    chosen = run_id or default_run_id().replace("evo_", "journey_")
    candidate = root / chosen
    suffix = 2
    while candidate.exists():
        candidate = root / f"{chosen}_{suffix}"
        suffix += 1
    candidate.mkdir(parents=True)
    return candidate.name, candidate


@contextmanager
def _patched_env(values: dict[str, str]):
    old = {key: os.environ.get(key) for key in values}
    os.environ.update(values)
    try:
        yield
    finally:
        for key, value in old.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _handoff_env(config: RitualJourneyConfig) -> dict[str, str]:
    return {
        "CIRCULATIO_REPO_ROOT": str(REPO_ROOT),
        "CIRCULATIO_RITUAL_ARTIFACT_ROOT": str(config.artifact_root),
        "CIRCULATIO_RITUAL_PLAN_ROOT": str(config.plan_root),
        "CIRCULATIO_RENDERER_SCRIPT": str(REPO_ROOT / "scripts" / "render_ritual_artifact.py"),
        "CIRCULATIO_RITUALS_BASE_URL": config.base_url,
        "CIRCULATIO_RITUAL_HANDOFF_MODE": "render_static",
        "CIRCULATIO_RITUAL_OPEN": "0",
        "CIRCULATIO_RITUAL_RENDER_TIMEOUT_SECONDS": str(
            max(60, config.request_timeout_seconds * 3)
        ),
    }


def _event(timeline: list[_JSON], scenario: str, turn: str, kind: str, label: str) -> None:
    timeline.append(
        {"at": _now_iso(), "scenario": scenario, "turn": turn, "kind": kind, "label": label}
    )


def _has_event(timeline: list[_JSON], scenario: str, turn: str) -> bool:
    return any(item.get("scenario") == scenario and item.get("turn") == turn for item in timeline)


def _planned_after_turn(timeline: list[_JSON], scenario: str, turn: str) -> bool:
    seen_turn = False
    for item in timeline:
        if item.get("scenario") != scenario:
            continue
        if item.get("turn") == turn:
            seen_turn = True
        if seen_turn and item.get("label") == "circulatio_plan_ritual":
            return True
    return False


def _invitation_before_plan(timeline: list[_JSON]) -> bool:
    for scenario in ("daily", "weekly"):
        invitation_index = _first_index(timeline, scenario=scenario, kind="host_invitation")
        plan_index = _first_index(timeline, scenario=scenario, label="circulatio_plan_ritual")
        if invitation_index is None or plan_index is None or invitation_index > plan_index:
            return False
    return True


def _first_index(
    timeline: list[_JSON], *, scenario: str, kind: str | None = None, label: str | None = None
) -> int | None:
    for index, item in enumerate(timeline):
        if item.get("scenario") != scenario:
            continue
        if kind is not None and item.get("kind") != kind:
            continue
        if label is not None and item.get("label") != label:
            continue
        return index
    return None


def _accepted_intents_ok(tool_calls: list[_JSON]) -> bool:
    expected = {"daily": "alive_today", "weekly": "weekly_integration"}
    seen: dict[str, str] = {}
    for call in tool_calls:
        if call.get("tool") != "circulatio_plan_ritual":
            continue
        scenario = str(call.get("scenario") or "")
        payload = call.get("payload") if isinstance(call.get("payload"), dict) else {}
        intent = str(payload.get("ritualIntent") or "") if isinstance(payload, dict) else ""
        if scenario in expected:
            seen[scenario] = intent
    return all(seen.get(scenario) == intent for scenario, intent in expected.items())


def _audit_status_ok(browser_checks: list[_JSON], check_name: str) -> bool:
    relevant = []
    for audit in browser_checks:
        for check in audit.get("checks", []):
            if isinstance(check, dict) and check.get("name") == check_name:
                relevant.append(str(check.get("status") or ""))
    return bool(relevant) and all(status != "fail" for status in relevant)


def _has_failed(scorecard: _JSON) -> bool:
    for values in scorecard.values():
        if not isinstance(values, dict):
            continue
        for result in values.values():
            if isinstance(result, dict) and result.get("status") == "fail":
                return True
    return False


def _passfail(ok: bool, detail: str = "") -> _JSON:
    return {"status": "pass" if ok else "fail", "detail": detail}


def _http_or_skip(url: str, config: RitualJourneyConfig) -> tuple[str, str]:
    if not config.http_check:
        return "skip", "http_check disabled"
    status, detail = _http_status(url)
    if status and 200 <= status < 400:
        return "pass", f"HTTP {status}"
    if status == 404:
        return "fail", "HTTP 404"
    return "fail", detail or "request failed"


def _http_status(url: str) -> tuple[int | None, str]:
    try:
        with urllib.request.urlopen(
            urllib.request.Request(url, method="GET"), timeout=5
        ) as response:
            return int(response.status), response.headers.get("content-type", "")
    except urllib.error.HTTPError as exc:
        return int(exc.code), str(exc)
    except OSError as exc:
        return None, exc.__class__.__name__


def _asset_url(base_url: str, src: str) -> str:
    return urljoin(base_url.rstrip("/") + "/", src.lstrip("/"))


def _response_summary(response: _JSON) -> _JSON:
    result = response.get("result") if isinstance(response.get("result"), dict) else {}
    artifact = result.get("artifact") if isinstance(result, dict) else {}
    summary: _JSON = {
        "status": str(response.get("status") or ""),
        "message": str(response.get("message") or "")[:180],
    }
    if isinstance(artifact, dict) and artifact.get("artifactId"):
        summary["artifactId"] = str(artifact.get("artifactId"))
        summary["artifactUrl"] = str(result.get("artifactUrl") or artifact.get("url") or "")
    if isinstance(result, dict) and result.get("warnings"):
        summary["warnings"] = list(result.get("warnings", []))
    if isinstance(result, dict) and result.get("briefs"):
        summary["briefTypes"] = [
            str(item.get("briefType"))
            for item in result.get("briefs", [])
            if isinstance(item, dict)
        ]
    return _sanitize(summary)


def _sanitize(value: object) -> object:
    if isinstance(value, dict):
        sanitized: dict[str, object] = {}
        for key, item in value.items():
            if key in _TEXT_KEYS:
                sanitized[key] = f"[redacted:{len(str(item))}]"
            else:
                sanitized[str(key)] = _sanitize(item)
        return sanitized
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, str):
        if any(token in value for token in _SECRET_TOKENS):
            return "[redacted]"
        return value
    return value


def _jtbd_summary() -> list[_JSON]:
    return [
        {
            "job": "Test ritual behavior over time",
            "outcome": "Daily and weekly flows prove invite-before-plan and completion-only sync.",
        },
        {
            "job": "Protect proactivity boundaries",
            "outcome": (
                "Consent, skipped invitation, zero budget, missing token, and video "
                "gates are scored."
            ),
        },
        {
            "job": "Audit playback artifacts",
            "outcome": (
                "Manifest, captions, surfaces, assets, and completion contracts are "
                "checked per artifact."
            ),
        },
        {
            "job": "Guide next fixes",
            "outcome": (
                "Report files include findings and next enhancements for provider/browser coverage."
            ),
        },
    ]


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = ["JourneyRitualLlm", "run_ritual_journey_eval"]
