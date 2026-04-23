# Hermes Rituals Implementation Plan

## Purpose

This document turns the embodied presentation direction into an implementation plan.

It does not replace the backend architecture in `Circulatio`. It defines how to build a host-rendered presentation layer on top of existing symbolic runtime surfaces:
- hold-first storage
- `intakeContext`
- `ThreadDigest`
- journeys
- `alive_today`
- review and living-myth surfaces

The product-facing frame is:

```text
Hermes Rituals turns dreams, body states, recurring symbols, and emerging life threads
into guided rituals, symbolic broadcasts, and cinematic renderings.
```

## Product Families

Hermes Rituals should be treated as one system with three render families:

- `Rituals`: guided sessions and symbolic containers
- `Broadcasts`: serialized or periodic companion voice
- `Cinema`: audiovisual renderings of the same symbolic material

These are not separate intelligence systems. They are different host renderings of shared derived context.

## Jobs To Be Done

### Capture and hold

- When I wake up with a dream or body impression, help me capture it quickly by voice or text and hold it without forcing meaning.
- When I do not want interpretation yet, let the system acknowledge and retain the material while staying close to the immediate feeling-tone.

### Stay with one image

- When one image, figure, or body-feeling feels alive, guide me into a short contained ritual, dream return, or active-imagination container.
- When I am activated or overwhelmed, offer a paced breath-led or body-led container rather than symbolic overreach.

### Sense continuity

- When something is recurring across dreams, body states, or reflections, help me feel continuity gently through thread-aware rituals or broadcasts.
- When a journey is already active, let new material fold into it without making me reconstruct the context manually.

### Receive a shareable artifact

- When I want something beautiful and legible, turn the same symbolic material into text, audio, subtitles, image, and cinematic rendering.
- When I want to return later, let me resume the same artifact or thread from a stable URL.

## Primary User Stories

These stories are intentionally more concrete than the JTBD. They should drive route design, component boundaries, and backend contract priorities.

`V1` stories are the minimum set the first frontend should be able to express convincingly.

### Capture

- `V1` As a user waking from a dream, I want to speak it immediately into the system so I can capture it before it fades.
- `V1` As a user with a fresh dream or body impression, I want to lightly edit the transcript before saving so the captured material still feels like mine.
- `V1` As a user who is not asking for meaning yet, I want the system to acknowledge and hold what I shared without escalating into interpretation.
- As a user who cannot speak aloud, I want to enter the same material by text and move into the same artifact flow.

### Rituals

- `V1` As a user with one vivid dream image, I want the system to turn it into a short guided ritual with voice, transcript, and breath pacing.
- `V1` As a user returning to a charged symbol or figure, I want a dream-return ritual that stays with that image rather than generalizing too quickly.
- `V1` As a user who feels activated or overwhelmed, I want a containment-first ritual that slows me down before offering symbolic depth.
- As a user in an active process or threshold, I want the ritual mode to shift toward threshold-crossing or body-descent when that is more appropriate than reflection.

### Broadcasts

- `V1` As a user asking what feels alive lately, I want a short myth-weather style broadcast built from recent symbolic material.
- As a user with an active journey, I want new material to fold into a journeycast so I can feel continuity across days or weeks.
- As a user looking back on the week, I want a symbolic audio letter or review broadcast that notices patterns cautiously without overclaiming.

### Cinema

- `V1` As a user who wants a more cinematic rendering, I want one dream or ritual to become a narrated audiovisual artifact with captions and scene cards.
- As a user who wants to share something beautiful, I want to export a ritual or dream rendering as a video without losing the symbolic atmosphere.

### Continuity

- `V1` As a returning user, I want to open a ritual URL later and resume the same artifact and thread rather than starting from scratch.
- As a user with recurring material, I want the system to show gentle continuity between this artifact and an existing journey or thread without forcing interpretation.

### Live Follow-up

- As a user responding to a ritual prompt, I want to answer by voice and have the next artifact adapt from that reply.
- As a user moving from playback into conversation, I want to continue in a live companion session without losing the symbolic context of the current artifact.

## User Story Priority

The first implementation should satisfy these `V1` stories before expanding surface area:

- speech capture from a fresh dream or body-state
- transcript review and save
- hold-first acknowledgement
- ritual generation from anchored fresh material
- containment-aware ritual playback with transcript and breath pacing
- myth-weather or short broadcast generation
- one cinematic rendering path
- stable artifact resume via URL

