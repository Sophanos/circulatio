from __future__ import annotations

import asyncio
import hashlib
import json
from copy import deepcopy

from circulatio.domain.errors import PersistenceError, ProfileStorageCorruptionError
from circulatio.domain.ids import create_id
from circulatio.hermes.agent_bridge_contracts import (
    BridgeOperation,
    BridgeRequestEnvelope,
    BridgeResponseEnvelope,
    BridgeStatus,
    HermesSourceContext,
)
from circulatio.hermes.boot_validation import PluginBootError
from circulatio.hermes.command_parser import CirculatioCommandParser
from circulatio.hermes.result_renderer import CirculatioResultRenderer

from .runtime import get_runtime

_PARSER = CirculatioCommandParser()
_RENDERER = CirculatioResultRenderer()


async def handle_circulation(raw_args: str | None = None, **kwargs: object) -> str:
    command = _extract_command_text(raw_args=raw_args, kwargs=kwargs)
    try:
        request = build_command_request(raw_args=command, kwargs=kwargs)
    except Exception as exc:
        return _render_command_error(raw_args=command, kwargs=kwargs, exc=exc)
    try:
        response = await get_runtime(request["source"].get("profile")).bridge.dispatch(request)
    except Exception as exc:
        response = _boot_failure_response(request=request, exc=exc)
    return _RENDERER.render(response)


def handle_circulation_sync(raw_args: str | None = None, **kwargs: object) -> str:
    command = _extract_command_text(raw_args=raw_args, kwargs=kwargs)
    try:
        request = build_command_request(raw_args=command, kwargs=kwargs)
    except Exception as exc:
        return _render_command_error(raw_args=command, kwargs=kwargs, exc=exc)
    try:
        coro = get_runtime(request["source"].get("profile")).bridge.dispatch(request)
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop is not None and loop.is_running():
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(asyncio.run, coro)
                response = future.result()
        else:
            response = asyncio.run(coro)
    except Exception as exc:
        response = _boot_failure_response(request=request, exc=exc)
    return _RENDERER.render(response)


def _extract_command_text(*, raw_args: str | None, kwargs: dict[str, object]) -> str:
    candidates = (
        raw_args,
        kwargs.get("raw_args"),
        kwargs.get("args"),
        kwargs.get("command_args"),
        kwargs.get("user_args"),
        kwargs.get("command"),
        kwargs.get("text"),
    )
    for candidate in candidates:
        if candidate is None:
            continue
        if isinstance(candidate, str):
            return candidate
        return str(candidate)
    return ""


def build_command_request(*, raw_args: str, kwargs: dict[str, object]) -> BridgeRequestEnvelope:
    parsed = _PARSER.parse(raw_args)
    source = _source_context(raw_args=raw_args, kwargs=kwargs)
    user_id = _normalize_user_id(source=source, kwargs=kwargs)
    return {
        "requestId": create_id("bridge_req"),
        "idempotencyKey": _command_idempotency_key(source=source, subcommand=parsed.subcommand),
        "userId": user_id,
        "source": source,
        "operation": parsed.operation,
        "payload": deepcopy(parsed.payload),
    }


def build_tool_request(
    *,
    operation: BridgeOperation,
    payload: dict[str, object],
    tool_name: str,
    kwargs: dict[str, object],
) -> BridgeRequestEnvelope:
    source = _source_context(raw_args=f"tool:{tool_name}", kwargs=kwargs)
    user_id = _normalize_user_id(source=source, kwargs=kwargs)
    encoded_payload = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    tool_call_id = kwargs.get("tool_call_id")
    session_id = source.get("sessionId")
    message_id = source.get("messageId")
    if tool_call_id:
        token = str(tool_call_id)
    elif message_id and session_id:
        token = f"{session_id}:{message_id}:{tool_name}"
    else:
        token = hashlib.sha256(encoded_payload.encode("utf-8")).hexdigest()
    return {
        "requestId": create_id("bridge_req"),
        "idempotencyKey": f"tool:{tool_name}:{token}",
        "userId": user_id,
        "source": source,
        "operation": operation,
        "payload": deepcopy(payload),
    }


def _source_context(*, raw_args: str, kwargs: dict[str, object]) -> HermesSourceContext:
    platform = str(kwargs.get("platform") or kwargs.get("source_platform") or "cli")
    session_id = kwargs.get("session_id") or kwargs.get("sessionId")
    message_id = kwargs.get("message_id") or kwargs.get("messageId")
    profile = kwargs.get("profile") or kwargs.get("profile_name") or "default"
    return {
        "platform": platform,
        "sessionId": str(session_id) if session_id is not None else None,
        "messageId": str(message_id) if message_id is not None else None,
        "profile": str(profile) if profile is not None else None,
        "rawCommand": f"/circulation {raw_args}".strip(),
    }


