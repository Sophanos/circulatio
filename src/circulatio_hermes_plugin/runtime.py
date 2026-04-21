from __future__ import annotations

from circulatio.hermes.runtime import (
    HermesProfileCirculatioRuntime,
    build_hermes_circulatio_runtime,
)

_RUNTIMES: dict[str, HermesProfileCirculatioRuntime] = {}


def get_runtime(profile: str | None = None) -> HermesProfileCirculatioRuntime:
    key = profile or "default"
    runtime = _RUNTIMES.get(key)
    if runtime is None:
        runtime = build_hermes_circulatio_runtime()
        _RUNTIMES[key] = runtime
    return runtime


def set_runtime(
    runtime: HermesProfileCirculatioRuntime, profile: str | None = None
) -> HermesProfileCirculatioRuntime:
    key = profile or "default"
    existing = _RUNTIMES.get(key)
    if existing is not None and existing is not runtime:
        existing.close()
    _RUNTIMES[key] = runtime
    return runtime


def reset_runtimes() -> None:
    for runtime in list(_RUNTIMES.values()):
        runtime.close()
    _RUNTIMES.clear()
