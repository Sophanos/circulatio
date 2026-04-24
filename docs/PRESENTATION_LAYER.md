# Presentation Layer
## Embodied Presentation Contract

> **Status:** Phase 1 plan-only ritual delivery is implemented for local/static playback. Circulatio emits typed ritual plans, the repo-local renderer CLI turns those plans into static artifact manifests, and the Hermes Rituals frontend can play the manifest. The renderer now has explicit Chutes provider profiles for speech, captions, image, music, and video, but those calls remain opt-in, budget-gated, and renderer-owned. Scheduled ritual invitations, completion sync, and any server/job system remain later work. Circulatio still does not own frontend rendering as a backend responsibility.

Circulatio should evolve from a text interpretation backend into a **symbolic backend that emits embodied, voice-aware, breath-aware, interaction-ready presentation plans**. Hosts render them; Circulatio does not own frontend code.

The product-facing frame is **Hermes Rituals**:
- **Rituals** — guided sessions and symbolic containers
- **Broadcasts** — serialized or periodic companion voice
- **Cinema** — audiovisual renderings of the same symbolic material
- **Breath surface** — simple respiratory pacing for inhale, hold, exhale, and rest
- **Meditation surface** — non-respiratory settling for coherence, attention, and symbolic containment

These are not separate intelligence systems and not separate backend tool calls. They are different host renderings of shared derived context, enabled by arguments on one presentation-planning call.

---

## Core Rule

Circulatio emits **typed presentation plans**. Hosts render them.

Circulatio produces:
- text
- voice script
- speech markup plan
- breath / meditation / animation spec
- association interaction spec
- delivery policy

Hosts render:
- audio
- animation
- interactive cards
- subtitles
- video compositions
- breath pacers
- meditation fields
- notifications
- dashboard surfaces

Current backend implication:
- Coach-facing runtime surfaces can now emit typed `resourceInvitation` payloads from `coachState`, but those invitations stay curated, provenance-bound, and host-rendered. They are not arbitrary media lookup or recommendation flows.
- Ritual planning is a read-only presentation compiler over existing Circulatio surfaces. It creates no material, no interpretation run, no weekly review record, and no media blob.

---

## Backend Contracts

### Phase 1 Local Artifact Flow

```text
Hermes host/tool call
-> circulatio.presentation.plan_ritual
-> PresentationRitualPlan JSON
-> scripts/render_ritual_artifact.py --mock-providers --dry-run
-> hermes_ritual_artifact.v1 manifest.json
-> Hermes Rituals frontend /artifacts/{artifactId}
```

Phase 1 enabled surfaces are text, voiceScript-as-plan, captions, breath, and meditation. Audio is mock/placeholder by default. Chutes provider-backed speech, captions, image, music, and video are available only when the renderer is called with an explicit `--provider-profile chutes_*`, a positive `--max-cost-usd`, an API token in `CHUTES_API_TOKEN` or the configured token env var, and a plan that does not disable external providers. Circulatio still emits plans only; it does not call Chutes or store media blobs.

### PresentationArtifact (planned)

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

### VoiceScript (planned)

```text
VoiceScript
- segments[]
- tone: steady | gentle | clear | warm | holding | neutral
- pace: normal | measured | slow
- pausePolicy
- silenceMarkers[]
- contraindications[]
```

The LLM should not emit raw SSML as canonical output. It should emit structured voice intent. Deterministic code can then render safe SSML or plain-text pause instructions.

### BreathCycleSpec (planned)

```text
BreathCycleSpec
- inhaleSeconds
- holdSeconds
- exhaleSeconds
- restSeconds
- cycles
- pattern: steadying | lengthened_exhale | box_breath | orienting
- visualForm: pacer | wave | mandala | horizon
- syncMarkers[]
```

`pattern` is the normalized breathing shape used by the runtime. `techniqueName` is the user-facing or host-requested technique label when one is explicitly wanted, including named forms such as prana-derived breathing or other custom practices. If the technique matters, the host should either carry the user's explicit preference or ask. Circulatio may suggest a fit, but the host owns whether to surface that suggestion, ask a clarifying question, or fall back to a neutral steadying pattern.

Breath tools should make the respiratory instruction legible. A default pacer can use one restrained grey ring: inhale expands, hold rests at maximum radius, exhale contracts, and rest quiets. Any vibration or edge pulse is a timing cue, not a symbolic interpretation.

### MeditationFieldSpec (planned)

