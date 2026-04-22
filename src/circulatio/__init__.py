from __future__ import annotations

from importlib import import_module
from typing import Any

from .domain import *  # noqa: F401,F403

_domain_all = [name for name in globals() if not name.startswith("_")]

_EXPORTS: dict[str, tuple[str, str]] = {
    "BuildContextInput": ("circulatio.adapters.context_adapter", "BuildContextInput"),
    "ContextAdapter": ("circulatio.adapters.context_adapter", "ContextAdapter"),
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
    "LifeOsReferenceAdapter": ("circulatio.adapters.life_os_adapter", "LifeOsReferenceAdapter"),
    "CirculatioService": ("circulatio.application.circulatio_service", "CirculatioService"),
    "CirculatioCore": ("circulatio.core.circulatio_core", "CirculatioCore"),
    "SafetyGate": ("circulatio.core.safety_gate", "SafetyGate"),
    "BridgeError": ("circulatio.hermes.agent_bridge_contracts", "BridgeError"),
    "BridgePendingProposal": ("circulatio.hermes.agent_bridge_contracts", "BridgePendingProposal"),
    "BridgeRequestEnvelope": ("circulatio.hermes.agent_bridge_contracts", "BridgeRequestEnvelope"),
    "BridgeResponseEnvelope": (
        "circulatio.hermes.agent_bridge_contracts",
        "BridgeResponseEnvelope",
    ),
    "BridgeStatus": ("circulatio.hermes.agent_bridge_contracts", "BridgeStatus"),
    "CirculatioAgentBridge": ("circulatio.hermes.agent_bridge", "CirculatioAgentBridge"),
    "CirculatioCommandParser": ("circulatio.hermes.command_parser", "CirculatioCommandParser"),
    "CirculatioResultRenderer": ("circulatio.hermes.result_renderer", "CirculatioResultRenderer"),
    "HermesCirculationCommandRouter": (
        "circulatio.hermes.command_router",
        "HermesCirculationCommandRouter",
    ),
    "HermesCommandResult": ("circulatio.hermes.command_router", "HermesCommandResult"),
    "HermesSourceContext": ("circulatio.hermes.agent_bridge_contracts", "HermesSourceContext"),
    "HermesProfileCirculatioRuntime": (
        "circulatio.hermes.runtime",
        "HermesProfileCirculatioRuntime",
    ),
    "InMemoryCirculatioRuntime": ("circulatio.hermes.runtime", "InMemoryCirculatioRuntime"),
    "InMemoryIdempotencyStore": ("circulatio.hermes.idempotency", "InMemoryIdempotencyStore"),
    "ProposalAliasIndex": ("circulatio.hermes.proposal_alias_index", "ProposalAliasIndex"),
    "SQLiteIdempotencyStore": ("circulatio.hermes.idempotency", "SQLiteIdempotencyStore"),
    "build_hermes_circulatio_runtime": (
        "circulatio.hermes.runtime",
        "build_hermes_circulatio_runtime",
    ),
    "build_in_memory_circulatio_runtime": (
        "circulatio.hermes.runtime",
        "build_in_memory_circulatio_runtime",
    ),
    "HermesCirculationFacade": (
        "circulatio.orchestration.hermes_circulation_facade",
        "HermesCirculationFacade",
    ),
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

__all__ = list(dict.fromkeys([*_domain_all, *_EXPORTS.keys()]))


def register(ctx: Any) -> None:
    """Compatibility shim for hosts that import the top-level package by plugin name."""
    from circulatio_hermes_plugin import register as plugin_register

    plugin_register(ctx)


__all__.append("register")


def __getattr__(name: str) -> Any:
    target = _EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module 'circulatio' has no attribute {name!r}")
    module_name, attribute_name = target
    value = getattr(import_module(module_name), attribute_name)
    globals()[name] = value
    return value
