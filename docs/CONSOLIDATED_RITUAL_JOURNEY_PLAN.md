# Consolidated Ritual Journey Plan

> Status: Current ritual backend, renderer handoff, and Hermes Rituals playback are connected by explicit contracts and local E2E coverage. Kokoro TTS, DiffRhythm music, and WAN image-to-video provider contracts have been live-smoke-tested through Chutes. Official OpenAI transcription is wired as an optional caption provider, while fallback captions remain canonical.
>
> Scope: Documentation and implementation guidance for the layered Hermes Rituals path. Circulatio remains a symbolic backend and read-only ritual planner. Hermes-agent owns tool choice. The renderer owns provider calls. Hermes Rituals owns playback. Whisper through the current Chutes path is unresolved; OpenAI transcription is optional and must read `OPENAI_API_KEY` from the server environment, never from tool arguments.

---

## 1. Layered System

```text
Layer 0  Memory and context
         Circulatio records dreams, body states, events, symbols, journeys, goals, patterns,
         practice outcomes, and alive-today summaries. Raw material stays inside Circulatio.

Layer 1  Hermes-agent routing
         Hermes reads the user message and available memory context, then chooses whether to call
         circulatio_plan_ritual and which requestedSurfaces to enable.

Layer 2  Scheduled invitation
         Cron may create ritual_invitation rhythmic briefs only. The brief can suggest a ritual,
         but it must not plan, render, or call providers before user acceptance.

Layer 3  Accepted ritual plan
         User acceptance triggers one circulatio_plan_ritual call. Circulatio returns a
         PresentationRitualPlan and renderRequest.allowedSurfaces. Planning is read-only.

Layer 4  Renderer handoff
         The local plugin persists the plan and invokes the renderer. Mock/dry-run is default.
         Provider-backed render requires provider profile, token env, positive budget, allowed surface,
         source-data policy, provider allowlist, and beta gates for music/video.

Layer 5  Artifact manifest
         The renderer writes manifest.json plus generated or fallback assets: narration, captions,
         image, music, cinema, breath, meditation, sections, and completion fields.

Layer 6  Hermes Rituals playback
         The frontend loads the manifest into one artifact player. Ritual, broadcast, cinema,
         breath, meditation, image/photo, companion, and body capture are lenses/channels, not
         separate intelligence systems.

Layer 7  Completion sync
         Completion calls circulatio_record_ritual_completion only. It may include explicit
         reflection, body state, or practice feedback. It must not trigger interpretation.

Layer 8  Future live guidance
         Apple Fitness-like guided sessions belong to Hermes-agent/live guidance through a
         guidanceSessionId. Sensor/body coaching remains host-owned and separate from the planner.
```

The main puzzle is the connection between layers. Each layer already has a partial contract; the missing product proof is that a real Hermes-agent journey can choose the right subset of surfaces, render safely after consent, and play correctly in the browser.

---

## 2. Surface Selection Contract

Hermes-agent should select the smallest useful ritual surface set. It should not enable every channel by default.

Examples:

```text
User asks to settle now
-> ritualIntent: breath_container
-> requestedSurfaces: breath enabled; audio, music, image, cinema disabled

Dream + activated body state suggests a contained integration ritual
-> ritualIntent: guided_ritual or journey_broadcast
-> requestedSurfaces: breath + meditation + optional slow audio + optional music

User asks for music from a dream thread
-> requestedSurfaces: music enabled with allowExternalGeneration=true
-> renderPolicy: chutes_music or chutes_all, positive budget, allowBetaMusic=true

User asks for a quiet ambient ritual with no talking
-> requestedSurfaces: music + breath or meditation; audio disabled

User asks for spoken meditation
-> requestedSurfaces: audio enabled with slow pace or speed around 0.82-0.9,
   captions enabled, meditation enabled

User explicitly asks for cinematic artifact
-> requestedSurfaces: image/cinema enabled only if provider, budget, and beta gates pass
```

Planner options already model these axes:

- `ritualIntent`: weekly integration, alive-today, hold container, guided ritual, breath container, meditation container, image return, active imagination container, journey broadcast, threshold container.
- `narrativeMode`: full guided, sparse guided, breath only, meditation only, user script, hybrid.
- `requestedSurfaces`: text, audio, captions, breath, meditation, image, music, cinema.
- `audio`: voice id, tone, pace, and provider speed; Kokoro speed is important for meditation immersion.
- `music`: style intent, duration, seed, and derived user-facing-only provider prompt.
- `renderPolicy`: render mode, provider allowlist, provider profile, budget, timeout, beta flags, and source-data policy.

`text` remains plan metadata and fallback copy. It should not force a text-heavy rendered experience when Hermes selected breath, music, meditation, or cinema as the primary surface.

---

## 3. Provider State

