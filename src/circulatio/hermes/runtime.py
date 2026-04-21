from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import cast

from ..adapters.context_adapter import ContextAdapter
from ..adapters.context_builder import CirculatioLifeContextBuilder
from ..adapters.life_os_adapter import HermesProfileLifeOsReferenceAdapter
from ..adapters.method_context_builder import CirculatioMethodContextBuilder
from ..application.circulatio_service import CirculatioService
from ..core.circulatio_core import CirculatioCore
from ..llm.hermes_model_adapter import HermesModelAdapter
from ..llm.ports import CirculatioLlmPort, CirculatioMethodStateLlmPort
from ..repositories.circulatio_repository import CirculatioRepository
from ..repositories.hermes_profile_circulatio_repository import HermesProfileCirculatioRepository
from ..repositories.in_memory_circulatio_repository import InMemoryCirculatioRepository
from .agent_bridge import CirculatioAgentBridge
from .amplification_sources import default_trusted_amplification_sources
from .command_router import HermesCirculationCommandRouter
from .idempotency import IdempotencyStore, InMemoryIdempotencyStore, SQLiteIdempotencyStore
from .profile_paths import get_circulatio_db_path
from .proposal_alias_index import ProposalAliasIndex


@dataclass(frozen=True)
class CirculatioRuntime:
    repository: CirculatioRepository
    core: CirculatioCore
    service: CirculatioService
    router: HermesCirculationCommandRouter
    bridge: CirculatioAgentBridge
    idempotency_store: IdempotencyStore
    proposal_alias_index: ProposalAliasIndex
    llm: CirculatioLlmPort | None
    life_os: HermesProfileLifeOsReferenceAdapter | None
    life_context_builder: CirculatioLifeContextBuilder | None
    method_context_builder: CirculatioMethodContextBuilder | None

    def close(self) -> None:
        for resource in (self.repository, self.idempotency_store):
            close = getattr(resource, "close", None)
            if callable(close):
                close()


InMemoryCirculatioRuntime = CirculatioRuntime
HermesProfileCirculatioRuntime = CirculatioRuntime


def build_in_memory_circulatio_runtime(
    *,
    llm: CirculatioLlmPort | None = None,
) -> InMemoryCirculatioRuntime:
    repository = InMemoryCirculatioRepository()
    life_os = None
    life_context_builder = CirculatioLifeContextBuilder(repository)
    method_context_builder = CirculatioMethodContextBuilder(repository)
    context_adapter = ContextAdapter(
        repository,
        life_os=life_os,
        life_context_builder=life_context_builder,
        method_context_builder=method_context_builder,
    )
    core = CirculatioCore(repository, llm=llm)
    method_state_llm = _as_method_state_llm(llm)
    service = CirculatioService(
        repository,
        core,
        context_adapter=context_adapter,
        method_state_llm=method_state_llm,
        trusted_amplification_sources=default_trusted_amplification_sources(),
    )
    router = HermesCirculationCommandRouter(service)
    idempotency_store = InMemoryIdempotencyStore()
    proposal_alias_index = ProposalAliasIndex()
    bridge = CirculatioAgentBridge(
        router=router,
        service=service,
        idempotency_store=idempotency_store,
        proposal_alias_index=proposal_alias_index,
    )
    return CirculatioRuntime(
        repository=repository,
        core=core,
        service=service,
        router=router,
        bridge=bridge,
        idempotency_store=idempotency_store,
        proposal_alias_index=proposal_alias_index,
        llm=llm,
        life_os=life_os,
        life_context_builder=life_context_builder,
        method_context_builder=method_context_builder,
    )


def build_hermes_circulatio_runtime(
    *,
    db_path: str | Path | None = None,
    llm: CirculatioLlmPort | None = None,
    hermes_home: Path | None = None,
    started_ttl_seconds: int = 900,
) -> HermesProfileCirculatioRuntime:
    resolved_db_path = (
        Path(db_path) if db_path is not None else get_circulatio_db_path(hermes_home=hermes_home)
    )
    repository = HermesProfileCirculatioRepository(db_path=resolved_db_path)
    model_adapter = llm or HermesModelAdapter()
    life_os = HermesProfileLifeOsReferenceAdapter(llm=model_adapter, hermes_home=hermes_home)
    life_context_builder = CirculatioLifeContextBuilder(repository)
    method_context_builder = CirculatioMethodContextBuilder(repository)
    context_adapter = ContextAdapter(
        repository,
        life_os=life_os,
        life_context_builder=life_context_builder,
        method_context_builder=method_context_builder,
    )
    core = CirculatioCore(repository, llm=model_adapter)
    method_state_llm = _as_method_state_llm(model_adapter)
    service = CirculatioService(
        repository,
        core,
        context_adapter=context_adapter,
        method_state_llm=method_state_llm,
        trusted_amplification_sources=default_trusted_amplification_sources(),
    )
    router = HermesCirculationCommandRouter(service)
    idempotency_store = SQLiteIdempotencyStore(
        db_path=repository.db_path,
        started_ttl_seconds=started_ttl_seconds,
    )
    proposal_alias_index = ProposalAliasIndex()
    bridge = CirculatioAgentBridge(
        router=router,
        service=service,
        idempotency_store=idempotency_store,
        proposal_alias_index=proposal_alias_index,
    )
    return CirculatioRuntime(
        repository=repository,
        core=core,
        service=service,
        router=router,
        bridge=bridge,
        idempotency_store=idempotency_store,
        proposal_alias_index=proposal_alias_index,
        llm=model_adapter,
        life_os=life_os,
        life_context_builder=life_context_builder,
        method_context_builder=method_context_builder,
    )


def _as_method_state_llm(
    llm: CirculatioLlmPort | None,
) -> CirculatioMethodStateLlmPort | None:
    if llm is None or not hasattr(llm, "route_method_state_response"):
        return None
    return cast(CirculatioMethodStateLlmPort, llm)
