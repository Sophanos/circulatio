> **Implementation status:** Phases 1–9 core backend/runtime surfaces are implemented and targeted-tested. This includes LLM-first interpretation, approval-gated Phase 8/9 durable writes, threshold/living-myth review workflows, bounded analysis packets, the bounded read-only `discovery` digest, derived projections, proactive invitation seeds, Hermes/plugin exposure, the Phase 1 plan-only ritual presentation contract, and an offline Evolution OS for prompt fragments, skills, and tool descriptions.
>
> **Consolidated docs:** See `ARCHITECTURE.md` for the system framing. See `ROADMAP.md` for the product overview and use cases. See `INTERPRETATION_ENGINE_SPEC.md` for the Jungian hermeneutic specification. See `RUNBOOK.md` for safety, evidence, typology, and demo rules. See `PRESENTATION_LAYER.md` for the deferred embodied presentation contract. See `EMBODIED_GUIDANCE_SURFACE.md` for the future live body/camera guidance and Coach OS session contract.

# Circulatio Engineering Guide
## Technical Specification For Builders

Read `ROADMAP.md` first to understand what every line of code is in service of. This document tells you how to build it.

---

## Architecture Lock

Circulatio is a **symbolic/individuation backend for Hermes**. It is not a generic wellness tracker, productivity OS, or therapy simulator.

### Bounded Domains (What We Own)
- **Episodic materials:** dreams, events, reflections
- **Semantic memory:** compacted, stable meaning extracted from recurrence
- **Graph memory:** symbol recurrence, pattern, contradiction, compensation
- **Soma/body:** sensations, activation, fatigue, sleep-like markers, embodied reactions
- **Culture/collective:** mythic frames, symbolic traditions, amplification packs, personal vs. collective distinction
- **Goals/life-direction:** explicit aims, tensions, repeated avoidance, emergent direction
- **Practices/reviews:** recommendations, outcomes, follow-ups, integration work

### Explicit "Will Not Do"
- Generic calorie/sleep/wellness tracker without symbolic depth
- Unbounded productivity OS or task manager
- Medical diagnosis or therapy simulator
- Frontend visualization (out of scope for this phase)

### Integration Boundary
- **Hermes owns:** session orchestration, gateway routing, LLM inference, cron scheduling, ritual delivery messages, and ritual-invitation acceptance
- **Circulatio owns:** individuation state, memory, graph, symbolic interpretation logic, user adaptation profile, typed ritual plans, scheduled ritual-invitation brief payloads, and idempotent ritual-completion events
- **Renderer CLI owns:** local/static artifact manifest generation, mock provider output, provider/cache boundaries, fallback WebVTT captions, raw-prompt provider guards, and beta gates for music/video
- **Hermes Rituals frontend owns:** playback of artifact manifests, real-audio waveform decoding and scrub sync, photo-lens image rendering, breath pacers, meditation fields, caption-derived transcript sections, quiet completion UI, idempotency-key generation, completion POST validation, bounded companion UI, and the no-camera-first live guidance shell

### Ritual Runtime Boundaries
- Scheduled cron may create `ritual_invitation` rhythmic briefs only after `proactive_briefing` consent.
- Scheduled cron must not call `circulatio.presentation.plan_ritual`, run the renderer, or call external providers.
- Manual acceptance is the boundary for planning: accept the brief, then call `circulatio_plan_ritual` with the safe `acceptancePayload`.
- Completion sync is a separate persistence operation. It records playback state, optional body state, optional literal reflection text, and explicit practice feedback only; it never triggers interpretation, review generation, proposal creation, provider rendering, or practice recommendation.
- Provider-backed rendering stays opt-in, budget-gated, renderer-owned, and disabled for music/video unless beta flags are present.
- Mock/dry-run artifacts must not be treated as proof of live media. Check manifest provider fields and concrete `audio.wav`, `image.png`, and `captions.vtt` sources before debugging frontend playback.
- The current Hermes Rituals player chrome is product-sensitive. Improve media accuracy underneath it; do not redesign the visible waveform/scrub/caption controls without explicit UI approval.

