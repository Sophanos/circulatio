> **Implementation status:** Phases 1–9 core backend/runtime surfaces are implemented and targeted-tested. This includes LLM-first interpretation, approval-gated Phase 8/9 durable writes, threshold/living-myth review workflows, bounded analysis packets, the bounded read-only `discovery` digest, derived projections, proactive invitation seeds, Hermes/plugin exposure, and an offline Evolution OS for prompt fragments, skills, and tool descriptions.
>
> **Consolidated docs:** See `ARCHITECTURE.md` for the system framing, scalability thesis, and builder-psyche separation. See `ROADMAP.md` for the product overview and use cases. See `INTERPRETATION_ENGINE_SPEC.md` for the Jungian hermeneutic specification. See `RUNBOOK.md` for safety, evidence, typology, and demo rules. See `JOURNEY_FAMILIES.md` for the derived longitudinal journey families and eval-case framing used to test backend continuity, pacing, and host behavior.

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
- **Hermes owns:** session orchestration, gateway routing, LLM inference, cron scheduling
- **Circulatio owns:** individuation state, memory, graph, symbolic interpretation logic, user adaptation profile

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
  routing contract for journey-family cases
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
* `tools/journey_cli_eval/` package modules for dataset loading, prompt packaging, adapter
  execution, normalization, scoring, caching, traces, reporting, and run orchestration
* `scripts/evaluate_journey_cli.py`

**Local workflow:**

```bash
.venv/bin/python -m unittest tests.test_journey_cli_eval
.venv/bin/python scripts/evaluate_journey_cli.py --adapter fake --strict
```

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

## Phase 1: Native Memory-Kernel Scaffolding ✅ IMPLEMENTED

**Status:** Complete. Files exist and tests pass.

Add typed memory-kernel scaffolding as a **derived projection**, not a new durable store.

### Module

`src/circulatio/domain/memory.py`

Use a new module instead of adding all of this to `domain/types.py` because the memory-kernel shapes are a separate domain surface from interpretation input/output wire types.

### New Domain Types

```text
MemoryNamespace = Literal[
  "materials",
  "context_snapshots",
  "interpretation_runs",
  "evidence",
  "personal_symbols",
  "patterns",
  "typology_lenses",
  "practice_sessions",
  "weekly_reviews",
  "integrations",
  "suppressed_hypotheses",
]
```

Use plural namespace names because repository buckets already store plural collections with matching product-domain concepts.

Add provenance:
```text
MemoryKernelProvenance
- sourceNamespace: MemoryNamespace
- sourceId: Id
- materialId?
- runId?
- evidenceIds[]
- createdAt?
- observedAt?
```

Add importance:
```text
MemoryImportance
- score: float        # 0.0–1.0 deterministic hint, not embedding score
- reasons[]          # e.g. "recurring_symbol", "recent_practice_outcome"
- recurrenceCount?
- userConfirmed?
- lastSeen?
```

Add memory item:
```text
MemoryKernelItem
- id
- userId
- namespace
- entityId
- entityType
- label
- summary
- keywords[]
- provenance
- importance
- privacyClass
- createdAt
- updatedAt
```

Add retrieval query and snapshot:
```text
MemoryRetrievalRankingProfile = Literal[
  "default",
  "recency",
  "recurrence",
  "importance",
]

MemoryRetrievalQuery
- namespaces?
- relatedEntityIds?
- windowStart?
- windowEnd?
- privacyClasses?
- textQuery?              # keyword filtering only; no embedding/vector behavior
- rankingProfile?
- limit?

MemoryKernelSnapshot
- userId
- query?
- items[]
- generatedAt
- rankingNotes[]
```

### Repository Surface

Add to `CirculatioRepository`:
```text
async build_memory_kernel_snapshot(
    user_id: Id,
    *,
    query: MemoryRetrievalQuery | None = None,
) -> MemoryKernelSnapshot
```

Do **not** add this to `GraphMemoryRepository` unless a concrete existing implementation already satisfies all new methods.

### In-Memory Projection Behavior

Implement in `in_memory_projections.py` as a pure locked-bucket helper:
```text
build_memory_kernel_snapshot_locked(bucket, user_id, query) -> MemoryKernelSnapshot
```

