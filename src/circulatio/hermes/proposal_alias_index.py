from __future__ import annotations

import asyncio
from copy import deepcopy
from dataclasses import dataclass

from ..domain.errors import EntityNotFoundError, ValidationError
from ..domain.types import Id, MemoryWriteProposal

_SESSION_FALLBACK = "__global__"


@dataclass
class ProposalAliasMapping:
    owner_id: Id
    alias_to_proposal_id: dict[str, Id]
    proposal_ids_in_order: list[Id]


class ProposalAliasIndex:
    def __init__(self) -> None:
        self._runs: dict[tuple[Id, str, Id], ProposalAliasMapping] = {}
        self._reviews: dict[tuple[Id, str, Id], ProposalAliasMapping] = {}
        self._latest_run_by_session: dict[tuple[Id, str], Id] = {}
        self._lock = asyncio.Lock()

    async def record_run(
        self,
        *,
        user_id: Id,
        session_id: str | None,
        run_id: Id,
        proposals: list[MemoryWriteProposal],
    ) -> None:
        await self._record_mapping(
            store=self._runs,
            user_id=user_id,
            session_id=session_id,
            owner_id=run_id,
            proposals=proposals,
        )
        async with self._lock:
            self._latest_run_by_session[(user_id, self._session_key(session_id))] = run_id

    async def record_review(
        self,
        *,
        user_id: Id,
        session_id: str | None,
        review_id: Id,
        proposals: list[MemoryWriteProposal],
    ) -> None:
        await self._record_mapping(
            store=self._reviews,
            user_id=user_id,
            session_id=session_id,
            owner_id=review_id,
            proposals=proposals,
        )

    async def _record_mapping(
        self,
        *,
        store: dict[tuple[Id, str, Id], ProposalAliasMapping],
        user_id: Id,
        session_id: str | None,
        owner_id: Id,
        proposals: list[MemoryWriteProposal],
    ) -> None:
        alias_to_proposal_id = {
            f"p{index}": proposal["id"] for index, proposal in enumerate(proposals, start=1)
        }
        key = (user_id, self._session_key(session_id), owner_id)
        async with self._lock:
            store[key] = ProposalAliasMapping(
                owner_id=owner_id,
                alias_to_proposal_id=alias_to_proposal_id,
                proposal_ids_in_order=[proposal["id"] for proposal in proposals],
            )

    async def resolve_run_ref(self, *, user_id: Id, session_id: str | None, run_ref: str) -> Id:
        if run_ref != "last":
            return run_ref
        async with self._lock:
            run_id = self._latest_run_by_session.get((user_id, self._session_key(session_id)))
        if run_id is None:
            raise EntityNotFoundError("No interpretation run is available for this session yet.")
        return run_id

    async def resolve_proposal_refs(
        self,
        *,
        user_id: Id,
        session_id: str | None,
        run_id: Id,
        proposal_refs: list[str],
        pending_proposal_ids: list[Id],
    ) -> list[Id]:
        return await self._resolve_proposal_refs(
            store=self._runs,
            user_id=user_id,
            session_id=session_id,
            owner_id=run_id,
            proposal_refs=proposal_refs,
            pending_proposal_ids=pending_proposal_ids,
            owner_label="run",
        )

    async def resolve_review_proposal_refs(
        self,
        *,
        user_id: Id,
        session_id: str | None,
        review_id: Id,
        proposal_refs: list[str],
        pending_proposal_ids: list[Id],
    ) -> list[Id]:
        return await self._resolve_proposal_refs(
            store=self._reviews,
            user_id=user_id,
            session_id=session_id,
            owner_id=review_id,
            proposal_refs=proposal_refs,
            pending_proposal_ids=pending_proposal_ids,
            owner_label="review",
        )

    async def _resolve_proposal_refs(
        self,
        *,
        store: dict[tuple[Id, str, Id], ProposalAliasMapping],
        user_id: Id,
        session_id: str | None,
        owner_id: Id,
        proposal_refs: list[str],
        pending_proposal_ids: list[Id],
        owner_label: str,
    ) -> list[Id]:
        if not proposal_refs:
            raise ValidationError("At least one proposal reference is required.")
        if "all" in proposal_refs:
            remaining = [proposal_id for proposal_id in pending_proposal_ids]
            if not remaining:
                raise ValidationError(
                    f"{owner_label.title()} {owner_id} has no pending proposals to select."
                )
            if len(proposal_refs) == 1:
                return remaining
        mapping = await self._mapping(
            store=store,
            user_id=user_id,
            session_id=session_id,
            owner_id=owner_id,
            owner_label=owner_label,
        )
        resolved: list[Id] = []
        missing: list[str] = []
        for proposal_ref in proposal_refs:
            if proposal_ref == "all":
                for proposal_id in pending_proposal_ids:
                    if proposal_id not in resolved:
                        resolved.append(proposal_id)
                continue
            proposal_id = mapping.alias_to_proposal_id.get(proposal_ref)
            if proposal_id is None:
                if proposal_ref in mapping.proposal_ids_in_order:
                    proposal_id = proposal_ref
                else:
                    missing.append(proposal_ref)
                    continue
            if proposal_id not in resolved:
                resolved.append(proposal_id)
        if missing:
            raise ValidationError(
                f"Unknown proposal references for {owner_label} {owner_id}: {missing}"
            )
        return resolved

    async def alias_for_proposal(
        self,
        *,
        user_id: Id,
        session_id: str | None,
        run_id: Id,
        proposal_id: Id,
    ) -> str | None:
        mapping = await self._mapping(
            store=self._runs,
            user_id=user_id,
            session_id=session_id,
            owner_id=run_id,
            owner_label="run",
        )
        for alias, mapped_proposal_id in mapping.alias_to_proposal_id.items():
            if mapped_proposal_id == proposal_id:
                return alias
        return None

    async def list_pending_aliases(
        self,
        *,
        user_id: Id,
        session_id: str | None,
        run_id: Id,
        pending_proposal_ids: list[Id],
    ) -> list[tuple[str, Id]]:
        return await self._list_pending_aliases(
            store=self._runs,
            user_id=user_id,
            session_id=session_id,
            owner_id=run_id,
            pending_proposal_ids=pending_proposal_ids,
            owner_label="run",
        )

    async def list_review_pending_aliases(
        self,
        *,
        user_id: Id,
        session_id: str | None,
        review_id: Id,
        pending_proposal_ids: list[Id],
    ) -> list[tuple[str, Id]]:
        return await self._list_pending_aliases(
            store=self._reviews,
            user_id=user_id,
            session_id=session_id,
            owner_id=review_id,
            pending_proposal_ids=pending_proposal_ids,
            owner_label="review",
        )

    async def _list_pending_aliases(
        self,
        *,
        store: dict[tuple[Id, str, Id], ProposalAliasMapping],
        user_id: Id,
        session_id: str | None,
        owner_id: Id,
        pending_proposal_ids: list[Id],
        owner_label: str,
    ) -> list[tuple[str, Id]]:
        mapping = await self._mapping(
            store=store,
            user_id=user_id,
            session_id=session_id,
            owner_id=owner_id,
            owner_label=owner_label,
        )
        aliases: list[tuple[str, Id]] = []
        for proposal_id in mapping.proposal_ids_in_order:
            if proposal_id not in pending_proposal_ids:
                continue
            alias = next(
                (
                    name
                    for name, mapped_proposal_id in mapping.alias_to_proposal_id.items()
                    if mapped_proposal_id == proposal_id
                ),
                proposal_id,
            )
            aliases.append((alias, proposal_id))
        return deepcopy(aliases)

    async def _mapping(
        self,
        *,
        store: dict[tuple[Id, str, Id], ProposalAliasMapping],
        user_id: Id,
        session_id: str | None,
        owner_id: Id,
        owner_label: str,
    ) -> ProposalAliasMapping:
        async with self._lock:
            mapping = store.get((user_id, self._session_key(session_id), owner_id))
            if mapping is None:
                raise EntityNotFoundError(
                    f"No proposal aliases are available for {owner_label} {owner_id}."
                )
            return deepcopy(mapping)

    def _session_key(self, session_id: str | None) -> str:
        return session_id or _SESSION_FALLBACK