### Storage Boundary
- SQLite is the canonical local backend
- Graph storage starts as SQLite adjacency / normalized tables with migration path to graph DB
- No external vector store in the current runtime; symbolic keyword expansion remains the retrieval seam

### Ontology Stability Rule
No new top-level domain concepts can be added without updating this document.

---

## Core Principles For Engineers

1. **You are not the source of insight. The user's psyche is.** Your job is to hold, connect, and surface — not to explain.
2. **Pattern over interpretation.** A held recurrence is more powerful than a clever reading.
3. **Body is symbol.** Somatic events are as meaningful as dreams. Do not flatten them to wellness data.
4. **Culture is amplification, not explanation.** Offer mythic, sociological, and psychological parallels as resonance, not proof, and never dump too much amplification at once.
5. **Shadow work requires consent.** Never name a projection the user is not ready to see. Offer; do not impose.
6. **The unconscious has its own timing.** Do not rush the door. Keep the key present.
7. **The goal is individuation, not optimization.** More conscious conflict is better than unconscious harmony.
8. **Your memory is your value.** The user forgets. You must not. This is why the graph and memory kernel are sacred.
9. **Proactive is gentle.** Surface patterns only when they are ripe. Never create anxiety to drive engagement.
10. **The user should need you less over time.** Success is obsolescence — the user becomes their own Circulatio.
11. **Continuity before conclusion.** The graph and memory kernel serve continuity; the method layer serves interpretation; integration happens only after both are present.

---

## Current State Analysis

### Existing Ownership And Data Flow

Circulatio already owns the baseline durable records that the later Phase 4-9 runtime builds on:

* `MaterialRecord` in `domain/materials.py`
* `SymbolRecord` and `SymbolHistoryEntry` in `domain/symbols.py`
* `PatternRecord` and `PatternHistoryEntry` in `domain/patterns.py`
* `PracticeSessionRecord` in `domain/practices.py`
* `InterpretationRunRecord` in `domain/interpretations.py`
* `ContextSnapshot` in `domain/context.py`
* `WeeklyReviewRecord` in `domain/reviews.py`
* `IntegrationRecord` in `domain/integration.py`
* Derived projections in `repositories/in_memory_projections.py`

The current interpretation call chain is:

```text
CirculatioService.create_and_interpret_material()
→ create_material()
→ interpret_existing_material()
→ _build_material_input()
→ ContextAdapter.build_material_input()
   → native life-context builder
   → native method-context builder
   → Hermes fallback only when needed
→ _store_context_snapshot()
→ CirculatioCore.interpret_material()
   → SafetyGate
   → LLM interpretation path first
   → methodGate / depthReadiness / amplification prompts / dream-series suggestions
   → local fallback only when the model omits or fails structured output
→ persist run / evidence / practice recommendation
```

The important current rule is that Circulatio no longer treats local heuristics as the primary source of meaning. The model is the intended source of interpretive moves. Local code still owns safety hard-stops, evidence integrity, storage, privacy, IDs, and schema normalization.

The current method-state connector chain is:

```text
Hermes/host decides a follow-up answer is context-bound
→ explicit bridge/tool call (`circulatio.method_state.respond`)
→ CirculatioService.process_method_state_response()
→ store response as bounded reflection material + evidence
→ direct user-reported record writes OR approval-gated proposals
→ derived method-context projections (`recentDreamDynamics`, method-state summary, clarification state)
→ later interpretation / review / practice calls consume the enriched method context
```

This connector is intentionally additive. It is not a hidden capture-any ingress. Hermes still owns intent recognition and routing. Circulatio only accepts explicit, anchored follow-up responses and turns them into evidence-backed durable state or pending proposals.

### Current Phase 4-7 Snapshot