Initial item sources:

| Namespace | Source records | Summary behavior |
|-----------|---------------|------------------|
| `materials` | `bucket.materials` and `bucket.material_summaries` | Prefer stored summary/title/tags; never expose raw text |
| `personal_symbols` | `bucket.symbols` | canonical name, recurrence, valence hints |
| `patterns` | `bucket.patterns` | label, formulation, activation intensity, confidence |
| `practice_sessions` | `bucket.practice_sessions` | practice type, target, outcome if completed |
| `context_snapshots` | `bucket.context_snapshots` | summary plus source/window |
| `weekly_reviews` | `bucket.weekly_reviews` | result user-facing response summarized/truncated |
| `integrations` | `bucket.integrations` | action, affected ids, note summary |
| `evidence` | `bucket.evidence` | quote/summary only, privacy preserved |
| `suppressed_hypotheses` | `bucket.suppressed` | normalized claim key and reason |

Filtering:
1. Exclude records with status `"deleted"`.
2. Apply namespace filter.
3. Apply privacy class filter.
4. Apply window overlap using best available timestamp.
5. Apply simple case-insensitive keyword matching for `textQuery`.
6. Apply limit, default `20`, hard cap `100`.

Ranking:
- `default`: importance score desc, then updated/created desc.
- `recency`: latest timestamp desc.
- `recurrence`: recurrence count desc, then importance.
- `importance`: importance score desc.

### Symbolic Keyword Expansion (Amendment To Base Plan)

Add a lightweight symbolic expansion layer:
- When a `PersonalSymbol` is extracted, generate `symbolicFingerprint`: a list of related concepts (e.g., `serpent` → `snake, reptile, wisdom, danger, kundalini, uroboros`).
- Store in `MemoryKernelItem.keywords`.
- Memory query matches against this expanded set.
- This is deterministic, requires no external dependencies, and gives 60-70% of cross-symbol retrieval.
- Leave seam: `MemoryKernelItem.embedding?: list[float]` for future Phase.

### Compaction (Amendment To Base Plan)

When `raw` episodic records exceed threshold per namespace, generate `semantic` summary:
- Simple concatenation + recurrence count for now.
- Key is bucket classification (`episodic` → `semantic`).
- Preserve `compactedFromIds` lineage.

---

## Phase 2: Native Graph-Engine Scaffolding ✅ IMPLEMENTED

**Status:** Complete. Files exist and tests pass.

Add graph query and allowlist types over the existing domain vocabulary. The graph is derived from current records at query time.

### Extend `domain/graph.py`

Add missing vocabulary:
```text
GraphNodeType += "EvidenceItem"
GraphEdgeType += "SUMMARIZES"
```

Add graph query types:
```text
GraphTraversalDirection = Literal["outbound", "inbound", "both"]

GraphQuery
- rootNodeIds?
- nodeTypes?
- edgeTypes?
- maxDepth?
- direction?
- includeEvidence?
- limit?

GraphNodeProjection
- id
- userId
- type
- sourceId
- label
- summary?
- privacyClass
- createdAt
- updatedAt
- metadata?

GraphEdgeProjection
- id
- userId
- type
- fromNodeId
- toNodeId
- evidenceIds[]
- createdAt

GraphQueryAllowlist
- nodeTypes[]
- edgeTypes[]
- maxDepth
- maxLimit

GraphQueryResult
- userId
- nodes[]
- edges[]
- allowlist
- warnings[]
```

Add constant:
```text
DEFAULT_GRAPH_QUERY_ALLOWLIST
```

Allowed node types (current Circulatio vocabulary only):
```text
MaterialEntry, DreamEntry, ReflectionEntry, ChargedEventNote, ContextSnapshot,
PersonalSymbol, DreamFigure, MotifMention, Theme, ComplexCandidate,
InterpretationRun, PracticeSession, IntegrationNote, LifeEventRef,
StateSnapshotRef, TypologyLens, TypologyHypothesis, WeeklyReview, EvidenceItem
```