## Non-Goals

- Do not turn Circulatio into a generic wellness app.
- Do not silently escalate hold-first storage into interpretation.
- Do not add heuristic symbol classification or keyword routing.
- Do not build a second symbolic backend in the web app.
- Do not embed Hermes CLI into the website.
- Do not start with immersive 3D as the primary experience.

## Existing Foundations

The current repo already contains the symbolic substrate this plan should build on:

- hold-first storage for dreams, reflections, events, symbolic notes, and body states
- additive host-only `intakeContext` at store time
- derived `ThreadDigest` as a unifying read model across journeys, dream series, loops, tensions, and longitudinal threads
- journey containers and journey-page surfaces
- `alive_today`, discovery, review, threshold, living-myth, and analysis-packet workflows
- Hermes bridge and plugin surfaces for host routing

Hermes Rituals should reuse these surfaces rather than creating parallel record families.

## Core Principles

- Text is canonical. Audio, subtitles, and video are renderings of typed plans.
- Hermes owns routing, session handoff, and user-facing orchestration.
- Circulatio owns durable records, context derivation, evidence-bound planning, and privacy policy.
- Web surfaces render typed artifacts and should not contain symbolic inference logic.
- Pattern references remain factual and tentative unless the user explicitly asks for interpretation.
- The same symbolic source should be renderable as a ritual, broadcast, or cinematic artifact.

## System Model

### Backend responsibilities

`Circulatio` should:
- store material
- derive `intakeContext`
- derive `ThreadDigest`
- assemble the symbolic context bundle for presentation
- choose or recommend a `RitualMode`
- emit a typed `PresentationArtifact`

### Host responsibilities

`Hermes` should:
- recognize user intent
- decide when to store, interpret, review, or generate a presentation artifact
- call Circulatio workflows
- return a stable artifact URL plus identifiers
- optionally re-open or continue a session later

### Web responsibilities

`Hermes Rituals web` should:
- render the artifact
- capture voice or text follow-up
- play audio
- show transcript and subtitles
- render breath pacing and ambient motion
- export cinematic compositions

## Product Surfaces

### Rituals

Primary ritual modes:
- `holding`
- `dream_return`
- `active_imagination`
- `threshold`
- `body_descent`
- `night_closure`
- `morning_omen`

Rituals are the experiential container. They answer:

```text
What kind of experience should this symbolic moment become?
```

### Broadcasts

Primary broadcast types:
- `myth_weather`
- `journeycast`
- `weekly_symbolic_letter`
- `review_broadcast`

Broadcasts are the serialized companion voice. They answer:

```text
What ongoing voice should accompany the user across days or weeks?
```

### Cinema

Primary cinema types:
- `dream_cinema`
- `ritual_cinema`
- `journey_render`
- `review_render`

Cinema is the audiovisual rendering surface. It answers:

```text
How should the same symbolic material be rendered beautifully and legibly?
```

## Runtime Flow

### Core flow

```text
Hermes chat
-> Circulatio store / derive
-> intakeContext + ThreadDigest
-> PresentationArtifact plan
-> Hermes returns artifact URL
-> Hermes Rituals web renders artifact
-> user plays / resumes / exports
```

### Example ritual flow

```text
user shares dream
-> Hermes stores dream
-> Circulatio returns host-only intakeContext
-> Hermes requests ritual artifact
-> Circulatio emits ritual PresentationArtifact
-> Hermes returns /rituals/:artifactId
-> web page loads transcript, audio, breath cues, and controls
```

### Example broadcast flow

```text
user asks what feels alive lately
-> Hermes requests alive_today or review surface
-> Circulatio emits journey-aware broadcast artifact
-> Hermes returns /broadcasts/:artifactId
-> web page renders playable episode with transcript
```

### Example cinema flow

```text
user wants a dream rendered
-> Hermes requests cinema artifact from anchored source material
-> Circulatio emits subtitle and visual scene plan
-> web page renders preview and exportable composition
```

## Contracts

### PresentationArtifact

Suggested domain shape:

```text
PresentationArtifact
- id
- userId
- sessionId?
- sourceType
- mode
- title
- summary
- threadSummary?
- text
- voiceScript?
- speechMarkup?
- transcriptAlignment?
- audioPlan?
- visualPlan?
- breathCycleSpec?
- somaticAnimationSpec?
- deliveryPolicy
- privacyClass
- createdAt
```

