from __future__ import annotations

from ..domain.errors import ConflictError, EntityDeletedError, EntityNotFoundError
from ..domain.graph import SuppressHypothesisRequest
from ..domain.ids import create_id, now_iso
from ..domain.records import DeletionMode
from ..domain.types import Id, SuppressedHypothesisSummary
from .in_memory_bucket import UserCirculatioBucket


def ensure_unique(store: dict[Id, object], record_id: Id, label: str) -> None:
    if record_id in store:
        raise ConflictError(f"{label.capitalize()} already exists: {record_id}")


def get_visible(
    *,
    store: dict[Id, object],
    record_id: Id,
    include_deleted: bool,
    label: str,
):
    record = store.get(record_id)
    if record is None:
        raise EntityNotFoundError(f"Unknown {label}: {record_id}")
    if isinstance(record, dict) and record.get("status") == "deleted" and not include_deleted:
        raise EntityDeletedError(f"{label.capitalize()} is deleted: {record_id}")
    return record


def tombstone_record(
    record: dict[str, object], *, mode: DeletionMode, erase_fields: tuple[str, ...]
) -> None:
    record["status"] = "deleted"
    record["deletedAt"] = now_iso()
    if mode == "erase":
        for field_name in erase_fields:
            if field_name in record:
                record[field_name] = ""


def suppress_hypothesis_locked(
    bucket: UserCirculatioBucket, request: SuppressHypothesisRequest
) -> SuppressedHypothesisSummary:
    existing = bucket.suppressed.get(request["normalizedClaimKey"])
    if existing is not None:
        return existing
    record: SuppressedHypothesisSummary = {
        "id": create_id("suppressed"),
        "normalizedClaimKey": request["normalizedClaimKey"],
        "reason": request["reason"],
        "note": request.get("note"),
        "timestamp": now_iso(),
    }
    bucket.suppressed[record["normalizedClaimKey"]] = record
    return record
