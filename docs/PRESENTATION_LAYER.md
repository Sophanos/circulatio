# Presentation Layer
## Embodied Presentation Contract

> **Status:** Phase 1 plan-only ritual delivery is implemented for local/static playback. Circulatio emits typed ritual plans, the repo-local renderer CLI turns those plans into static artifact manifests, and the Hermes Rituals frontend can play those manifests. Provider-backed rendering remains opt-in, budget-gated, and renderer-owned. Phase 2 adds scheduled ritual invitations only. Phase 3 adds idempotent completion sync and provider hardening. Circulatio still does not own frontend rendering, cron, consent prompting, delivery, or external media calls.

Circulatio should evolve from a text interpretation backend into a **symbolic backend that emits embodied, voice-aware, breath-aware, interaction-ready presentation plans**. Hosts render them; Circulatio does not own frontend code.

The product-facing frame is **Hermes Rituals**:
- **Rituals** - guided sessions and symbolic containers
- **Broadcasts** - serialized or periodic companion voice
- **Cinema** - audiovisual renderings of the same symbolic material
- **Breath surface** - simple respiratory pacing for inhale, hold, exhale, and rest
- **Meditation surface** - non-respiratory settling for coherence, attention, and symbolic containment

These are not separate intelligence systems and not separate backend tool calls. They are different host renderings of shared derived context, enabled by arguments on one presentation-planning call.

---

## Ownership Boundary

### Circulatio owns

- Durable individuation records
- Source context derivation
- Typed ritual plans
- Ritual invitation domain records
- Completion domain records
- Evidence-backed synthesis and interpretation when explicitly requested
- Practice, review, body-state, goal, symbol, and pattern persistence

### Hermes owns

- Natural-language intent recognition
- Consent checks and consent UX
- Cron and proactive scheduling
- Tool selection and routing
- Manual acceptance of invitations
- Delivery surfaces and notification timing
- Returning artifact URLs to the user

### Renderer owns

- Provider calls
- Provider cache
- Rendering manifests
- Static artifacts
- Fallback captions
- Budget gates
- Raw-material provider guards
- Video and music provider gates

### Frontend owns

- Artifact playback
- Completion capture
- Completion route validation before host forwarding
- Stable completion IDs
- User-authored reflection submission
- Explicit practice feedback UI

Circulatio is the backend symbolic contract. Hermes decides when the contract should be invoked. The renderer turns a plan into files. The frontend plays the files and captures user action.

---

## Core Rules

Circulatio emits **typed presentation plans**. Hosts render them.

Circulatio produces:
- text
- voice script
- speech markup plan
- breath, meditation, and animation specs
- association interaction specs
- delivery policy
- source references
- ritual invitation summaries
- ritual completion events

Hosts and renderers produce:
- audio
- animation
- interactive cards
- subtitles
- video compositions
- breath pacers
- meditation fields
- notifications
- dashboard surfaces
- artifact URLs

Hard boundaries:
- No scheduled planning.
- No scheduled rendering.
- No raw material text to external providers.
- No hidden interpretation during storage, planning, rendering, acceptance, or completion.
- No automatic practice router beyond the minimal safety fallback floor.
- No video by default.
- No music by default.
- No provider-backed render path without explicit provider, budget, and product gates.

Current backend implication:
- Coach-facing runtime surfaces can emit typed `resourceInvitation` payloads from `coachState`, but those invitations stay curated, provenance-bound, and host-rendered. They are not arbitrary media lookup or recommendation flows.
- Ritual planning is a read-only presentation compiler over existing Circulatio surfaces. It creates no material, no interpretation run, no weekly review record, no practice session, and no media blob.
- Weekly scheduled ritual invitations are proactive briefs. They are not ritual plans and not artifact render requests.

---

## Phase 1 Local Artifact Flow

```text
Hermes host/tool call
-> circulatio.presentation.plan_ritual
-> PresentationRitualPlan JSON
-> scripts/render_ritual_artifact.py --mock-providers --dry-run
-> hermes_ritual_artifact.v1 manifest.json
-> Hermes Rituals frontend /artifacts/{artifactId}
```

Phase 1 enabled surfaces are text, `voiceScript`-as-plan, captions, breath, and meditation. Audio is mock/placeholder by default. Chutes provider-backed speech, captions, image, music, and video are available only when the renderer is called with:
- an explicit `--provider-profile chutes_*`
- a positive `--max-cost-usd`
- an API token in `CHUTES_API_TOKEN` or the configured token env var
- a plan that does not disable external providers
- a renderer-side product gate that allows the requested surface

