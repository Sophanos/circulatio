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
- `/live/[sessionId]`

## Artifact Media Contract

- `/artifacts/[artifactId]` is the local manifest player. It should load `apps/hermes-rituals-web/public/artifacts/{artifactId}/manifest.json`, not the older mock-only ritual/broadcast/cinema routes.
- Real provider artifacts are identified by concrete manifest sources: `surfaces.audio.src`, `surfaces.image.enabled + src`, caption tracks, and caption segments. Dry-run artifacts may be useful but can have mock audio and no generated image.
- `RitualPlayer` must preserve the current dark, minimal player chrome. The waveform may become more accurate, but do not redesign the visible scrub bar, caption stack, or play controls without an explicit product request.
- Audio playback uses `artifact.audioUrl` first. Silent WAV blob URLs are fallback-only. When real audio exists, the player waits for metadata, uses actual media duration, decodes audio peaks for the waveform, and ties waveform progress to scrub/playback time.
- Image-backed artifacts should enter the Photo lens by default when no cinema video is present. The Photo lens renders the manifest image through `coverImageUrl` / `scenes`.
- Caption segments are first-class: they drive `CaptionStack`, transcript grouping, section rows, and ElevenLabs-style character alignment. Whisper failures should still leave fallback caption segments plus a warning.
- Browser verification should check `manifest.json`, `audio.wav`, `image.png`, and `captions.vtt` return `200`; wait for audio metadata before asserting duration, because the slider may start from planned manifest duration and then switch to actual audio duration.
- In dev, ignore stale hot-reload errors from before a rebuild only if a fresh tab after the check start has no new console errors.

## Notes

- Data is mocked first via `lib/mock-artifacts.ts`.
- The ritual page is the flagship v1 surface.
- `start` serves the output produced by the Turbopack production build.
- Local UI primitives are structured so official ElevenLabs UI registry components can replace targeted wrappers later.
