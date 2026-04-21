---
name: circulatio
description: Hermes-Circulatio guidance for symbolic interpretation, durable symbolic memory, review workflows, and individuation backend architecture.
metadata:
  related_skills: [memory, reflection, context]
---

# Circulatio Skill

## Purpose

Use this skill when working on Hermes-Circulatio as the individuation backend inside Hermes.

The backend owns:

- symbolic materials
- compact context snapshots
- evidence and interpretation runs
- proposal approval and rejection state
- symbol and pattern history
- optional typology lenses
- practice recommendations and practice outcomes
- review and feedback flows
- revision, deletion, and suppression

## Architecture Guidance

Keep the current layering clear:

- `CirculatioCore` is the side-effect-free interpretation engine
- repositories own durable record persistence and projections
- `CirculatioService` owns backend workflow orchestration
- Hermes-facing wrappers map product/runtime commands onto service methods
- Hermes owns UX, orchestration, scheduling, and consent presentation

## Core Rules

- Keep observations separate from hypotheses.
- Keep hypotheses evidence-backed and cautious.
- Keep interpretation side-effect free.
- Make durable changes through explicit backend operations.
- Preserve revision, deletion, and suppression as first-class flows.
- Keep typology optional and non-deterministic.
- Do not let Circulatio become a general life tracker.

## Context Guidance

If context is available from another source, normalize it into Circulatio’s schema rather than treating the external shape as the product model.

Store compact individuation-relevant snapshots, not raw life logs.

## Evidence Guidance

Every observation, hypothesis, and proposal should reference inspectable evidence.

Interpretation runs, reviews, and histories should remain traceable back to stored evidence IDs.

## Safety Guidance

Blocked states should produce grounding-only behavior, no typology, and no durable proposal generation from the interpretation path.

Safety blocks should still allow a run record and safe practice guidance, but not depth-work persistence.

## Product Direction

Do not treat Circulatio as only a one-shot interpreter.

Treat it as the backend for:

- material intake
- interpretation
- run storage
- evidence storage
- approval/rejection
- history and review
- revision and deletion
- practice tracking

## Current Status

The current repository already includes:

- durable domain records
- a durable repository contract
- an in-memory backend implementation
- a service layer for backend workflows
- a Hermes-facing command router
- SQLite-backed `HermesProfileCirculatioRepository` with optimistic concurrency
- Full Hermes plugin packaging with entry point registration
- Agent bridge with idempotency (request hashing, response replay, TTL-based cleanup)
- `HermesProfileLifeOsReferenceAdapter` reading Hermes state.db, MEMORY.md, USER.md, SOUL.md
- `HermesModelAdapter` with JSON repair and model path verification
- Boot validation (entry point, asset, storage health)
- 11 registered tools and 1 command in plugin.yaml
- Full command and tool dispatch through the bridge

The main remaining steps are:

- Cron/scheduled briefing delivery
- Broader integration and contract tests
- Pagination and query ergonomics for large data sets
- Deployment as a running Hermes service
