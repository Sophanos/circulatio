from __future__ import annotations

from typing import NotRequired, Required, TypedDict

from .materials import MaterialRecord
from .patterns import PatternRecord
from .practices import PracticeSessionRecord
from .records import RecordStatus
from .symbols import SymbolRecord
from .types import CirculationSummaryResult, Id, ISODateString


class WeeklyReviewRecord(TypedDict, total=False):
    id: Required[Id]
    userId: Required[Id]
    windowStart: Required[ISODateString]
    windowEnd: Required[ISODateString]
    createdAt: Required[ISODateString]
    deletedAt: NotRequired[ISODateString]
    recurringSymbolIds: Required[list[Id]]
    activePatternIds: Required[list[Id]]
    materialIds: Required[list[Id]]
    contextSnapshotIds: Required[list[Id]]
    evidenceIds: Required[list[Id]]
    practiceSuggestionId: NotRequired[Id]
    result: Required[CirculationSummaryResult]
    status: Required[RecordStatus]


class DashboardSummary(TypedDict, total=False):
    recentMaterials: Required[list[MaterialRecord]]
    pendingProposalCount: Required[int]
    recurringSymbols: Required[list[SymbolRecord]]
    activePatterns: Required[list[PatternRecord]]
    latestReview: NotRequired[WeeklyReviewRecord]
    latestPracticeRecommendation: NotRequired[PracticeSessionRecord]
    safetyBlockedRecentRunsCount: Required[int]