Current live-smoke-tested provider contracts:

- Kokoro TTS: `https://chutes-kokoro.chutes.ai/speak`, top-level payload, `text`, `voice`, `speed`; useful meditation speeds are around `0.82-0.9`.
- DiffRhythm music: `https://chutes-diffrhythm.chutes.ai/generate`, top-level payload, `style_prompt`, `music_duration`, `scheduler`, `cfg_strength`, `seed`, `steps`, `lyrics`, `batch_size`.
- WAN image-to-video: `https://chutes-wan-2-2-i2v-14b-fast.chutes.ai/generate`, top-level payload, `image`, `prompt`, `frames`, `fps`, `resolution`, `guidance_scale`, `guidance_scale_2`, `negative_prompt`.

Provider rules:

- Circulatio never calls providers.
- Provider prompts must be derived from user-facing summaries, themes, symbols, and source refs, never raw dream text or private notes.
- Music and video stay off unless explicit product gates pass.
- Chutes Whisper is not considered working. Renderer fallback captions and plan-derived caption segments remain canonical.
- Official OpenAI transcription is optional for timed captions. It requires `transcriptionProvider=openai`, `providerAllowlist` containing `openai`, a configured key env var such as `OPENAI_API_KEY`, and the same no-raw-material provider policy. Literal API keys must never be committed or passed in payloads.

---

## 4. E2E Coverage

The current tests cover backend planner contracts, renderer/provider payloads, local handoff behavior, completion sync, live provider smoke checks, and browser playback hooks. The implemented proof is split by layer:

1. Hermes-agent routing evals
   - Input: user message + memory context.
   - Expected: correct tool choice and argument plan.
   - Cases: breath only, dream/body breath+music, quiet/no narration, full voice/music/image, cinema, scheduled cron, invitation accept, invitation decline, and artifact completion.

2. Scheduled ritual acceptance path
   - Cron emits `ritual_invitation` only through `circulatio_generate_rhythmic_briefs`.
   - User acceptance triggers `circulatio_plan_ritual` with the safe acceptance payload.
   - Accepted planning triggers renderer handoff only after consent.
   - Skip/dismiss/decline does not plan or render.

3. Provider-backed render path
   - Mock/dry-run remains default.
   - Chutes render requires token, provider profile, positive budget, allowed surfaces, provider allowlist, and beta gates.
   - OpenAI transcription requires provider allowlist, env-key lookup, and failure-tolerant fallback captions.
   - Failure returns warnings and fallback manifest where possible.

4. Browser playback path (`agent-browser` or OpenAI Browser Use)
   - Load `/artifacts/{artifactId}`.
   - Verify manifest, audio, music, image, captions, and video URLs return expected statuses.
   - Verify narration metadata, music loop/sync, captions, breath pacer, image/photo lens, cinema lens, body capture at completion, and completion POST.

5. Journey CLI integration
   - Ritual-specific tool-choice cases live in method eval datasets.
   - Accepted invitation -> plan -> render -> artifact report checks are in compound journey cases.
   - Reports include selected tool sequence, requested surfaces, render policy, artifact URL, manifest surfaces, browser driver used (`agent-browser` or OpenAI Browser Use), and check result.
   - Provider tokens stay redacted and user-authored text stays out of `tool_calls.json`.

---

## 5. Documentation Ownership

Keep the docs split like this:

- `docs/PRESENTATION_LAYER.md`: canonical architecture, ownership, flow boundaries, provider safety, completion, and future live guidance bridge.
- `docs/CONSOLIDATED_RITUAL_JOURNEY_PLAN.md`: layered implementation map and remaining puzzle pieces.
- `docs/JOURNEY_CLI.md`: what the evaluator proves, how to run it, and what remains missing.
- `docs/ENGINEERING_GUIDE.md`: stable backend/runtime constraints and pointers to presentation docs.

Docs must not claim a flow is production-ready until the corresponding E2E path exists. Mock renderer output, provider smoke tests, and browser playback each prove different things and should stay named separately.

---

## 6. Remaining Implementation Pass

Next work should stay focused on hardening rather than changing ownership boundaries:

1. Run provider-backed smoke jobs regularly with Chutes speech/music/image/video enabled separately.
2. Investigate alternate transcription providers or local transcription if OpenAI/Whisper cost, latency, or privacy posture is not acceptable.
3. Expand real Hermes-agent baseline cases as host behavior stabilizes.
4. Keep live guidance as a separate `guidanceSessionId` layer after artifact playback remains stable.

---

## 7. Combined Experience Phase 7-9 Plan

These Phase 7-9 labels describe the Hermes Rituals experience layer. They do not replace the backend roadmap phase numbers already used elsewhere.

### Phase 7: Completion And Memory Loop

Implemented target:

