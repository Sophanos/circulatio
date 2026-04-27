export type ArtifactMode = "ritual" | "broadcast" | "cinema"

export type RitualSectionKind = "arrival" | "breath" | "image" | "reflection" | "closing"
export type RitualSectionPreferredLens = "cinema" | "photo" | "breath" | "meditation" | "body"

export type RitualSection = {
  id: string
  title: string
  startMs: number
  endMs: number
  kind: RitualSectionKind
  preferredLens?: RitualSectionPreferredLens
  capturePrompt?: string
  transcript?: string
  captionCount?: number
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
  id?: string
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

export type PresentationMeditationSurface = {
  enabled: boolean
  fieldType: string
  durationMs: number
  macroProgressPolicy: string
  microMotion: string
  instructionDensity: string
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
  meditation?: PresentationMeditationSurface
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
  sections?: RitualSection[]
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
    meditation?: PresentationMeditationSurface
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
      checksum?: string | null
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

function isRitualSectionKind(value: unknown): value is RitualSectionKind {
  return (
    value === "arrival" ||
    value === "breath" ||
    value === "image" ||
    value === "reflection" ||
    value === "closing"
  )
}

function isRitualSectionPreferredLens(value: unknown): value is RitualSectionPreferredLens {
  return (
    value === "cinema" ||
    value === "photo" ||
    value === "breath" ||
    value === "meditation" ||
    value === "body"
  )
}

function sectionTitle(kind: RitualSectionKind) {
  switch (kind) {
    case "arrival":
      return "Arrival"
    case "breath":
      return "Breath"
    case "image":
      return "Image return"
    case "reflection":
      return "Reflection"
    case "closing":
      return "Closing"
  }
}

function captionOverlapsSection(caption: CaptionCue, section: Pick<RitualSection, "startMs" | "endMs">) {
  return caption.endMs > section.startMs && caption.startMs < section.endMs
}

function attachCaptionMetadata(section: RitualSection, captions: CaptionCue[]): RitualSection {
  const overlapping = captions.filter((caption) => captionOverlapsSection(caption, section))
  if (overlapping.length === 0) return section

  return {
    ...section,
    transcript: section.transcript ?? overlapping.map((caption) => caption.text).join(" "),
    captionCount: section.captionCount ?? overlapping.length
  }
}

function cleanManifestSections(
  manifest: RitualArtifactManifest,
  captions: CaptionCue[]
): RitualSection[] {
  const durationMs = manifest.durationMs || 60000
  const rawSections = manifest.sections ?? []
  if (rawSections.length === 0) return []

  return rawSections
    .map((section, index): RitualSection | null => {
      const startMs = Math.max(0, Math.min(Number(section.startMs), durationMs))
      const endMs = Math.max(startMs, Math.min(Number(section.endMs), durationMs))
      if (!Number.isFinite(startMs) || !Number.isFinite(endMs) || endMs <= startMs) return null

      const kind = isRitualSectionKind(section.kind) ? section.kind : "reflection"
      const preferredLens = isRitualSectionPreferredLens(section.preferredLens)
        ? section.preferredLens
        : undefined

      return attachCaptionMetadata(
        {
          ...section,
          id: section.id?.trim() || `section-${index + 1}`,
          title: section.title?.trim() || sectionTitle(kind),
          startMs,
          endMs,
          kind,
          preferredLens,
          capturePrompt: section.capturePrompt?.trim() || undefined
        },
        captions
      )
    })
    .filter((section): section is RitualSection => Boolean(section))
    .sort((a, b) => a.startMs - b.startMs)
}

function breathDurationMs(manifest: RitualArtifactManifest) {
  const breath = manifest.surfaces.breath
  if (!breath?.enabled) return 0
  const cycleMs = Math.max(
    (breath.inhaleSeconds + breath.holdSeconds + breath.exhaleSeconds + breath.restSeconds) * 1000,
    1
  )
  return cycleMs * Math.max(breath.cycles ?? 1, 1)
}

function surfacePreferredLens(manifest: RitualArtifactManifest): RitualSectionPreferredLens {
  const cinema = manifest.surfaces.cinema
  if (cinema?.enabled && cinema.src) return "cinema"
  const image = manifest.surfaces.image
  if (image?.enabled && image.src) return "photo"
  return "breath"
}

function hasVisualSurface(manifest: RitualArtifactManifest) {
  return Boolean(
    (manifest.surfaces.cinema?.enabled && manifest.surfaces.cinema.src) ||
      (manifest.surfaces.image?.enabled && manifest.surfaces.image.src)
  )
}

function surfaceAwareManifestSections(
  manifest: RitualArtifactManifest,
  captions: CaptionCue[]
): RitualSection[] {
  const durationMs = Math.max(manifest.durationMs || 60000, 1)
  const sections: RitualSection[] = []
  const closingDurationMs = Math.min(
    48000,
    Math.max(18000, Math.round(durationMs * 0.16))
  )
  const arrivalDurationMs = Math.min(
    12000,
    Math.max(6000, Math.round(durationMs * 0.04))
  )
  const closingStartMs = Math.max(arrivalDurationMs, durationMs - closingDurationMs)
  let cursor = 0

  const push = (section: RitualSection) => {
    if (section.endMs <= section.startMs) return
    sections.push(attachCaptionMetadata(section, captions))
    cursor = section.endMs
  }

  push({
    id: "section-arrival",
    title: "Arrival",
    startMs: cursor,
    endMs: Math.min(arrivalDurationMs, durationMs),
    kind: "arrival",
    preferredLens: surfacePreferredLens(manifest),
    channels: { voice: true, ambient: true }
  })

  const breathMs = breathDurationMs(manifest)
  if (breathMs > 0 && cursor < closingStartMs) {
    push({
      id: "section-breath",
      title: "Breath",
      startMs: cursor,
      endMs: Math.min(cursor + breathMs, closingStartMs),
      kind: "breath",
      preferredLens: "breath",
      skippable: true,
      channels: { voice: true, breath: true, pulse: true }
    })
  }

  if (hasVisualSurface(manifest) && cursor < closingStartMs) {
    const imageDurationMs = Math.min(
      30000,
      Math.max(12000, Math.round(durationMs * 0.1))
    )
    push({
      id: "section-image",
      title: "Image return",
      startMs: cursor,
      endMs: Math.min(cursor + imageDurationMs, closingStartMs),
      kind: "image",
      preferredLens: surfacePreferredLens(manifest),
      skippable: true,
      channels: { voice: true, ambient: true }
    })
  }

  if (cursor < closingStartMs) {
    push({
      id: "section-reflection",
      title: "Reflection",
      startMs: cursor,
      endMs: closingStartMs,
      kind: "reflection",
      preferredLens: manifest.surfaces.meditation?.enabled ? "meditation" : surfacePreferredLens(manifest),
      skippable: true,
      channels: { voice: true, ambient: true }
    })
  }

  if (closingStartMs < durationMs) {
    push({
      id: "section-closing",
      title: "Closing",
      startMs: closingStartMs,
      endMs: durationMs,
      kind: "closing",
      preferredLens: "body",
      capturePrompt: manifest.interaction.finishPrompt,
      channels: { voice: true, breath: true }
    })
  }

  return sections
}

function legacyCaptionSections(manifest: RitualArtifactManifest, captions: CaptionCue[]): RitualSection[] {
  const durationMs = manifest.durationMs || 60000
  if (captions.length > 0) {
    return captions.map((caption, index) => {
      const isFirst = index === 0
      const isLast = index === captions.length - 1
      const isBreath = index === 1
      const isImageReturn = Boolean(manifest.surfaces.image?.enabled) && index === 2
      const kind: RitualSectionKind = isFirst
        ? "arrival"
        : isBreath
          ? "breath"
          : isLast
            ? "closing"
            : isImageReturn
              ? "image"
              : "reflection"
      const title = isFirst
        ? "Arrival"
        : isBreath
          ? "Breath"
          : isLast
            ? "Closing"
            : isImageReturn
              ? "Image return"
              : "Stillness"

      return {
        id: `section-${caption.id || index + 1}`,
        title,
        startMs: caption.startMs,
        endMs: caption.endMs,
        kind,
        transcript: caption.text,
        captionCount: 1,
        skippable: !isFirst && !isLast,
        channels: {
          voice: true,
          ambient: kind !== "breath",
          breath: kind === "breath" || kind === "closing",
          pulse: kind === "breath",
          music: false
        }
      }
    })
  }

  return []
}

export function deriveRitualSectionsFromManifest(manifest: RitualArtifactManifest): RitualSection[] {
  const captions = manifest.surfaces.captions?.segments ?? []
  const explicitSections = cleanManifestSections(manifest, captions)
  if (explicitSections.length > 0) return explicitSections

  const surfaceSections = surfaceAwareManifestSections(manifest, captions)
  if (surfaceSections.length > 0) return surfaceSections

  return legacyCaptionSections(manifest, captions)
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
    meditation: manifest.surfaces.meditation?.enabled
      ? manifest.surfaces.meditation
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
    ritualSections: deriveRitualSectionsFromManifest(manifest)
  }
}