The codebase now already contains the Phase 4-7 substrate that later work should build on rather than replace:

* `MethodContextSnapshot` is part of interpretation input and persisted context snapshots.
* `ThreadDigest` is a derived internal read model beside `MethodContextSnapshot`; it unifies journeys, dream series, threshold/process loops, goal tension, practice-loop, and longitudinal thread refs without creating a new durable record family.
* Domain records now exist for conscious attitude, personal amplification, body states, goals, dream series, culture, adaptation, journeys, and proactive briefs.
* `CirculatioCore` accepts LLM-produced `methodGate`, `depthReadiness`, amplification prompts, dream-series suggestions, and richer practice metadata.
* Hermes/plugin surfaces now support hold-first storage for dreams, events, reflections, symbolic notes, and body states, plus `alive_today`, the bounded read-only `discovery` digest, journey-page assembly, low-risk journey-container management, label-based journey resolution, explicit `/circulation journey ...` QA commands, interpretation, review, and approval flows.
* Hold-first material storage now also returns an additive, non-persisted `intakeContext` packet at the Hermes bridge boundary. That packet is built only from lightweight post-store projections (`build_method_context_snapshot_from_records()` plus `get_dashboard_summary()`), is explicitly `host_only`, remains factual and bounded, does not create interpretation runs/context snapshots, and does not change the brief public acknowledgement text.

### Current Phase 8/9 Snapshot

As of April 2026, the Phase 8/9 backend slice is also present in the main runtime:

* domain records, workflow contracts, and repository persistence now cover individuation and living-myth record families
* LLM contracts and core mapping now surface `individuationAssessment`, threshold review, living myth review, and bounded analysis packets without adding deterministic meaning engines
* durable writes derived from threshold and living-myth workflows remain proposal-based and require explicit approval before persistence
* derived memory-kernel and graph projections now include approved individuation/living-myth material without exposing raw material text
* proactive runtime support now includes threshold, chapter, return, bridge, and analysis-packet invitations based only on approved/projected records
* Hermes/plugin surfaces now expose threshold review, living myth review, analysis packet, review proposal approval/rejection, direct user-capture tools for explicit Phase 8 records, and an explicit method-state response operation for anchored clarifying/follow-up answers
* personalization now includes durable `InteractionFeedbackRecord` events, typed explicit-preference scopes, learned communication/practice policy slots under `learnedSignals`, derived runtime hints for prompts, and Hermes-side Atropos communication/practice env builders for bounded policy-learning
* Hermes may now autonomously create and update `JourneyRecord` containers as low-risk organizational writes, resolve them by exact/normalized human label when the host supplies that label, and expose explicit journey lifecycle slash commands for QA/debug/demo, while interpretation-derived durable symbolic memory remains approval-gated
* the repo now includes an external Hermes-host smoke harness that installs Circulatio into a temporary Hermes home/site-packages path and exercises host-level plugin load, store, journey lifecycle, and page rendering without adding a second command-only architecture
* the repo now also includes a conversational real-host QA protocol at `tests/evals/HERMES_CIRCULATIO_REAL_HOST_HARNESS.md` for strict operator-driven routing, leak, fallback, and retry-loop checks through `hermes chat`

The remaining work in this area should be refinement, wider validation, and documentation upkeep rather than a new architectural phase transition.

### Current Evolution OS Tooling

Circulatio now includes a repo-local, offline Evolution OS layer: optimize text artifacts first, evaluate them against explicit rubrics, stage reviewable candidate bundles, and require human review before adoption. This tooling stays outside the runtime path even though it lives in the same repo. It is builder infrastructure, not product behavior.

**Current targets:**

* `src/circulatio/llm/prompt_fragments.py` — extracted prompt policy fragments for interpretation, practice, threshold review, living myth review, method-state routing, and packet generation
* `src/circulatio_hermes_plugin/skills/circulation/SKILL.md` — Hermes-facing host-routing instructions
* `src/circulatio_hermes_plugin/schemas.py` — tool descriptions used during Hermes tool selection

