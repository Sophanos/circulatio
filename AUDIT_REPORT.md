# Circulatio Repo-Aware Discovery Audit

**Assumed complete:** `circulatio_discovery` digest, three-layer method-state architecture, host/runtime behavior improvements around questioning, routing, and pacing.

**Audit date:** 2026-04-21

---

## 1. Executive Verdict

### Is the current implementation coherent?

Partially. The backend is no longer a collection of isolated record types. The `MethodContextSnapshot` -> `MethodStateSummary` -> `RuntimeMethodStatePolicy` chain creates a genuine longitudinal spine for depth decisions. Safety gating, practice reconciliation, and proactive cadence are deterministic and consistent. The adaptation engine tracks real signals and injects hints into LLM prompts.

However, the system still behaves like **connected islands of good ideas** rather than a single symbolic organism. Several high-leverage connections are wired but not closed:

- **Method-state policy is computed and then ignored** by the clarification pipeline and method-state capture loop.
- **Goals and goal tensions exist** but do not shape interpretation or practice targeting.
- **Personalization is real for tone and modality** but stops short of closing the feedback-to-policy loop.
- **Discovery is deterministic and omits** the very method-state context that would make it useful for host routing.
- **Containment is represented four different ways** with no canonical runtime authority.

### What is strongest?

- `MethodContextSnapshot` / `MethodStateSummary` derivation from repository records is the best architectural achievement. It aggregates body states, conscious attitudes, reality anchors, threshold processes, relational scenes, and wellbeing into a single runtime snapshot.
- `PracticeEngine` reconciliation is clean: safety -> method gate -> consent -> hints -> fallback.
- The three-layer architecture (raw evidence -> derived summaries -> runtime decisions) is real and tested.

### What is still fragmented?

- The loop from `answer_clarification` -> `_route_clarification_answer` -> record creation is wired but untested and breaks on unstructured host input.
- `preferredClarificationTargets` from method-state policy are never consumed when forming questions.
- Goals are side records, not woven into interpretation or life context.
- Practices are safety-gated and preference-shaped, but not tension-targeted or body-aware.
- Feedback is counted, not auto-applied.
- Discovery misses method-state context entirely.

---

## 2. Top Findings (Prioritized)

| Priority | Finding | Leverage |
|----------|---------|----------|
| **P0** | `preferredClarificationTargets` computed by `derive_runtime_method_state_policy` are **never consumed** when the LLM generates a `clarificationPlan`. The policy steers nothing. | High: closes the method-state -> questioning loop. |
| **P0** | `answer_clarification` has **zero test coverage** and stalls on unstructured host input (no LLM fallback to extract payload from free text). | High: the primary user-response loop is untested and brittle. |
| **P0** | `process_method_state_response` does **not** consult method-state policy before applying capture candidates. A user in `grounding_only` mode can still be prompted to record a `threshold_process` or `numinous_encounter`. | High: containment policy is bypassed in the capture loop. |
| **P1** | Goals and goal tensions are in `MethodContextSnapshot` but **absent from `LifeContextSnapshot`**. Deterministic interpretation infrastructure ignores them. | High: makes goals side records instead of symbolic drivers. |
| **P1** | `PracticeEngine` is **blind to goal tensions and body states**. Practices are generic; no concept of "target the one-sidedness." | High: misses the core Jungian practice principle. |
| **P1** | Discovery is **deterministic** and omits `consciousAttitude`, `bodyStates`, `methodState`, and `journey_threads`. It is a memory/graph dashboard, not a method-state read surface. | High: host cannot use discovery to decide routing. |
| **P2** | Containment/grounding state exists in **four parallel representations** (`SafetyDisposition`, `RealityAnchorSummary`, `MethodStateSummary`, `RuntimeMethodStatePolicy`) with no invariant checking. | Medium: can produce contradictory depth decisions. |
| **P2** | `derive_runtime_method_state_policy` defaults to **permissive `standard` depth** when snapshot is missing/stale. | Medium: silent fallback to full depth when containment data is absent. |
| **P2** | Feedback records are aggregated into stats but **never auto-applied** to learned policy. The loop is open. | Medium: personalization stops at counting. |
| **P3** | `TypologyLensRecord` is full CRUD but **never drives runtime behavior**. | Low: dead-weight storage. |
| **P3** | `numinous_encounter`, `aesthetic_resonance`, `inner_outer_correspondence`, `archetypal_pattern` are schema-complete but **zero downstream consumption**. | Low: unused ontology. |

