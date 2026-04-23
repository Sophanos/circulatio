from __future__ import annotations

from pathlib import Path

from circulatio.adapters.context_adapter import ContextAdapter
from circulatio.adapters.context_builder import CirculatioLifeContextBuilder
from circulatio.adapters.method_context_builder import CirculatioMethodContextBuilder
from circulatio.application.circulatio_service import CirculatioService
from circulatio.core.circulatio_core import CirculatioCore
from circulatio.domain.ids import create_id
from circulatio.hermes.amplification_sources import default_trusted_amplification_sources
from circulatio.repositories.in_memory_circulatio_repository import InMemoryCirculatioRepository
from tests._helpers import FakeCirculatioLlm
from tools.journey_cli_eval.dataset import load_journey_cases

REPO_ROOT = Path(__file__).resolve().parents[1]
JOURNEY_DATASETS = [
    REPO_ROOT / "tests" / "evals" / "journey_cli" / "baseline.jsonl",
    REPO_ROOT / "tests" / "evals" / "journey_cli" / "compound.jsonl",
    REPO_ROOT / "tests" / "evals" / "journey_cli" / "redteam.jsonl",
]


class FakeLifeOs:
    async def get_life_context_snapshot(
        self, *, user_id: str, window_start: str, window_end: str
    ) -> dict[str, object]:
        del user_id
        return {
            "windowStart": window_start,
            "windowEnd": window_end,
            "lifeEventRefs": [],
            "focusSummary": "Synthetic journey-case helper context.",
            "source": "journey-case-helper",
        }


def load_journey_case(case_id: str) -> dict[str, object]:
    return load_journey_cases(JOURNEY_DATASETS, case_ids=[case_id])[0]


def build_service_fixture() -> tuple[
    InMemoryCirculatioRepository, CirculatioService, FakeCirculatioLlm
]:
    repository = InMemoryCirculatioRepository()
    llm = FakeCirculatioLlm()
    core = CirculatioCore(repository, llm=llm)
    builder = CirculatioLifeContextBuilder(repository)
    context_adapter = ContextAdapter(
        repository,
        life_os=FakeLifeOs(),
        life_context_builder=builder,
        method_context_builder=CirculatioMethodContextBuilder(repository),
    )
    service = CirculatioService(
        repository,
        core,
        context_adapter=context_adapter,
        method_state_llm=llm,
        trusted_amplification_sources=default_trusted_amplification_sources(),
    )
    return repository, service, llm


async def seed_history_seed(
    *,
    case: dict[str, object],
    repository: InMemoryCirculatioRepository,
    service: CirculatioService,
    user_id: str,
) -> None:
    history = case.get("historySeed") if isinstance(case.get("historySeed"), dict) else {}

    for preference in list(history.get("consentPreferences", [])):
        if not isinstance(preference, dict):
            continue
        await service.set_consent_preference(
            {
                "userId": user_id,
                "scope": preference.get("scope", "projection_language"),
                "status": preference.get("status", "withhold"),
                "note": preference.get("note"),
                "source": "journey_case_seed",
            }
        )

    for journey in list(history.get("journeys", [])):
        if not isinstance(journey, dict):
            continue
        await repository.create_journey(
            {
                "id": str(journey.get("id") or create_id("journey")),
                "userId": user_id,
                "label": str(journey.get("label") or "Journey"),
                "status": str(journey.get("status") or "active"),
                "relatedMaterialIds": list(journey.get("relatedMaterialIds", [])),
                "relatedSymbolIds": list(journey.get("relatedSymbolIds", [])),
                "relatedPatternIds": list(journey.get("relatedPatternIds", [])),
                "relatedDreamSeriesIds": list(journey.get("relatedDreamSeriesIds", [])),
                "relatedGoalIds": list(journey.get("relatedGoalIds", [])),
                "relatedBodyStateIds": list(journey.get("relatedBodyStateIds", [])),
                "currentQuestion": str(journey.get("currentQuestion") or ""),
                "createdAt": str(journey.get("createdAt") or "2026-04-18T00:00:00Z"),
                "updatedAt": str(journey.get("updatedAt") or "2026-04-18T00:00:00Z"),
            }
        )

    for practice in list(history.get("practiceSessions", [])):
        if not isinstance(practice, dict):
            continue
        await repository.create_practice_session(
            {
                "id": str(practice.get("id") or create_id("practice")),
                "userId": user_id,
                "practiceType": str(practice.get("practiceType") or "journaling"),
                "reason": str(practice.get("reason") or "Journey-case seed."),
                "instructions": list(practice.get("instructions", ["Write briefly."])),
                "durationMinutes": int(practice.get("durationMinutes") or 5),
                "contraindicationsChecked": list(
                    practice.get("contraindicationsChecked", ["none"])
                ),
                "requiresConsent": bool(practice.get("requiresConsent", False)),
                "status": str(practice.get("status") or "recommended"),
                "followUpPrompt": practice.get("followUpPrompt"),
                "nextFollowUpDueAt": practice.get("nextFollowUpDueAt"),
                "source": str(practice.get("source") or "manual"),
                "followUpCount": int(practice.get("followUpCount") or 0),
                "relatedJourneyIds": list(practice.get("relatedJourneyIds", [])),
                "createdAt": str(practice.get("createdAt") or "2026-04-18T00:00:00Z"),
                "updatedAt": str(practice.get("updatedAt") or "2026-04-18T00:00:00Z"),
                "activationBefore": practice.get("activationBefore"),
                "activationAfter": practice.get("activationAfter"),
                "outcome": practice.get("outcome"),
                "completedAt": practice.get("completedAt"),
                "note": practice.get("note"),
            }
        )

    for body_state in list(history.get("bodyStates", [])):
        if not isinstance(body_state, dict):
            continue
        await service.store_body_state(
            {
                "userId": user_id,
                "sensation": str(body_state.get("sensation") or "tightness"),
                "observedAt": str(body_state.get("observedAt") or "2026-04-18T09:00:00Z"),
                "bodyRegion": body_state.get("bodyRegion"),
                "activation": body_state.get("activation"),
                "tone": body_state.get("tone"),
                "temporalContext": body_state.get("temporalContext"),
                "noteText": body_state.get("noteText"),
            }
        )
