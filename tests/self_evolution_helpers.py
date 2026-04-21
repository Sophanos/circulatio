from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from tools.self_evolution.llm_client import EvolutionLlmResponse


@dataclass(frozen=True)
class FakeEvolutionCall:
    schema_name: str
    messages: list[dict[str, str]]
    metadata: dict[str, object]


class FakeEvolutionLlmClient:
    def __init__(
        self,
        responses: Mapping[str, object | list[object]] | None = None,
        *,
        handler: Callable[[str, list[dict[str, str]], dict[str, object]], dict[str, object]] | None = None,
    ) -> None:
        self.calls: list[FakeEvolutionCall] = []
        self._handler = handler
        self._responses: dict[str, list[object]] = {}
        for schema_name, payload in (responses or {}).items():
            if isinstance(payload, list):
                self._responses[str(schema_name)] = list(payload)
            else:
                self._responses[str(schema_name)] = [payload]

    async def complete_json(
        self,
        *,
        messages: list[dict[str, str]],
        schema: dict[str, object],
        schema_name: str,
        max_tokens: int,
        temperature: float,
        timeout_seconds: float | None,
        metadata: Mapping[str, object] | None = None,
    ) -> EvolutionLlmResponse:
        metadata_map = {str(key): value for key, value in (metadata or {}).items()}
        self.calls.append(
            FakeEvolutionCall(
                schema_name=schema_name,
                messages=messages,
                metadata=metadata_map,
            )
        )
        payload = self._next_payload(schema_name, messages, metadata_map)
        return EvolutionLlmResponse(
            payload=payload,
            raw_text=json.dumps(payload, sort_keys=True),
            provider="fake",
            model="fake-model",
            usage={"completion_tokens": max_tokens},
            latency_ms=1,
            cache_hit=False,
            error=None,
        )

    def _next_payload(
        self,
        schema_name: str,
        messages: list[dict[str, str]],
        metadata: dict[str, object],
    ) -> dict[str, object]:
        if self._handler is not None:
            return dict(self._handler(schema_name, messages, metadata))
        queue = self._responses.get(schema_name)
        if not queue:
            raise AssertionError(f"No fake evolution payload configured for schema '{schema_name}'.")
        value = queue.pop(0)
        if not isinstance(value, Mapping):
            raise AssertionError(
                f"Fake evolution payload for schema '{schema_name}' must be a mapping."
            )
        return {str(key): item for key, item in value.items()}
