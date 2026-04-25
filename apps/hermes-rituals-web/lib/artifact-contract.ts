export type ArtifactMode = "ritual" | "broadcast" | "cinema"

export type RitualSectionKind = "arrival" | "breath" | "image" | "reflection" | "closing"

export type RitualSection = {
  id: string
  title: string
  startMs: number
  endMs: number
  kind: RitualSectionKind
  muted?: boolean
  skippable?: boolean
  channels?: {
    voice?: boolean
    ambient?: boolean
    breath?: boolean
    pulse?: boolean
    music?: boolean
  }
}

export type TranscriptAlignment = {
  characters: string[]
  characterStartTimesSeconds: number[]
  characterEndTimesSeconds: number[]
}

export type ArtifactChannelState = {
  muted: boolean
  gain: number
}

export type ArtifactChannels = {
  voice?: ArtifactChannelState
  ambient?: ArtifactChannelState
  breath?: ArtifactChannelState
  pulse?: ArtifactChannelState
  music?: ArtifactChannelState
}

export type BreathPattern =
  | "steadying"
  | "lengthened_exhale"
  | "box_breath"
  | "orienting"

export type BreathPreferenceSource =
  | "explicit_user_preference"
  | "host_prompted_preference"
  | "host_default"
  | "llm_suggested"

export type BreathVisualForm = "orb" | "wave" | "mandala" | "horizon" | "pacer"

export type BreathCycle = {
  inhaleMs: number
  holdMs: number
  exhaleMs: number
  restMs: number
  cycles?: number
  pattern?: BreathPattern
  techniqueName?: string
  preferenceSource?: BreathPreferenceSource
  visualForm?: BreathVisualForm
}

export type CaptionCue = {
  startMs: number
  endMs: number
  text: string
}

export type PresentationScene = {
  id: string
  title: string
  prompt?: string
  imageUrl?: string
  startMs?: number
  endMs?: number
}

export type PresentationVideoProvider = "youtube" | "direct"

export type PresentationVideoPlaybackMode = "ambient_loop" | "transport_synced"

export type PresentationVideoPresentation = "stage_card" | "full_background"

export type PresentationVideoSource = {
  provider: PresentationVideoProvider
  url: string
  title?: string
  posterImageUrl?: string
  playbackMode?: PresentationVideoPlaybackMode
  presentation?: PresentationVideoPresentation
  startAtSeconds?: number
}

export type RitualMusicService = "apple_music" | "host_curated" | "local_render"

export type RitualQueueTrack = {
  id: string
  title: string
  artist: string
  album?: string
  artworkUrl?: string
  durationLabel?: string
  sectionId?: string
}

export type RitualMusicQueue = {
  title: string
  subtitle?: string
  mixNote?: string
  service?: RitualMusicService
  artworkUrl?: string
  tracks: RitualQueueTrack[]
}

export type PresentationArtifact = {
  id: string
  mode: ArtifactMode
  title: string
  summary: string
  privacyClass?: string
  durationMs?: number
  completionPrompt?: string
  completionEndpoint?: string
  captureBodyResponse?: boolean
  threadSummary?: string
  sessionId?: string
  journeyId?: string
  audioUrl?: string
  videoUrl?: string
  stageVideo?: PresentationVideoSource
  coverImageUrl?: string
  transcript?: string
  transcriptAlignment?: TranscriptAlignment
  captions?: CaptionCue[]
  channels?: ArtifactChannels
  breathCycle?: BreathCycle
  scenes?: PresentationScene[]
  ritualSections?: RitualSection[]
  musicQueue?: RitualMusicQueue
}

export type SessionPhase = "hold" | "rendering" | "playback" | "review"

export type RitualArtifactSourceRef = {
  sourceType: string
  recordId?: string
  role: string
  label?: string
  evidenceIds?: string[]
}

export type RitualCaptionTrack = {
  src: string
  format: "webvtt" | "segments"
  lang: string
  kind: "subtitles" | "captions"
  label: string
}

