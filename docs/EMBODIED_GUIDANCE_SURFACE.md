# Embodied Guidance Surface
## Live Body, Camera, Media, And Coach OS Contract

> **Status:** Design contract. This is a future Hermes-owned live guidance surface after the embodied presentation layer. It is not a Circulatio router, not medical diagnosis, and not part of `circulatio.presentation.plan_ritual`.

The embodied guidance surface connects reference media, camera/body signals, movement practice, active imagination, and Coach OS. It should feel like a personal mirror: consent-bound, sparse, adaptive, and useful for yoga, qi gong, breathwork, meditation, and symbolic body inquiry.

---

## Core Idea

This is not exactly "agent-browser for camera."

`agent-browser` can test the browser UI. Camera guidance needs a separate **body sensor runtime**:
- camera or mobile camera access;
- local pose/body estimation;
- confidence scoring;
- typed body events;
- Hermes-agent guidance over those events.

The camera runtime reads the body locally. Hermes-agent coaches the session. Circulatio stores only explicit user writes and bounded summaries.

---

## Recommended Architecture

Use a **track-based experience orchestrator**, not one monolithic ritual mode.

```text
timeline track    ritual sections, current time, phase, recommended lens
media track       audio, captions, image, cinema, reference video
sensor track      camera, pose, movement, breath estimate, confidence
coach track       Hermes-agent cues, coachState, safety pacing
persistence track explicit body state, practice outcome, reflection, completion
```

Each track can be absent. The orchestrator derives one current frame:

```text
ExperienceFrame =
  phase
  activeSection
  recommendedLens
  effectiveLens
  referencePhase
  bodySignal
  coachCue
  allowedWrites
```

Why this is better:
- artifact playback works now;
- reference video plus user capture fits later;
- yoga, qi gong, meditation, and active imagination share one session model;
- Hermes-agent can subscribe to events without owning the player;
- Circulatio stays a durable memory and Coach OS backend, not a camera runtime.

---

## Boundary

`PRESENTATION_LAYER.md` covers rendered artifacts:
- plan ritual;
- render audio, image, captions, or cinema;
- play artifact;
- record completion.

This document covers live guidance:
- observe body in real time;
- guide movement or attention;
- compare user movement to reference media when available;
- optionally capture active imagination;
- optionally record practice outcome, body state, or reflection.

Do not put live camera reading into the ritual planner. A ritual artifact may launch a guidance session, but live body guidance is a host runtime surface.

---

## Main Approaches

### 1. Local Mirror

Camera pose runs locally and gives simple feedback:
- standing;
- seated;
- arms raised;
- movement slowed;
- low confidence;
- off camera.

No Hermes-agent required. No durable writes by default.

### 2. Reference Media With User Capture

The host plays reference video or ritual media while capturing how the user moves.

Two streams stay separate:
- reference media: video, captions, sections, target phase, teacher cue;
- user stream: pose confidence, movement phase, body-region marks, safety stops.

Feedback should start coarse:
- following;
- paused;
- moving too fast;
- off camera;
- low confidence.

Only later add pose-specific cues, and only with clear safety language.

### 3. Hermes Live Coach

Hermes-agent joins the same `guidanceSessionId`.

```text
body events
-> host event stream
-> Hermes-agent
-> coachState-aware cue
-> optional explicit Circulatio write
```

Hermes receives bounded body events, not raw video.

### 4. Post-Session Analysis

The live session stays simple. Afterward the host summarizes:
- duration;
- phases completed;
- pauses or stops;
- user-selected body response;
- optional reflection.

Circulatio can then record practice outcome, body state, or reflection.

### 5. Training And Habit Loop

Use existing practice records first:

```text
PracticeSessionRecord
-> accepted practice
-> guided session
-> outcome
-> Coach OS follow-up
-> rhythmic brief or next practice
```

This should feel like Coach OS, not a task manager:
- one next practice;
- one reason it fits;
- one follow-up;
- no streak pressure by default.

### 6. Active Imagination Container

The user explicitly starts imaginal capture during or after movement.

Rules:
- user starts capture;
- Hermes-agent uses sparse prompts;
- camera events support pacing only;
- saved material is user-authored text or transcript;
- Circulatio holds/stores first unless interpretation is explicitly requested.

---

## Ownership

### Hermes-agent

- Live session orchestration.
- Same conversational session.
- Consent and capture prompts.
- Coach OS cue selection.
- Circulatio tool calls only after explicit user action.

### Frontend or mobile host

- Camera and microphone permissions.
- Local pose/body estimation.
- Mirror UI, overlays, stops, and confidence.
- Typed body event stream.
- Raw video local by default.

### Circulatio

- Durable records only after explicit action.
- Coach OS context through enriched `MethodContextSnapshot.coachState`.
- Body states, practice outcomes, reflections, symbolic notes, method-state responses, and journey links when requested.
- No raw camera-frame interpretation.

---

## Session Model

Use one live guidance session for continuity, with separate durable records for specific actions.

```text
guidanceSessionId
  hostSessionId
  optional artifactId
  optional ritualPlanId
  optional practiceSessionId
  optional activeImaginationCaptureId
  optional bodyStateIds[]
  optional journeyId
  optional coachLoopKey
```

Rules:
- same `guidanceSessionId` for one continuous live experience;
- same `hostSessionId` so Hermes-agent stays present;
- new `practiceSessionId` when the user accepts a practice;
- new active-imagination capture id when the user starts that container;
- new body-state record only when the user marks or saves body data;
- do not reuse ritual completion ids for camera guidance.

---

## Coach OS Alignment

Use the existing `coachState` contract. Do not create a parallel coach model.