Circulatio still emits plans only. It does not call Chutes, does not store media blobs, and does not manage artifact cache.

### Phase 1 stabilization gate

Before Phase 2 starts, stabilize these leftovers:

1. Manual Hermes "save plan, run renderer, return URL" must become a real product path.
2. Completion UI and routes must not imply Circulatio sync until Phase 3 lands.
3. Fallback captions must remain first-class artifact output.
4. Music and video must remain behind stricter product gates.
5. Planned/deferred statuses in this document and linked docs must stay current.

---

## Phase 2 Scheduled Ritual Invitations

Phase 2 adds **weekly scheduled ritual invitations only**. Cron may create a rhythmic brief, but must not call `plan_ritual` and must not render media.

### New proactive brief type

Use a dedicated proactive brief type:

```text
ritual_invitation
```

Do not overload:
- `weekly`
- `resource_invitation`
- `practice`
- `alive_today`

The brief carries a typed `RitualInvitationSummary`. Hermes receives enough structured data to present an invitation and later resolve acceptance, without Circulatio producing a ritual plan prematurely.

### Scheduled flow

```text
Hermes cron
-> check proactive_briefing consent
-> circulatio_generate_rhythmic_briefs(source="scheduled")
-> ProactiveEngine emits ritual_invitation brief
-> Hermes delivers invitation only
```

Cron explicitly must not call:
- `circulatio.presentation.plan_ritual`
- `scripts/render_ritual_artifact.py`
- any provider-backed render path
- any frontend artifact completion path

### Manual acceptance flow

```text
User accepts
-> Hermes resolves brief
-> Hermes calls circulatio.presentation.plan_ritual
-> Circulatio returns PresentationRitualPlan
-> Hermes may run renderer manually
-> Hermes returns /artifacts/{artifactId}
```

User acceptance is the boundary between invitation and planning. Accepted planning is still read-only. It creates no material, no interpretation run, no weekly review, and no practice session.

### Invitation summary contract

```text
RitualInvitationSummary
- invitationId
- userId
- sourceRef
- title
- summary
- suggestedIntent
- suggestedSurfaces
- privacyClass
- cadence
- generatedAt
- expiresAt?
- acceptancePayload
```

`acceptancePayload` is for Hermes routing. It should contain enough stable references to call `circulatio.presentation.plan_ritual` after acceptance, not enough data to render media directly.

### Plan draft contract

```text
RitualInvitationPlanDraft
- sourceRefs[]
- ritualIntent
- narrativeMode
- requestedSurfaces
- privacyClass
- safetyContext
- deliveryPolicy
- defaultRenderPolicy
```

The draft is not a plan. It is a typed suggestion for a later accepted plan request.

### Phase 2 acceptance criteria

- Scheduled cron creates only a `ritual_invitation` brief.
- `proactive_briefing` consent is required.
- No scheduled planning or rendering occurs.
- Dedupe, cooldown, cadence, and scheduled max reuse existing rhythmic brief machinery.
- User acceptance is required before `circulatio.presentation.plan_ritual`.
- Accepted planning creates no material, interpretation run, weekly review, or practice session.
- Default accepted render policy disables external providers and video.
- Source references survive through the brief and accepted plan path.
- Raw material text is never exposed in proactive brief payloads.

---

## Phase 3 Completion Sync And Provider Hardening

Phase 3 adds **idempotent completion sync** and hardens provider rendering. Completion is an explicit user action or playback event. It is not interpretation.

### Completion flow

```text
Frontend POST /api/artifacts/{artifactId}/complete
-> validates manifest + idempotency key
-> forwards normalized payload to Hermes
-> Hermes dispatches circulatio.presentation.record_ritual_completion
-> Circulatio stores event idempotently
-> optional literal reflection material
-> optional explicit practice feedback
-> no interpretation run
```

The completion route must require either:
- `Idempotency-Key` header
- `completionId` in the request body

Replays with the same key and same normalized payload return the existing event. The same key with a different normalized payload is a validation error.

### Completion event contract

```text
RitualCompletionEvent
- id
- userId
- artifactId
- planId?
- sourceRefs[]
- idempotencyKey
- completedAt
- durationMs?
- playbackState:
    completed
    partial
    abandoned
- completedSections[]
- reflectionMaterialId?
- practiceFeedbackId?
- metadata
- createdAt
```

