# Journey Session Architect Prompt

This is the primary working document for **longitudinal session design**.

Use this file when the real question is:

- what full user session or multi-session arc do we want to design?
- what should the host say turn by turn?
- what should we log and analyze later?
- how do we turn that session plan into current backend, bridge, method, and host tests?

This file is intentionally **not** a tool-call eval document.

`docs/JOURNEY_FAMILIES.md` remains the reference catalog for journey-family vocabulary and case
stories. This file is the planning document for turning that material into **one coherent
longitudinal session spec** that can be used in the existing test stack.

## Working Goal

We want to design and later analyze **longitudinal sessions**, not just isolated turns.

That means each planned session should define:

- the user arc across several turns or days
- the expected host tone and pacing at each step
- the bounded response style at each step
- the durable or read-only state expectations at each step
- the assertions we later mirror into the current tests

## Current File Paths

These are the files that matter for this workflow.

### Core reference docs

- `docs/JOURNEY_SESSION_ARCHITECT_PROMPT.md`
  Primary planning doc for longitudinal session specs.
- `docs/JOURNEY_FAMILIES.md`
  Reference taxonomy, canonical families, baseline cases, and layer mapping.
- `docs/ROADMAP.md`
  Product use cases and value language.
- `docs/ENGINEERING_GUIDE.md`
  Architecture, boundaries, and implementation placement.

### Current truth layers

- `tests/test_circulatio_service.py`
  Backend truth for persistence, projections, read-mostly behavior, practice adaptation, and
  consent/runtime behavior.
- `tests/test_hermes_bridge_plugin.py`
  Hermes/plugin truth for bounded host-facing tool surfaces and structured outputs.
- `tests/test_hermes_host_smoke.py`
  Opt-in real Hermes host test harness.
- `scripts/hermes_host_smoke.py`
  Real Hermes host smoke path.

### Current method-artifact layer

- `src/circulatio_hermes_plugin/skills/circulation/SKILL.md`
  Host-routing contract.
- `tests/evals/circulatio_method/*.jsonl`
  Current artifact-facing method evals for prompt fragments, skill text, and tool descriptions.

### Current journey planning/eval assets

- `tests/evals/journey_cli/baseline.jsonl`
  Baseline journey case fixtures.
- `tests/evals/journey_cli/compound.jsonl`
  Compound journey fixtures.
- `tests/evals/journey_cli/redteam.jsonl`
  Red-team fixtures.
- `tests/journey_case_helpers.py`
  Seed/setup helper path for mirroring selected journey cases into runtime tests.
- `tests/test_journey_families_service.py`
  Current service-side journey mirror tests.
- `tests/test_journey_families_bridge.py`
  Current bridge-side journey mirror tests.

## What We Are Actually Building

The target is not "a better synthetic route eval".

The target is a **longitudinal session spec** that can later be used in four places:

1. **Design review**
   Read the planned session and decide whether the arc feels right.
2. **Manual or real-host run**
   Use the session as the script for Hermes or another host.
3. **Transcript analysis**
   Review what the host actually did over the whole arc.
4. **Test mirroring**
   Extract the durable truth into existing service, bridge, method, and smoke tests.

## Roadmap

### Phase 1. Pick one umbrella session, not all 12 cases

Start with one session pack of **4 to 6 turns**.

Recommended first session packs:

- `practice_reentry_001 -> embodied_recurrence_001 -> relational_scene_001 -> feedback_correction_001`
- `symbol_body_pressure_001 -> goal_tension_001 -> symbol_body_pressure_002`
- `practice_reentry_002 -> practice_reentry_003 -> embodied_recurrence_003`

Why:

- easier to review than all 12 at once
- easier to run manually with Hermes
- easier to mirror into current tests without inventing a new system

### Phase 2. Write one longitudinal session spec

For that pack, define:

- user messages verbatim
- prior context before each turn
- expected host route/surface
- expected host response style
- forbidden host moves
- what to log during the run

Output should be one session document, not scattered notes.

