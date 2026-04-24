import {
  ritualArtifactFromManifest,
  type ArtifactMode,
  type PresentationArtifact,
  type RitualArtifactManifest,
  type SessionShell
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
  },
  "session-weekly-ritual": {
    id: "session-weekly-ritual",
    phase: "playback",
    continuity:
      "This dry-run artifact comes from a Circulatio ritual plan and static manifest, not from live media generation.",
    lastTouchedAt: "2026-04-24T09:00:00.000Z",
    aliveToday: ["weekly continuity", "lengthened exhale", "settling field"],
    holdAcknowledgement:
      "The ritual is rendered from a plan and does not add symbolic memory by itself."
  }
}

export const weeklyRitualDryRunManifest: RitualArtifactManifest = {
  schemaVersion: "hermes_ritual_artifact.v1",
  artifactId: "weekly-ritual-dry-run",
  planId: "ritual_plan_fixture_weekly",
  createdAt: "2026-04-24T09:00:00Z",
  title: "This week's holding ritual",
  description: "A static dry-run ritual from an existing Circulatio weekly surface.",
  privacyClass: "private",
  locale: "en-US",
  sourceRefs: [
    {
      sourceType: "weekly_review",
      recordId: "weekly_review_fixture",
      role: "primary",
      label: "Weekly review",
      evidenceIds: []
    }
  ],
  durationMs: 300000,
  surfaces: {
    text: {
      body:
        "Let this arrive as material already held, not as a task to solve. Take a few measured breaths. The week can be present as a field of continuity before it becomes explanation. Let the breath and the image loosen their grip on each other."
    },
    audio: {
      src: null,
      mimeType: null,
      durationMs: null,
      provider: null,
      voiceId: null,
      checksum: null
    },
    captions: {
      tracks: [
        {
          src: "/artifacts/weekly-ritual-dry-run/captions.vtt",
          format: "webvtt",
          lang: "en-US",
          kind: "subtitles",
          label: "English"
        }
      ],
      segments: [
        {
          id: "cap_1",
          startMs: 0,
          endMs: 7000,
          text: "Let this arrive as material already held, not as a task to solve."
        },
        {
          id: "cap_2",
          startMs: 9000,
          endMs: 17000,
          text: "Take a few measured breaths, letting the exhale be slightly longer."
        },
        {
          id: "cap_3",
          startMs: 20000,
          endMs: 34000,
          text: "The week can be present as a field of continuity before it becomes explanation."
        },
        {
          id: "cap_4",
          startMs: 36000,
          endMs: 48000,
          text: "Let the field settle around what is already known."
        },
        {
          id: "cap_5",
          startMs: 50000,
          endMs: 60000,
          text: "Notice one body response and leave the rest unforced."
        }
      ]
    },
    breath: {
      enabled: true,
      pattern: "lengthened_exhale",
      inhaleSeconds: 4,
      holdSeconds: 0,
      exhaleSeconds: 6,
      restSeconds: 2,
      cycles: 5,
      visualForm: "pacer",
      phaseLabels: true
    },
    meditation: {
      enabled: true,
      fieldType: "coherence_convergence",
      durationMs: 180000,
      macroProgressPolicy: "session_progress",
      microMotion: "convergence",
      instructionDensity: "sparse"
    },
    image: {
      enabled: false,
      src: null,
      alt: "No generated image for this artifact.",
      provider: null
    },
    cinema: {
      enabled: true,
      src: "https://www.youtube.com/watch?v=aqz-KE-bpKQ",
      posterSrc: "https://picsum.photos/seed/river-gate-video/1920/1080",
      mimeType: null,
      durationMs: null,
      provider: "youtube",
      title: "River gate ambient study",
      playbackMode: "ambient_loop",
      presentation: "full_background",
      startAtSeconds: 12
    }
  },
  timeline: [
    { atMs: 0, kind: "voice", ref: "cap_1" },
    { atMs: 9000, kind: "breath_phase", phase: "inhale" },
    { atMs: 90000, kind: "meditation_phase", phase: "settle" }
  ],
  interaction: {
    finishPrompt: "What did you notice in your body or attention after this?",
    captureBodyResponse: true,
    completionEndpoint: "/api/artifacts/weekly-ritual-dry-run/complete",
    returnCommand: "/circulation ritual complete weekly-ritual-dry-run",
    completion: {
      enabled: true,
      endpoint: "/api/artifacts/weekly-ritual-dry-run/complete",
      idempotencyRequired: true,
      captureReflection: true,
      capturePracticeFeedback: true,
      completionIdStrategy: "client_uuid"
    }
  },
  safety: {
    stopInstruction: "Stop if this increases activation; orient to the room.",
    contraindications: [],
    blockedSurfaces: []
  },
  render: {
    rendererVersion: "ritual-renderer.v1",
    mode: "dry_run_manifest",
    providers: ["mock"],
    cacheKeys: [],
    budget: { currency: "USD", estimated: 0, actual: 0 },
    warnings: []
  }
}

const artifacts: PresentationArtifact[] = [
  {
    ...ritualArtifactFromManifest(weeklyRitualDryRunManifest),
    sessionId: "session-weekly-ritual"
  },
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
    stageVideo: {
      provider: "youtube",
      url: "https://www.youtube.com/watch?v=aqz-KE-bpKQ",
      title: "River gate ambient study",
      posterImageUrl: "https://picsum.photos/seed/river-gate-video/1920/1080",
      playbackMode: "ambient_loop",
      presentation: "full_background",
      startAtSeconds: 12
    },
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
      restMs: 2200,
      cycles: 4,
      pattern: "lengthened_exhale",
      techniqueName: "Steadying",
      preferenceSource: "host_default",
      visualForm: "orb"
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
    ],
    musicQueue: {
      title: "River Gate ritual mix",
      subtitle: "Infuse shell with Apple Music pacing",
      mixNote:
        "A restrained sequence for the threshold return: low pulse first, breath-led middle, then a closing wash without forcing a climax.",
      service: "apple_music",
      artworkUrl: "https://picsum.photos/seed/river-gate-mix/800/800",
      tracks: [
        {
          id: "track-arrival",
          title: "Cold bank, still water",
          artist: "Hermes Rituals",
          album: "Threshold sketches",
          artworkUrl: "https://picsum.photos/seed/track-arrival/300/300",
          durationLabel: "1:08",
          sectionId: "section-arrival"
        },
        {
          id: "track-breath",
          title: "Lengthened exhale under fog",
          artist: "Hermes Rituals",
          album: "Threshold sketches",
          artworkUrl: "https://picsum.photos/seed/track-breath/300/300",
          durationLabel: "2:54",
          sectionId: "section-breath"
        },
        {
          id: "track-image",
          title: "Dog at the reed line",
          artist: "Hermes Rituals",
          album: "Threshold sketches",
          artworkUrl: "https://picsum.photos/seed/track-image/300/300",
          durationLabel: "1:42",
          sectionId: "section-image"
        },
        {
          id: "track-reflection",
          title: "Gate held closed",
          artist: "Hermes Rituals",
          album: "Threshold sketches",
          artworkUrl: "https://picsum.photos/seed/track-reflection/300/300",
          durationLabel: "1:58",
          sectionId: "section-reflection"
        },
        {
          id: "track-closing",
          title: "Return without crossing",
          artist: "Hermes Rituals",
          album: "Threshold sketches",
          artworkUrl: "https://picsum.photos/seed/track-closing/300/300",
          durationLabel: "2:11",
          sectionId: "section-closing"
        }
      ]
    }
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
  return Math.max(captionEnd, sceneEnd, sectionEnd, artifact.durationMs ?? 60000)
}