### Source types

Initial supported `sourceType` values:
- `ritual_session`
- `journey_broadcast`
- `weekly_review`
- `alive_today`
- `threshold_invitation`
- `cinema_render`

### RitualMode

Suggested runtime enum:

```text
RitualMode
- holding
- dream_return
- active_imagination
- threshold
- body_descent
- night_closure
- morning_omen
```

### AudioChannelPlan

Suggested channel layout:

```text
AudioChannelPlan
- master
- voice
- ambient
- breath
- pulse
- music
```

Each channel should support:
- `muted`
- `gain`
- `autoplayAllowed`
- `duckingPolicy`

### BreathCycleSpec

Suggested shape:

```text
BreathCycleSpec
- inhaleMs
- holdMs
- exhaleMs
- restMs
- cycleCount?
- visualStyle
- audioCueStyle?
```

## Web Architecture

### Stack

Recommended presentation stack:
- `Next.js`
- `TypeScript`
- `shadcn/ui`
- `ElevenLabs UI`
- `Motion`
- `Remotion`

Recommended AI/media services:
- `Kimi K2.6` for composition and planning
- `ElevenLabs` for STT, TTS, transcript alignment, and voice UI

### Why this split

- `Circulatio` remains the symbolic brain
- `Hermes` remains the routing host
- the web app becomes the artifact surface

This keeps the product coherent and avoids pushing symbolic logic into the frontend.

### Routes

Recommended routes:
- `/capture/:sessionId`
- `/rituals/:artifactId`
- `/broadcasts/:artifactId`
- `/cinema/:artifactId`
- `/artifacts/:artifactId`
- `/live/:sessionId` later, not v1-critical

### ElevenLabs UI usage

Use the existing web components selectively:

- `Speech Input` for intake capture
- `Transcript Viewer` for synced transcript playback
- `Audio Player` for standard playback surfaces
- `Conversation` only for later live-companion flows

Do not let stock components define the full experience. `Hermes Rituals` should keep a custom `RitualPlayer` for channel mixing, breath sync, and symbolic pacing.

## Media UX

### Channel model

The first player should support:
- master mute
- per-channel mute
- per-channel gain
- ambient ducking under voice
- optional channel presets by ritual mode

Recommended channels:
- `voice`
- `ambient`
- `breath`
- `pulse`
- `music`

### Autoplay policy

Browser autoplay should be handled conservatively:
- page may auto-load text, visuals, and transcript
- ambient may begin muted if policy allows
- full audio begins on first user gesture when needed

### RitualPlayer

The custom player should unify:
- transcript progression
- audio channels
- breath ring timing
- progress and scrub
- play/pause
- export entry points

## Backend Changes

### Phase 1: Presentation contracts

Add:
- `src/circulatio/domain/presentation.py`
- workflow/result types for presentation artifacts

The implementation should remain derived and additive. No new durable symbolic record family should be introduced for threads.

### Phase 2: Artifact planning workflow

Add a service-layer workflow in `circulatio_service.py` that:
- accepts anchored material, journey, or review input
- assembles symbolic context from existing projections
- emits a `PresentationArtifact`

This planning workflow should reuse:
- `intakeContext`
- `ThreadDigest`
- journeys
- `alive_today`
- review surfaces

### Phase 3: Hermes bridge

Extend the Hermes bridge/plugin result contract to return:
- `artifactId`
- `sessionId`
- `mode`
- `url`

Hermes chat remains the entry point. The web app becomes the artifact surface.

### Phase 4: Media adapters

Add host-facing support for:
- TTS generation metadata
- transcript alignment
- image/cover render references
- cinema export requests

Text and plan persistence should remain primary. Audio/video bytes should be treated as ephemeral by default.

## Frontend Phases

### Phase A: Capture

Build `/capture/:sessionId` with:
- text input
- speech input
- body-state capture
- simple handoff into ritual generation

### Phase B: Rituals v1

Build `/rituals/:artifactId` with:
- title and summary
- transcript
- custom ritual player
- breath ring
- per-channel mute
- simple ambient visuals

Initial ritual modes:
- `holding`
- `dream_return`
- `threshold`

### Phase C: Broadcasts v1

Build `/broadcasts/:artifactId` with:
- episode-style playback
- transcript
- cover card
- queue or chapter layout

Initial broadcast types:
- `myth_weather`
- `journeycast`