---

## 3. Centralization Map

| Concern | What Should Be Canonical | Current State |
|---------|--------------------------|---------------|
| **Containment** | `MethodStateSummary.containment` (derived from reality anchors + body states + wellbeing) | Fragmented across `RealityAnchorSummary`, `ThresholdProcess`, `NuminousEncounter`, `SymbolicWellbeingSnapshot` |
| **Grounding** | `MethodStateSummary.containment.groundingNeed` | Duplicated as `SafetyDisposition.depthWorkAllowed`, `RealityAnchorSummary.groundingRecommendation`, `RuntimeMethodStatePolicy.depthLevel` |
| **Ego strength** | `MethodStateSummary.egoCapacity` | Derived correctly but not tested exhaustively; not consumed by capture loop |
| **Relational isolation** | `MethodStateSummary.relationalField` (derived from reality anchors + wellbeing + scenes) | Fragmented across `RealityAnchorSummary.relationshipContact`, `SymbolicWellbeingSnapshot.relationalSpaciousness`, `PsychicOppositionDetails.pressureTone` |
| **One-sidedness** | `GoalTensionRecord` + `PatternRecord` + `ConsciousAttitudeSnapshot` | Not centralized; no summary weaves these together for practice targeting |
| **Typology/function balance** | Ephemeral `TypologyAssessment` inside interpretation result only | `TypologyLensRecord` durable CRUD is dead weight; should be dropped or merged into adaptation profile |
| **Goal tension** | `GoalTensionRecord` as first-class input to `LifeContextSnapshot` and `PracticeEngine` | Present in `MethodContextSnapshot` but ignored by interpretation and practice |
| **Practice adaptation** | `PracticeEngine` should accept `goal_tensions` and `body_states` | Currently only safety/method_gate/consent/hints |
| **Symbolic wellbeing** | `living_myth_record` with `recordType == "symbolic_wellbeing_snapshot"` | Real if persisted, but review-result field alone does nothing |

---

## 4. Personalization Audit

### Where personalization is real

- `AdaptationEngine` derives `CommunicationHints` (tone, questioningStyle, symbolicDensity), `InterpretationHints` (depthPreference, modalityBias), `PracticeHints` (preferredModalities, avoidedModalities, maxDurationMinutes, recentSkips/Completions), and `RhythmCadenceHints` (cooldowns, quietHours, engagement-based adjustments).
- These hints are injected into LLM prompts via `prompt_builder` and `prompt_fragments`.
- Practice duration is clamped to explicit preference.
- Recent skips are surfaced to avoid repeating rejected practice types.

### Where personalization is superficial

- **Closed-loop learning is open:** `interaction_feedback_interpretation` and `interaction_feedback_practice` events increment counters in `interactionFeedbackStats`, but no method auto-derives policy updates from them. The host is expected to call `apply_learned_policy_update` manually.
- **Ego strength trajectory, typology indicators, and amplification pack affinity** are documented in `ENGINEERING_GUIDE.md` but absent from `UserAdaptationProfileRecord`.
- **Prompt hints are weak:** `RUNTIME_HINT_POLICY` tells the LLM to "treat them as guidance" but does not include concrete behavioral rules (e.g., "when `questioningStyle` is `soma_first`, open with a body sensation question").
- **Method-state policy personalization is ignored:** `preferredClarificationTargets` derived from user history are computed and discarded.

### What to centralize next