**Current infrastructure:**

* `tools/self_evolution/targets.py` — target registry, mutation scope, owner, and immutable dependency metadata
* `tools/self_evolution/dataset_builder.py` — schemaVersion 1/2 JSONL loading plus split/severity/gate normalization
* `tools/self_evolution/fitness.py` — deterministic rubric scoring with blocking/major/minor case metadata
* `tools/self_evolution/constraints.py` — prompt-fragment, skill-size, tool-description, dataset-coverage, and immutable-bundle gates
* `tools/self_evolution/evaluator.py` — baseline, candidate-path, and candidate-bundle evaluation with regression reporting
* `tools/self_evolution/artifacts.py` — candidate discovery, staging, hashing, git provenance, and diff generation
* `tools/self_evolution/review.py` — `report.json`, `report.md`, `manifest.json`, `candidate_manifest.json`, `diff.patch`, and rationale packaging
* `tools/self_evolution/optimizer.py` — offline candidate orchestration; phase 1 fully supports `manual`
* `scripts/evaluate_circulatio_method.py` — strict gate plus candidate-bundle evaluation CLI
* `scripts/evolve_circulatio_method.py` — manual candidate staging CLI for review-package generation
* `tests/evals/circulatio_method/` — hand-authored eval fixtures, including schemaVersion 2 split/severity coverage

**Current contract:**

* Optimize offline only. No mid-conversation prompt mutation.
* Optimize text artifacts before code.
* Keep raw multilingual feedback notes out of runtime prompts and review artifacts.
* Emit reviewable run directories under `artifacts/self_evolution/runs/`; do not write prompt changes into user state.
* Require explicit evaluator pass plus normal repo tests before accepting a candidate.
* Do not let the optimizer freely mutate `SafetyGate`, approval logic, persistence schemas, evidence integrity, or direct durable-write rules.

**Current commands:**

```bash
.venv/bin/python scripts/evaluate_circulatio_method.py --strict
.venv/bin/python scripts/evolve_circulatio_method.py --target prompt_fragments --strategy manual --prompt-fragments src/circulatio/llm/prompt_fragments.py
```

This is the current offline builder path. The repo does **not** yet ship reflection/pareto search or provider-backed execution/judge gates; it ships the extraction points, datasets, reports, and constraints needed to add those later without weakening runtime boundaries.

### Journey CLI Comparative Evals

Circulatio now also includes a separate repo-local Journey CLI comparison layer under
`tools/journey_cli_eval/` and `scripts/evaluate_journey_cli.py`.

**Purpose:**

* compare local external coding CLIs such as `kimi`, `codex`, and `opencode` against the Hermes
  routing contract for journey-family cases, with an optional lightweight `hermes` adapter when a
  local Hermes CLI is available
* keep the comparison strictly local, opt-in, and artifact-producing
* map failures back to the right owner: method evals, backend service tests, bridge tests, or real
  host smoke

**Boundary:**

* subprocess adapters only; no provider API client is introduced
* missing CLIs skip unless `--require-adapters` is passed
* the harness runs in disposable temp workspaces and must not use the main repo as subprocess cwd
* no prompt mutation, no runtime mutation, and no hidden capture-any ingress are introduced
* findings are review inputs, not backend truth and not a replacement for `CirculatioService`, the
  Hermes bridge tests, or `scripts/hermes_host_smoke.py`

**Primary assets:**

* `tests/evals/journey_cli/schema/journey_case.schema.json`
* `tests/evals/journey_cli/*.jsonl`
* `tests/evals/journey_cli/README.md`
* `tests/evals/journey_cli/JOURNEY_FAMILIES.md` — longitudinal journey family taxonomy and canonical cases
* `tools/journey_cli_eval/` package modules for dataset loading, prompt packaging, adapter
  execution, normalization, scoring, caching, traces, reporting, and run orchestration
