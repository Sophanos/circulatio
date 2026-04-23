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

export type BreathVisualForm = "orb" | "wave" | "mandala" | "horizon"

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

export type PresentationArtifact = {
  id: string
  mode: ArtifactMode
  title: string
  summary: string
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
}

export type SessionPhase = "hold" | "rendering" | "playback" | "review"

export type SessionShell = {
  id: string
  phase: SessionPhase
  continuity: string
  lastTouchedAt: string
  aliveToday: string[]
  holdAcknowledgement: string
}
