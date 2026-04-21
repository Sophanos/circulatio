from __future__ import annotations

from typing import NotRequired, Required, TypedDict

from .records import ContextSnapshotSource, RecordStatus
from .types import (
    Id,
    ISODateString,
    LifeContextSnapshot,
    MethodContextSnapshot,
    PrivacyClass,
    SessionContext,
)


class ContextSnapshot(TypedDict, total=False):
    id: Required[Id]
    userId: Required[Id]
    windowStart: NotRequired[ISODateString]
    windowEnd: NotRequired[ISODateString]
    source: Required[ContextSnapshotSource]
    sessionContext: NotRequired[SessionContext]
    lifeContextSnapshot: NotRequired[LifeContextSnapshot]
    methodContextSnapshot: NotRequired[MethodContextSnapshot]
    summary: NotRequired[str]
    relatedMaterialIds: NotRequired[list[Id]]
    createdAt: Required[ISODateString]
    deletedAt: NotRequired[ISODateString]
    privacyClass: Required[PrivacyClass]
    status: Required[RecordStatus]
