# Circulatio Skill Pack

This skill pack supports Hermes-Circulatio as the individuation backend inside Hermes Agent.

It is designed to work with:

- Hermes Agent for conversation, tooling, orchestration, and UX
- Circulatio backend for symbolic materials, context, interpretation runs, evidence, approval flows, history, and review

## Scope

This package focuses on:

- symbolic interpretation
- durable symbolic memory
- evidence-backed observations and hypotheses
- bounded amplification
- proposal approval and rejection
- revision, deletion, and suppression flows
- practice routing and practice outcomes
- review across time

## Current Architecture

The current backend is split into clear layers:

- `CirculatioCore` stays side-effect free and produces `InterpretationResult`
- `CirculatioRepository` defines durable backend persistence contracts
- `InMemoryCirculatioRepository` remains the reference test/dev implementation
- `HermesProfileCirculatioRepository` is the durable Hermes-profile SQLite repository for real runtime use
- `CirculatioService` orchestrates create, interpret, approve, reject, revise, delete, history, and review workflows
- Hermes-facing command routing maps `/circulation ...` commands to service workflows

## Current Workflow Shape

The intended backend flow is:

1. Hermes creates or loads material.
2. Circulatio hydrates context and symbolic memory.
3. `CirculatioCore` interprets without side effects.
4. Circulatio stores the run, evidence, and recommended practice.
5. Hermes presents pending proposals and hypotheses.
6. User approval, rejection, revision, or deletion is sent back into Circulatio.
7. Circulatio updates durable records and histories.

## Current Limits

The current runtime should avoid:

- active imagination by default
- deterministic typology
- graph visualization as a product dependency
- diagnostic claims
- hidden writes during interpretation
- turning Circulatio into raw life tracking

## Working Assumption

Context and symbolic state should be modeled in Circulatio’s backend rather than scattered across ad hoc notes or memory layers.

## Current Gaps

Remaining work beyond the current repository state:

- broader pagination and query ergonomics for larger histories
- internal refactoring of the large in-memory repository implementation
- end-to-end evaluation of prompt quality across larger real Hermes histories

## Optional Scripts

The files under `optional-skills/creative/circulatio/scripts/` are legacy reference artifacts from an earlier standalone prototype path.

They are not part of the active Circulatio runtime architecture. The active product path is now:

- `src/circulatio/core/`
- `src/circulatio/llm/`
- `src/circulatio/application/`
- `src/circulatio/hermes/`
- `src/circulatio_hermes_plugin/`

That means the optional scripts should be treated as historical examples only, not as runtime dependencies or the interpretation engine.

## References

Primary code paths:

- `src/circulatio/core/circulatio_core.py`
- `src/circulatio/application/circulatio_service.py`
- `src/circulatio/repositories/circulatio_repository.py`
- `src/circulatio/repositories/in_memory_circulatio_repository.py`
- `src/circulatio/hermes/command_router.py`
- `PRD.md`
