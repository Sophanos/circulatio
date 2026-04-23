import type {
  ArtifactMode,
  PresentationArtifact,
  SessionShell
} from "@/lib/artifact-contract"

const sessions: Record<string, SessionShell> = {
  "session-river-gate": {
    id: "session-river-gate",
    phase: "playback",
    continuity:
      "This artifact stays anchored to one returning image: the pale river gate at the edge of waking.",
    lastTouchedAt: "2026-04-23T06:41:00.000Z",
    aliveToday: ["river threshold", "metal gate", "chest pressure", "returning dog figure"],
    holdAcknowledgement:
      "Held without forcing meaning. The image remains intact and available for later interpretation."
  },
  "session-myth-weather": {
    id: "session-myth-weather",
    phase: "review",
    continuity:
      "Recent dreams, body states, and reflective fragments are folded into one careful companion voice.",
    lastTouchedAt: "2026-04-22T20:14:00.000Z",
    aliveToday: ["weather shift", "returning corridor", "body fatigue"],
    holdAcknowledgement:
      "Recent material was gathered first, then rendered as a short myth-weather broadcast."
  },
  "session-cinema-river": {
    id: "session-cinema-river",
    phase: "rendering",
    continuity:
      "A single dream image is being rendered across narration, captions, and scene cards without changing its symbolic source.",
    lastTouchedAt: "2026-04-23T07:12:00.000Z",
    aliveToday: ["bridge crossing", "silver current", "fog field"],
    holdAcknowledgement:
      "The source image is still primary. Cinema is a rendering path, not a new interpretation layer."
  }
}

