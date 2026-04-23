# Embodied Presentation Plan

## Purpose

Circulatio should not be framed as adding generic multimodal features. The right frame is an **Embodied Presentation & Ritual Media Layer**.

Product-facing, this can be understood as **Hermes Rituals**:
- **Rituals** for guided sessions
- **Broadcasts** for podcast / daily myth weather
- **Cinema** for audiovisual renderings

Circulatio does not only answer. It can speak, pause, breathe, invite, and create symbolic interaction containers.

This layer exists to support individuation work, not to turn Circulatio into a wellness app, frontend animation system, or notification engine.

These should not be treated as separate products stitched together later. They are three presentation families rendered from the same symbolic backend:
- **Rituals** are the experiential container
- **Broadcasts** are the serialized or periodic companion voice
- **Cinema** is the audiovisual rendering surface

The backend remains responsible for symbolic context, timing, consent, and evidence-bound framing. Hosts remain responsible for rendering and delivery.

## Product Frame

The clean external story is not:

```text
Circulatio adds TTS, visuals, and maybe podcasts
```

It is:

```text
Hermes Rituals turns dreams, body states, recurring symbols, and emerging life threads into guided rituals, symbolic broadcasts, and cinematic renderings.
```

Operationally:
- intake gives the system fresh symbolic material
- thread-awareness determines what is actually alive
- ritual mode selection determines what kind of container is appropriate
- presentation rendering determines whether the artifact becomes a spoken ritual, a journey broadcast, or a cinematic piece

This keeps the architecture coherent:
- **Rituals** answer: what kind of experience should this become?
- **Broadcasts** answer: what ongoing voice should accompany the user across days or weeks?
- **Cinema** answers: how should the same symbolic material be rendered beautifully and legibly?

The key architectural point is that these are not separate intelligence systems. They are different host renderings of shared derived context.

## Core Rule

Circulatio emits **typed presentation plans**. Hosts render them.

Circulatio produces:
- text
- voice script
- speech markup plan
- breath / animation spec
- association interaction spec
- delivery policy

Hosts render:
- audio
- animation
- interactive cards
- subtitles
- video compositions
- notifications
- dashboard surfaces
- CLI or app delivery

Circulatio should remain backend-first, consent-bound, LLM-first, and evidence-bound.

Current backend implication:
- Coach-facing runtime surfaces can now emit typed `resourceInvitation` payloads from `coachState`, but those invitations stay curated, provenance-bound, and host-rendered. They are not arbitrary media lookup or recommendation flows.

## Roadmap Placement

**Current runtime status (April 2026):** The core backend/runtime through the living-myth layer is now implemented. The current embedded Hermes fit also includes read-mostly journey pages, label-addressable lightweight journey containers, explicit `/circulation journey ...` QA commands, and a repo-owned external Hermes-host smoke harness. This document remains a later presentation/runtime track layered on top of those symbolic and consent-bound workflow surfaces.

This should not replace Phase 8 or 9.

Recommended sequence:
- Phase 6: Practice Engine & Adaptation Learning
- Phase 7: Rhythmic Companion Runtime
- Phase 7.5: Embodied Presentation Contract
- Phase 8: Teleological Individuation Layer
- Phase 9: Living Myth & Integration Layer
- Phase 10: Embodied Companion Runtime

Why:
- Phase 7.5 adds typed presentation contracts without committing to any host runtime.
- Phases 8 and 9 provide deeper symbolic content.
- Phase 10 adds actual TTS adapters, local audio generation, breath sync, MCP rendering, or standalone host rendering.

## Naming Principles

### Product-facing

Prefer:
- Hermes Rituals
- rituals
- broadcasts
- cinema
- journeycast
- dream cinema
- myth weather
- spoken rhythmic invitation
- breath container
- somatic visual guide
- association circle
- active imagination container
- rhythmic invitation
- mythic state mirror
- rhythm keeper

Avoid:
- multimodal output
- content verticals
- podcast feature
- video mode
- wellness animation
- word-association test
- guided meditation product
- proactive notification

### Engineering-facing

Prefer:
- `PresentationArtifact`
- `VoiceScript`
- `SpeechMarkupPlan`
- `VoiceDeliveryPlan`
- `SomaticAnimationSpec`
- `BreathCycleSpec`
- `AssociationProtocol`
- `AssociationSessionRecord`
- `AssociationResponseRecord`
- `RhythmicPresentationPlan`
- `InvitationDeliveryPolicy`

