# Circulatio Individuation-OS Audit Report
**Auditor:** individuation-os audit agent  
**Date:** 2026-04-21  
**Scope:** Post-workstreams audit (discovery digest, three-layer method-state, host/runtime behavior improvements)  
**Assumption:** Workstreams 1–3 (discovery, method-state architecture, host/runtime behavior) are complete.

---

## 1. Executive Verdict

### Is the current implementation coherent?
**Partially coherent — with significant fragmentation below the surface.**

The system presents a coherent *interface*: materials go in, context is built, LLM interprets, proposals are gated, approved records feed back into context. The loop *looks* closed. But under inspection, several of the deepest layers are **write-only or prompt-only** — they exist in records and docs but do not actually change runtime behavior.

### What is strongest?
- **Approval-gated write architecture** is real and disciplined. Proposals flow from LLM → pending → user approve/reject → durable record. This is not theater.
- **Context adapter pipeline** (`ContextAdapter` + `CirculatioLifeContextBuilder` + `MethodContextBuilder`) correctly assembles multi-layer snapshots from native records. The LLM receives a rich, longitudinal context.
- **Amplification prompt loop is fully closed.** Answer → `PersonalAmplificationRecord` → future `MethodContextSnapshot`. This is the one place where a secondary question reliably produces typed, durable, feedback-loop output.
- **Safety backstop** is minimal, deterministic, and respected — exactly as designed.

### What is still fragmented?
- **Containment/grounding records are stored but never read by the runtime** that decides "go deeper or ground now." Five overlapping fields across four record types encode the same semantic idea with no canonical fusion.
- **Discovery is a memory inventory, not a method-state read surface.** It omits `MethodContextSnapshot`, adaptation profile, goals, practices, journeys, threshold processes, and living-myth context — the very layers that would make it a "soul OS" digest rather than a symbolic dashboard.
- **Personalization is mostly theater.** `explicitPreferences` is always `{}`. All tone, depth, and questioning instructions are hardcoded. The 20+ interaction implicit learning affects rhythm cadence and practice modality hints, but *never* the interpretation prompt itself.
- **Coach/witness is rhetorical, not behavioral.** `get_witness_state()` is a data fetch. There is no witness protocol, no coaching state machine, no containment-aware response shaping.
- **Typology proposal plumbing is broken.** The LLM cannot actually propose new typology lenses through interpretation because the proposal builder lacks a branch for it.
- **Clarifying questions have no return path.** A question is emitted, the host asks it, the answer re-enters as untyped generic material with no linkage to the original question.

---

## 2. Top Findings (Prioritized)

| # | Finding | Severity | Layer |
|---|---------|----------|-------|
| 1 | **Containment records are write-only w.r.t. runtime depth decisions.** `DepthReadiness` + `MethodGate` are ephemeral per-call; they never fuse with stored `RealityAnchorSummary`, `SymbolicWellbeingSnapshot`, `ThresholdProcessRecord`, or `SelfOrientationSnapshot`. | **Critical** | Runtime |
| 2 | **Discovery omits the deepest layers.** No `MethodContextSnapshot`, no adaptation, no goals/practices/journeys, no threshold/individuation/living-myth context. It is a graph/memory dashboard, not a method-state digest. | **Critical** | Read surface |
| 3 | **Personalization stops at the interpretation prompt boundary.** `explicitPreferences` is always empty. Tone, depth, questioning style are hardcoded. The adaptation engine tracks 20+ samples but the interpretation workflow never reads them. | **High** | Runtime / Prompt |
| 4 | **Coach/witness behavior is not implemented.** It exists as prompt phrasing and README copy. No state machine, no containment-aware response shaping, no coach protocol. | **High** | Behavioral |
| 5 | **Typology lens creation from interpretation is broken.** `store_typology_lens` is listed in supported actions but `build_proposals_from_llm()` has no branch for it. Schema omits `typologyAssessment`. Options `enableTypology`/`maxTypologyHypotheses` are dead flags. | **High** | Core / Mapping |
| 6 | **Clarifying question loop is broken.** No answer endpoint, no `clarificationIntent`/`captureTargets`, no automatic typed capture routing. Answers become standalone untyped materials. | **High** | Method-state connector |
| 7 | **Goals and tensions are side records, not woven into synthesis.** Present in `MethodContextSnapshot` as "tentative co-occurrence" prompt instruction only. No deterministic steering. No central summary ties goals + tensions + practices + patterns. | **Medium** | Synthesis |
| 8 | **Practices are generic LLM outputs, not one-sidedness balancers.** No prompt or engine logic connects conscious attitude / compensation / one-sidedness to practice selection. | **Medium** | Practice engine |
| 9 | **Five overlapping grounding fields with no canonical normalization.** `groundingRecommendation`, `groundingStatus`, `invitationReadiness`, `containmentNeed`, `groundingCapacity` all encode the same idea. | **Medium** | Domain model |
| 10 | **Three deferred packet types are docs-only.** `TopicContextPacket`, `ThresholdPacket`, `RelationalFieldPacket` appear in `ROADMAP.md` but have no implementation. | **Low** | Missing surface |