- Add `derive_learned_policy_from_stats` to `AdaptationEngine` to close the feedback loop without host intervention.
- Merge typology signals into `learnedSignals` or drop durable `TypologyLensRecord` storage.
- Add explicit prompt fragment rules per `questioningStyle` and `modalityBias` value.

---

## 5. Goals / Practice / Coach Audit

### Are goals truly integrated into symbolic method?

No. Goals and tensions are stored, projected into `MethodContextSnapshot`, and visible to the LLM, but:
- `LifeContextSnapshot` omits them entirely.
- Deterministic interpretation mapping (`build_life_context_links`, `build_symbol_mentions`, `build_observations`) never references goals.
- `PracticeEngine` does not accept goal tensions or body states as input.
- There is no derived summary weaving `goals + tensions + practices + outcomes + patterns` together.

### Are practices balancing one-sidedness?

No. `PracticeEngine.reconcile_llm_practice` gates on safety, method gate, consent, and soft adaptation hints. It has no concept of "target the user's one-sidedness" or "address active tension." The prompt fragments do not instruct the LLM to do so either.

### Is coach/witness behavior real?

No. `get_witness_state` returns a generic `MethodContextSnapshot`. There is no `WitnessState` record type, no witness-specific state machine, and no witness engine. The "witness" behavior is entirely prompt copy (`WITNESS_METHOD_POLICY`, `PRACTICE_STYLE_POLICY`).

### What is missing

- `GoalTensionRecord` must enter `LifeContextSnapshot`.
- `PracticeEngine` must accept `goal_tensions` and `body_states`, and annotate practice plans with `targetedTensionId` / `targetedBodyStateId`.
- A new prompt fragment (`GOAL_TENSION_PRACTICE_POLICY`) must instruct the LLM to frame practices in relation to active tensions and compensatory patterns.

---

## 6. Discovery Audit

### Is the discovery surface sufficient?

No. `circulatio_discovery` is a deterministic, read-only digest built from `DashboardSummary`, `MemoryKernelSnapshot`, `MethodContextSnapshot`, and `GraphQueryResult`. It exposes four fixed sections:

- `recurring` — symbols/patterns with recurrence > 1
- `dream_body_event_links` — graph triads crossing categories
- `ripe_to_revisit` — candidates with multi-source presence or graph degree > 1
- `held_for_now` — recent materials not consumed above

### What it misses

- `consciousAttitude` — never added as candidates
- `bodyStates` — only surface indirectly via graph triads
- `methodState` (`containment`, `egoCapacity`, `relationalField`) — completely ignored
- `journey_threads` — no dedicated section
- `review/analysis_packet` — appear only as generic memory items
- **No connection to proactive brief generation** — `ProactiveEngine` and `generate_journey_page` query their own data; discovery is never reused.

### What additional read surfaces or summaries should feed it

- `consciousAttitude` and `recentBodyStates` from `MethodContextSnapshot`
- `methodState.containment` and `methodState.egoCapacity` as a new `containment_and_grounding` section
- `journey_threads` as a dedicated section
- `living_myth_reviews` and `analysis_packets` as explicit sections, not generic memory items

### Should discovery be LLM-first?

Not necessarily, but it should be method-state-aware. The host needs discovery to answer "what is happening in this psyche right now?" not just "what symbols recurred?"

---

## 7. File-Level Recommendations

