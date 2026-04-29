# AGENTS.md — Circulatio

> Symbolic/individuation backend for Hermes. Phases 1–9 core backend/runtime surfaces are implemented. Phase 7 standalone distribution remains deferred.

## What This Repo Is

- **Is:** Backend for dreams, reflections, body states, symbols, patterns, Jungian depth interpretation.
- **Is not:** Wellness tracker, productivity OS, therapy simulator, or frontend.

**Ownership split:**
- **Hermes/OpenClaw/host agent owns:**
  - Natural-language intent recognition
  - Tool selection
  - Routing between store / interpret / synthesis flows
  - Proactive scheduling and delivery
- **Circulatio owns:**
  - Durable individuation records
  - Context derivation
  - Evidence-backed synthesis and interpretation
  - Reviews, practices, approval flows
  - Body-state / goal / symbol / pattern persistence
- **Standalone Circulatio** (Phase 7+) gets its own LLM runtime separate from host routing.

For embedded integrations, Circulatio is a backend tool surface, not the router.

## Dev Environment

- Python 3.11+. Virtual env at `.venv/`.
- Install: `pip install -e ".[dev]"`
- No Docker, no Makefile, no CI.

## Commands

```bash
# Gate
python -m pytest tests/

# Single test
python -m pytest tests/test_circulatio_service.py::CirculatioServiceTests::test_create_material_and_llm_interpretation_persists_run_and_evidence -v

# Lint / format
ruff check src tests
ruff format src tests

# Typecheck (circulatio only; plugin excluded)
mypy src/circulatio
```

## Code Style

- Ruff: line-length 100, target py311, lint `E,F,I,UP`.
- mypy: `strict = false`, packages `circulatio` only.
- Use `from __future__ import annotations`.

## Architecture

```text
src/
  circulatio/               ← Core library
    domain/                 ← Types, records, graph vocab. No I/O.
    application/            ← CirculatioService orchestrates workflows.
    core/                   ← CirculatioCore, LLM orchestration, safety, evidence.
    repositories/           ← In-memory + SQLite. No external graph DB.
    adapters/               ← Context builder, Hermes/Life-OS adapters.
    hermes/                 ← Bridge contracts, router, runtime wiring.
    llm/                    ← Prompts, model adapter, JSON schema.
  circulatio_hermes_plugin/ ← Hermes plugin (tools, commands, schemas, yaml)
```

- Hermes entry: `circulatio_hermes_plugin.register()`
- Local entry: `CirculatioService` + `CirculatioRepository`
- Tests: async. pytest-asyncio strict mode. `async def test_*`.

## Repository Patterns

- `CirculatioRepository` abstract boundary. Implementations:
  - `InMemoryCirculatioRepository` (dev/tests)
  - `HermesProfileCirculatioRepository` (prod, SQLite)
- Graph and memory-kernel are **derived projections** at query time. No separate graph DB.
- No external vector store. Symbolic interpretation comes from LLM structured output; deterministic local logic is limited to safety backstops and minimal fallback behavior.

## Routing Contract

- **Embedded hosts:** Hermes-agent first; OpenClaw later through MCP or equivalent typed tool exposure.
- **Default host behavior:** host LLM chooses among explicit Circulatio tools like store, interpret, review, and "alive today" synthesis.
- **No universal ingress:** avoid a generic "capture anything and classify it internally" tool.
- **Store vs interpret:** host chooses whether to hold/store, interpret, or synthesize. Circulatio should not silently escalate a stored note into interpretation because a heuristic matched.
- **Standalone:** when Circulatio runs without Hermes later, ship a separate local LLM loop rather than embedding Hermes assumptions in the backend.

Routing is LLM-driven at the host layer. Hermes-agent and future OpenClaw/MCP hosts decide when Circulatio is relevant and which Circulatio tool to call.

## Docs Hierarchy

1. `docs/ARCHITECTURE.md` — System framing, scalability thesis, builder-psyche separation.
2. `docs/ROADMAP.md` — Vision, use cases, phases.
3. `docs/ENGINEERING_GUIDE.md` — Tech spec, current state, runtime constraints.
4. `docs/INTERPRETATION_ENGINE_SPEC.md` — Jungian hermeneutic method.
5. `docs/RUNBOOK.md` — Safety, evidence, typology, demo script.
6. `docs/SELF_EVOLUTION_OS.md` — Offline Evolution OS contract and CLI.
7. `docs/PRESENTATION_LAYER.md` — Deferred embodied presentation contract (backend-only).
8. `tests/evals/journey_cli/JOURNEY_FAMILIES.md` — Longitudinal journey families and eval cases.

## Locked

- **No heuristics:** Nearly zero deterministic shortcuts. No keyword matchers, regex lists, or hardcoded if/else routing tables outside the minimal safety backstop. Use LLM structured output, explicit contracts, and schema normalization rather than local interpretation layers.
- **Reprompt MCP tools:** Always use reprompt MCP tools when available.
- **Hold first:** Ambient captures stored without interpretation unless user explicitly asks for meaning/analysis. The unconscious has its own timing.
- **Practice fallback:** When the LLM is unavailable, return grounding if safety-blocked and journaling otherwise. Do not add a separate deterministic practice router beyond that floor.
- **Adaptation:** Explicit profile first, implicit learning after 20+ interactions.
- **Storage:** SQLite canonical. Graph is derived, not separate DB.
- **Scope:** No frontend, no medical diagnosis, no unbounded task management.

## Testing

- `tests/_helpers.py` has `FakeCirculatioLlm` — standard LLM test double.
- Integration tests: Hermes bridge plugin (`test_hermes_bridge_plugin.py`).
- Durability tests: SQLite idempotency, corrupt-bucket isolation (`test_hermes_runtime_durability.py`).
- Browser/UI verification must use `agent-browser` only: https://github.com/vercel-labs/agent-browser. Do not add Playwright browser tests, Playwright config, or Playwright package dependencies to this repo.

## Mistakes to Avoid

- Do not add top-level domain concepts without updating `ENGINEERING_GUIDE.md`.
- Do not expose raw material text in context snapshots or graph nodes. Summaries/titles/tags only.
- Route interpretation through `ContextAdapter`, not direct repository path.
- Plugin package (`circulatio_hermes_plugin`) is intentionally outside mypy coverage.