Fields that matter:
- `activeLoops`: candidate loops such as `soma`, `practice_integration`, `goal_guidance`, `journey_reentry`, and `resource_support`.
- `selectedMove`: the one move that should shape the next cue.
- `selectedMove.kind`: bounded move kind such as `ask_body_checkin`, `ask_practice_followup`, `offer_practice`, `offer_resource`, or `hold_silence`.
- `selectedMove.promptFrame`: safe user-facing prompt frame.
- `selectedMove.capture.anchorRefs`: provenance anchors for explicit writes.
- `withheldMoves`: moves blocked by consent, safety, cooldown, or method policy.
- `globalConstraints.depthLevel`: `grounding_only`, `gentle`, or `standard`.
- `globalConstraints.blockedMoves`: hard blocks.
- `cooldownKeys`: loops that should not be prompted again yet.
- `resourceInvitation`: curated support when another prompt would be too much.

Current `CoachSurface` does not include `embodied_guidance`.

First implementation should use:
- `practice_followup` when a practice session exists;
- `method_state_response` when the user is answering an anchored prompt;
- `generic` for local mirror or unstructured guidance.

Add a dedicated `embodied_guidance` `CoachSurface` only if live body sessions need distinct move ranking in `CoachEngine.select_surface_move()`.

---

## Sensor Data Policy

Allowed live signals:
- pose landmarks;
- confidence;
- movement phase;
- stillness or motion;
- approximate breath pace;
- body region selected by user;
- user-confirmed sensation.

Allowed durable summaries, with consent:
- practice duration;
- completed phases;
- user-authored body note;
- coarse movement summary;
- safety stop;
- user feedback on a cue.

Disallowed by default:
- raw video storage;
- hidden audio transcripts;
- face or emotion inference;
- injury diagnosis;
- medical posture claims;
- symbolic interpretation from pose;
- hidden adaptation writes from camera events.

---

## Events And Writes

Host events:

```text
guidance_started
camera_enabled
camera_denied
reference_media_started
reference_phase_changed
body_signal_observed
guidance_cue_delivered
practice_phase_changed
body_region_marked
active_imagination_started
active_imagination_saved
practice_completed
guidance_completed
guidance_stopped_for_safety
```

Circulatio writes, only when explicit:

```text
store_body_state
generate_practice_recommendation
respond_practice_recommendation
record_practice_outcome
store_reflection
store_symbolic_note
method_state_respond
record_ritual_completion
```

`record_ritual_completion` is only for artifact playback completion. It should not carry camera telemetry.

---

## Minimal Session Payload

```json
{
  "guidanceSessionId": "guidance_...",
  "hostSessionId": "hermes_session_...",
  "userId": "user_...",
  "mode": "guided_practice",
  "linkedArtifactId": "ritual_artifact_...",
  "practiceSessionId": "practice_...",
  "coachLoopKey": "coach:soma:body_1",
  "sensorPolicy": {
    "cameraEnabled": true,
    "rawVideoStorage": false,
    "poseLocalOnly": true,
    "durableMovementSummaryAllowed": false
  },
  "ephemeralSignals": {
    "poseConfidence": 0.82,
    "movementPhase": "standing_balance",
    "breathPaceEstimate": "slow",
    "safetyFlags": []
  }
}
```

This is host runtime state, not a new Circulatio durable object.

---

## Implementation Path

1. Build local mirror mode with camera permission, pose confidence, and no persistence.
2. Add typed body event stream in the frontend or mobile host.
3. Add reference media as a separate track from user camera capture.
4. Attach Hermes-agent to `guidanceSessionId` and `hostSessionId`.
5. Load enriched `coachState` before live coaching.
6. Add explicit write buttons for body state, practice outcome, and reflection.
7. Add active imagination capture as a separate explicit mode.
8. Add training loops through `PracticeSessionRecord`, journeys, goals, rhythmic briefs, and adaptation preferences.

---

## Questions To Answer

### Product Slice

- What ships first: local mirror, ritual continuation, reference-video training, or Hermes live coach?
- Which practice family comes first: breath, qi gong, yoga, meditation, or active imagination?
- Is body capture only at closing/completion first, or can the user mark body response mid-session?

### Session Identity

- Does the frontend create `guidanceSessionId`, with Hermes-agent attaching `hostSessionId`?
- Can one `guidanceSessionId` include multiple practice segments?
- When a ritual artifact launches guidance, is the artifact the parent context or just one source ref?

### Media And Movement

- Are reference videos free-form media, or must they be sectioned practice templates?
- Who authors phase labels for yoga/qi gong: human templates, provider metadata, or later local analysis?
- Should feedback compare only coarse phase alignment first, or include pose-specific cues?

### Sensor Boundary

- Which pose runtime comes first: MediaPipe, MoveNet, native mobile, or another local model?
- Are movement summaries ever durable, or are camera-derived observations always ephemeral?
- How do we handle low confidence, low light, off-camera body, multiple people, or unsafe movement?

### Hermes And Coach OS

- Does Hermes-agent speak live during practice, or only summarize afterward for the first version?
- Do we need a new `embodied_guidance` `CoachSurface`, or can the first version use `practice_followup` and `generic`?
- What safety states force the session into grounding or stop mode?

### Persistence

- What is the minimum explicit write set: body state, practice outcome, reflection, or active imagination note?
- Should training loops remain `PracticeSessionRecord`-based, or later get a dedicated template library?
- What user action converts active imagination from temporary capture into stored material?

---

## Non-Goals

- No diagnosis.
- No therapy simulator.
- No hidden camera memory.
- No automatic symbolic interpretation from movement.
- No unbounded habit tracker.
- No raw video in Circulatio.
- No camera data inside ritual completion events.