`reflectionMaterialId` is only present when the user explicitly authors a reflection. That reflection is stored literally. Recording completion must not trigger interpretation, symbol extraction, material classification, or practice suggestion.

`practiceFeedbackId` is only present when the user explicitly provides feedback about a practice. It is not inferred from playback.

### Completion input contract

```text
RecordRitualCompletionInput
- userId
- artifactId
- manifestVersion
- idempotencyKey
- completedAt
- playbackState
- durationMs?
- completedSections[]
- reflectionText?
- practiceFeedback?
- clientMetadata?
```

### Idempotency contract

Repository storage must be keyed by:

```text
(userId, idempotencyKey)
```

Rules:
- First valid request creates a completion event.
- Same key plus same normalized payload returns the existing event.
- Same key plus different normalized payload fails validation.
- Replays create no duplicate reflection material and no duplicate practice feedback.
- Missing idempotency key fails before Hermes dispatch.

This follows the general idempotency-key pattern for retry-safe POST side effects.

### Provider hardening

Provider hardening remains renderer-side:
- Chutes speech and image stay opt-in and budget-gated.
- Whisper/captions may fail transiently.
- Fallback captions from `voiceScript.segments` stay first-class.
- Fallback captions must be valid timed cue files.
- Music and video remain explicit beta/developer surfaces.
- Raw material text never goes to external providers.
- Video is never enabled by default.

### Phase 3 acceptance criteria

- Completion POST validates artifact, manifest, payload, and idempotency.
- Completion is stored as `RitualCompletionEvent`.
- Same idempotency key plus same payload creates no duplicate side effects.
- Same idempotency key plus different payload is rejected.
- Reflection is stored literally only when user-authored.
- Practice feedback is recorded only when explicitly provided.
- No interpretation is triggered.
- Caption fallback survives Whisper failure and writes WebVTT cues.
- Music and video remain off by default.
- External providers remain opt-in, budget-gated, and renderer-owned.

---

## Backend Contracts

### PresentationArtifact

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

### VoiceScript

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

### BreathCycleSpec

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

### MeditationFieldSpec

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

### AssociationProtocol

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

## Tool Calling Contract

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

Planning is read-only. It compiles a presentation plan from existing context and explicit source references.

Completion sync uses a separate operation:

```text
circulatio.presentation.record_ritual_completion

input
- RecordRitualCompletionInput

output
- RitualCompletionEvent
- replayed: boolean
```

Recording completion is a persistence action only. It must not call the interpretation engine.

---

## Hermes And Plugin Contract

Phase 2 Hermes/plugin impact:
- `agent_bridge_contracts.py` adds the `ritual_invitation` proactive payload shape.
- `command_router.py` may add optional `/circulation ritual accept` dispatch.
- `agent_bridge.py` routes accepted invitation planning only after manual acceptance.
- `tools.py`, `schemas.py`, and `plugin.yaml` expose only the necessary accepted planning path.
- `skills/circulation/SKILL.md` strengthens the scheduled invitation-only rule.

Phase 3 Hermes/plugin impact:
- `agent_bridge_contracts.py` adds `circulatio.presentation.record_ritual_completion`.
- `command_router.py` adds completion dispatch.
- `agent_bridge.py` routes the completion operation.
- `tools.py`, `schemas.py`, and `plugin.yaml` add a completion tool if plugin dispatch is used.
- Completion dispatch must preserve the no-interpretation rule.

Hermes must enforce consent before scheduled invitation delivery. Circulatio can validate inputs and privacy classes, but Hermes owns consent UX and delivery timing.

---

## Renderer Contract

Renderer-owned responsibilities:
- Extend artifact manifest `interaction` with completion flags.
- Populate stable completion fields for frontend use.
- Preserve fallback captions on Whisper failure.
- Keep provider calls isolated under provider adapters.
- Keep provider caches renderer-owned.
- Enforce budget gates before provider calls.
- Enforce raw prompt guards before provider calls.
- Keep video behind explicit beta/developer gates.
- Keep default weekly ritual artifacts text, breath, meditation, and captions only.

`contracts.py` should model completion fields in the manifest. `renderer.py` should fill them. `providers/chutes.py` should remain provider-specific and should not leak provider assumptions into Circulatio domain types.

`scripts/render_ritual_artifact.py` should remain a manual renderer entrypoint unless a later host job system explicitly owns scheduling. Phase 2 cron must not call it.

