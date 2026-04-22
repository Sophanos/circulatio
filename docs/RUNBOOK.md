# Circulatio Runbook

Quick reference for safety, evidence, typology, and demos. Read `ENGINEERING_GUIDE.md` for implementation details and `INTERPRETATION_ENGINE_SPEC.md` for Jungian method.

**Implementation status (April 2026):** The current runtime includes the bounded read-only `discovery` digest, read-mostly journey pages, autonomous low-risk journey-container writes through Hermes tool exposure, threshold review, living myth review, bounded analysis packets, review-proposal approval/rejection, approval-gated Phase 8/9 durable writes, a host-only post-store `intakeContext` packet for hold-first material capture, and an offline Evolution OS for prompt fragments, the Circulatio host skill, and tool descriptions. Use those workflows as workflows, not as direct deterministic memory writes.

---

## 1. Safety & Practice Routing

Circulatio is an individuation backend — not a therapist, crisis line, or diagnostic authority.

### Safety Precheck (before depth work)

- self-harm or harm-to-others risk
- psychosis-like or delusional certainty
- mania-like escalation
- severe dissociation
- panic or overwhelm
- intoxication
- minors or other policy-sensitive cases

### Routing Table

| User state | Recommended route | Avoid |
|------------|-------------------|-------|
| Crisis or severe destabilization | Grounding only + human-support guidance | Symbolic depth, archetypal inflation |
| High anxiety or overwhelm | Short grounding or settling practice | Deep confrontation, deterministic pattern claims |
| Stable but emotionally charged | Witnessing, cautious interpretation, integration journaling | Excess amplification |
| Stable but in an active threshold | Threshold review, bounded packet, or simple holding language first | Premature archetypal certainty or forced synthesis |
| Strong image with low-to-moderate activation | Image-close journaling first | Forced dialogue |
| After any deep practice | Integration journaling | Ending at interpretation only |

### Practice Types

- grounding
- brief meditation
- journaling
- passive imagination (only when explicitly supported and safe)

### Tone Rules

Prefer:
- collaborative prompts
- bounded challenge supported by evidence
- user authority over meaning and storage

Avoid:
- shaming language
- oracle framing
- dependency cues
- deterministic diagnosis or typing language

---

## 2. Evidence Model

Circulatio separates observations from hypotheses and keeps the backend auditable.

### EvidenceItem Types

- `dream_text_span`
- `material_text_span`
- `user_association`
- `prior_material`
- `recurring_symbol`
- `life_event_ref`
- `life_os_state_snapshot`
- `practice_outcome`
- `cultural_reference`
- `counterevidence`
- `session_context`

### Observations

Descriptive statements grounded in evidence: repeated images, figures, motifs, structure, recurrence, life-context links, practice-related change.

### Hypotheses

Tentative interpretive moves: possible compensation, recurring pattern or complex-candidate activation, symbolic meaning, practice need.

Each hypothesis must include: evidence IDs, confidence, user-test prompt, counterevidence when relevant.

### Confidence Rules

| Confidence | When allowed |
|------------|--------------|
| `low` | Single material entry, weak associations, limited context |
| `medium` | Multiple converging signals with modest ambiguity |
| `high` | Strong repeated evidence across materials, user associations, and context, with low contradiction |

`high` confidence should remain rare.

### Phrasing Rules

Prefer: "One possibility is...", "There is some evidence for...", "This may be compensating for..."

Avoid: "This means...", "You have X complex.", "The material proves..."

### Disconfirmation

The backend supports: rejection, refinement, suppression, revision, later counterevidence. Disconfirmed material remains in the audit trail while dropping out of active use.

---

## 3. Typology Guardrails

Typology is an optional lens. It remains subordinate to image-close observation, recurrence, feedback, and safety.

