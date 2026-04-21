from __future__ import annotations

from importlib import import_module
from typing import Any

_EXPORTS: dict[str, tuple[str, str]] = {
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
    "ParsedCirculationCommand": ("circulatio.hermes.command_parser", "ParsedCirculationCommand"),
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
}

__all__ = list(_EXPORTS)


def __getattr__(name: str) -> Any:
    target = _EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module 'circulatio.hermes' has no attribute {name!r}")
    module_name, attribute_name = target
    value = getattr(import_module(module_name), attribute_name)
    globals()[name] = value
    return value
