from __future__ import annotations

from importlib import import_module
from typing import Any

_EXPORTS: dict[str, tuple[str, str]] = {
    "CirculatioRepository": (
        "circulatio.repositories.circulatio_repository",
        "CirculatioRepository",
    ),
    "GraphMemoryRepository": (
        "circulatio.repositories.graph_memory_repository",
        "GraphMemoryRepository",
    ),
    "HermesProfileCirculatioRepository": (
        "circulatio.repositories.hermes_profile_circulatio_repository",
        "HermesProfileCirculatioRepository",
    ),
    "InMemoryCirculatioRepository": (
        "circulatio.repositories.in_memory_circulatio_repository",
        "InMemoryCirculatioRepository",
    ),
    "InMemoryGraphMemoryRepository": (
        "circulatio.repositories.in_memory_graph_memory_repository",
        "InMemoryGraphMemoryRepository",
    ),
}

__all__ = list(_EXPORTS)


def __getattr__(name: str) -> Any:
    target = _EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module 'circulatio.repositories' has no attribute {name!r}")
    module_name, attribute_name = target
    value = getattr(import_module(module_name), attribute_name)
    globals()[name] = value
    return value
