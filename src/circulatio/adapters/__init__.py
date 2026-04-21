from __future__ import annotations

from importlib import import_module
from typing import Any

_EXPORTS: dict[str, tuple[str, str]] = {
    "BuildContextInput": ("circulatio.adapters.context_adapter", "BuildContextInput"),
    "CirculatioLifeContextBuilder": (
        "circulatio.adapters.context_builder",
        "CirculatioLifeContextBuilder",
    ),
    "ContextAdapter": ("circulatio.adapters.context_adapter", "ContextAdapter"),
    "CirculatioMethodContextBuilder": (
        "circulatio.adapters.method_context_builder",
        "CirculatioMethodContextBuilder",
    ),
    "HermesMemoryBackedRepository": (
        "circulatio.adapters.hermes_memory_adapter",
        "HermesMemoryBackedRepository",
    ),
    "HermesMemoryPort": ("circulatio.adapters.hermes_memory_adapter", "HermesMemoryPort"),
    "HermesCirculatioPersistencePort": (
        "circulatio.adapters.hermes_persistence_adapter",
        "HermesCirculatioPersistencePort",
    ),
    "HermesProfileLifeOsReferenceAdapter": (
        "circulatio.adapters.life_os_adapter",
        "HermesProfileLifeOsReferenceAdapter",
    ),
    "LifeContextBuilder": ("circulatio.adapters.context_builder", "LifeContextBuilder"),
    "MethodContextBuilder": ("circulatio.adapters.method_context_builder", "MethodContextBuilder"),
    "LifeOsReferenceAdapter": ("circulatio.adapters.life_os_adapter", "LifeOsReferenceAdapter"),
}

__all__ = list(_EXPORTS)


def __getattr__(name: str) -> Any:
    target = _EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module 'circulatio.adapters' has no attribute {name!r}")
    module_name, attribute_name = target
    value = getattr(import_module(module_name), attribute_name)
    globals()[name] = value
    return value
