from __future__ import annotations

from ..domain.ids import create_id
from ..domain.types import EvidenceItem, EvidenceType, ISODateString, PrivacyClass


class EvidenceLedger:
    def __init__(self, *, timestamp: ISODateString) -> None:
        self._timestamp = timestamp
        self._items: list[EvidenceItem] = []

    def add(
        self,
        *,
        evidence_type: EvidenceType,
        source_id: str,
        quote_or_summary: str,
        privacy_class: PrivacyClass,
        reliability: str,
    ) -> str:
        evidence_id = create_id("evidence")
        self._items.append(
            {
                "id": evidence_id,
                "type": evidence_type,
                "sourceId": source_id,
                "quoteOrSummary": quote_or_summary[:240],
                "timestamp": self._timestamp,
                "privacyClass": privacy_class,
                "reliability": reliability,
            }
        )
        return evidence_id

    def all(self) -> list[EvidenceItem]:
        return list(self._items)


class EvidenceIntegrityError(RuntimeError):
    pass