| File | Change | Priority |
|------|--------|----------|
| `src/circulatio/core/circulatio_core.py` | Consume `preferredClarificationTargets` from `derive_runtime_method_state_policy` when building `clarificationPlan`. Steer `captureTarget` and `expectedTargets` to match policy. | P0 |
| `src/circulatio/application/circulatio_service.py` | In `process_method_state_response`, call `derive_runtime_method_state_policy` and withhold/downgrade capture candidates when policy indicates `grounding_only` or fragile ego capacity. | P0 |
| `src/circulatio/application/circulatio_service.py` | In `_route_clarification_answer`, add an LLM fallback path (or host contract) to extract structured payload from free-text `answerText` when `answerPayload` is missing. | P0 |
| `src/circulatio/repositories/in_memory_projection_contexts.py` | Extend `build_life_context_snapshot_locked` to include `_project_goal_summary` and `_project_goal_tension_summary`. | P1 |
| `src/circulatio/core/practice_engine.py` | Add `goal_tensions` and `body_states` parameters to `reconcile_llm_practice`. Annotate plan with `targetedTensionId` / `targetedBodyStateId` when active. | P1 |
| `src/circulatio/application/circulatio_service.py` | Extend `_add_method_context_discovery_candidates` to ingest `consciousAttitude`, `recentBodyStates`, and `methodState.containment/egoCapacity`. Add new discovery sections. | P1 |
| `src/circulatio/core/method_state_policy.py` | Change empty/missing snapshot default from `standard` to `gentle` with `blockedMoves: ["active_imagination"]`. | P2 |
| `src/circulatio/repositories/in_memory_projection_method_state.py` | Give `realityAnchors.groundingRecommendation` precedence over older `symbolicWellbeing` and body-state data in `_derive_containment_grounding_summary`. | P2 |
| `src/circulatio/core/adaptation_engine.py` | Add `derive_learned_policy_from_stats` to auto-propose policy updates from `interactionFeedbackStats`, `practiceStats`, and `rhythmStats`. | P2 |
| `src/circulatio/llm/prompt_fragments.py` | Add value-specific behavioral rules per `questioningStyle` and `modalityBias`. Add `GOAL_TENSION_PRACTICE_POLICY`. | P2 |
| `src/circulatio/repositories/in_memory_projections.py` | Remove duplicate `build_dashboard_summary_locked` (line ~1667); delegate to `in_memory_projection_contexts.py` or move to `in_memory_projection_shared.py`. | P3 |
| `src/circulatio/domain/typology.py` | Either drop durable `TypologyLensRecord` CRUD and keep typology ephemeral, or merge active lens summaries into `UserAdaptationProfileRecord.learnedSignals`. | P3 |

---

## 8. Quick Wins vs Deeper Changes

### Quick wins (1-3 small changes, high leverage)

1. **Consume `preferredClarificationTargets` in the interpretation pipeline.**
   - File: `src/circulatio/core/circulatio_core.py` (or `interpretation_mapping.py`)
   - Effort: ~10 lines. When `clarificationPlan` is built, override `captureTarget` if it conflicts with policy-preferred targets.
   - Impact: Closes the method-state -> questioning loop for the first time.

2. **Add `answer_clarification` unit tests.**
   - File: `tests/test_circulatio_service.py`
   - Effort: ~100 lines. Cover each supported capture target, `needs_review` fallback, and dead-end `interpretation_preference` / `typology_feedback` targets.
   - Impact: The most under-tested surface in the user loop becomes guarded.

3. **Harden empty-snapshot default in `method_state_policy.py`.**
   - File: `src/circulatio/core/method_state_policy.py`
   - Effort: ~5 lines. Return `gentle` + `blockedMoves: ["active_imagination"]` instead of `standard`.
   - Impact: Removes silent permissive fallback when containment data is stale or missing.

### Medium changes (targeted additions)

1. **Make `process_method_state_response` policy-aware.**
   - File: `src/circulatio/application/circulatio_service.py`
   - Effort: ~30 lines. Consult `derive_runtime_method_state_policy` before applying candidates.
   - Impact: Capture loop respects containment state.

2. **Add goals to `LifeContextSnapshot`.**
   - File: `src/circulatio/repositories/in_memory_projection_contexts.py`
   - Effort: ~40 lines. New `_project_goal_summary` and `_project_goal_tension_summary` helpers.
   - Impact: Goals become first-class symbolic material for interpretation.

