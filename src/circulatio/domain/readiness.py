from __future__ import annotations

from typing import Literal, NotRequired, Required, TypedDict

from .types import Id, ISODateString

ConsentPreferenceStatus = Literal["allow", "ask_each_time", "declined", "revoked"]


class ConsentPreferenceRecord(TypedDict, total=False):
    id: Required[Id]
    userId: Required[Id]
    scope: Required[str]
    status: Required[ConsentPreferenceStatus]
    note: NotRequired[str]
    source: Required[Literal["explicit_user", "default_policy", "import"]]
    createdAt: Required[ISODateString]
    updatedAt: Required[ISODateString]


class ConsentPreferenceUpdate(TypedDict, total=False):
    scope: str
    status: ConsentPreferenceStatus
    note: str
    source: Literal["explicit_user", "default_policy", "import"]
    updatedAt: ISODateString