---

## Frontend Contract

Frontend Phase 3 work:
- `artifact-contract.ts` adds completion fields to `RitualArtifactManifest.interaction`.
- `mock-artifacts.ts` updates the weekly fixture.
- `app/artifacts/[artifactId]/page.tsx` extracts manifest loading for reuse.
- `app/api/artifacts/[artifactId]/complete/route.ts` adds a POST route.
- Ritual components add completion submit UI and stable completion ID handling.

The completion route should validate:
- artifact exists
- manifest exists
- route `artifactId` matches manifest artifact ID
- request has `Idempotency-Key` or `completionId`
- payload matches the manifest's completion contract
- Hermes adapter is configured before forwarding

Next.js App Router Route Handlers are the intended shape for `app/api/.../route.ts` POST handling. The route should normalize payload before forwarding to Hermes so Circulatio receives stable idempotency semantics.

---

## Source Context And Privacy

Ritual planning and invitation generation must use source references, titles, summaries, tags, and derived context. They must not expose raw material text in:
- context snapshots
- graph nodes
- proactive brief payloads
- provider prompts
- artifact manifests
- renderer cache keys

When user-authored reflection is submitted on completion, it is stored literally because the user explicitly authored it for that purpose. That storage still does not trigger interpretation.

---

## Experience Stories

- A user says, "I only need help breathing for a minute." The host calls `plan_ritual` with `narrativeMode=breath_only` and `requestedSurfaces.breath.enabled=true`, then renders a minimal pacer with inhale, hold, exhale, and rest labels.
- A user brings a charged dream image but does not want interpretation yet. The host calls the same planner with `requestedSurfaces.meditation.enabled=true` and renders a coherence field that settles attention without turning the image into advice.
- A user receives a weekly invitation. Hermes delivers a `ritual_invitation` brief only. If the user accepts, Hermes calls `plan_ritual`; otherwise no plan or artifact exists.
- A user completes a ritual and adds a sentence about what happened. The frontend posts completion with an idempotency key. Circulatio stores a completion event and literal reflection material, then stops.
- A provider caption call fails. The renderer emits fallback WebVTT captions from `voiceScript.segments` and keeps the artifact playable.
- A user already has a breathing practice and names it directly. The host carries that explicit preference in `requestedSurfaces.breath.request` instead of letting Circulatio infer a technique from keywords.
- A user wants the image, music, and breath all present. The host enables multiple `requestedSurfaces` in one tool call, but the renderer still requires explicit provider, budget, and beta gates before producing non-default media.

---

## Implementation Impact

### Docs

- `docs/PRESENTATION_LAYER.md`: this Phase 2/3 architecture plan.
- `docs/ROADMAP.md`: add Phase 7.6/7.7 entries for ritual invitation and completion/provider hardening.
- `docs/ENGINEERING_GUIDE.md`: document cron, acceptance, completion, and provider boundaries.
- `README.md`: add manual plan -> render -> artifact URL path.

### Backend

- `src/circulatio/domain/presentation.py`: add `RitualInvitationSummary`, `RitualInvitationPlanDraft`, and `RitualCompletionEvent`.
- `src/circulatio/domain/proactive.py`: add `ritual_invitation`; add optional `ritualInvitation`.
- `src/circulatio/application/workflow_types.py`: add `RecordRitualCompletionInput` and result type.
- `src/circulatio/application/circulatio_service.py`: add `record_ritual_completion`; preserve read-only `plan_ritual`.
- `src/circulatio/core/proactive_engine.py`: generate consent-bound weekly ritual invitation seeds.
- `src/circulatio/core/circulatio_core.py`: preserve proactive brief source refs; keep accepted plan read-only.
- Repository layer: add idempotent completion-event storage keyed by `(userId, idempotencyKey)`.

### Hermes/plugin

- `agent_bridge_contracts.py`: add `circulatio.presentation.record_ritual_completion`.
- `command_router.py`: add completion dispatcher; optional `/circulation ritual accept`.
- `agent_bridge.py`: route new completion operation.
- `tools.py`, `schemas.py`, `plugin.yaml`: add completion tool if plugin dispatch is used.
- `commands.py`: add ritual accept command only if needed.
- `skills/circulation/SKILL.md`: strengthen scheduled invitation-only and completion no-interpretation rules.

### Renderer

