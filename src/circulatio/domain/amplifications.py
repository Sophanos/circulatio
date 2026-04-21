from __future__ import annotations

from typing import Literal, NotRequired, Required, TypedDict

from .records import RecordStatus
from .types import Id, ISODateString, PrivacyClass

AmplificationPromptStatus = Literal[
    "pending",
    "answered",
    "skipped",
    "expired",
    "deleted",
]


class AmplificationPromptRecord(TypedDict, total=False):
    id: Required[Id]
    userId: Required[Id]
    materialId: NotRequired[Id]
    runId: NotRequired[Id]
    symbolId: NotRequired[Id]
    symbolMentionId: NotRequired[Id]
    surfaceText: Required[str]
    canonicalName: Required[str]
    promptText: Required[str]
    reason: Required[str]
    status: Required[AmplificationPromptStatus]
    createdAt: Required[ISODateString]
    updatedAt: Required[ISODateString]
    answeredAt: NotRequired[ISODateString]
    responseAmplificationId: NotRequired[Id]
    deletedAt: NotRequired[ISODateString]


class AmplificationPromptUpdate(TypedDict, total=False):
    status: AmplificationPromptStatus
    updatedAt: ISODateString
    answeredAt: ISODateString
    responseAmplificationId: Id
    deletedAt: ISODateString


class PersonalAmplificationRecord(TypedDict, total=False):
    id: Required[Id]
    userId: Required[Id]
    materialId: NotRequired[Id]
    runId: NotRequired[Id]
    promptId: NotRequired[Id]
    symbolId: NotRequired[Id]
    canonicalName: Required[str]
    surfaceText: Required[str]
    associationText: Required[str]
    feelingTone: NotRequired[str]
    bodySensations: NotRequired[list[str]]
    memoryRefs: NotRequired[list[Id]]
    source: Required[Literal["user_response", "user_answered_prompt", "session_input", "import"]]
    evidenceIds: Required[list[Id]]
    privacyClass: Required[PrivacyClass]
    status: Required[RecordStatus]
    createdAt: Required[ISODateString]
    updatedAt: Required[ISODateString]
    deletedAt: NotRequired[ISODateString]


class PersonalAmplificationUpdate(TypedDict, total=False):
    canonicalName: str
    surfaceText: str
    associationText: str
    feelingTone: str
    bodySensations: list[str]
    memoryRefs: list[Id]
    evidenceIds: list[Id]
    privacyClass: PrivacyClass
    status: RecordStatus
    updatedAt: ISODateString
    deletedAt: ISODateString