export type RitualCaptionSegment = CaptionCue & {
  id: string
}

export type RitualCompletionContract = {
  enabled: boolean
  endpoint: string
  idempotencyRequired: true
  captureReflection: boolean
  capturePracticeFeedback: boolean
  completionIdStrategy: "client_uuid"
}

export type RitualCompletionBodyStatePayload = {
  sensation: string
  bodyRegion?: string
  activation?: "low" | "moderate" | "high" | "overwhelming"
  tone?: string
  temporalContext?: string
  noteText?: string
  privacyClass?: string
}

export type RitualArtifactManifest = {
  schemaVersion: "hermes_ritual_artifact.v1"
  artifactId: string
  planId: string
  createdAt: string
  title: string
  description: string
  privacyClass: "private" | "sensitive" | "session_only" | string
  locale: string
  sourceRefs: RitualArtifactSourceRef[]
  durationMs: number
  surfaces: {
    text: { body: string }
    audio?: {
      src: string | null
      mimeType?: string | null
      durationMs?: number | null
      provider?: string | null
      model?: string | null
      voiceId?: string | null
      checksum?: string | null
      placeholderSrc?: string | null
    }
    captions?: {
      tracks?: RitualCaptionTrack[]
      segments?: RitualCaptionSegment[]
    }
    breath?: {
      enabled: boolean
      pattern: BreathPattern
      inhaleSeconds: number
      holdSeconds: number
      exhaleSeconds: number
      restSeconds: number
      cycles?: number
      visualForm?: BreathVisualForm
      phaseLabels?: boolean
    }
    meditation?: {
      enabled: boolean
      fieldType: string
      durationMs: number
      macroProgressPolicy: string
      microMotion: string
      instructionDensity: string
    }
    image?: {
      enabled: boolean
      src: string | null
      alt?: string
      provider?: string | null
      model?: string | null
      checksum?: string | null
    }
    cinema?: {
      enabled: boolean
      src: string | null
      posterSrc?: string | null
      mimeType?: string | null
      durationMs?: number | null
      provider?: PresentationVideoProvider | string | null
      model?: string | null
      title?: string | null
      playbackMode?: PresentationVideoPlaybackMode | string | null
      presentation?: PresentationVideoPresentation | string | null
      startAtSeconds?: number | null
    }
    music?: {
      src: string | null
      mimeType?: string | null
      durationMs?: number | null
      provider?: string | null
      model?: string | null
      checksum?: string | null
    }
  }
  timeline: Array<Record<string, string | number | boolean | null>>
  interaction: {
    finishPrompt: string
    captureBodyResponse: boolean
    completionEndpoint?: string
    returnCommand?: string
    completion?: RitualCompletionContract
  }
  safety: {
    stopInstruction: string
    contraindications: string[]
    blockedSurfaces: string[]
  }
  render: {
    rendererVersion: string
    mode: string
    providers: string[]
    cacheKeys: string[]
    budget: { currency: string; estimated: number; actual: number }
    warnings: string[]
  }
}

export type SessionShell = {
  id: string
  phase: SessionPhase
  continuity: string
  lastTouchedAt: string
  aliveToday: string[]
  holdAcknowledgement: string
}

function manifestVisualForm(value?: string | null): BreathVisualForm {
  if (value === "wave" || value === "mandala" || value === "horizon" || value === "pacer") {
    return value
  }
  return "orb"
}

function manifestVideoProvider(value?: string | null): PresentationVideoProvider {
  return value === "youtube" ? "youtube" : "direct"
}

function manifestVideoPlaybackMode(value?: string | null): PresentationVideoPlaybackMode {
  return value === "ambient_loop" ? "ambient_loop" : "transport_synced"
}

function manifestVideoPresentation(value?: string | null): PresentationVideoPresentation {
  return value === "full_background" ? "full_background" : "stage_card"
}

