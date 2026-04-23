from __future__ import annotations

from circulatio.core.journey_followthrough_engine import JourneyFollowthroughEngine


def _journey(**overrides: object) -> dict[str, object]:
    journey = {
        "id": "journey_1",
        "userId": "user_1",
        "label": "Journey",
        "status": "active",
        "relatedMaterialIds": [],
        "relatedSymbolIds": [],
        "relatedPatternIds": [],
        "relatedDreamSeriesIds": [],
        "relatedGoalIds": [],
        "relatedBodyStateIds": [],
        "createdAt": "2026-04-01T00:00:00Z",
        "updatedAt": "2026-04-09T00:00:00Z",
    }
    journey.update(overrides)
    return journey


def _practice(**overrides: object) -> dict[str, object]:
    practice = {
        "id": "practice_1",
        "userId": "user_1",
        "practiceType": "journaling",
        "reason": "Track what returned.",
        "instructions": ["Write briefly."],
        "durationMinutes": 5,
        "contraindicationsChecked": ["none"],
        "requiresConsent": False,
        "status": "completed",
        "followUpCount": 0,
        "relatedJourneyIds": ["journey_1"],
        "createdAt": "2026-04-09T00:00:00Z",
        "updatedAt": "2026-04-09T00:00:00Z",
        "completedAt": "2026-04-09T00:00:00Z",
    }
    practice.update(overrides)
    return practice


def test_mature_reentry_threshold_delays_return_after_absence() -> None:
    engine = JourneyFollowthroughEngine()
    practices = [
        _practice(id="practice_1", followUpCount=2, completedAt="2026-04-01T00:00:00Z"),
        _practice(id="practice_2", followUpCount=2, completedAt="2026-04-05T00:00:00Z"),
        _practice(id="practice_3", followUpCount=2, completedAt="2026-04-09T00:00:00Z"),
    ]
    journeys = [_journey(updatedAt="2026-04-09T00:00:00Z")]

    immature = engine.build_summaries(
        method_context={"windowStart": "2026-04-01T00:00:00Z", "windowEnd": "2026-04-15T00:00:00Z"},
        thread_digests=[],
        journeys=journeys,
        recent_practices=practices,
        existing_briefs=[],
        dashboard=None,
        adaptation_profile=None,
        now="2026-04-15T00:00:00Z",
    )[0]
    mature = engine.build_summaries(
        method_context={"windowStart": "2026-04-01T00:00:00Z", "windowEnd": "2026-04-15T00:00:00Z"},
        thread_digests=[],
        journeys=journeys,
        recent_practices=practices,
        existing_briefs=[],
        dashboard=None,
        adaptation_profile={"sampleCounts": {"total": 25}, "learnedSignals": {"matured": True}},
        now="2026-04-15T00:00:00Z",
    )[0]

    assert immature["family"] == "practice_reentry"
    assert immature["recommendedMoveKind"] == "return_to_journey"
    assert mature["family"] == "cross_family"


def test_due_followup_after_activation_prefers_gentler_reentry() -> None:
    engine = JourneyFollowthroughEngine()

    summary = engine.build_summaries(
        method_context={"windowStart": "2026-04-18T00:00:00Z", "windowEnd": "2026-04-23T00:00:00Z"},
        thread_digests=[],
        journeys=[_journey(updatedAt="2026-04-18T00:00:00Z")],
        recent_practices=[
            _practice(
                nextFollowUpDueAt="2026-04-19T00:00:00Z",
                activationBefore="moderate",
                activationAfter="high",
            )
        ],
        existing_briefs=[],
        dashboard=None,
        adaptation_profile=None,
        now="2026-04-23T00:00:00Z",
    )[0]

    assert summary["family"] == "practice_reentry"
    assert summary["readiness"] == "ready"
    assert summary["recommendedSurface"] == "practice_followup"
    assert summary["recommendedMoveKind"] == "offer_resource"
    assert summary["bodyFirst"] is True
    assert "high_intensity_after_activation" in summary["blockedEscalations"]