Allowed edge types:
```text
MENTIONS, INSTANCE_OF, FEATURES, MAY_EXPRESS, LINKED_TO, CONTEXTUALIZED_BY,
SUPPORTED_BY, CONTRADICTED_BY, AMPLIFIED_BY, DRAWS_FROM, USED_EVIDENCE,
TARGETED, CONFIRMS_OR_REJECTS, SUMMARIZES
```

### Repository Surface

Add to `CirculatioRepository`:
```text
async query_graph(
    self,
    user_id: Id,
    *,
    query: GraphQuery | None = None,
) -> GraphQueryResult
```

### In-Memory Graph Derivation

Add in `in_memory_projections.py`:
```text
query_graph_locked(bucket, user_id, query) -> GraphQueryResult
```

Build nodes from bucket records:

| Record | Node type |
|--------|-----------|
| `MaterialRecord.materialType == "dream"` | `DreamEntry` |
| `reflection` | `ReflectionEntry` |
| `charged_event` | `ChargedEventNote` |
| `symbolic_motif`, `practice_outcome` | `MaterialEntry` |
| `ContextSnapshot` | `ContextSnapshot` |
| `InterpretationRunRecord` | `InterpretationRun` |
| `EvidenceItem` | `EvidenceItem` |
| `SymbolRecord` | `PersonalSymbol` |
| `PatternRecord.patternType == "complex_candidate"` | `ComplexCandidate` |
| `PatternRecord.patternType == "theme"` | `Theme` |
| other pattern types | `Theme` initially, `metadata.patternType` preserved |
| `PracticeSessionRecord` | `PracticeSession` |
| `IntegrationRecord` | `IntegrationNote` |
| `WeeklyReviewRecord` | `WeeklyReview` |
| `TypologyLensRecord` | `TypologyLens` |

Derive edges from current fields:
```text
InterpretationRun -DRAWS_FROM-> Material
InterpretationRun -USED_EVIDENCE-> EvidenceItem
InterpretationRun -CONTEXTUALIZED_BY-> ContextSnapshot
Material -CONTEXTUALIZED_BY-> ContextSnapshot
Material -MENTIONS-> PersonalSymbol (via linkedMaterialIds)
Pattern -SUPPORTED_BY-> EvidenceItem
Pattern -CONTRADICTED_BY-> EvidenceItem
Pattern -LINKED_TO-> PersonalSymbol (via linkedSymbolIds)
PracticeSession -DRAWS_FROM-> Material
PracticeSession -LINKED_TO-> InterpretationRun
WeeklyReview -SUMMARIZES-> Material / PersonalSymbol / Pattern
IntegrationNote -CONFIRMS_OR_REJECTS-> InterpretationRun
IntegrationNote -LINKED_TO-> affected entity nodes
```

### Symbol-to-Symbol Inferred Edges (Amendment To Base Plan)

At query time, add inferred edges:
```text
if Symbol_A and Symbol_B appear in same Material:
  add edge Symbol_A -ASSOCIATED_WITH-> Symbol_B

if Symbol_A consistently precedes BodyState_X within 24h:
  add edge Symbol_A -TRIGGERS-> BodyState_X

if Symbol_A appears in dreams where Goal_Y is marked avoided:
  add edge Symbol_A -CORRELATES_WITH-> Goal_Y
```

These edges are computed from the bucket at query time. They connect **symbols to symbols**, not just records to records.

Query algorithm:
1. Build candidate nodes and edges.
2. Validate against `DEFAULT_GRAPH_QUERY_ALLOWLIST`.
3. Clamp `maxDepth` to allowlist max (initially `2`).
4. Clamp `limit` to allowlist max (initially `100`).
5. BFS/DFS from root nodes with direction/edge/node filters.
6. Deduplicate by id.
7. Return warnings for unmatched roots or clamped limits.

Failure behavior:
- Invalid type: raise `ValidationError`.
- Missing root: warning, not failure.
- Empty graph: empty result.
- Deleted records: excluded.

---

## Phase 3: Circulatio-Derived Context Builder ✅ IMPLEMENTED

**Status:** Complete. Files exist and tests pass.

Add a real native builder and make it the primary life-context source.

### Module

`src/circulatio/adapters/context_builder.py`