---

## 3. Centralization Map

| Concern | What exists | What should be canonical | Filepath(s) |
|---------|-------------|-------------------------|-------------|
| **Containment** | `RealityAnchorSummary`, `ThresholdProcessRecord`, `NuminousEncounterRecord`, `SymbolicWellbeingSnapshot` | A single **query-time `PsycheReadiness` projection** computed from latest approved records + fused with `SafetyDisposition` | `src/circulatio/core/containment_projection.py` (new) |
| **Grounding** | `groundingRecommendation`, `groundingStatus`, `groundingCapacity`, `containmentNeed` | Normalize to one enum (`steady / strained / grounding_first / unknown`) inside `PsycheReadiness` | `src/circulatio/domain/types.py` |
| **Ego strength** | `SelfOrientationSnapshot.egoRelation` | Include in `PsycheReadiness` as `egoStance` | `src/circulatio/repositories/in_memory_projection_contexts.py` |
| **Relational isolation** | `RelationalSceneRecord`, `ProjectionHypothesis` | Keep as derived records, but add a **relational spaciousness signal** to `PsycheReadiness` (e.g., `relationalPressure: none / moderate / high`) | `src/circulatio/core/containment_projection.py` |
| **One-sidedness** | `ConsciousAttitudeSnapshot`, `PsychicOppositionRecord` | `ConsciousAttitudeSnapshot` should feed a **compensation vector** into `MethodContextSnapshot`, and the practice prompt should explicitly ask the LLM to balance it | `src/circulatio/llm/prompt_builder.py` |
| **Typology / function balance** | `TypologyLensRecord`, `TypologyAssessment` (transient) | Fix proposal builder so `TypologyLensRecord` is actually creatable from interpretation. Keep it **soft/contextual only** — no deterministic routing. | `src/circulatio/core/interpretation_mapping.py` |
| **Goal tension** | `GoalRecord`, `GoalTensionRecord` | Add an explicit **goal-tension section** to `AnalysisPacket` and `DiscoveryResult`. Surface active tensions with their linked symbols and practices. | `src/circulatio/domain/living_myth.py`, `src/circulatio/application/circulatio_service.py` |
| **Practice adaptation** | `PracticeAdaptationHints`, `AdaptationEngine` | Thread `explicitPreferences` into interpretation and practice prompts. Add `UserWorkingMode` (soma-first, image-first, etc.) | `src/circulatio/llm/prompt_builder.py`, `src/circulatio/core/adaptation_engine.py` |
| **Symbolic wellbeing** | `SymbolicWellbeingSnapshot` (orphaned) | Build it from living-myth reviews AND feed it into `PsycheReadiness`. Make it a first-class readable summary, not just a proposal candidate. | `src/circulatio/core/circulatio_core.py`, `src/circulatio/repositories/in_memory_projection_contexts.py` |

---

## 4. Personalization Audit

### Where personalization is real
| Mechanism | Effect | Evidence |
|-----------|--------|----------|
| `AdaptationEngine` implicit learning (20+ samples) | Adjusts `minimumHoursBetweenBriefs`, `dismissedTriggerCooldownHours`, `preferredModalities`, `avoidedModalities` | `src/circulatio/core/adaptation_engine.py:51` |
| `PracticeEngine` duration clamping | Hard-enforces `maxDurationMinutes` from adaptation hints | `src/circulatio/core/practice_engine.py:118` |
| `ProactiveEngine` cadence filtering | Suppresses briefs based on engagement rate | `src/circulatio/core/proactive_engine.py:84` |
| Consent preferences | Deterministically blocks moves (e.g., `active_imagination` if consent revoked) | `src/circulatio/core/practice_engine.py:103` |