Avoid:
- `WellnessAnimation`
- `MeditationPlayer`
- `WordAssociationTest`
- `SelfScoreDashboard`
- `TherapyMode`

## Phase 7.5: Embodied Presentation Contract

This phase adds no TTS dependency, frontend, or scheduler.

### New module

`src/circulatio/domain/presentation.py`

### Core types

```text
PresentationArtifact
VoiceScript
SpeechMarkupPlan
SomaticAnimationSpec
BreathCycleSpec
AssociationProtocol
PresentationDeliveryPolicy
```

### Conceptual shape

```text
PresentationArtifact
- id
- userId
- sourceType:
    ritual_session
    interpretation
    practice
    rhythmic_brief
    journey_broadcast
    weekly_review
    alive_today
    threshold_invitation
    cinema_render
- text
- voiceScript?
- speechMarkup?
- mediaSpecs[]
- interactionSpec?
- deliveryPolicy
- privacyClass
- createdAt
```

## Voice Design

Use `VoiceDeliveryPlan`, not `TTSOutput`.

### Voice script

```text
VoiceScript
- segments[]
- tone:
    steady
    gentle
    clear
    warm
    holding
    neutral
- pace:
    normal
    measured
    slow
- pausePolicy
- silenceMarkers[]
- contraindications[]
```

The LLM should not emit raw SSML as canonical output. It should emit structured voice intent. Deterministic code can then render safe SSML or plain-text pause instructions.

### Voice provider tiers

- `NoopVoiceAdapter`
- `LocalSystemVoiceAdapter`
- `PiperVoiceAdapter`
- `CloudVoiceAdapter`

Default privacy rule:
- dream content
- active imagination scripts
- raw associations

should use local TTS only unless the user explicitly allows cloud synthesis.

Audio should be ephemeral by default.

Persist:
- text
- voice script
- speech markup
- provider metadata
- checksum

Do not persist audio by default.

## Breath And Animation Design

Use breath and animation only where they deepen containment.

Default use cases:
- grounding practice
- somatic tracking
- body check-in
- active imagination container
- high-activation resource invitation
- breath-based practice follow-up

### Breath cycle spec

```text
BreathCycleSpec
- inhaleSeconds
- holdSeconds
- exhaleSeconds
- restSeconds
- cycles
- pattern:
    steadying
    lengthened_exhale
    box_breath
    orienting
- visualForm:
    orb
    wave
    mandala
    horizon
- syncMarkers[]
```

### Somatic animation spec

```text
SomaticAnimationSpec
- type:
    breath_cycle
    focus_orb
    grounding_scan
    image_holding
    threshold_marker
- durationSeconds
- keyframes
- timing
- accessibilityFallbackText
- reducedMotionFallback
```

Hosts map this to actual animation systems. Circulatio should not own rendering code.

## Association Circle

Do not call it a word-association test.

Use:
- `AssociationCircle`
- `AssociationProtocol`
- `AssociationSessionRecord`
- `AssociationResponseRecord`

It exists for personal amplification and symbolic charge, not diagnosis.

### Protocol shape

```text
AssociationProtocol
- protocolType:
    personal_symbol_association
    dream_image_association
    opposition_association
    numinous_image_association
    threshold_association
- stimuli[]
- captureReactionTime: boolean
- captureBodyResponse: boolean
- reproductionRound: boolean
- maxStimuli
- safetyBoundary
```

```text
AssociationResponseRecord
- stimulusId
- responseText
- reactionTimeMs?
- hesitationObserved?
- skipped?
- bodySensation?
- feelingTone?
- userMarkedCharged?
```

Allowed deterministic observations:
- response skipped
- response delayed
- user marked charged
- repeated association returned
- body sensation reported

Not allowed deterministically:
- this proves a complex
- this reveals trauma
- this is mother archetype
- this means repression

LLM may later turn the session into a tentative, evidence-bound hypothesis.

## Delivery Policy

```text
PresentationDeliveryPolicy
- deliveryMode:
    inline
    spoken_optional
    spoken_default
    visual_optional
    visual_default
    silent_hold
- requiresConsent
- consentScope
- depthHoursOnly
- quietHoursRespected
- ephemeralAudio
- cloudSynthesisAllowed
```

This keeps proactivity safe and host-independent.

## Presentation Engine

New module:

`src/circulatio/core/presentation_engine.py`

Responsibilities:
- build presentation artifacts from LLM voice/media directives
- clamp timing
- escape SSML
- validate media specs
- add reduced-motion fallbacks
- decide whether voice/animation is eligible