- Disabled by default.
- Signals are evidence-backed hints, not identity assignments.
- Hypotheses stay outside the main symbolic hypothesis list.
- Confidence is capped at `medium`.
- Durable typology storage requires explicit approval.
- Do not run in crisis, grounding-only, intoxication, overwhelm, mania-like activation, severe dissociation, or psychosis-like certainty states.
- Do not use typology to intensify practice routing.

Allowed language: "One possible typology lens is...", "There is weak evidence for...", "This should be tested against your experience."

Disallowed language: "You are a thinking type.", "This proves your inferior function is...", deterministic anima/animus claims.

---

## 4. Method-State Connector Guardrails

- Hermes/host must call the connector explicitly. Do not expose or simulate a hidden capture-any route.
- Hold-first store tools may return a host-only `intakeContext` packet in the bridge/tool `result`. Hosts may use it for immediate conversational continuity, but must not treat it as durable state, user-facing interpretation, or a license to append symbolic meaning to the public acknowledgement text.
- `circulatio.method_state.respond` requires anchors for clarifying answers, freeform follow-ups, relational-scene notes, dream-dynamics notes, goal feedback, and practice feedback. Only explicit `body_note` and `consent_update` may omit anchors.
- Direct writes are limited to explicit user-reported operational state. Projection hypotheses, inner/outer correspondence, typology lenses, dream-series claims, and living-myth synthesis stay approval-gated.
- Re-check consent and safety at capture time and again at proposal approval time.
- In grounding-only states, allow body state, consent changes, and low-intensity practice feedback; withhold projection language, active imagination, typology, archetypal patterning, and living-myth synthesis.
- If freeform routing is unavailable, return no-capture with warnings or follow-up prompts. Do not guess with deterministic symbolic heuristics.
- Idempotency keys are required. Replays should return the stored capture result rather than creating duplicate evidence or records.

---

## 5. Demo Script

Goal: show Hermes-Circulatio as a longitudinal individuation backend, not a one-off interpreter.

Quick smoke path: `python demo.py`

External Hermes-host smoke path: `.venv/bin/python scripts/hermes_host_smoke.py`

Prerequisites for the true external host smoke:

- local `hermes` CLI available on `PATH` or passed via `--hermes-bin`
- a working Hermes `config.yaml` and provider/auth setup in the source Hermes home so the store-note and journey-page host calls can complete
- if you want missing prerequisites to fail instead of skip, run `.venv/bin/python scripts/hermes_host_smoke.py --require-host`

The repo-owned demo harness exercises the packaged Hermes plugin surface against the in-memory runtime, including hold-first reflection capture, bounded discovery, autonomous journey-container creation, journey-page rendering, interpretation, approval, review, packet, practice, rhythmic brief, and explicit `/circulation` command paths.

### Seed Ingredients

- 3–5 dreams across one symbolic series (`/circulation dream`)
- 3–5 reflections or charged events (`/circulation reflect`, `/circulation event`)
- 1 recurring-thread note that Hermes can store first and then attach to a durable journey container through the tool surface
- 3 safety red-team cases (crisis_handoff, grounding_only)
- 3 feedback cases: approve, reject, partially refine (`/circulation revise`)
- 1 threshold-oriented cluster with body and relational context for `/circulation review threshold`
- 1 broader month-scale cluster for `/circulation review living-myth`
- 1 packet-oriented use case for `/circulation packet --focus threshold`

### Primary Flow

1. Show prior recurring symbols via `/circulation symbols` and `/circulation symbols --name "water" --history`.
2. Show the bounded discovery surface: `/circulation discovery --query "water chest tension"`.
3. Show a stored context snapshot (e.g. low focus after authority conflict).
4. Enter a recurring-thread note and show journey organization:
   - Hermes tool path: `circulatio_store_reflection` followed by `circulatio_create_journey`
   - Read-mostly page: `/circulation journey`
   - Manual QA path: `/circulation journey create --label "Laundry return"`, `/circulation journey list`, `/circulation journey get --label "Laundry return"`, `/circulation journey pause --label "Laundry return"`, `/circulation journey resume --label "Laundry return"`