* `scripts/evaluate_journey_cli.py`

**Local workflow:**

```bash
.venv/bin/python -m unittest tests.test_journey_cli_eval
.venv/bin/python scripts/evaluate_journey_cli.py --adapter fake --strict
```

**Ritual eval mode:**

`--ritual-eval` runs a local simulator/evaluator for daily and weekly ritual journeys. It records
Hermes-style tool calls, verifies invite-before-plan behavior, renders accepted artifacts, records
completion, audits manifest/playback contracts, and writes `report.json`, `report.md`,
`timeline.json`, `tool_calls.json`, `browser_checks.json`, and `artifacts_checked.json` under
`artifacts/journey_cli_eval/runs/{runId}/`.

Default ritual eval uses mock/dry-run accepted renders and scores live-media surfaces as expected
fallbacks. Chutes-backed accepted renders require `--ritual-live-providers`, a positive
`--ritual-max-cost-usd`, an allowed provider profile, and a configured token. Video remains off by
default and requires `--ritual-include-video`, `--ritual-allow-beta-video`, plan policy,
provider-profile, token, and budget gates.

See `docs/JOURNEY_CLI.md` for the JTBD, report shape, and provider/browser examples.

This layer is complementary to Evolution OS. It sharpens the routing contract and surfaces drift,
but it does not change the adoption gates: method-eval pass, normal repo tests, and explicit human
review still decide whether a later artifact change is acceptable.

### What Should Be Reused

Reuse these existing structures rather than inventing parallel storage:

* `UserCirculatioBucket` as the in-memory source of truth.
* `in_memory_projections.py` as the home for derived native projections.
* Existing `HermesMemoryContext` summaries as source material for context-building where useful.
* Existing record list/query methods on `CirculatioRepository`.
* Existing `compact_life_context_snapshot()` as the final bounding/normalization step.

---

## Historical Implementation Notes

Phases 1–3 (memory-kernel scaffolding, graph-engine scaffolding, and native context builder) are fully implemented. The detailed design specifications (domain types, repository surfaces, projection behavior, filtering, ranking, graph derivation algorithms, and file-by-file impact tables) have been retired from this document because they are now canonically expressed in the code and tests.

If you need to understand the exact shapes, see:
- `src/circulatio/domain/memory.py` — memory-kernel types
- `src/circulatio/domain/graph.py` — graph query types and allowlist
- `src/circulatio/adapters/context_builder.py` — `CirculatioLifeContextBuilder`
- `src/circulatio/repositories/in_memory_projections.py` — derived projection helpers
- `tests/test_memory_graph_scaffolding.py` — memory and graph tests
- `tests/test_context_builder.py` — context derivation tests

---

## Coach OS Flow

The current runtime now has a single derived coach operating contract rather than separate surface-specific pacing logic.

Canonical flow:
```text
records
→ MethodContextSnapshot
→ MethodStateSummary
→ runtime method-state policy
→ coachState
→ surface-selected move
→ anchored reply through process_method_state_response()
```

Implementation notes:
- `CoachEngine` is a pure core service. It derives `witnessState` and `coachState` from typed summaries, runtime policy, consent/cooldown context, recent practices, journeys, and active briefs.
- `coachState` is attached during `CirculatioService._enrich_method_context_snapshot()`. It is derived every time and is not a new canonical storage family.
- `witnessState` remains as a compatibility summary for older prompt consumers, but both `witnessState` and `coachState.witness` now come from the same engine.
- `ResourceEngine` is a second pure core service that selects only from a curated local catalog. Resource invitations are typed, provenance-bound summaries, not arbitrary links or search results.
- `alive_today`, rhythmic briefs, journey pages, practice generation, weekly review inputs, threshold/living-myth/analysis packet inputs, and method-state response routing now all consume the same enriched method context contract.
- Deterministic logic stays limited to safety, consent, pacing, cadence, cooldowns, provenance, and routing. Symbolic interpretation and user-facing language remain LLM-shaped or host-rendered.