### New Component

```text
CirculatioLifeContextBuilder
- repository: CirculatioRepository
- default_window_days: int = 7

async build_life_context_snapshot(
    *,
    user_id: Id,
    window_start: str,
    window_end: str,
    material_id: Id | None = None,
) -> LifeContextSnapshot | None
```

Behavior:
- Calls repository native projection method.
- Returns `None` when no meaningful native signals exist.
- Always returns source `"circulatio-backend"` when it returns a snapshot.
- Never reads Hermes profile state.
- Never includes raw material text.
- Always passes output through `compact_life_context_snapshot()`.

### Native Context Derivation Algorithm

Inputs: symbols, symbol history, patterns, pattern history, practice sessions, materials, interpretation runs, stored feedback, suppressed hypotheses.

Output fields:

| Field | Derivation |
|-------|-----------|
| `windowStart` | requested window start |
| `windowEnd` | requested window end |
| `source` | `"circulatio-backend"` |
| `lifeEventRefs` | recent `charged_event` materials and important summarized reflections; summary/title/tags only |
| `moodSummary` | recent symbol valenceHistory tones and tone shifts |
| `energySummary` | practice outcome activation deltas |
| `focusSummary` | top recurring symbols plus active/recurring patterns by activation intensity |
| `mentalStateSummary` | safety dispositions, feedback trends, suppression/rejection patterns |
| `habitSummary` | material frequency and completed/skipped practice cadence |
| `notableChanges` | symbol history emergence/valence shifts, pattern status changes, new active patterns, completed practices |

Bounding rules:
- `lifeEventRefs`: max 5
- `notableChanges`: max 5
- Summary strings: concise enough for compaction
- Skip raw material text
- Exclude `exclude_material_id`

Meaningfulness rule: Return `None` if only `windowStart`, `windowEnd`, `source` would be present.

### Context Precedence

In `ContextAdapter`:
```text
1. Circulatio-derived snapshot from CirculatioLifeContextBuilder
2. Explicit provided lifeContextSnapshot from caller
3. Hermes profile life-OS snapshot, only if lifeOsWindow is provided
4. No lifeContextSnapshot
```

Do **not** merge Hermes fields into a native snapshot in this phase. `LifeContextSnapshot` has a single `source` field and no per-entry provenance.

### ContextAdapter Changes

Constructor:
```text
ContextAdapter(
    repository: GraphMemoryRepository,
    life_os: LifeOsReferenceAdapter | None = None,
    life_context_builder: LifeContextBuilder | None = None,
    default_life_context_window_days: int = 7,
)
```

Window resolution:
```text
if lifeOsWindow exists:
    window_start = lifeOsWindow.start
    window_end = lifeOsWindow.end
else:
    anchor = materialDate or now_iso()
    window_end = anchor
    window_start = anchor - default_life_context_window_days
```

Error behavior:
- Native builder failure: log warning, continue to fallback.
- Provided snapshot compaction failure: skip it.
- Hermes failure: existing behavior.
- Interpretation should not fail solely because context building failed.

### Service Wiring

Modify `CirculatioService._build_material_input()` to always use `ContextAdapter.build_material_input()`.

Before:
```text
if life_os_window:
    adapter path
else:
    direct repository path
```

After:
```text
always build BuildContextInput
always call ContextAdapter.build_material_input()
```

### Weekly Review Wiring

Update `build_circulation_summary_input_locked()`:
```text
native_snapshot = build_life_context_snapshot_locked(...)
if native_snapshot:
    result["lifeContextSnapshot"] = native_snapshot
elif overlapping stored context snapshots exist:
    result["lifeContextSnapshot"] = latest stored snapshot
```

### Source Enum Fix

Update `ContextSnapshotSource` in `domain/records.py`:
```text
"circulatio-backend"
"circulatio-life-os"
```

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

## Open Engineering Tasks

### 1. Practice Delivery