const artifacts: PresentationArtifact[] = [
  {
    id: "ritual-river-gate",
    mode: "ritual",
    title: "Return to the river gate before naming it.",
    summary:
      "A containment-first dream-return ritual built from one waking image, paced by breath and spoken softly enough to preserve the original charge.",
    threadSummary:
      "The same gate appeared across three recent captures: once in a dream, once as morning chest pressure, and once as a threshold image during reflection.",
    sessionId: "session-river-gate",
    journeyId: "journey-threshold-river",
    coverImageUrl: "https://picsum.photos/seed/river-gate/1600/1200",
    transcript:
      "Let the river stay a river for a moment. Let the gate remain closed, silver, and patient. You do not need to explain why it returned. Breathe with the distance between your body and the image. Let the dog stand at the edge if it wants to. Notice what changes when you do not advance.",
    captions: [
      { startMs: 0, endMs: 6000, text: "Let the river stay a river for a moment." },
      { startMs: 6000, endMs: 13500, text: "Let the gate remain closed, silver, and patient." },
      { startMs: 13500, endMs: 23000, text: "You do not need to explain why it returned." },
      { startMs: 23000, endMs: 33000, text: "Breathe with the distance between your body and the image." },
      { startMs: 33000, endMs: 43000, text: "Let the dog stand at the edge if it wants to." },
      { startMs: 43000, endMs: 56000, text: "Notice what changes when you do not advance." }
    ],
    channels: {
      voice: { muted: false, gain: 0.82 },
      ambient: { muted: false, gain: 0.48 },
      breath: { muted: false, gain: 0.66 },
      pulse: { muted: true, gain: 0.2 },
      music: { muted: true, gain: 0.15 }
    },
    breathCycle: {
      inhaleMs: 4200,
      holdMs: 1800,
      exhaleMs: 6400,
      restMs: 2200
    },
    scenes: [
      {
        id: "scene-river-1",
        title: "Bank before the crossing",
        prompt: "Cold silver water under fog. A narrow gate appears on the opposite bank.",
        imageUrl: "https://picsum.photos/seed/bank-crossing/1200/900",
        startMs: 0,
        endMs: 18000
      },
      {
        id: "scene-river-2",
        title: "The animal keeps watch",
        prompt: "A dark dog waits without approaching, half inside the reeds.",
        imageUrl: "https://picsum.photos/seed/dog-watch/1200/900",
        startMs: 18000,
        endMs: 36000
      },
      {
        id: "scene-river-3",
        title: "The gate stays closed",
        prompt: "The threshold remains visible without demanding entry.",
        imageUrl: "https://picsum.photos/seed/gate-closed/1200/900",
        startMs: 36000,
        endMs: 56000
      }
    ],
    ritualSections: [
      {
        id: "section-arrival",
        title: "Arrival",
        startMs: 0,
        endMs: 6000,
        kind: "arrival",
        muted: false,
        skippable: false,
        channels: { voice: true, ambient: true, breath: true }
      },
      {
        id: "section-breath",
        title: "Grounding breath",
        startMs: 6000,
        endMs: 23000,
        kind: "breath",
        muted: false,
        skippable: true,
        channels: { voice: true, ambient: true, breath: true, pulse: true }
      },
      {
        id: "section-image",
        title: "Image return",
        startMs: 23000,
        endMs: 33000,
        kind: "image",
        muted: false,
        skippable: true,
        channels: { voice: true, ambient: true }
      },
      {
        id: "section-reflection",
        title: "Reflection",
        startMs: 33000,
        endMs: 43000,
        kind: "reflection",
        muted: false,
        skippable: true,
        channels: { voice: true, ambient: true, music: true }
      },
      {
        id: "section-closing",
        title: "Closing",
        startMs: 43000,
        endMs: 56000,
        kind: "closing",
        muted: false,
        skippable: false,
        channels: { voice: true, ambient: true, breath: true }
      }
    ]
  },
  {
    id: "broadcast-myth-weather-0422",
    mode: "broadcast",
    title: "Myth weather for the week of returning corridors.",
    summary:
      "A short audio letter gathering the motifs that feel most alive lately without overclaiming what they mean.",
    threadSummary:
      "The weather changed around corridor dreams, low body energy, and a repeated image of standing before doors that do not open yet.",
    sessionId: "session-myth-weather",
    journeyId: "journey-corridor-letter",
    coverImageUrl: "https://picsum.photos/seed/myth-weather/1600/1200",
    transcript:
      "This week feels corridor-shaped. Several images ask for patience rather than interpretation. The body reads tired, but not empty. A door recurs. So does weather pressure. The voice of the week is not revelation. It is atmosphere held long enough to become legible.",
    captions: [
      { startMs: 0, endMs: 6000, text: "This week feels corridor-shaped." },
      { startMs: 6000, endMs: 15000, text: "Several images ask for patience rather than interpretation." },
      { startMs: 15000, endMs: 23500, text: "The body reads tired, but not empty." },
      { startMs: 23500, endMs: 34000, text: "A door recurs. So does weather pressure." },
      { startMs: 34000, endMs: 48000, text: "The voice of the week is not revelation. It is atmosphere held long enough to become legible." }
    ],
    scenes: [
      {
        id: "scene-broadcast-1",
        title: "Corridor weather",
        prompt: "Long corridor lit by pale morning light.",
        imageUrl: "https://picsum.photos/seed/corridor-weather/1200/900",
        startMs: 0,
        endMs: 24000
      },
      {
        id: "scene-broadcast-2",
        title: "Door pressure",
        prompt: "Closed doors under low metallic sky.",
        imageUrl: "https://picsum.photos/seed/door-pressure/1200/900",
        startMs: 24000,
        endMs: 48000
      }
    ]
  },
  {
    id: "cinema-river-gate",
    mode: "cinema",
    title: "River gate cinema render.",
    summary:
      "A first cinematic rendering path with captions, scene cards, and a restrained stage designed for later Remotion export.",
    threadSummary:
      "Built from the same river-threshold material as the ritual artifact so the user can move between render families without losing continuity.",
    sessionId: "session-cinema-river",
    journeyId: "journey-threshold-river",
    coverImageUrl: "https://picsum.photos/seed/cinema-river-cover/1600/1200",
    videoUrl: "mock://river-gate-cinema",
    transcript:
      "The water keeps its own counsel. The threshold is visible now. You can cross later, or not at all. For this moment, the image only asks to be seen.",
    captions: [
      { startMs: 0, endMs: 8000, text: "The water keeps its own counsel." },
      { startMs: 8000, endMs: 18000, text: "The threshold is visible now." },
      { startMs: 18000, endMs: 32000, text: "You can cross later, or not at all." },
      { startMs: 32000, endMs: 44000, text: "For this moment, the image only asks to be seen." }
    ],
    scenes: [
      {
        id: "scene-cinema-1",
        title: "Waterline",
        prompt: "Low silver current with graphite edges.",
        imageUrl: "https://picsum.photos/seed/waterline/1200/900",
        startMs: 0,
        endMs: 12000
      },
      {
        id: "scene-cinema-2",
        title: "Threshold frame",
        prompt: "A gate suspended in fog, almost architectural.",
        imageUrl: "https://picsum.photos/seed/threshold-frame/1200/900",
        startMs: 12000,
        endMs: 26000
      },
      {
        id: "scene-cinema-3",
        title: "Held crossing",
        prompt: "The stage widens, but nothing rushes the crossing.",
        imageUrl: "https://picsum.photos/seed/held-crossing/1200/900",
        startMs: 26000,
        endMs: 44000
      }
    ]
  }
]

export function getArtifact(artifactId: string) {
  return artifacts.find((artifact) => artifact.id === artifactId)
}

export function getArtifactsByMode(mode: ArtifactMode) {
  return artifacts.filter((artifact) => artifact.mode === mode)
}

export function getAllArtifacts() {
  return artifacts
}

export function getSession(sessionId?: string) {
  return sessionId ? sessions[sessionId] : undefined
}

export function getArtifactDuration(artifact: PresentationArtifact) {
  const captionEnd = artifact.captions?.at(-1)?.endMs ?? 0
  const sceneEnd = artifact.scenes?.at(-1)?.endMs ?? 0
  const sectionEnd = artifact.ritualSections?.at(-1)?.endMs ?? 0
  return Math.max(captionEnd, sceneEnd, sectionEnd, 60000)
}