### Where personalization is superficial
| Claim | Reality |
|-------|---------|
| "Explicit profile first, implicit learning after 20+ interactions" | `explicitPreferences` is initialized as `{}` and **never written to** by any service API. The user has no way to set depth preference, tone, questioning style, or working modality. |
| "Adaptation profile affects interpretation" | `interpret_material()` never consults the adaptation profile. It is passed into practice and rhythmic brief inputs only. |
| "Questioning style adapts to the user" | All questioning instructions are hardcoded in `prompt_builder.py:64`. No variation for soma-first, feeling-first, image-first, reflective, or avoidant users. |
| "Interpretation depth preference" | Listed in `ENGINEERING_GUIDE.md:629` but **no field, API, or engine logic exists** for it. |
| "Typology informs runtime" | `TypologyLensRecord` is stored and fed to LLM as context, but zero deterministic behavior changes. By design, but also by broken proposal path. |

### What to centralize next
1. **`CirculatioService.set_adaptation_preference(scope, payload)`** — validated write path for `explicitPreferences.practice.*`, `explicitPreferences.rhythm.*`, `explicitPreferences.interpretation.*`, `explicitPreferences.communication.*`.
2. **Inject explicit preferences into `build_interpretation_messages`** — add an `instructions` block that overrides hardcoded defaults when preferences are set.
3. **`UserWorkingMode` record** — distinct from Jungian typology, captures `preferredModalities: [soma, image, feeling, reflection]` and `pacingStyle: [gentle, direct, spacious]`.

---

## 5. Goals / Practice / Coach Audit

### Are goals and tensions integrated into symbolic interpretation?
**No — they are side records with context presence only.**

- Goals and tensions appear in `MethodContextSnapshot` and are fed to the LLM.
- Prompt instruction treats them as **"tentative co-occurrence unless the supplied context already confirms them."**
- `build_proposals_from_llm()` can emit `upsert_goal_tension`, which is good.
- But there is **no deterministic synthesis** that connects goal tension X + recurring symbol Y + practice Z = emergent direction W.
- `AnalysisPacket` omits an explicit goals/tensions section.

### Are practices balancing one-sidedness?
**No.**

- Practice prompt asks for "one bounded practice recommendation" with generic constraints.
- No mention of compensation, conscious attitude, or one-sidedness in prompt or engine.
- `PracticeEngine` applies safety/consent/duration rules only.
- `INTERPRETATION_ENGINE_SPEC.md` discusses one-sidedness, but **no code or prompt connects it to practice selection.**

### Is coach/witness behavior real?
**No — it is rhetorical framing in prompts and docs.**

- No `Coach` class, no witness state machine, no coaching protocol.
- `get_witness_state()` (`circulatio_service.py:407`) returns a raw `MethodContextSnapshot` — a data fetch, not a witnessing interaction.
- "Witness" language appears in `build_practice_messages` and `build_rhythmic_brief_messages` as stylistic instructions.
- There is **no runtime behavior that says** "because the user's containment is strained, I will offer grounding instead of depth" based on stored records.

### What is still missing?
1. **Coach/witness response layer** — a lightweight post-interpretation filter that modulates user-facing response based on `PsycheReadiness` (see Centralization Map).
2. **Goal-tension synthesis** — explicit sections in `AnalysisPacket`, `DiscoveryResult`, and `CirculationSummaryResult` that surface active tensions with their symbolic and somatic correlates.
3. **One-sidedness-aware practice prompt** — modify `build_practice_messages` to include `consciousAttitude.compensationVector` and instruct the LLM to suggest practices that balance the current stance.
4. **Practice outcome → goal tension feedback** — when a practice is completed, check if it shifted a goal tension status and surface that in the next review.

---

## 6. Discovery Audit

### Is `circulatio_discovery` useful as the main read surface?
**Useful as a memory inventory. Insufficient as a primary read surface.**

### What it exposes (cleanly)
- Recurring symbols from dashboard + memory kernel
- Dream/body/event graph links and triad clusters
- Ripe-to-revisit candidates (multi-source ranking)
- Held-for-now recent materials

### What it omits (critically)
| Omitted layer | Why it matters for depth psychology |
|---------------|-------------------------------------|
| `MethodContextSnapshot` | "Where am I in my process?" |
| `activeGoals` / `goalTensions` | "What am I trying to become?" |
| `recentPracticeSessions` / `practiceOutcomes` | "What have I been doing with this material?" |
| `activeJourneys` | "What thread does this belong to?" |
| `thresholdProcesses` / `realityAnchors` | "Can I go deeper right now?" |
| `livingMythContext` / `latestSymbolicWellbeing` | "What is the narrative arc of my symbolic life?" |
| `adaptationProfile` | "How do I best receive this?" |
| `pendingAmplificationPrompts` | "What questions am I still answering?" |

