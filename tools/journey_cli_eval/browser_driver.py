from __future__ import annotations

import json
import os
import shutil
import subprocess
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

BrowserStepStatus = Literal["pass", "fail", "skip"]
BrowserResultStatus = Literal["pass", "fail", "skip"]
REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class BrowserDriverConfig:
    enabled: bool
    driver: Literal["agent-browser"]
    command: str
    required: bool
    base_url: str
    timeout_seconds: int
    screenshots_dir: Path
    run_dir: Path


@dataclass(frozen=True)
class BrowserDriverTask:
    artifact_id: str
    artifact_url: str
    live_url: str
    completion_endpoint: str
    idempotency_key: str
    guidance_session_id: str


@dataclass
class BrowserDriverStep:
    name: str
    status: BrowserStepStatus
    detail: str = ""
    stdout: str = ""
    stderr: str = ""


@dataclass
class BrowserDriverResult:
    artifact_id: str
    driver: str
    status: BrowserResultStatus
    reason: str
    artifact_url: str
    live_url: str
    started_at: str
    finished_at: str
    screenshots: list[str] = field(default_factory=list)
    steps: list[BrowserDriverStep] = field(default_factory=list)
    completion_post: dict[str, object] = field(default_factory=dict)

    def to_json(self) -> dict[str, object]:
        return asdict(self)


def run_browser_driver_task(
    config: BrowserDriverConfig,
    task: BrowserDriverTask,
) -> BrowserDriverResult:
    started_at = _now_iso()
    screenshots: list[str] = []
    steps: list[BrowserDriverStep] = []
    completion_post: dict[str, object] = {}

    def finish(status: BrowserResultStatus, reason: str) -> BrowserDriverResult:
        return BrowserDriverResult(
            artifact_id=task.artifact_id,
            driver=config.driver,
            status=status,
            reason=reason,
            artifact_url=task.artifact_url,
            live_url=task.live_url,
            started_at=started_at,
            finished_at=_now_iso(),
            screenshots=screenshots,
            steps=steps,
            completion_post=completion_post,
        )

    if not config.enabled:
        steps.append(BrowserDriverStep("browser_driver_enabled", "skip", "browser driver disabled"))
        return finish("skip", "disabled")

    if not shutil.which(config.command):
        steps.append(
            BrowserDriverStep("browser_driver_available", "skip", f"{config.command} not found")
        )
        return finish("skip", "agent_browser_not_found")

    reachable, detail = _url_reachable(task.artifact_url)
    if not reachable:
        status: BrowserStepStatus = "fail" if config.required else "skip"
        steps.append(BrowserDriverStep("browser_base_url_reachable", status, detail))
        return finish("fail" if config.required else "skip", "base_url_unreachable")
    steps.append(BrowserDriverStep("browser_base_url_reachable", "pass", detail))

    command_steps: list[tuple[str, list[str]]] = [
        ("browser_open_artifact", ["open", task.artifact_url]),
        ("browser_wait_artifact", ["wait", "--load", "networkidle"]),
        (
            "browser_artifact_shell_visible",
            ["find", "testid", "ritual-artifact-client", "text"],
        ),
        (
            "browser_open_companion",
            ["find", "testid", "ritual-companion-toggle", "click"],
        ),
        (
            "browser_fill_companion",
            [
                "find",
                "placeholder",
                "Ask without storing anything yet",
                "fill",
                "save this reflection: the breath felt softer.",
            ],
        ),
        (
            "browser_send_companion",
            ["find", "testid", "ritual-companion-send", "click"],
        ),
        ("browser_wait_approval", ["wait", "--text", "Awaiting approval"]),
        (
            "browser_companion_local_preview_action_visible",
            ["find", "testid", "ritual-companion-action-card", "text"],
        ),
        (
            "browser_approve_action",
            ["find", "testid", "ritual-companion-action-approve", "click"],
        ),
        ("browser_wait_local_preview", ["wait", "--text", "Local preview"]),
        (
            "browser_continue_live",
            ["find", "testid", "ritual-continue-live", "click"],
        ),
        ("browser_wait_live_url", ["wait", "--url", "**/live/**"]),
        ("browser_live_route_handoff", ["find", "testid", "live-guidance-shell", "text"]),
        (
            "browser_live_focus_movement",
            ["find", "testid", "live-focus-movement", "click"],
        ),
        ("browser_wait_movement", ["wait", "--text", "movement"]),
        (
            "browser_camera_preflight_explicit",
            ["find", "testid", "live-camera-preflight", "click"],
        ),
        ("browser_wait_camera_optional", ["wait", "--text", "Camera is optional"]),
        ("browser_no_camera", ["find", "testid", "live-no-camera", "click"]),
        ("browser_wait_no_camera", ["wait", "--text", "No-camera guidance is active"]),
        ("browser_pause_live", ["find", "testid", "live-pause", "click"]),
        ("browser_wait_paused", ["wait", "--text", "Guidance is paused"]),
        ("browser_complete_live", ["find", "testid", "live-complete", "click"]),
        ("browser_wait_completed", ["wait", "--text", "Live guidance was completed"]),
    ]

    for name, args in command_steps:
        step = _run_agent_browser(config, args, name=name)
        steps.append(step)
        if step.status == "fail":
            _try_close(config, steps)
            return finish("fail", name)

    completion_post = _run_completion_post(config, task, steps)
    screenshot_path = config.screenshots_dir / f"{task.artifact_id}-live.png"
    screenshot = _run_agent_browser(
        config,
        ["screenshot", str(screenshot_path)],
        name="browser_screenshot_live",
    )
    steps.append(screenshot)
    if screenshot.status == "pass":
        screenshots.append(str(screenshot_path))
    _try_close(config, steps)

    if not completion_post.get("firstOk") or not completion_post.get("secondOk"):
        return finish("fail", "completion_post_idempotency_failed")
    if any(step.status == "fail" for step in steps):
        return finish("fail", "browser_step_failed")
    return finish("pass", "passed")