Operational implication:
- If a surface bypasses `_enrich_method_context_snapshot()`, it bypasses `coachState`. Future surface work should treat enrichment as mandatory for any coach-facing flow.

---

## Runtime Architecture Constraints (Phases 4–7)

> **For full product descriptions, see `ROADMAP.md`.** This section captures the architectural direction that now exists in the runtime, plus the constraints later work should preserve.

### Phase 4: LLM-First Depth Interpretation

**Core technical challenge:** Push symbolic interpretation, method gating, and depth moves into structured LLM output without reintroducing local heuristic engines.

**Architecture:**
- `CirculatioCore.interpret_material()` remains LLM-first for symbols, figures, motifs, hypotheses, method gates, depth readiness, amplification prompts, dream-series suggestions, and practice recommendations
- `SafetyGate` remains the only deterministic interpretive backstop: a fast pre-LLM screen plus post-LLM reconciliation where the gate wins
- Local code continues to own evidence integrity, schema normalization, persistence, and privacy boundaries
- If the LLM is unavailable, the only non-LLM practice fallback is grounding when safety-blocked and journaling otherwise

**Integration:**
- Keep the JSON contracts, adapters, and evidence ledger aligned with the LLM output schema
- Extend prompts and schemas rather than adding new detector classes
- Preserve hold-first behavior so stored material is not escalated into interpretation without an explicit interpret action

### Phase 5: Soma, Goal, Culture Layers

**Core technical challenge:** Make body states, goals, and cultural frames first-class graph citizens.

**Architecture:**
- Extend `MaterialRecord` for body states (sensations, activation, fatigue markers)
- Add `GoalRecord` and `GoalTensionRecord` to domain
- Add `CulturalAmplificationPack` as optional lens
- Keep `CulturalFrame` as the user-owned lens while Hermes hosts maintain a separate trusted amplification-source registry for collective amplification research
- Extend graph edges: `TRIGGERS` (symbol → body), `CORRELATES_WITH` (symbol → goal), `AMPLIFIED_BY` (symbol → culture)
- Update `CirculatioLifeContextBuilder` to derive soma and goal summaries

### Phase 6: Practice Engine And Adaptation Learning

**Core technical challenge:** Centralize practice lifecycle and learning without turning practice selection into a heuristic router.

**Architecture:**
- `PracticeEngine` owns deterministic reconciliation for safety, consent, method limits, explicit duration caps, lifecycle defaults, and coarse outcome signals
- `CirculatioCore.generate_practice()` is LLM-first and returns bounded practice recommendations without persisting
- `CirculatioService` persists recommendations, accepts/skips, records outcomes, records explicit interpretation/practice feedback, and emits adaptation events through explicit workflow methods
- `AdaptationEngine` validates explicit preference scopes, stores learned policy separately, derives soft typed hints, and never overrides explicit consent or explicit preferences

### Phase 7: Rhythmic Companion Runtime

**Core technical challenge:** Surface longitudinal rhythm without notification spam, hidden background work, or deterministic symbolic copy.

**Architecture:**
- `ProactiveEngine` remains the deterministic cadence layer for seed generation, dedupe, cooldowns, priority, and status transitions
- `CirculatioCore.generate_rhythmic_brief()` is LLM-first for witness-language and bounded fallback handling
- `CirculatioService.generate_rhythmic_briefs()` exposes an idempotent runtime surface for Hermes scheduling and manual pulls
- Hermes/plugin surfaces expose explicit practice and brief commands/tools instead of hidden schedulers

### Later: Standalone Distribution

Standalone packaging is no longer Phase 7. Treat it as a later distribution concern after the embedded rhythmic runtime is stable.

---

## Open Engineering Tasks

### 1. Hermes Ritual Experience Layer