### Phase D: Cinema v1

Build `/cinema/:artifactId` with:
- subtitle timeline
- scene card preview
- export flow via `Remotion`

Keep first cinema rendering polished and simple. Avoid full 3D in v1.

### Phase E: Live companion

Build `/live/:sessionId` later for:
- live STT
- live TTS
- conversational continuation

This should remain a separate mode from the ritual player.

## Repo Impact

Likely files/modules:

- `docs/EMBODIED_PRESENTATION_PLAN.md`
- `docs/ENGINEERING_GUIDE.md`
- `src/circulatio/domain/presentation.py`
- `src/circulatio/application/workflow_types.py`
- `src/circulatio/application/circulatio_service.py`
- `src/circulatio/hermes/agent_bridge_contracts.py`
- `src/circulatio/hermes/agent_bridge.py`
- `src/circulatio_hermes_plugin/schemas.py`
- a new web app, likely under `apps/` or similar

## Testing Plan

### Backend tests

Add tests for:
- presentation artifact planning from fresh material
- ritual mode selection from bounded context
- broadcast artifact generation from `alive_today` and journey surfaces
- cinema artifact planning from anchored material
- privacy and local/cloud synthesis policy handling

### Bridge tests

Add tests for:
- URL and artifact identifiers in bridge responses
- host-only vs user-visible fields
- stable session continuation handoff

### Web tests

Add tests for:
- transcript rendering
- player controls
- per-channel mute
- autoplay-safe startup
- route hydration from `artifactId`

## Acceptance Criteria

- Hermes chat can create a stable ritual URL from fresh material.
- The ritual page loads from a typed artifact without extra manual host composition.
- A user can speak a dream, receive a ritual, and play it back in one flow.
- Recurrent material can become a journey-aware broadcast.
- The same source can render as text, audio, and cinema.
- Hold-first behavior remains intact.

## Hackathon MVP

If the immediate goal is a compelling demo, the first cut should be:

- speech or text capture
- ritual artifact planning
- one ritual URL
- transcript + TTS + ambient + breath ring
- one broadcast type
- one cinema type

Recommended flagship flow:

```text
dream or body-state capture
-> ritual artifact plan
-> ritual playback page
-> optional cinema export
```

This is enough to show:
- creativity
- usefulness
- strong presentation
- real Hermes/Circulatio depth

## Open Questions

- Should `PresentationArtifact` be persisted fully, or should some media fields remain transient only?
- Which voice providers are allowed by privacy class?
- Should cinema exports be stored, or generated on demand?
- Should journey broadcasts be generated proactively, on-demand, or both?
- How much of the composition step should be Kimi-driven versus Circulatio-structured?

## Recommended Sequence

1. Add presentation contracts and workflow types.
2. Add backend artifact planning in Circulatio.
3. Add Hermes bridge URL/session support.
4. Build the Rituals web app with capture and ritual playback.
5. Add broadcasts.
6. Add cinema export.
7. Add live companion mode later.

## Further Evolution

Hermes Rituals should be treated as the first premium surface of a broader future `Hermes Agent OS`, not as a dead-end standalone fork.

The intended layering is:

```text
Circulatio = symbolic backend and durable context
Hermes = host agent and routing layer
Hermes Rituals = first artifact and media surface
Hermes Agent OS = later broader operating surface
```

If the product later expands, `Hermes Rituals` can become one module inside a larger operating system that also includes:
- `Rituals`
- `Broadcasts`
- `Cinema`
- `Journeys`
- `Reviews`
- `Memory`
- `Live`

To preserve that path, the implementation should stay:
- contract-driven
- session-based
- artifact-based
- componentized
- routeable beyond ritual-only metaphors

This means:
- prefer generic contracts like `PresentationArtifact`, `ArtifactSession`, and `ThreadDigest`
- avoid baking all infrastructure around meditation-only or ritual-only naming
- keep the web app capable of adding broader workspace, journey, review, and memory surfaces later
- keep `Hermes Rituals` emotionally strong while leaving room for `Hermes Agent OS` to absorb it cleanly

## Final Boundary

Hermes Rituals should make the system feel alive without moving the symbolic center of gravity out of Circulatio.

The right architecture is:

```text
Circulatio derives
Hermes routes
Hermes Rituals renders
```

That keeps the backend evidence-bound and consent-bound while still allowing the product to become audible, visible, embodied, and beautiful.