def test_symbol_body_life_pressure_uses_explicit_body_link_and_goal_tension() -> None:
    engine = JourneyFollowthroughEngine()

    summary = engine.build_summaries(
        method_context={
            "windowStart": "2026-04-20T00:00:00Z",
            "windowEnd": "2026-04-23T00:00:00Z",
            "recentBodyStates": [
                {
                    "id": "body_1",
                    "sensation": "tightness",
                    "bodyRegion": "chest",
                    "activation": "high",
                    "observedAt": "2026-04-22T12:00:00Z",
                }
            ],
            "goalTensions": [
                {
                    "id": "tension_1",
                    "goalIds": ["goal_1"],
                    "status": "active",
                    "tensionSummary": "Safety and expression are both live.",
                }
            ],
            "methodState": {},
        },
        thread_digests=[],
        journeys=[
            _journey(
                relatedSymbolIds=["symbol_1"],
                relatedGoalIds=["goal_1"],
                relatedBodyStateIds=["body_1"],
                updatedAt="2026-04-22T12:00:00Z",
            )
        ],
        recent_practices=[],
        existing_briefs=[],
        dashboard=None,
        adaptation_profile=None,
        now="2026-04-23T00:00:00Z",
    )[0]

    assert summary["family"] == "symbol_body_life_pressure"
    assert summary["recommendedMoveKind"] == "ask_body_checkin"
    assert summary["bodyFirst"] is True
    assert summary["relatedGoalTensionIds"] == ["tension_1"]
    assert "bypassing_body_contact" in summary["blockedEscalations"]


def test_cooldown_quiets_journey_followthrough() -> None:
    engine = JourneyFollowthroughEngine()

    summary = engine.build_summaries(
        method_context={"windowStart": "2026-04-20T00:00:00Z", "windowEnd": "2026-04-23T00:00:00Z"},
        thread_digests=[],
        journeys=[_journey(updatedAt="2026-04-22T12:00:00Z")],
        recent_practices=[],
        existing_briefs=[
            {
                "id": "brief_1",
                "userId": "user_1",
                "briefType": "journey_checkin",
                "status": "dismissed",
                "title": "Journey check-in",
                "summary": "A light followthrough invitation.",
                "relatedJourneyIds": ["journey_1"],
                "relatedMaterialIds": [],
                "relatedSymbolIds": [],
                "relatedPracticeSessionIds": [],
                "evidenceIds": [],
                "cooldownUntil": "2026-04-30T00:00:00Z",
                "updatedAt": "2026-04-23T00:00:00Z",
                "createdAt": "2026-04-23T00:00:00Z",
            }
        ],
        dashboard=None,
        adaptation_profile=None,
        now="2026-04-23T00:00:00Z",
    )[0]

    assert summary["readiness"] == "quiet"
    assert summary["cooldownUntil"] == "2026-04-30T00:00:00Z"
    assert "journey_brief_cooldown_active" in summary["reasons"]


def test_recent_stabilization_quiets_when_no_new_signal_has_arrived() -> None:
    engine = JourneyFollowthroughEngine()

    summary = engine.build_summaries(
        method_context={"windowStart": "2026-04-18T00:00:00Z", "windowEnd": "2026-04-23T00:00:00Z"},
        thread_digests=[],
        journeys=[
            _journey(
                updatedAt="2026-04-20T00:00:00Z",
                lastBriefedAt="2026-04-21T00:00:00Z",
            )
        ],
        recent_practices=[
            _practice(
                followUpCount=2,
                activationBefore="high",
                activationAfter="low",
                completedAt="2026-04-20T00:00:00Z",
                updatedAt="2026-04-20T00:00:00Z",
            )
        ],
        existing_briefs=[],
        dashboard=None,
        adaptation_profile=None,
        now="2026-04-23T00:00:00Z",
    )[0]

    assert summary["readiness"] == "quiet"
    assert "journey_recent_practice_quieting" in summary["reasons"]