It is deterministic only for presentation safety and formatting.

Allowed:
- clamp unsafe pauses or durations
- escape unsafe markup
- disable cloud voice when consent is missing
- disable animation for reduced-motion settings

Not allowed:
- symbolic interpretation
- choosing media based on metaphysical claims
- forcing association or animation because a complex is suspected

## Proactivity With Embodied Media

Use invitation types, not notifications.

### Spoken Rhythmic Invitation
Trigger:
- daily or weekly rhythm
- review due
- practice follow-up due

### Somatic Resource Invitation
Trigger:
- high activation
- repeated skipped practices
- charged material
- grounding is more appropriate than depth work

Contract note:
- resource invitations should be emitted as typed summaries with capture metadata
- hosts decide whether to render them as cards, links, audio, or later voice/breath containers
- the catalog must stay curated and local/configured, not search-derived

### Association Circle Invitation
Trigger:
- returning symbol
- unanswered amplification prompt becomes ripe again
- same image appears across dream, body, and goal tension

### Threshold Holding Invitation
Trigger:
- threshold marker
- emergent third signal
- dream-sequence turning point
- numinous encounter

### Bridge Practice Invitation
Trigger:
- opposition active long enough
- a third possibility appears
- user performs a bridging action

## File Impact

### New files

- `src/circulatio/domain/presentation.py`
- `src/circulatio/domain/associations.py`
- `src/circulatio/core/presentation_engine.py`
- `src/circulatio/adapters/voice_adapter.py`

Optional later:
- `src/circulatio/adapters/piper_voice_adapter.py`
- `src/circulatio/adapters/system_voice_adapter.py`
- `src/circulatio/hermes/rhythm_tick.py`
- `src/circulatio_mcp_server/`

### Modified files

- `src/circulatio/domain/practices.py`
- `src/circulatio/domain/proactive.py`
- `src/circulatio/domain/types.py`
- `src/circulatio/llm/contracts.py`
- `src/circulatio/llm/prompt_builder.py`
- `src/circulatio/core/circulatio_core.py`
- `src/circulatio/application/circulatio_service.py`
- `src/circulatio/repositories/circulatio_repository.py`

## Stage Plan

### Stage 1: Presentation Contract
Build:
- `PresentationArtifact`
- `VoiceScript`
- `SpeechMarkupPlan`
- `BreathCycleSpec`
- `SomaticAnimationSpec`
- `AssociationProtocol`
- `PresentationEngine`

No TTS dependency, no frontend, no scheduler.

### Stage 2: Practice + Brief Presentation
Connect presentation artifacts to:
- `PracticePlan`
- `PracticeSessionRecord`
- `ProactiveBriefRecord`
- rhythmic brief results

Start with:
- spoken rhythmic invitation
- active imagination voice script
- breath container media spec
- first ritual session templates
- first broadcast template for daily myth weather / journeycast

### Stage 3: Association Circle
Build:
- `AssociationSessionRecord`
- `AssociationResponseRecord`
- `start_association_circle()`
- `record_association_response()`
- `complete_association_circle()`

### Stage 4: Optional TTS Adapters
Add:
- `NoopVoiceAdapter`
- `SystemVoiceAdapter`
- `PiperVoiceAdapter`
- `CloudVoiceAdapter`

### Stage 5: Host Rhythm Contract
Expose:
- `run_rhythm_tick(input) -> RhythmTickResult`

Hermes, cron, MCP, CLI, or standalone runtime calls it. Circulatio should not own time itself.

### Stage 6: MCP / Universal Agent Output
Expose presentation artifacts as structured tool output.

This is the point where the host can start treating a single symbolic result as one of several render families:
- ritual
- broadcast
- cinema

### Stage 7: Standalone Runtime
Later host/runtime work can render:
- text
- local TTS
- CLI breath timing
- simple local notifications
- association sessions
- journey broadcasts
- dream cinema / subtitle-driven audiovisual pieces

## Final Boundary

Circulatio should evolve from:

```text
text interpretation backend
```

to:

```text
symbolic backend that emits embodied, voice-aware, breath-aware, interaction-ready presentation plans
```

but not into:
- frontend app
- notification engine
- therapy simulator
- guided meditation product
- clinical test platform

The best summary is:

> Circulatio remains backend-pure, LLM-first, consent-bound, and evidence-bound. Through Hermes Rituals, it learns when a moment should become a guided ritual, a companion broadcast, a cinematic rendering, be spoken plainly, breathed with, held in silence, or explored through association.