```text
artifact playback
-> quiet completion panel
-> optional body state, literal words, or practice note
-> POST /api/artifacts/{artifactId}/complete with one idempotency key
-> external Hermes completion endpoint when configured
-> repo-local Circulatio completion bridge otherwise
-> no interpretation, review generation, practice escalation, renderer call, or provider call
```

The frontend completion panel now composes the existing body picker instead of making body capture own the whole closing experience. Completion can be submitted with no notes, with body state, with literal reflection text, with a practice note, or with any explicit combination. Saved state is idempotent and shown as already held rather than creating another write.

### Phase 8: Hermes Companion Inside Ritual

Implemented target:

```text
current ritual frame
-> guidanceSessionId
-> bounded guidance session create/resume
-> companion chat from source refs + currentFrame
-> optional RitualCompanionAction
-> explicit approve/reject route
-> Hermes owns any durable Circulatio tool execution
```

`RitualGuidanceFrame` now carries phase and available tracks directly, so Hermes does not need to infer live context from lens alone. The companion can be paused or minimized, local preview stays non-durable, approval cards show user-facing persistence summaries instead of idempotency-key fragments, and the local E2E path can propose approve/reject action cards without Hermes executing durable writes.

### Phase 9: No-Camera Live Guidance First Slice

Implemented target:

```text
artifact completion or companion rail
-> /live/{guidanceSessionId}?artifactId=...
-> no-camera live guidance shell
-> one focus mode at a time: breath, meditation, image, movement, or companion cue
-> optional camera preflight screen
-> camera permission only after explicit user action
-> companion remains a bounded track, not the live guidance system itself
```

This pass does not implement pose estimation, reference movement comparison, camera telemetry, movement scoring, or live sensor persistence. It creates the safe host-owned shell those tracks can attach to later, with Journey CLI browser-driver artifacts proving the local handoff and completion boundaries when `agent-browser` is installed.

### Enabled Use Cases

- Complete a ritual with no notes, only marking that it was held.
- Complete with explicit body-state detail at closing.
- Complete with literal reflection words without interpretation.
- Complete with practice feedback metadata without inferring it from playback time.
- Use the in-ritual companion with phase, section, lens, available track, completion, and source-reference context.
- Pause or minimize the companion without stopping playback.
- Approve or reject proposed durable actions through a card that avoids internal backend identifiers.
- Continue into `/live/{guidanceSessionId}` as a no-camera guided session from completion or the companion rail.
- Select a live focus mode and complete/stop/pause the live continuation.
- Enter camera preflight explicitly while keeping no-camera guidance available.
- Exercise local preview action proposal, approve/reject, and non-durable approval evidence without Hermes.
- Capture Journey CLI `agent-browser` pass/fail/skip artifacts for artifact page, companion action, live handoff, camera preflight, and completion route idempotency.

### Remaining Work

- Production Hermes-agent subscription to guidance events and action execution.
- Production Hermes live coaching attached to `guidanceSessionId` and `hostSessionId`.
- Provider-backed browser-driver checks with live audio/image/video artifacts, beyond local mock artifacts.
- Local sensor runtime, pose confidence, reference media comparison, and bounded live body events.
- Explicit practice-session IDs in completion feedback when a rendered artifact is attached to an accepted practice.

---

## 8. Retained Phase 7-9 Architect And Designer Prompts

Use these prompts after Phases 1-6 are underway or completed. They are for planning the next implementation slice, not for bypassing the existing boundaries.

### Architect Prompt

