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

export type BreathCycle = {
  inhaleMs: number
  holdMs: number
  exhaleMs: number
  restMs: number
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
