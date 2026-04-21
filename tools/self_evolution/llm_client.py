from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from circulatio.llm.hermes_model_adapter import HermesModelAdapter

from .cache import LlmCallCache, build_cache_key


@dataclass(frozen=True)
class EvolutionLlmResponse:
    payload: dict[str, object]
    raw_text: str | None = None
    provider: str | None = None
    model: str | None = None
    usage: dict[str, object] | None = None
    latency_ms: int | None = None
    cache_hit: bool = False
    error: str | None = None


class EvolutionLlmClient(Protocol):
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
    ) -> EvolutionLlmResponse: ...


class HermesEvolutionLlmClient:
    def __init__(
        self,
        *,
        provider: str | None = "auto",
        model: str | None = None,
        temperature: float = 0.2,
        timeout_seconds: float | None = None,
        cache_root: Path | None = None,
        event_sink: Callable[[str, dict[str, object] | None], None] | None = None,
        adapter: HermesModelAdapter | None = None,
    ) -> None:
        self._provider = provider
        self._model = model
        self._temperature = temperature
        self._timeout_seconds = timeout_seconds
        self._adapter = adapter or HermesModelAdapter(
            provider=provider,
            model=model,
            temperature=temperature,
            request_timeout_seconds=timeout_seconds,
        )
        self._cache = (
            LlmCallCache(cache_root, event_sink=event_sink)
            if cache_root is not None
            else None
        )

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
        cache_key = build_cache_key(
            schema_name=schema_name,
            metadata={
                "provider": self._provider,
                "model": self._model,
                "temperature": temperature,
                "timeoutSeconds": timeout_seconds,
                "maxTokens": max_tokens,
                "schema": json.dumps(schema, sort_keys=True),
                "messages": json.dumps(messages, sort_keys=True),
                **metadata_map,
            },
        )
        if self._cache is not None:
            cached = self._cache.get(cache_key)
            if cached is not None and isinstance(cached.get("payload"), dict):
                raw_text = (
                    str(cached.get("rawText"))
                    if cached.get("rawText") is not None
                    else None
                )
                provider = (
                    str(cached.get("provider"))
                    if cached.get("provider")
                    else self._provider
                )
                model = (
                    str(cached.get("model"))
                    if cached.get("model")
                    else self._model
                )
                latency_ms = (
                    int(cached["latencyMs"])
                    if isinstance(cached.get("latencyMs"), int)
                    else None
                )
                return EvolutionLlmResponse(
                    payload=dict(cached["payload"]),
                    raw_text=raw_text,
                    provider=provider,
                    model=model,
                    usage=(
                        dict(cached["usage"])
                        if isinstance(cached.get("usage"), dict)
                        else None
                    ),
                    latency_ms=latency_ms,
                    cache_hit=True,
                    error=str(cached.get("error")) if cached.get("error") else None,
                )

        response = await self._adapter.complete_structured_json(
            messages=messages,
            schema=schema,
            schema_name=schema_name,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout_seconds=timeout_seconds,
        )
        normalized = EvolutionLlmResponse(
            payload=dict(response.get("payload") or {}),
            raw_text=str(response.get("rawText")) if response.get("rawText") is not None else None,
            provider=str(response.get("provider")) if response.get("provider") else self._provider,
            model=str(response.get("model")) if response.get("model") else self._model,
            usage=dict(response["usage"]) if isinstance(response.get("usage"), dict) else None,
            latency_ms=(
                int(response["latencyMs"])
                if isinstance(response.get("latencyMs"), int)
                else None
            ),
            cache_hit=bool(response.get("cacheHit")),
            error=str(response.get("error")) if response.get("error") else None,
        )
        if self._cache is not None:
            self._cache.put(
                {
                    "schemaVersion": 1,
                    "cacheKey": cache_key,
                    "provider": normalized.provider,
                    "model": normalized.model,
                    "schemaName": schema_name,
                    "payload": normalized.payload,
                    "rawText": normalized.raw_text,
                    "usage": normalized.usage,
                    "latencyMs": normalized.latency_ms,
                    "error": normalized.error,
                    "metadata": metadata_map,
                }
            )
        return normalized