```text
You are the implementation architect for Circulatio and Hermes Rituals Phases 7-9.

Use RepoPrompt MCP for all repo reading, searching, and documentation edits. Start by reading:
- docs/PRESENTATION_LAYER.md
- docs/CONSOLIDATED_RITUAL_JOURNEY_PLAN.md
- docs/ROADMAP.md
- docs/ENGINEERING_GUIDE.md
- docs/JOURNEY_CLI.md
- docs/EMBODIED_GUIDANCE_SURFACE.md
- src/circulatio_hermes_plugin/skills/circulation/SKILL.md

Context:
Phases 1-6 are focused on ritual contract, Hermes-agent tool choice, scheduled invitation, renderer/provider hardening, browser playback checks through `agent-browser` or OpenAI Browser Use, and Journey CLI proof. Your task is to produce a detailed implementation plan for Phases 7-9:

Phase 7: Completion And Memory Loop
- Explicit completion writes only.
- Record ritual completion, optional literal reflection, optional body state, optional practice feedback.
- No hidden interpretation, review generation, practice escalation, or provider calls.
- Preserve idempotency and completion replay behavior.

Phase 8: Hermes-Agent Companion Inside Ritual
- Add a same-session Hermes companion around artifact playback.
- Use guidanceSessionId and bounded session events.
- Assistant text cannot execute durable writes.
- Any proposed action must require explicit user approve/reject.
- Companion should understand artifact phase, active section, available surfaces, completion state, and safe context refs.

Phase 9: Apple Fitness-Like Live Guidance
- Add future live guidance as a host-owned session layer attached to an artifact or practice.
- Track-based model: timeline, media, sensor, coach, persistence.
- Hermes receives bounded body events, not raw camera frames.
- Circulatio stores only explicit body states, practice outcomes, reflections, active imagination material, or completion summaries.
- Do not put camera, pose, or live coaching logic into circulatio_plan_ritual.

Deliver a decision-complete implementation plan that includes:
- Current-state summary from the docs and code surfaces.
- Target data flow diagrams for Phase 7, 8, and 9.
- Public interfaces and contracts to add or stabilize.
- Ownership by subsystem: Circulatio core/service, Hermes plugin, Hermes-agent host, renderer, Hermes Rituals frontend, Journey CLI.
- Storage and idempotency rules.
- Consent and safety boundaries.
- Failure modes and fallback behavior.
- E2E test plan, including Journey CLI and browser tests.
- Rollout order with smallest shippable slices.
- Explicit non-goals.

Important constraints:
- No raw dream/body/event text to external providers.
- No hidden interpretation during ritual completion, companion chat, or live guidance.
- No deterministic symbolic routing tables.
- No scheduled planning or rendering before acceptance.
- Do not create a new universal ingress tool.
- Do not make Circulatio own frontend rendering, camera runtime, or provider calls.
- Whisper is unresolved; fallback captions remain baseline.

After planning, update docs/CONSOLIDATED_RITUAL_JOURNEY_PLAN.md and docs/EMBODIED_GUIDANCE_SURFACE.md with the chosen Phase 7-9 plan, keeping docs honest about what is implemented vs planned.
```

### Designer Prompt

```text
You are the product and interaction designer for Hermes Rituals Phases 7-9.

Use RepoPrompt MCP for repo reading and docs edits. Start by reading:
- docs/PRESENTATION_LAYER.md
- docs/CONSOLIDATED_RITUAL_JOURNEY_PLAN.md
- docs/ROADMAP.md
- docs/EMBODIED_GUIDANCE_SURFACE.md
- apps/hermes-rituals-web/README.md

Context:
Phases 1-6 make the static ritual artifact real: selective surfaces, scheduled acceptance, provider-rendered media, browser playback, and Journey CLI proof. Your task is to design the next experience layer:

Phase 7: Completion And Memory Loop
- Design completion as a quiet closing moment, not a data-entry form.
- Let the user optionally record body state, reflection, and practice feedback.
- Make it clear that completion does not trigger interpretation unless the user asks.

Phase 8: Hermes-Agent Companion Inside Ritual
- Design Hermes as an in-session companion that can respond to the current phase without overwhelming the ritual.
- The companion should feel present but not chatty.
- Durable actions require explicit approval.
- The user should be able to ignore, minimize, or pause the companion.

Phase 9: Apple Fitness-Like Live Guidance
- Design the future live guidance experience as a calm guided session, not a dashboard.
- Use one primary focus at a time: breath, movement, meditation, image, or companion cue.
- Camera/body sensing must be visibly consentful and optional.
- Show body guidance as coarse, supportive cues first; avoid medical or corrective language.
- Treat live guidance as a layer attached to an artifact through guidanceSessionId, not as a replacement for artifact playback.

Deliver a detailed design implementation plan that includes:
- User journeys for direct ritual, scheduled ritual, completed ritual, in-ritual companion, and live guidance launch.
- Screen/state inventory for Phase 7, 8, and 9.
- Interaction rules for companion visibility, approval prompts, completion capture, and live guidance consent.
- Required UI states: loading, provider fallback, no captions, no music, companion unavailable, completion replay, sensor unavailable, low confidence, user stops session.
- Accessibility expectations for audio, captions, reduced motion, keyboard control, and non-camera fallback.
- Browser acceptance criteria for the designer-facing experience using `agent-browser` or OpenAI Browser Use.
- What must stay visually stable from the current artifact player.
- What docs need to be updated after design decisions.

Important constraints:
- Do not redesign the entire ritual player chrome unless there is a specific reason.
- Do not turn the companion into a feed or dashboard.
- Do not expose internal backend/tool names to the user.
- Do not imply therapy, diagnosis, or performance scoring.
- Do not make camera mandatory.
- Keep completion explicit, quiet, and reversible where possible.

After planning, update docs/CONSOLIDATED_RITUAL_JOURNEY_PLAN.md and docs/EMBODIED_GUIDANCE_SURFACE.md with the chosen Phase 7-9 experience plan and acceptance criteria.
```