### Phase 3. Run the session once in Hermes

Do one real run first.

Capture per turn:

- raw user message
- raw host reply
- visible route/tool if visible
- visible state/write if visible
- timestamp or duration
- notes about drift, pacing, or awkwardness

### Phase 4. Analyze the transcript

Review the transcript as a **session**, not as isolated turns.

Ask:

- did the session remain coherent across turns?
- did the pacing stay proportional?
- did the host stay hold-first where it should?
- did the session escalate too quickly anywhere?
- did feedback, re-entry, and read-mostly boundaries hold?

### Phase 5. Mirror the session into current tests

Once the session shape is good, mirror its assertions into existing paths.

- backend truth -> `tests/test_circulatio_service.py` or `tests/test_journey_families_service.py`
- bridge truth -> `tests/test_hermes_bridge_plugin.py` or `tests/test_journey_families_bridge.py`
- host-routing wording -> `tests/evals/circulatio_method/*.jsonl`
- real-host scenario -> `scripts/hermes_host_smoke.py` and `tests/test_hermes_host_smoke.py`

### Phase 6. Expand from one pack to three packs

After one pack is stable:

- one re-entry/practice pack
- one relational/body pack
- one dream/body/goal pack

Only later should we attempt a full 12-case longitudinal battery.

## What The Session Spec Must Produce

A good session spec should produce all of the following in one output:

- one session title
- one user situation
- one longitudinal arc summary
- a turn-by-turn plan
- transcript capture instructions
- analysis questions for later review
- a mapping into the current test layers

## Required Output Shape For The Session Spec

Any planner using this file should return these sections exactly:

1. `Session Intent`
2. `Included Cases`
3. `Longitudinal Arc`
4. `Turn Plan`
5. `Transcript Capture Sheet`
6. `Later Analysis Questions`
7. `Test Mapping`
8. `Failure Signals`

## Session Architect Prompt

Copy and use this prompt.

```text
You are the Longitudinal Session Architect for Circulatio.

Your task is to design one coherent longitudinal session or multi-session arc that can later be:
- run manually through Hermes or another host
- reviewed as a transcript
- mirrored into the current backend, bridge, method, and host-smoke tests

You are not designing a tool-call eval.
You are designing a session plan.

System boundaries:
- Hermes or another host owns routing and tool choice.
- Circulatio owns state, interpretation, reviews, practices, and durable memory.
- Ambient shares are hold-first unless the user explicitly asks for meaning.
- No host-side Jungian monologue.
- No hidden capture-any ingress.
- Read-mostly surfaces must remain read-mostly.
- Anchored follow-up stays anchored.
- Feedback routes to feedback tools, not new symbolic reflection.

Use the following baseline case vocabulary when useful:
- embodied_recurrence_001
- embodied_recurrence_002
- symbol_body_pressure_001
- thought_loop_001
- relational_scene_001
- relational_scene_002
- practice_reentry_001
- practice_reentry_002
- practice_reentry_003
- embodied_recurrence_003
- symbol_body_pressure_002
- goal_tension_001
- feedback_correction_001

Design a session for this use case:
<USE_CASE>

Umbrella story:
<UMBRELLA_STORY>

Included cases:
<INCLUDED_CASES>

Session shape:
- turns or phases: <TURN_COUNT>
- single sitting or multi-day: <SESSION_SHAPE>
- include re-entry: <YES_OR_NO>
- include feedback correction: <YES_OR_NO>
- include read-mostly journey access: <YES_OR_NO>

Current test targets to support later:
- backend truth: tests/test_circulatio_service.py, tests/test_journey_families_service.py
- bridge truth: tests/test_hermes_bridge_plugin.py, tests/test_journey_families_bridge.py
- method artifacts: tests/evals/circulatio_method/*.jsonl
- real host smoke: scripts/hermes_host_smoke.py, tests/test_hermes_host_smoke.py

Return exactly these sections:

1. Session Intent
State the user need, emotional pressure, symbolic pressure, and why this session should exist.

2. Included Cases
List the baseline case ids used and why each one belongs in the arc.

3. Longitudinal Arc
Describe the full arc in plain language. Make it concrete.

4. Turn Plan
For each turn provide:
- turn number
- linked case id
- user message verbatim
- context before the turn
- expected host route or surface
- expected host response behavior
- one example host reply
- forbidden host moves
- expected state consequence or non-consequence

5. Transcript Capture Sheet
Provide the exact fields that should be recorded during a real run:
- turnIndex
- caseId
- userMessage
- agentReply
- visibleRouteOrTool
- selectedSurface
- writeObserved
- replyBounded
- hostInterpretationLeak
- consentBoundaryHeld
- readMostlyBoundaryHeld
- durationMs
- notes

6. Later Analysis Questions
Provide concrete questions for reviewing the finished transcript.
Use these lenses:
- continuity
- pacing
- symbolic restraint
- body-first grounding
- consent handling
- feedback handling
- practice adaptation
- read-mostly boundaries
- re-entry quality
- host drift from contract

7. Test Mapping
Map the planned session into the current test paths.
For each planned turn or assertion, say whether it primarily belongs in:
- tests/test_circulatio_service.py
- tests/test_journey_families_service.py
- tests/test_hermes_bridge_plugin.py
- tests/test_journey_families_bridge.py
- tests/evals/circulatio_method/*.jsonl
- scripts/hermes_host_smoke.py
- tests/test_hermes_host_smoke.py

8. Failure Signals
List the concrete things that would make the session bad.
Examples:
- backlog dump on re-entry
- host-side interpretation instead of holding
- projection without consent
- read-only surface causing a write
- feedback rerouted into store_reflection
- pushing a new practice before practice outcome capture

Keep the output practical and observable. Avoid abstract therapy language. Prefer later-testable behavior over theory.
```