### What additional read surfaces should feed discovery?
1. **`MethodContextSnapshot`** — at minimum, `consciousAttitude`, `recentBodyStates`, `activeGoals`, `goalTensions`, `thresholdProcesses`, `realityAnchors`, `activeJourneys`, `pendingAmplificationPrompts`.
2. **`Adaptation profile`** — bias ranking toward user's preferred modalities; suppress recently skipped themes.
3. **`Weekly review summaries`** — surfacing what the system already synthesized so discovery does not just repeat raw memory.
4. **`Proactive briefs / rhythmic invitations`** — show pending invitations so the host can coordinate.

### Verdict
Discovery is currently a **bounded, deterministic, read-only memory browser** — which is defensible as a fallback. But if it is intended as the primary "show me what is alive" surface, it must ingest `MethodContextSnapshot` or be demoted in favor of `alive_today` and `journey_page`, which already use the full context.

**Recommendation:** Either (a) elevate discovery to a method-state-aware digest by merging it with `get_witness_state()` and adding goal/practice/journey/threshold sections, or (b) clearly document that discovery is the *inventory* surface and `alive_today`/`journey_page` are the *method-state* surfaces.

---

## 7. File-Level Recommendations

### Critical fixes

| File | Change | Rationale |
|------|--------|-----------|
| `src/circulatio/core/interpretation_mapping.py` | Add `store_typology_lens` branch in `build_proposals_from_llm()` (~line 504–690) | Typology lenses cannot be created from interpretation runs |
| `src/circulatio/llm/json_schema.py` | Add `typologyAssessment` to `INTERPRETATION_OUTPUT_SCHEMA` | LLM is not structurally bound to return typology data |
| `src/circulatio/core/circulatio_core.py` | Fuse stored containment records into `DepthReadiness` / `MethodGate` assessment, or create `PsycheReadiness` projection | Containment records are write-only w.r.t. runtime decisions |
| `src/circulatio/application/circulatio_service.py` | Add `answer_clarifying_question()` endpoint with `clarificationIntent`/`captureTargets` routing | Broken clarifying-question loop |
| `src/circulatio/application/circulatio_service.py` | Add `set_adaptation_preference()` API to write `explicitPreferences` | Personalization theater: preferences bucket is always empty |

### Medium additions

| File | Change | Rationale |
|------|--------|-----------|
| `src/circulatio/llm/prompt_builder.py` | Inject `explicitPreferences.interpretation.depthPreference` and `communication.questioningStyle` into interpretation instructions | Hardcoded prompts ignore user preference |
| `src/circulatio/llm/prompt_builder.py` | Add `consciousAttitude.compensationVector` to practice prompt; instruct LLM to balance one-sidedness | Practices are generic, not compensation-targeted |
| `src/circulatio/application/circulatio_service.py` | Merge `MethodContextSnapshot` into `generate_discovery()`; add goal/practice/journey/threshold sections | Discovery omits deepest layers |
| `src/circulatio/domain/living_myth.py` / `types.py` | Add `activeGoals` and `goalTensions` sections to `AnalysisPacket` | Goals are side records in synthesis |
| `src/circulatio/core/adaptation_engine.py` | Add `UserWorkingMode` derivation (soma-first, image-first, etc.) from practice outcomes and material types | "How user best works" is unmodeled |
| `src/circulatio/core/proactive_engine.py` | Actually use `adaptation_profile` in seed selection (currently discarded at line 36) | Dead parameter |
| `src/circulatio/domain/types.py` | Normalize 5 overlapping grounding fields into one enum | Duplicate ontology |

### Cleanup / dead weight removal

| File | Change | Rationale |
|------|--------|-----------|
| `src/circulatio/domain/types.py` | Remove or wire `enableTypology` and `maxTypologyHypotheses` | Dead flags |
| `src/circulatio/repositories/in_memory_projection_summary.py` | Either inject `recentTypologySignals` into prompt or stop computing it | Dead data path |
| `src/circulatio/core/interpretation_mapping.py` | Add builder for `symbolic_wellbeing_snapshot` in `build_individuation_from_llm()`, or remove from `_SUPPORTED_MEMORY_WRITE_ACTIONS` | Orphaned record type |
| `docs/ROADMAP.md` | Remove or defer `TopicContextPacket`, `ThresholdPacket`, `RelationalFieldPacket` | Docs-only vaporware |

---

## 8. Quick Wins vs Deeper Changes

### Quick wins (high leverage, small change)
1. **Fix typology proposal builder** — add one `elif action == "store_typology_lens"` branch in `interpretation_mapping.py`. Also add `typologyAssessment` to JSON schema. (~20 lines)
2. **Wire `enableTypology` option** — read the flag in `circulatio_core.py` and pass it to prompt builder; if false, omit typology lens summaries from context. (~10 lines)
3. **Add `set_adaptation_preference()` service method** — write validated keys into `explicitPreferences`. Expose via Hermes plugin tool. (~50 lines)