Phase 6 now keeps practice generation LLM-first while giving the runtime an explicit lifecycle:
- `PracticeEngine` is the deterministic boundary for consent, safety, lifecycle defaults, follow-up timing, and coarse outcome signals
- Practice recommendations remain LLM-shaped through `CirculatioCore.generate_practice()`
- Practice sessions persist explicit `recommended`, `accepted`, `skipped`, and `completed` states without introducing a deterministic symbolic router
- The fallback floor remains safety-blocked grounding or low-intensity journaling when the LLM path is unavailable

**Status:** Implemented. Further work should extend prompts and schemas, not add deterministic practice routing.

### 2. User Adaptation Profile

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

## File-By-File Impact

| File | Action |
|------|--------|
| `src/circulatio/domain/memory.py` | **New.** Phase 1 typed scaffolding. |
| `src/circulatio/domain/graph.py` | **Modify.** Add EvidenceItem, SUMMARIZES, query/result types, allowlist. |
| `src/circulatio/domain/records.py` | **Modify.** Add circulatio-backend and circulatio-life-os to ContextSnapshotSource. |
| `src/circulatio/adapters/context_builder.py` | **New.** CirculatioLifeContextBuilder. |
| `src/circulatio/adapters/context_adapter.py` | **Modify.** Add builder injection, precedence, window resolution. |
| `src/circulatio/adapters/__init__.py` | **Modify.** Export CirculatioLifeContextBuilder and LifeContextBuilder. |
| `src/circulatio/domain/feedback.py` | **New.** Durable interaction-feedback records for interpretation/practice feedback. |
| `src/circulatio/application/circulatio_service.py` | **Modify.** Unify _build_material_input() to always use ContextAdapter. |
| `src/circulatio/repositories/circulatio_repository.py` | **Modify.** Add abstract methods for memory kernel, graph query, life context. |
| `src/circulatio/repositories/in_memory_projections.py` | **Modify.** Add build_memory_kernel_snapshot_locked, query_graph_locked, build_life_context_snapshot_locked. |
| `src/circulatio/repositories/in_memory_circulatio_repository.py` | **Modify.** Implement three new abstract methods. |
| `src/circulatio/repositories/hermes_profile_circulatio_repository.py` | **Modify.** Implement three new abstract methods. |
| `src/circulatio/hermes/runtime.py` | **Modify.** Wire CirculatioLifeContextBuilder into both runtime builders. |
| `src/circulatio/hermes/atropos_envs.py` | **New.** Bounded Hermes-side communication/practice env builders plus reward helpers. |
| `tests/test_context_builder.py` | **New.** Tests for native context derivation and precedence. |
| `tests/test_memory_graph_scaffolding.py` | **New.** Tests for memory kernel and graph query. |
| `tests/test_circulatio_service.py` | **Modify.** Update service tests for unified context path. |

---

## Implementation Order

1. Add Phase 1 domain memory types (`domain/memory.py`).
2. Add Phase 2 graph query types (`domain/graph.py`).
3. Fix context source literals (`domain/records.py`).
4. Add repository abstract methods and in-memory projection helpers atomically.
5. Add `CirculatioLifeContextBuilder` (`adapters/context_builder.py`).
6. Update `ContextAdapter` precedence.
7. Unify `CirculatioService._build_material_input()`.
8. Wire runtime builders.
9. Update weekly review context projection.
10. Add Phase 1-2 tests.
11. Update service tests.
12. Add documentation.
13. Final validation: run full test suite, confirm no Kora-specific names, no vector/graph DB deps.

---

## Risks And Migration

### Persistence
No storage migration required if memory-kernel and graph outputs remain derived projections.

New `ContextSnapshot` records may contain `source: "circulatio-backend"` or `"circulatio-life-os"`. Existing records remain valid.

### Abstract Method Risk
Adding methods to `CirculatioRepository` is a breaking internal interface change. Must land atomically with all implementations.

### Context Behavior Change
After Phase 3:
```text
lifeOsWindow + native records → circulatio-backend snapshot
lifeOsWindow + no native records → hermes-life-os fallback
no lifeOsWindow + native records → circulatio-backend snapshot
no lifeOsWindow + no native records → no lifeContextSnapshot
```

### Privacy Risk
Native context builder must never summarize from raw `MaterialRecord.text`. Use only summary, title, tags, and metadata.

---

## Implemented Runtime Direction (4–7)

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