The next major product integration task is to connect the existing ritual pieces into one proofable path. This is not a new Circulatio domain phase; it is an orchestration and validation layer across Hermes-agent, the renderer, Hermes Rituals, and Journey CLI.

Required work:

- Add Hermes-agent routing evals that prove user message plus memory context becomes the correct `circulatio_plan_ritual` call and surface mix.
- Add scheduled ritual E2E coverage for `ritual_invitation -> user acceptance -> plan -> renderer -> artifact URL`; skip/dismiss/expired invitations must not plan or render.
- Add browser E2E checks over `/artifacts/{artifactId}` for narration, music, captions, breath, meditation, image/photo, cinema when enabled, companion rail, and completion POST.
- Keep Chutes provider calls renderer-owned and opt-in. Kokoro, DiffRhythm, and WAN are live-smoke-tested contracts, not proof of full playback.
- Treat Whisper as unresolved. Plan-derived or fallback caption segments remain the required caption baseline.
- Attach live guidance through `guidanceSessionId`. The first no-camera shell exists; the planner must not become camera-aware, pose-aware, or live-coaching-aware.

**Status:** Partially implemented. Backend planning, renderer contracts, provider smoke, local handoff, fixture browser playback, quiet completion capture, companion scaffolding, and a no-camera live shell exist; production Hermes-agent routing/subscription, scheduled acceptance E2E, provider-backed browser checks, and sensor guidance remain open.

### 2. Practice Delivery

Phase 6 now keeps practice generation LLM-first while giving the runtime an explicit lifecycle:
- `PracticeEngine` is the deterministic boundary for consent, safety, lifecycle defaults, follow-up timing, and coarse outcome signals
- Practice recommendations remain LLM-shaped through `CirculatioCore.generate_practice()`
- Practice sessions persist explicit `recommended`, `accepted`, `skipped`, and `completed` states without introducing a deterministic symbolic router
- The fallback floor remains safety-blocked grounding or low-intensity journaling when the LLM path is unavailable

**Status:** Implemented. Further work should extend prompts and schemas, not add deterministic practice routing.

### 3. User Adaptation Profile

Phase 6 also centralizes adaptation learning in `AdaptationEngine`. `UserAdaptationProfile` now tracks:
- **Engagement patterns:** Which namespaces does the user log most? (dream-heavy vs. body-heavy vs. goal-heavy)
- **Practice preferences:** Explicit preferred/avoided modalities plus explicit duration ceiling
- **Communication preferences:** Tone, questioning style, symbolic density
- **Interpretation preferences:** Depth pacing and modality bias
- **Amplification pack affinity:** Which cultural frames resonate? Which are ignored?
- **Typology indicators:** Cognitive function signals from language
- **Ego strength trajectory:** Confronting shadow vs. avoiding it
- **Rhythmic tolerance:** Engagement rate with unsolicited briefings and cadence preferences

**Explicit + implicit learning:** Explicit preferences are validated by scope and remain user-owned. Learned policy updates live separately under `learnedSignals.*Policy`, never rewrite explicit preferences, and only become prompt-visible through derived typed hints. Raw multilingual note text is stored durably on `InteractionFeedbackRecord` and excluded from runtime prompts.

**Status:** Implemented for communication, interpretation, practice, and rhythm scopes. Interaction feedback, learned policy updates, and Hermes Atropos env builders now exist as bounded runtime surfaces. Learned preferences remain soft and threshold-gated.

---

## For Product Thinkers

Go back to `ROADMAP.md` to remember why this matters.

The technical work here is scaffolding. The soul is in the use cases.

---

## Appendix A: Domain Records Cheat Sheet

Concise overview of the durable record types so an AI agent scanning this file gets the ontology without opening `domain/` modules.