- `contracts.py`: extend manifest `interaction` with completion flags.
- `renderer.py`: populate completion fields, harden provider gates, preserve fallback captions on Whisper failure.
- `cli.py`: add cache flags only if renderer-owned cache is implemented.
- `providers/chutes.py`: keep provider isolation; add stricter errors only as needed.
- `scripts/render_ritual_artifact.py`: no functional change expected.

### Frontend

- `artifact-contract.ts`: add completion fields to `RitualArtifactManifest.interaction`.
- `mock-artifacts.ts`: update weekly fixture.
- `app/artifacts/[artifactId]/page.tsx`: extract manifest loader for reuse.
- `app/api/artifacts/[artifactId]/complete/route.ts`: add POST route.
- `components/**`: add completion submit UI and stable completion ID.

---

## Required Tests And Evals

### Phase 2 tests

- `tests/test_rhythmic_runtime.py`: consent, dedupe, cooldown, scheduled max, ritual invitation seed.
- `tests/test_presentation_plan_service.py`: accepted proactive brief source ref and no-write assertions.
- `tests/test_hermes_bridge_plugin.py`: ritual invitation payload and optional accept command.
- `tests/test_hermes_host_smoke.py`: scheduled invitation smoke and accepted plan smoke.

### Phase 2 evals

- No scheduled planning.
- No scheduled rendering.
- Consent required.
- Acceptance required.
- No hidden interpretation.

### Phase 3 tests

- Backend completion service tests for event storage, replay, conflict, reflection-only storage, and no interpretation.
- Hermes bridge/plugin tests for completion tool dispatch and schema.
- Frontend route tests for valid POST, missing manifest, ID mismatch, missing idempotency, and adapter not configured.
- Renderer tests for Whisper failure fallback, budget gate, raw prompt guard, video gate, and default weekly no music/video.

### Phase 3 evals

- Completion does not interpret.
- Completion creates no hidden memory proposals.
- Raw-text boundary holds.
- Caption fallback survives provider failure.
- Music and video stay off by default.

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
- `SomaticAnimationSpec`, `BreathCycleSpec`, `MeditationFieldSpec`, `AssociationProtocol`
- `AssociationSessionRecord`, `AssociationResponseRecord`, `RhythmicPresentationPlan`
- `RitualInvitationSummary`, `RitualInvitationPlanDraft`, `RitualCompletionEvent`
- `InvitationDeliveryPolicy`

Avoid:
- `WellnessAnimation`, `MeditationPlayer`, `WordAssociationTest`, `SelfScoreDashboard`, `TherapyMode`

---

## Roadmap Placement

Recommended sequence:
- Phase 6: Practice Engine & Adaptation Learning - implemented
- Phase 7: Rhythmic Companion Runtime - implemented
- Phase 7.5: Embodied Presentation Contract - implemented as plan-only local artifact flow
- Phase 7.6: Scheduled Ritual Invitations - planned Phase 2
- Phase 7.7: Completion Sync And Provider Hardening - planned Phase 3
- Phase 8: Teleological Individuation Layer - implemented
- Phase 9: Living Myth & Integration Layer - implemented
- Phase 10: Embodied Companion Runtime - future host/runtime work

Why:
- Phase 7.5 adds typed presentation contracts without making Circulatio a renderer.
- Phase 7.6 adds consent-bound weekly invitations without scheduled planning or rendering.
- Phase 7.7 records completion idempotently and hardens providers without hidden interpretation.
- Phases 8 and 9 provide deeper symbolic content.
- Phase 10 adds actual host/runtime orchestration, TTS adapters, local audio generation, breath sync, MCP rendering, or standalone host rendering.

---

## External Format Grounding

- Next.js App Router Route Handlers are the expected shape for `app/api/.../route.ts` POST completion handling.
- WebVTT fallback captions should remain timed cue files generated from `voiceScript.segments`.
- Completion POSTs should use idempotency keys to avoid duplicate side effects on retry.

These are implementation constraints for the host/frontend/renderer. They do not change Circulatio ownership.

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
- provider media gateway
- cron scheduler

The best summary is:

> Circulatio remains backend-pure, LLM-first, consent-bound, evidence-bound, and host-rendered. Through Hermes Rituals, it can help a host decide when a moment should become a guided ritual, a companion broadcast, a cinematic rendering, plain speech, breath pacing, silence, or association, while keeping routing, delivery, rendering, provider calls, and completion UX outside the backend core.