3. **Make `PracticeEngine` tension-aware and body-aware.**
   - File: `src/circulatio/core/practice_engine.py`
   - Effort: ~50 lines. Add parameters, annotation logic, and adaptation notes.
   - Impact: Practices shift from generic to symbolic-targeting.

4. **Enrich discovery with method-state context.**
   - File: `src/circulatio/application/circulatio_service.py`
   - Effort: ~60 lines. Extend `_add_method_context_discovery_candidates` and `DiscoverySectionKey`.
   - Impact: Discovery becomes useful for host routing decisions.

### Deeper changes (only if justified)

1. **Canonical containment record.**
   - Merge redundant grounding fields from `RealityAnchorSummary`, `ThresholdProcess`, `NuminousEncounter`, and `SymbolicWellbeingSnapshot` into a single write path that feeds `MethodStateSummary.containment`.
   - Justification: Only if the current four-layer stack produces observable contradictions in production.

2. **Auto-policy derivation from feedback stats.**
   - Add `derive_learned_policy_from_stats` to `AdaptationEngine` and wire it into `CirculatioService` after feedback events.
   - Justification: Only if the host consistently fails to call `apply_learned_policy_update` and personalization stagnates.

3. **Dedicated `WitnessState` record type.**
   - Split witness behavior out from generic `MethodContextSnapshot` into a purpose-built summary with its own derivation rules and lifecycle.
   - Justification: Only if the host genuinely needs a distinct witness surface separate from method context.

---

## 9. Test and Verification Gaps

| Gap | What Should Be Tested | Suggested Test File |
|-----|----------------------|---------------------|
| **Clarification routing** | `answer_clarification` for each capture target; `needs_review` when `answerPayload` missing; dead-end behavior for `interpretation_preference` / `typology_feedback` | `tests/test_circulatio_service.py` |
| **Method-state policy gating** | `process_method_state_response` respects `grounding_only` policy; rejects `threshold_process` capture when ego capacity is fragile | `tests/test_circulatio_service.py` |
| **Method-state policy matrix** | Extract pure helper from `derive_runtime_method_state_policy` and test combinatoric inputs (containment x egoCapacity x relationalField x compensation) | `tests/test_method_state_policy.py` (new) |
| **Goal integration** | Store goals/tensions, run interpretation, assert they appear in `LifeContextSnapshot` and affect practice recommendation | `tests/test_context_builder.py` |
| **Discovery idempotency** | Assert repository material/run counts unchanged before/after `generate_discovery` | `tests/test_circulatio_service.py` |
| **Discovery method-state** | Store `consciousAttitude`, `bodyState`, `thresholdProcess`; assert they appear in discovery sections | `tests/test_circulatio_service.py` |
| **Practice tension-targeting** | Store active `goalTension` and `bodyState`; assert `PracticeEngine` annotates plan with `targetedTensionId` | `tests/test_practice_engine.py` |
| **Feedback closed loop** | Record 5x `too_long` practice feedback; assert auto-derived policy lowers `maxDurationMinutes` | `tests/test_circulatio_service.py` |
| **Typology inertness** | Store `TypologyLensRecord`; assert it does not affect `PracticeEngine` or `method_gate` (or drop it) | `tests/test_circulatio_core.py` |
| **Containment precedence** | Store `realityAnchors.groundingRecommendation = "grounding_first"` and older wellbeing snapshot; assert policy returns `grounding_only` | `tests/test_method_state_policy.py` (new) |
| **Duplicate dashboard** | Assert `in_memory_projections.py` and `in_memory_projection_contexts.py` do not diverge | `tests/test_memory_graph_scaffolding.py` |

---

## Closing Note

The Circulatio backend has moved from **scattered records** to **derived summaries** successfully. The critical gap is now the **runtime decision layer**: summaries exist, but the system does not consistently act on them. The highest-leverage work is not adding new ontology or new LLM paths. It is closing the loops that are already wired: consume the policy when forming questions, respect the policy when capturing answers, weave goals into life context, and make practices tension-aware. Do this, and the islands become an organism.