5. Enter new material: `/circulation dream "I was in a flooded house and found a snake under the stairs."`
   - Witnessing, recurrence links, cautious context links, pending proposals.
6. Show approval/rejection:
   - `/circulation approve <runId> <proposalId>`
   - `/circulation reject <runId> <proposalId> --reason "..."`
7. Show revision and deletion:
   - `/circulation revise <entityType> <entityId> --note "..." --set canonicalName="..."`
   - `/circulation delete <entityType> <entityId> --mode tombstone`
8. Show weekly review: `/circulation review week [start end]`
9. Show threshold review: `/circulation review threshold`
10. Show living myth review: `/circulation review living-myth`
11. Show review proposal gating:
   - `/circulation review approve <reviewId> <proposalRef>`
   - `/circulation review reject <reviewId> <proposalRef> --reason "do not save this"`
12. Show a bounded packet: `/circulation packet --focus threshold`

### What Should Be Noticeable

- Product backend, not a toy prompt.
- Not a generic dream dictionary.
- Evidence-backed, uncertain where needed.
- Safety gating blocks depth work by design.
- User control: proposals are pending until explicitly approved/rejected.
- Discovery stays read-only and bounded: it browses approved dashboard, memory-kernel, and graph state without creating runs, reviews, proposals, or writes.
- Journey containers can be created or updated autonomously by Hermes, but they stay lightweight and non-interpretive.
- Journey lifecycle QA commands are explicit and stable for debugging/demo use, while normal user flow remains tool-first through Hermes routing.
- Workflow outputs stay bounded; threshold/living-myth reviews and packets are not raw exports or auto-persisted symbolic truth.
- Idempotency-keyed: duplicate commands return the original response.
- Value increases across time because state is stored and queryable.

### Keep The Demo Clean

Do not demo: deterministic typology, diagnostic language, graph visualization, unrelated productivity/wellness dashboards.

---

## 6. Self-Evolution Guardrails

The self-evolution tooling is development infrastructure. It is not part of the live runtime loop.

### Evolution OS Boundary

- The Evolution OS is offline-only. It may generate candidate files, reports, diffs, manifests, and review packages under `artifacts/self_evolution/`, but it must not hot-swap prompt state into a live runtime.
- Phase 1 mutation targets are limited to `src/circulatio/llm/prompt_fragments.py`, `src/circulatio_hermes_plugin/skills/circulation/SKILL.md`, and descriptive text in `src/circulatio_hermes_plugin/schemas.py`.
- `SafetyGate`, `method_state_policy`, evidence integrity checks, approval-gated write logic, persistence schemas, and `CirculatioService` write semantics remain immutable guardrails for the optimizer.
- Candidate bundles with immutable files must fail review. Use `docs/SELF_EVOLUTION_OS.md` for the target registry, bundle format, promotion rules, and reviewer checklist.

- Run `.venv/bin/python scripts/evaluate_circulatio_method.py --strict` before proposing an evolved prompt fragment, skill, or tool-description candidate.
- Use `.venv/bin/python scripts/evolve_circulatio_method.py --strategy manual ...` when you want a staged candidate run with `manifest.json`, `report.json`, `report.md`, `diff.patch`, and rationale output for review.
- Run the normal repo tests before merge. The method eval is a gate, not a substitute for `pytest`.
- Treat prompt-fragment, skill, and tool-description edits as offline versioned artifacts. Do not hot-swap them mid-conversation.
- Keep raw `InteractionFeedbackRecord.note` text out of prompts and other live runtime artifacts unless a future design explicitly changes that privacy boundary.
- Do not auto-evolve `SafetyGate`, approval-gated write logic, evidence integrity checks, consent enforcement, or persistence schemas.
- Human review stays mandatory. A passing candidate is still a review candidate, not an auto-merge.
