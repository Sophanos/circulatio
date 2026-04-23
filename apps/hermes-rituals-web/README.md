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

## Notes

- Data is mocked first via `lib/mock-artifacts.ts`.
- The ritual page is the flagship v1 surface.
- `start` serves the output produced by the Turbopack production build.
- Local UI primitives are structured so official ElevenLabs UI registry components can replace targeted wrappers later.