### Medium changes (targeted additions)
1. **Build `PsycheReadiness` projection** — query-time canonical containment state from latest approved `RealityAnchorSummary`, `SymbolicWellbeingSnapshot`, `ThresholdProcessRecord`, `SelfOrientationSnapshot`. Fuse with `SafetyDisposition`. Feed into `MethodContextSnapshot` and `PracticeEngine`. (~150 lines)
2. **Merge `MethodContextSnapshot` into discovery** — add method-state sections to `DiscoveryResult` so it becomes a true method-aware digest. (~200 lines in service + types)
3. **Close clarifying-question loop** — new endpoint, `ClarifyingQuestionAnswer` record type, linkage to originating run, optional `captureTargets` for typed routing. (~150 lines)
4. **Add goal-tension sections to `AnalysisPacket`** — surface active tensions with linked symbols and practices. (~50 lines)

### Deeper changes (only if justified)
1. **Implement a lightweight `WitnessEngine`** — post-LLM filter that modulates user-facing response based on `PsycheReadiness`. This is the difference between "witness as tone" and "witness as behavior." Justified if the system is meant to actually contain users through threshold processes rather than just store records about them.
2. **Refactor five grounding fields into one normalized enum** — touches `types.py`, `individuation.py`, `living_myth.py`, all repository projections, and mapping code. Justified only if the duplication causes actual bugs.
3. **Add `UserWorkingMode` as a first-class record** — distinct from typology, captures soma-first/image-first/feeling-first/reflective preferences. Requires new record, repository methods, service API, prompt injection, and adaptation derivation. Justified if personalization is meant to be real rather than tracked.

---

## 9. Test and Verification Gaps

### What is completely untested
| Area | What should be tested |
|------|----------------------|
| Typology | `build_typology_assessment_from_llm()` with signals/hypotheses; `apply_typology_proposal_locked()` create vs update; integration test that interpretation emits a typology proposal |
| Containment | Whether stored `RealityAnchorSummary` / `SymbolicWellbeingSnapshot` / `ThresholdProcessRecord` actually affect `PracticeEngine` or `CirculatioCore` depth decisions |
| Personalization | Whether `explicitPreferences` changes alter prompt output; whether `AdaptationEngine` 20+ sample threshold changes `preferredModalities` |
| Discovery | Whether `generate_discovery` includes method-state sections (after fix) |
| Clarifying questions | End-to-end: emit question → answer → typed capture → next interpretation sees the capture |
| Goal-tension integration | Whether `AnalysisPacket` includes goal-tension sections (after fix) |
| Coach/witness | Whether `get_witness_state` or any future witness engine modulates response based on containment |

### What is tested but could be stronger
| Area | Current test | Gap |
|------|--------------|-----|
| Practice engine | Consent fallback, method gate, duration cap, activation delta | Does not test one-sidedness-aware recommendation |
| Context builder | Life context and method context assembly | Does not test that all containment fields are present and correctly sourced |
| Safety gate | Regex-based screen | Does not test fusion with stored containment records |
| Hermes bridge | Plugin load, tool availability, journey rendering | Does not test `discovery` tool output shape or method-state inclusion |

### Recommended new test files
1. `tests/test_containment_projection.py` — `PsycheReadiness` query-time projection from approved records.
2. `tests/test_typology_proposals.py` — Typology assessment mapping, proposal emission, approval application.
3. `tests/test_adaptation_personalization.py` — Explicit preference write, implicit learning threshold, prompt injection.
4. `tests/test_clarifying_question_loop.py` — End-to-end clarifying question answer flow.

---

## Appendix: Duplicate / Overlapping Ontology Summary

| Semantic idea | Fields | Records |
|---------------|--------|---------|
| "How much depth can this psyche tolerate?" | `groundingRecommendation` (`clear_for_depth / pace_gently / grounding_first`) | `RealityAnchorSummary` |
| | `groundingStatus` (`steady / strained / unknown`) | `ThresholdProcessRecord` |
| | `invitationReadiness` (`not_now / ask / ready`) | `ThresholdProcessRecord` |
| | `containmentNeed` (`ordinary_reflection / pace_gently / grounding_first`) | `NuminousEncounterRecord` |
| | `groundingCapacity` (`steady / strained / unknown`) | `SymbolicWellbeingSnapshot` |
| | `egoRelation` (`aligned / conflicted / avoidant / curious / unknown`) | `SelfOrientationSnapshot` |

**All six fields are written to repository but only ONE (`invitationReadiness`) is read by runtime code.**

---

*End of audit report.*