function manifestSections(manifest: RitualArtifactManifest): RitualSection[] {
  const durationMs = manifest.durationMs || 60000
  const arrivalEnd = Math.min(18000, durationMs)
  const breathEnd = Math.min(durationMs, 90000)
  const meditationStart = Math.min(durationMs, Math.max(breathEnd, durationMs - 180000))
  const sections: RitualSection[] = [
    {
      id: "section-arrival",
      title: "Arrival",
      startMs: 0,
      endMs: arrivalEnd,
      kind: "arrival",
      channels: { voice: true, ambient: true }
    },
    {
      id: "section-breath",
      title: "Breath",
      startMs: arrivalEnd,
      endMs: breathEnd,
      kind: "breath",
      skippable: true,
      channels: { voice: true, breath: true, pulse: true }
    },
    {
      id: "section-reflection",
      title: "Reflection",
      startMs: breathEnd,
      endMs: meditationStart,
      kind: "reflection",
      skippable: true,
      channels: { voice: true, ambient: true }
    },
    {
      id: "section-closing",
      title: "Closing",
      startMs: meditationStart,
      endMs: durationMs,
      kind: "closing",
      channels: { voice: true, breath: true }
    }
  ]

  return sections.filter((section) => section.endMs > section.startMs)
}

export function ritualArtifactFromManifest(
  manifest: RitualArtifactManifest
): PresentationArtifact {
  const breath = manifest.surfaces.breath
  const image = manifest.surfaces.image
  const cinema = manifest.surfaces.cinema
  const captions = manifest.surfaces.captions?.segments?.map((segment) => ({
    startMs: segment.startMs,
    endMs: segment.endMs,
    text: segment.text
  }))
  const stageVideo: PresentationVideoSource | undefined =
    cinema?.enabled && cinema.src
      ? {
          provider: manifestVideoProvider(cinema.provider),
          url: cinema.src,
          title: cinema.title ?? manifest.title,
          posterImageUrl: cinema.posterSrc ?? undefined,
          playbackMode: manifestVideoPlaybackMode(cinema.playbackMode),
          presentation: manifestVideoPresentation(cinema.presentation),
          startAtSeconds: cinema.startAtSeconds ?? undefined
        }
      : undefined

  return {
    id: manifest.artifactId,
    mode: "ritual",
    title: manifest.title,
    summary: manifest.description,
    privacyClass: manifest.privacyClass,
    durationMs: manifest.durationMs,
    completionPrompt: manifest.interaction.finishPrompt,
    completionEndpoint:
      manifest.interaction.completion?.endpoint ?? manifest.interaction.completionEndpoint,
    captureBodyResponse: manifest.interaction.captureBodyResponse,
    audioUrl: manifest.surfaces.audio?.src ?? undefined,
    videoUrl: cinema?.enabled && cinema.src ? cinema.src : undefined,
    stageVideo,
    coverImageUrl: image?.enabled && image.src ? image.src : stageVideo?.posterImageUrl,
    transcript: manifest.surfaces.text.body,
    captions,
    channels: {
      voice: { muted: false, gain: 0.82 },
      ambient: { muted: false, gain: 0.36 },
      breath: { muted: false, gain: 0.58 },
      pulse: { muted: false, gain: 0.24 }
    },
    breathCycle: breath?.enabled
      ? {
          inhaleMs: breath.inhaleSeconds * 1000,
          holdMs: breath.holdSeconds * 1000,
          exhaleMs: breath.exhaleSeconds * 1000,
          restMs: breath.restSeconds * 1000,
          cycles: breath.cycles,
          pattern: breath.pattern,
          techniqueName: breath.pattern.replaceAll("_", " "),
          preferenceSource: "host_default",
          visualForm: manifestVisualForm(breath.visualForm)
        }
      : undefined,
    scenes:
      image?.enabled && image.src
        ? [
            {
              id: "scene-manifest-image",
              title: manifest.title,
              imageUrl: image.src,
              startMs: 0,
              endMs: manifest.durationMs
            }
          ]
        : undefined,
    ritualSections: manifestSections(manifest)
  }
}
