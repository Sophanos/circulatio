from __future__ import annotations

from circulatio.repositories.in_memory_bucket import UserCirculatioBucket
from circulatio.repositories.in_memory_projections import build_thread_digests_locked


def test_build_thread_digests_locked_returns_journey_digest() -> None:
    bucket = UserCirculatioBucket()
    bucket.journeys["journey_1"] = {
        "id": "journey_1",
        "userId": "user_1",
        "label": "Bear pursuit",
        "status": "active",
        "relatedMaterialIds": ["material_1"],
        "relatedSymbolIds": [],
        "relatedPatternIds": [],
        "relatedDreamSeriesIds": [],
        "relatedGoalIds": [],
        "relatedBodyStateIds": [],
        "currentQuestion": "What keeps chasing me here?",
        "createdAt": "2026-04-22T10:00:00+00:00",
        "updatedAt": "2026-04-22T11:00:00+00:00",
    }

    result = build_thread_digests_locked(
        bucket,
        user_id="user_1",
        window_start="2026-04-22T00:00:00+00:00",
        window_end="2026-04-23T00:00:00+00:00",
    )

    assert len(result) == 1
    digest = result[0]
    assert digest["threadKey"] == "journey:journey_1"
    assert digest["kind"] == "journey"
    assert digest["journeyIds"] == ["journey_1"]
    assert digest["entityRefs"]["materials"] == ["material_1"]
    assert digest["surfaceReadiness"]["journeyPage"] == "ready"


def test_build_thread_digests_locked_includes_related_body_state_refs() -> None:
    bucket = UserCirculatioBucket()
    bucket.journeys["journey_1"] = {
        "id": "journey_1",
        "userId": "user_1",
        "label": "Somatic thread",
        "status": "active",
        "relatedMaterialIds": [],
        "relatedSymbolIds": [],
        "relatedPatternIds": [],
        "relatedDreamSeriesIds": [],
        "relatedGoalIds": [],
        "relatedBodyStateIds": ["body_1"],
        "currentQuestion": "What does the body keep carrying here?",
        "createdAt": "2026-04-22T10:00:00+00:00",
        "updatedAt": "2026-04-22T11:00:00+00:00",
    }

    result = build_thread_digests_locked(
        bucket,
        user_id="user_1",
        window_start="2026-04-22T00:00:00+00:00",
        window_end="2026-04-23T00:00:00+00:00",
    )

    assert len(result) == 1
    digest = result[0]
    assert digest["entityRefs"]["bodyStates"] == ["body_1"]


def test_build_thread_digests_locked_keeps_journey_kind_when_experiment_is_present() -> None:
    bucket = UserCirculatioBucket()
    bucket.journeys["journey_1"] = {
        "id": "journey_1",
        "userId": "user_1",
        "label": "Bear pursuit",
        "status": "active",
        "relatedMaterialIds": [],
        "relatedSymbolIds": [],
        "relatedPatternIds": [],
        "relatedDreamSeriesIds": [],
        "relatedGoalIds": [],
        "relatedBodyStateIds": [],
        "createdAt": "2026-04-22T10:00:00+00:00",
        "updatedAt": "2026-04-22T11:00:00+00:00",
    }
    bucket.journey_experiments["experiment_1"] = {
        "id": "experiment_1",
        "userId": "user_1",
        "journeyId": "journey_1",
        "title": "Current tending",
        "summary": "Stay with the thread lightly.",
        "status": "active",
        "source": "manual",
        "bodyFirst": False,
        "relatedPracticeSessionIds": [],
        "relatedBriefIds": [],
        "relatedSymbolIds": [],
        "relatedGoalTensionIds": [],
        "relatedBodyStateIds": [],
        "relatedResourceIds": [],
        "createdAt": "2026-04-22T12:00:00+00:00",
        "updatedAt": "2026-04-22T12:00:00+00:00",
    }

    result = build_thread_digests_locked(
        bucket,
        user_id="user_1",
        window_start="2026-04-22T00:00:00+00:00",
        window_end="2026-04-23T00:00:00+00:00",
    )

    assert len(result) == 1
    digest = result[0]
    assert digest["kind"] == "journey"
    assert digest["entityRefs"]["experiments"] == ["experiment_1"]