| Record | Key Purpose |
|--------|-------------|
| `MaterialRecord` | Stored symbolic material (dream, reflection, charged event, etc.) |
| `MaterialRevision` | Audit trail for material edits |
| `ContextSnapshot` | Life-context over a window |
| `InterpretationRun` | One interpretation pass over a material |
| `EvidenceItem` | Traceable support for observations and hypotheses |
| `SymbolMention` / `FigureMention` / `MotifMention` | Occurrences extracted from material |
| `PersonalSymbol` | Longitudinal symbol with recurrence and valence history |
| `SymbolHistoryEntry` | One event in a symbol's life |
| `PatternRecord` | Recurring tension or complex-candidate |
| `PatternHistoryEntry` | Changes to a pattern over time |
| `TypologyLensRecord` | Optional typology hint (disabled by default) |
| `PracticePlan` | Recommended next practice |
| `PracticeSessionRecord` | Completed practice and outcome |
| `IntegrationRecord` | Approval / rejection / feedback on a run |
| `WeeklyReviewRecord` | Review window output |

### State Machines

- **Material:** `active` → `revised` → `deleted`
- **Pattern:** `observed_signal` → `candidate` → `active` → `recurring` → `integrating` → `dormant` → `disconfirmed`
- **Typology:** `candidate` → `approved` → `user_refined` → `disconfirmed`

---

## Appendix B: Engine Interface Summary

Condensed core contract so an AI agent understands the interpretation boundary without opening `core/` or `llm/` modules.

### Primary Input

`MaterialInterpretationInput` carries: `userId`, `materialType`, `materialText`, optional `materialDate`, `sessionContext`, `wakingTone`, `userAssociations`, `explicitQuestion`, `culturalOrigins`, `lifeContextSnapshot`, `hermesMemoryContext`, `safetyContext`, and `options`.

Supporting inputs:
- `SessionContext` — current conversation notes (`source: "current-conversation"`)
- `LifeContextSnapshot` — mood, energy, focus, mental state, habits, notable changes
- `HermesMemoryContext` — recurring symbols, active complex candidates, recent summaries, practice outcomes, cultural preferences, suppressed hypotheses, typology summaries
- derived runtime hints — communication, interpretation, and practice hints built from explicit-over-learned adaptation resolution

### Primary Output

`InterpretationResult` carries: `runId`, `materialId`, `safetyDisposition`, `observations`, `evidence`, `materialStructure`, `dreamStructure`, `symbolMentions`, `figureMentions`, `motifMentions`, `personalSymbolUpdates`, `culturalAmplifications`, `hypotheses`, `compensationAssessment`, `complexCandidateUpdates`, `lifeContextLinks`, `typologyAssessment`, `practiceRecommendation`, `clarifyingQuestion`, `memoryWritePlan`, and `userFacingResponse`.

`MemoryWritePlan` carries: `runId`, `proposals[]`, `evidenceItems[]`.

### Key Calls

| Call | Input | Output | Purpose |
|------|-------|--------|---------|
| `interpretMaterial` | Symbolic material + context + memory | `InterpretationResult` | Main interpretation path |
| `interpretDream` | Dream material + context + memory | `InterpretationResult` | Dream-specialized wrapper |
| `generateCirculationSummary` | Time window + memory + context | Summary payload | Weekly review support |
| `recordIntegration` | Run id + approvals + feedback | Integration result | Convert response into learning |

### Core Invariants

1. Observations may appear without hypotheses.
2. Strong hypotheses require evidence.
3. Interpretation is side-effect free.
4. Durable mutation only via explicit repository/service operations.
5. User-facing claims must remain traceable to evidence.

### Service-Layer Boundary

Above the core, `CirculatioService` provides: material creation, create-and-interpret workflows, reinterpreting stored material, explicit method-state response processing for anchored follow-up answers, bounded read-only discovery assembly, proposal approval/rejection for interpretation, review, and method-state capture runs, hypothesis suppression, explicit interpretation/practice feedback recording, validated adaptation preference updates, revision and deletion, history queries, weekly review generation, practice outcome recording, and dashboard summaries.