def _run_completion_post(
    config: BrowserDriverConfig,
    task: BrowserDriverTask,
    steps: list[BrowserDriverStep],
) -> dict[str, object]:
    script = """
(async () => {
  const payload = {
    completionId: "__IDEMPOTENCY_KEY__",
    completedAt: new Date().toISOString(),
    playbackState: "completed",
    durationMs: 56000,
    completedSections: ["section-closing"],
    reflectionText: "Browser-driver idempotency proof.",
    practiceFeedback: {
      fit: "good_fit",
      sensorTelemetry: "must_not_forward"
    },
    bodyState: {
      sensation: "easing",
      bodyRegion: "chest",
      activation: "low",
      tone: "settled"
    },
    clientMetadata: {
      source: "journey_cli_agent_browser",
      cameraData: "must_not_forward"
    }
  };
  const headers = { "content-type": "application/json", "idempotency-key": "__IDEMPOTENCY_KEY__" };
  const first = await fetch("__COMPLETION_ENDPOINT__", {
    method: "POST",
    headers,
    body: JSON.stringify(payload)
  });
  const second = await fetch("__COMPLETION_ENDPOINT__", {
    method: "POST",
    headers,
    body: JSON.stringify(payload)
  });
  return JSON.stringify({
    firstStatus: first.status,
    secondStatus: second.status,
    firstOk: first.ok,
    secondOk: second.ok
  });
})()
""".strip()
    script = script.replace("__IDEMPOTENCY_KEY__", task.idempotency_key).replace(
        "__COMPLETION_ENDPOINT__", task.completion_endpoint
    )
    step = _run_agent_browser(config, ["eval", script], name="browser_completion_post_idempotent")
    steps.append(step)
    if step.status != "pass":
        return {"firstOk": False, "secondOk": False, "error": step.detail}
    return _parse_eval_json(step.stdout)


def _run_agent_browser(
    config: BrowserDriverConfig,
    args: list[str],
    *,
    name: str,
) -> BrowserDriverStep:
    env = os.environ.copy()
    env.pop("CHUTES_API_TOKEN", None)
    env.pop("OPENAI_API_KEY", None)
    try:
        completed = subprocess.run(
            [config.command, *args],
            cwd=REPO_ROOT,
            env=env,
            text=True,
            capture_output=True,
            timeout=config.timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return BrowserDriverStep(
            name,
            "fail",
            "timeout",
            stdout=exc.stdout or "",
            stderr=exc.stderr or "",
        )
    except OSError as exc:
        return BrowserDriverStep(name, "fail", exc.__class__.__name__)

    status: BrowserStepStatus = "pass" if completed.returncode == 0 else "fail"
    detail = "ok" if status == "pass" else f"exit {completed.returncode}"
    return BrowserDriverStep(
        name,
        status,
        detail,
        stdout=completed.stdout[-2000:],
        stderr=completed.stderr[-2000:],
    )


def _try_close(config: BrowserDriverConfig, steps: list[BrowserDriverStep]) -> None:
    if shutil.which(config.command):
        steps.append(_run_agent_browser(config, ["close"], name="browser_close"))


def _parse_eval_json(stdout: str) -> dict[str, object]:
    for line in reversed(stdout.splitlines()):
        text = line.strip()
        if not text:
            continue
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, str):
            try:
                parsed = json.loads(parsed)
            except json.JSONDecodeError:
                continue
        if isinstance(parsed, dict):
            return parsed
    return {"firstOk": False, "secondOk": False, "error": "completion_eval_parse_failed"}


def _url_reachable(url: str) -> tuple[bool, str]:
    try:
        with urllib.request.urlopen(
            urllib.request.Request(url, method="GET"), timeout=5
        ) as response:
            status = int(response.status)
            return 200 <= status < 400, f"HTTP {status}"
    except urllib.error.HTTPError as exc:
        return False, f"HTTP {exc.code}"
    except OSError as exc:
        return False, exc.__class__.__name__


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = [
    "BrowserDriverConfig",
    "BrowserDriverResult",
    "BrowserDriverStep",
    "BrowserDriverTask",
    "run_browser_driver_task",
]