## How To Use The Prompt Well

### Good input shape

Use a concrete user arc.

Good:

- "A user returns after six days, mentions recurring chest tightness after talking to one person, then later names a repeated shutting-down scene, and finally says the last interpretation missed them."
- "A user brings a recurring dream image, then a waking-life tension, then opens the journey page, and later asks for pattern help without wanting symbolic inflation."

Bad:

- "Test all journeys."
- "Make a session about Jungian stuff."

### Good session size

Start with **4 to 6 turns**.

Do not start with all 12 baseline cases in one run.

### Good analysis goal

The analysis target is:

- what happened across the arc
- where the host drifted
- which parts belong in service tests
- which parts belong in bridge tests
- which parts belong in method datasets
- which parts belong in real host smoke

## Transcript Capture Template

Use this later when running the real session.

```text
turnIndex:
caseId:
userMessage:
agentReply:
visibleRouteOrTool:
selectedSurface:
writeObserved:
replyBounded:
hostInterpretationLeak:
consentBoundaryHeld:
readMostlyBoundaryHeld:
durationMs:
notes:
```

## Later Analysis Checklist

After the transcript exists, answer these in order:

1. Did the host stay on the right surface turn by turn?
2. Did the host stay hold-first when the user was only sharing material?
3. Did the host avoid symbolic inflation when containment was thin?
4. Did re-entry stay light instead of becoming backlog pressure?
5. Did read-mostly turns remain read-mostly?
6. Did the host adapt practice pacing based on prior skip/outcome signals?
7. Did explicit feedback remain feedback instead of becoming new symbolic capture?
8. Did the session feel continuous rather than stateless?
9. Which turns should be mirrored into backend truth tests now?
10. Which turns should be mirrored into bridge or host-smoke tests now?

## Practical Starting Point

The first session I would design from this file is:

- `practice_reentry_001`
- `embodied_recurrence_001`
- `relational_scene_001`
- `feedback_correction_001`

Why:

- it gives you re-entry
- it gives you embodied recurrence
- it gives you relational restraint
- it gives you feedback correction
- it is long enough to feel longitudinal
- it maps cleanly into the current tests

That is the right first target before trying to build a full 12-case longitudinal suite.
