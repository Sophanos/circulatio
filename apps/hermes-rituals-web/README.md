# Hermes Rituals Web

Artifact-first frontend scaffold for Hermes Rituals.

## Principles

- `Circulatio` derives symbolic context and emits typed presentation artifacts.
- `Hermes` routes intent, sessions, and URLs.
- This web app renders artifacts and captures follow-up without becoming the symbolic brain.

## Stack

- Next.js
- TypeScript
- Tailwind
- shadcn-compatible structure
- ElevenLabs-compatible wrapper surfaces
- AI SDK UI streams for the ritual companion
- GSAP for motion
- Turbopack for dev and build

## Turbopack Setup

This app is configured so the same Next.js app runs through Turbopack for:

- web bundles
- App Router server components
- server-rendered route code during dev/build

Relevant files:

- [package.json](/Users/mibook/circulatio/apps/hermes-rituals-web/package.json)
  - `bun run dev` -> `next dev --turbopack`
  - `bun run build` -> `next build --turbopack`
- [next.config.ts](/Users/mibook/circulatio/apps/hermes-rituals-web/next.config.ts)
  - `turbopack.root = __dirname`

## Run

From the repo root:

```bash
cd apps/hermes-rituals-web
bun install
bun run dev
```

Open:

- `http://localhost:3000`
- `http://localhost:3000/rituals/ritual-river-gate`

## Production

```bash
cd apps/hermes-rituals-web
bun install
bun run build
bun run start
```

## Useful Commands

```bash
cd apps/hermes-rituals-web

# local dev with Turbopack
bun run dev

# production build with Turbopack
bun run build

# serve the production build
bun run start

# type check
bun run typecheck

# lint
bun run lint

# browser artifact playback checks
# start the app, then drive it with agent-browser
bun run dev
agent-browser open http://127.0.0.1:3000/artifacts/{artifactId}
agent-browser snapshot -i
```

## Ports

- dev on another port: `bun run dev -- --port 3001`
- prod on another port: `bun run start -- --port 3001`

## Routes

- `/capture/new`
- `/rituals/[artifactId]`
- `/broadcasts/[artifactId]`
- `/cinema/[artifactId]`
- `/artifacts/[artifactId]`
- `/live/[guidanceSessionId]`

## Completion And Memory Loop

The artifact player opens a quiet completion panel at closing or playback completion. The user can complete with no notes, add explicit body-state detail, add literal words, add practice feedback, or combine those fields. Completion posts to `/api/artifacts/[artifactId]/complete` with one idempotency key and must not trigger interpretation.

`HERMES_RITUAL_COMPLETION_URL` forwards completion to a host endpoint when configured. When it is unset, the web app uses the repo-local `scripts/record_ritual_completion.py` bridge with `CIRCULATIO_PROFILE` / `HERMES_PROFILE` and records through `circulatio_record_ritual_completion` only.

## Ritual Companion

The artifact player can open a same-session Hermes companion in the existing rail. The companion forwards only bounded guidance frames, source refs, UI messages, and explicit action approval decisions. The frame includes phase, active section, lens, available tracks, playback state, completion state, and allowed explicit writes.

Environment variables:

- `HERMES_GUIDANCE_SESSIONS_URL`: Hermes collection endpoint for guidance session create/resume, event forwarding, and approved/rejected action decisions.
- `HERMES_RITUAL_CHAT_URL`: Hermes stream endpoint for `/api/ritual-chat`.

When these env vars are unset, the app runs in local preview mode. Local preview creates deterministic non-persisting guidance session IDs, returns AI SDK UI-message fallback streams, accepts bounded session events without persistence, and never executes durable writes.

Durable writes cannot execute from assistant text. Hermes may propose `RitualCompanionAction` objects, but the UI must send an explicit approve/reject decision to `/api/guidance-sessions/[guidanceSessionId]/actions`; Hermes owns any mapping to Circulatio tools. The companion can be paused or minimized without pausing artifact playback.

## Live Guidance

`/live/[guidanceSessionId]` is now a no-camera-first live continuation shell. It supports one active focus mode at a time: breath, meditation, image, movement, or companion cue. Camera remains off by default; the user must enter camera preflight and explicitly enable camera before the browser requests permission. This route does not yet implement pose estimation, reference movement comparison, sensor event persistence, or production live coaching.

Local AI Elements-style components are copied under `components/ai-elements`. Do not add a runtime import from `ai-elements`. To refresh the component source manually, use:

```bash
npx ai-elements@1.9.0 add message prompt-input conversation tool confirmation
```

## Artifact Media Contract

- `/artifacts/[artifactId]` is the local manifest player. It loads `apps/hermes-rituals-web/public/artifacts/{artifactId}/manifest.json` first and falls back to local fixtures only while mocks are being retired.
- Real provider artifacts are identified by concrete manifest sources: `surfaces.audio.src`, `surfaces.image.enabled + src`, caption tracks, and caption segments. Dry-run artifacts may be useful but can have mock audio and no generated image.
- `RitualPlayer` must preserve the current dark, minimal player chrome. The waveform may become more accurate, but do not redesign the visible scrub bar, caption stack, or play controls without an explicit product request.
- Audio playback uses `artifact.audioUrl` first. Silent WAV blob URLs are fallback-only. When real audio exists, the player waits for metadata, uses actual media duration, decodes audio peaks for the waveform, and ties waveform progress to scrub/playback time.
- Image-backed artifacts should enter the Photo lens by default when no cinema video is present. The Photo lens renders the manifest image through `coverImageUrl` / `scenes`.
- Caption segments are first-class: they drive `CaptionStack`, transcript grouping, section rows, and ElevenLabs-style character alignment. Chutes/OpenAI transcription failures should still leave fallback caption segments plus a warning.
- Browser verification should check `manifest.json`, `audio.wav`, `image.png`, `music.wav`, `cinema.mp4`, and `captions.vtt` when those sources exist; wait for audio metadata before asserting duration, because the slider may start from planned manifest duration and then switch to actual audio duration.
- Browser verification uses `agent-browser` only (https://github.com/vercel-labs/agent-browser). Start the local app, open `/artifacts/{artifactId}`, verify narration/music/cinema/breath/body completion behavior, and confirm a narrow breath+music artifact does not show narration, transcript, or cinema UI.
- In dev, ignore stale hot-reload errors from before a rebuild only if a fresh tab after the check start has no new console errors.

## Notes

- Ritual, broadcast, cinema, breath, meditation, image/photo, and body remain experience categories/lenses inside the canonical artifact player.
- Legacy `/rituals`, `/broadcasts`, and `/cinema` routes are compatibility redirects to `/artifacts/[artifactId]`.
- Mock data is being sunset by replacing each mock artifact with a manifest fixture under `public/artifacts`; keep `lib/mock-artifacts.ts` as a temporary fixture index only.
- The artifact player is the flagship v1 surface.
- `start` serves the output produced by the Turbopack production build.
- Local UI primitives are structured so official ElevenLabs UI registry components can replace targeted wrappers later.
