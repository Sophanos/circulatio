from __future__ import annotations

from typing import Literal, NotRequired, Required, TypedDict

from .types import Id, ISODateString, PsychologicalFunction, TypologyRole


class TypologyLensRecord(TypedDict, total=False):
    id: Required[Id]
    userId: Required[Id]
    role: Required[TypologyRole]
    function: Required[PsychologicalFunction]
    claim: Required[str]
    confidence: Required[Literal["low", "medium"]]
    status: Required[Literal["candidate", "user_refined", "disconfirmed", "deleted"]]
    evidenceIds: Required[list[Id]]
    counterevidenceIds: Required[list[Id]]
    userTestPrompt: Required[str]
    linkedMaterialIds: Required[list[Id]]
    createdAt: Required[ISODateString]
    updatedAt: Required[ISODateString]
    deletedAt: NotRequired[ISODateString]
    lastSeen: NotRequired[ISODateString]


class TypologyLensUpdate(TypedDict, total=False):
    role: TypologyRole
    function: PsychologicalFunction
    claim: str
    confidence: Literal["low", "medium"]
    status: Literal["candidate", "user_refined", "disconfirmed", "deleted"]
    evidenceIds: list[Id]
    counterevidenceIds: list[Id]
    userTestPrompt: str
    linkedMaterialIds: list[Id]
    updatedAt: ISODateString
    deletedAt: ISODateString
    lastSeen: ISODateString