def _render_command_error(*, raw_args: str, kwargs: dict[str, object], exc: Exception) -> str:
    stripped = raw_args.strip()
    if not stripped:
        return _usage_text()
    request = _fallback_request(raw_args=raw_args, kwargs=kwargs)
    return _RENDERER.render(
        {
            "requestId": request["requestId"],
            "idempotencyKey": request["idempotencyKey"],
            "replayed": False,
            "status": "validation_error",
            "message": str(exc),
            "result": {},
            "pendingProposals": [],
            "affectedEntityIds": [],
            "errors": [{"code": "validation_error", "message": str(exc), "retryable": False}],
        }
    )


def _fallback_request(*, raw_args: str, kwargs: dict[str, object]) -> BridgeRequestEnvelope:
    source = _source_context(raw_args=raw_args, kwargs=kwargs)
    return {
        "requestId": create_id("bridge_req"),
        "idempotencyKey": _command_idempotency_key(source=source, subcommand="invalid"),
        "userId": _normalize_user_id(source=source, kwargs=kwargs),
        "source": source,
        "operation": "circulatio.material.interpret",
        "payload": {},
    }


def _usage_text() -> str:
    return "\n".join(
        [
            "Usage: /circulation <subcommand>",
            "Examples:",
            '- /circulation dream "I walked through a house and found a snake in the cellar."',
            "- /circulation journey",
            '- /circulation discovery --query "snake and chest tension" --limit 4',
            (
                '- /circulation journey create --label "Laundry return" --question '
                '"Why does this keep returning?"'
            ),
            "- /circulation journey list --status active",
            '- /circulation journey get --label "Laundry return"',
            (
                '- /circulation journey update --label "Laundry return" --question '
                '"What keeps looping back here?"'
            ),
            '- /circulation journey pause --label "Laundry return"',
            '- /circulation journey resume --label "Laundry return"',
            "- /circulation practice",
            "- /circulation practice accept practice_session_123",
            "- /circulation brief",
            "- /circulation brief dismiss proactive_brief_123",
            "- /circulation review threshold",
            "- /circulation review living-myth",
            "- /circulation approve last p1",
            '- /circulation reject last p1 --reason "do not save this"',
            "- /circulation review approve living_myth_review_123 p1",
            "- /circulation packet --focus threshold",
            "- /circulation symbols --history",
            "- /circulation review week",
        ]
    )


def _normalize_user_id(*, source: HermesSourceContext, kwargs: dict[str, object]) -> str:
    explicit_user_id = kwargs.get("user_id") or kwargs.get("userId")
    if explicit_user_id:
        return str(explicit_user_id)
    profile = source.get("profile") or "default"
    platform = source.get("platform") or "cli"
    platform_user_id = (
        kwargs.get("platform_user_id")
        or kwargs.get("platformUserId")
        or kwargs.get("author_id")
        or kwargs.get("authorId")
    )
    if platform == "cli" and not platform_user_id:
        return f"hermes:{profile}:local"
    if platform_user_id:
        return f"hermes:{platform}:{platform_user_id}"
    return f"hermes:{platform}:anonymous"


def _boot_failure_response(
    *,
    request: BridgeRequestEnvelope,
    exc: Exception,
) -> BridgeResponseEnvelope:
    status: BridgeStatus = "error"
    code = "plugin_boot_error"
    message = "Circulatio could not boot its Hermes runtime."
    retryable = False
    if isinstance(exc, PluginBootError):
        message = str(exc)
    elif isinstance(exc, ProfileStorageCorruptionError):
        code = "profile_storage_error"
        message = str(exc)
    elif isinstance(exc, PersistenceError):
        code = "profile_storage_unavailable" if exc.retryable else "profile_storage_error"
        status = "retryable_error" if exc.retryable else "error"
        message = str(exc)
        retryable = exc.retryable
    elif isinstance(exc, PermissionError):
        code = "profile_storage_error"
        message = "Circulatio could not access the profile storage required to boot."
    return {
        "requestId": request["requestId"],
        "idempotencyKey": request["idempotencyKey"],
        "replayed": False,
        "status": status,
        "message": message,
        "result": {},
        "pendingProposals": [],
        "affectedEntityIds": [],
        "errors": [{"code": code, "message": message, "retryable": retryable}],
    }


def _command_idempotency_key(*, source: HermesSourceContext, subcommand: str) -> str:
    profile = source.get("profile") or "default"
    platform = source.get("platform") or "cli"
    session_id = source.get("sessionId") or "sessionless"
    subcommand_key = subcommand.replace(" ", "-")
    message_id = source.get("messageId")
    if message_id:
        return f"hermes:{profile}:{platform}:{session_id}:{message_id}:circulation:{subcommand_key}"
    raw_command = source.get("rawCommand") or subcommand
    command_hash = hashlib.sha256(raw_command.encode("utf-8")).hexdigest()
    return f"hermes:{profile}:{platform}:{session_id}:circulation:{subcommand_key}:{command_hash}"