```text
MeditationFieldSpec
- fieldType:
    coherence_convergence
    attention_anchor
    threshold_stillness
    image_afterglow
- durationMs
- sourceRefs[]
- macroProgressPolicy:
    session_progress
    section_progress
    untimed
- microMotion:
    still
    pulse
    convergence
    shimmer
- instructionDensity:
    none
    sparse
    phase_label
- safetyBoundary
- syncMarkers[]
```

Meditation fields are not breath instructions. They can borrow the same playback clock, but their job is containment, attention, and symbolic settling. For example, a coherence convergence field can let scattered traces slowly gather into one ring across the session while small phase-linked pulses keep the field alive.

### AssociationProtocol (planned)

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

---

## Tool Calling Contract (planned)

Embodied presentation should arrive through one explicit host bridge/tool call, not through a generic "make media" ingress and not through one backend tool per visual mode.

The tool call plans a ritual. Its arguments decide which surfaces are available for the host to render. Breath and meditation remain semantically distinct inside the same call:

```text
circulatio.presentation.plan_ritual

input
- sourceRefs[]
- ritualIntent:
    hold_container
    guided_ritual
    breath_container
    meditation_container
    image_return
    active_imagination_container
- narrativeMode:
    full_guided
    sparse_guided
    breath_only
    meditation_only
    user_script
    hybrid
- requestedSurfaces:
    breath:
      enabled: boolean
      request?: BreathCycleSpec
    meditation:
      enabled: boolean
      request?: MeditationFieldSpec
    photo:
      enabled: boolean
    cinema:
      enabled: boolean
    audio:
      enabled: boolean
- privacyClass
- safetyContext
- deliveryPolicy
```

`requestedSurfaces.breath.request` asks for respiratory pacing. `requestedSurfaces.meditation.request` asks for a settling field or attention container. The host may render both in one ritual from the same tool response, but the tool call keeps them semantically separate so a meditation visual does not silently become a breathing instruction.

### Experience Stories

- A user says, "I only need help breathing for a minute." The host calls `plan_ritual` with `narrativeMode=breath_only` and `requestedSurfaces.breath.enabled=true`, then renders a minimal pacer with inhale, hold, exhale, and rest labels.
- A user brings a charged dream image but does not want interpretation yet. The host calls the same planner with `requestedSurfaces.meditation.enabled=true` and renders a coherence field that settles attention without turning the image into advice.
- A user pauses midway through a ritual because the material feels too strong. The host can switch from cinema or narration into a meditation surface returned by the same plan, preserving the same timeline while reducing verbal density.
- A user already has a breathing practice and names it directly. The host carries that explicit preference in `requestedSurfaces.breath.request` instead of letting Circulatio infer a technique from keywords.
- A user wants the image, music, and breath all present. The host enables multiple `requestedSurfaces` in one tool call, but Circulatio still returns typed specs; the host decides whether to expose lens switching, queue controls, or a single focused surface.

---

## Naming Principles

### Product-facing

Prefer:
- Hermes Rituals, rituals, broadcasts, cinema, journeycast, dream cinema, myth weather
- spoken rhythmic invitation, breath container, somatic visual guide, association circle
- active imagination container, rhythmic invitation, mythic state mirror, rhythm keeper

Avoid:
- multimodal output, content verticals, podcast feature, video mode
- wellness animation, word-association test, guided meditation product, proactive notification

### Engineering-facing

Prefer:
- `PresentationArtifact`, `VoiceScript`, `SpeechMarkupPlan`, `VoiceDeliveryPlan`
- `SomaticAnimationSpec`, `BreathCycleSpec`, `AssociationProtocol`
- `AssociationSessionRecord`, `AssociationResponseRecord`, `RhythmicPresentationPlan`
- `InvitationDeliveryPolicy`

Avoid:
- `WellnessAnimation`, `MeditationPlayer`, `WordAssociationTest`, `SelfScoreDashboard`, `TherapyMode`

---

## Roadmap Placement

Recommended sequence:
- Phase 6: Practice Engine & Adaptation Learning ✅
- Phase 7: Rhythmic Companion Runtime ✅
- Phase 7.5: Embodied Presentation Contract (this document)
- Phase 8: Teleological Individuation Layer ✅
- Phase 9: Living Myth & Integration Layer ✅
- Phase 10: Embodied Companion Runtime (future host/runtime work)

Why:
- Phase 7.5 adds typed presentation contracts without committing to any host runtime.
- Phases 8 and 9 provide deeper symbolic content.
- Phase 10 adds actual TTS adapters, local audio generation, breath sync, MCP rendering, or standalone host rendering.

---

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
