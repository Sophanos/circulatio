import type {
  PresentationArtifact,
  RitualSection,
  RitualSectionPreferredLens
} from "@/lib/artifact-contract"

export type RitualExperiencePhase = "preparing" | "arrival" | "ritual" | "closing" | "complete"
export type RitualExperienceTrack =
  | "cinema"
  | "photo"
  | "breath"
  | "meditation"
  | "body_map"
  | "captions"
  | "voice"
export type RitualBodyPromptMode = "hidden" | "inline_hint" | "focused_capture"
export type RitualAllowedWrite = "body_state" | "reflection_text" | "active_imagination_note"
export type RitualExperienceCompletionStatus = "idle" | "submitting" | "saved" | "error"

export type RitualExperienceFrame = {
  phase: RitualExperiencePhase
  activeSection: RitualSection | null
  recommendedLens: RitualSectionPreferredLens
  effectiveLens: RitualSectionPreferredLens
  availableTracks: RitualExperienceTrack[]
  bodyPromptMode: RitualBodyPromptMode
  allowedWrites: RitualAllowedWrite[]
}

export type DeriveRitualExperienceFrameInput = {
  artifact: PresentationArtifact
  sections: RitualSection[]
  currentMs: number
  userLensOverride?: RitualSectionPreferredLens | null
  completionStatus?: RitualExperienceCompletionStatus
}

export function selectInitialRitualLens(artifact: PresentationArtifact): RitualSectionPreferredLens {
  if (hasCinemaTrack(artifact)) return "cinema"
  if (hasPhotoTrack(artifact)) return "photo"
  return "breath"
}

export function deriveRitualExperienceFrame({
  artifact,
  sections,
  currentMs,
  userLensOverride,
  completionStatus = "idle"
}: DeriveRitualExperienceFrameInput): RitualExperienceFrame {
  const activeSection = getActiveSection(sections, currentMs)
  const availableTracks = getAvailableTracks(artifact)
  const bodyPromptMode = getBodyPromptMode({
    artifact,
    activeSection,
    userLensOverride,
    completionStatus
  })
  const recommendedLens = getRecommendedLens({
    artifact,
    activeSection,
    bodyPromptMode
  })
  const effectiveLens = userLensOverride ?? recommendedLens

  return {
    phase: getPhase({ sections, activeSection, currentMs, completionStatus }),
    activeSection,
    recommendedLens,
    effectiveLens,
    availableTracks,
    bodyPromptMode,
    allowedWrites: getAllowedWrites(activeSection)
  }
}

function getActiveSection(sections: RitualSection[], currentMs: number) {
  return sections.find((section) => currentMs >= section.startMs && currentMs < section.endMs) ?? null
}

function getPhase({
  sections,
  activeSection,
  currentMs,
  completionStatus
}: {
  sections: RitualSection[]
  activeSection: RitualSection | null
  currentMs: number
  completionStatus: RitualExperienceCompletionStatus
}): RitualExperiencePhase {
  if (completionStatus === "saved") return "complete"
  if (activeSection?.kind === "arrival") return "arrival"
  if (activeSection?.kind === "closing") return "closing"
  if (!activeSection) {
    const firstStart = sections[0]?.startMs ?? 0
    return currentMs < firstStart ? "preparing" : "ritual"
  }
  return "ritual"
}

function getRecommendedLens({
  artifact,
  activeSection,
  bodyPromptMode
}: {
  artifact: PresentationArtifact
  activeSection: RitualSection | null
  bodyPromptMode: RitualBodyPromptMode
}): RitualSectionPreferredLens {
  if (bodyPromptMode === "focused_capture") return "body"
  if (activeSection?.preferredLens && activeSection.preferredLens !== "body") {
    return activeSection.preferredLens
  }

  switch (activeSection?.kind) {
    case "breath":
      return "breath"
    case "image":
      return selectVisualLens(artifact)
    case "reflection":
      return hasMeditationTrack(artifact) ? "meditation" : selectVisualLens(artifact)
    case "closing":
      return hasMeditationTrack(artifact) ? "meditation" : selectVisualLens(artifact)
    case "arrival":
    default:
      return selectInitialRitualLens(artifact)
  }
}

function getBodyPromptMode({
  artifact,
  activeSection,
  userLensOverride,
  completionStatus
}: {
  artifact: PresentationArtifact
  activeSection: RitualSection | null
  userLensOverride?: RitualSectionPreferredLens | null
  completionStatus: RitualExperienceCompletionStatus
}): RitualBodyPromptMode {
  if (!artifact.captureBodyResponse && !artifact.completionEndpoint) return "hidden"
  if (userLensOverride === "body") return "focused_capture"
  if (completionStatus === "submitting" || completionStatus === "saved") return "focused_capture"
  return activeSection?.kind === "closing" ? "inline_hint" : "hidden"
}

function getAllowedWrites(activeSection: RitualSection | null): RitualAllowedWrite[] {
  if (activeSection?.kind === "closing") {
    return ["body_state", "reflection_text", "active_imagination_note"]
  }
  if (activeSection?.kind === "reflection") {
    return ["reflection_text", "active_imagination_note"]
  }
  return []
}

function getAvailableTracks(artifact: PresentationArtifact): RitualExperienceTrack[] {
  const tracks: RitualExperienceTrack[] = []
  if (hasCinemaTrack(artifact)) tracks.push("cinema")
  if (hasPhotoTrack(artifact)) tracks.push("photo")
  if (artifact.breathCycle) tracks.push("breath")
  if (hasMeditationTrack(artifact)) tracks.push("meditation")
  if (artifact.captureBodyResponse || artifact.completionEndpoint) tracks.push("body_map")
  if ((artifact.captions?.length ?? 0) > 0) tracks.push("captions")
  if (artifact.audioUrl || artifact.transcript || (artifact.captions?.length ?? 0) > 0) {
    tracks.push("voice")
  }
  return tracks
}

function selectVisualLens(artifact: PresentationArtifact): RitualSectionPreferredLens {
  if (hasCinemaTrack(artifact)) return "cinema"
  if (hasPhotoTrack(artifact)) return "photo"
  return "meditation"
}

function hasCinemaTrack(artifact: PresentationArtifact) {
  return Boolean(
    artifact.stageVideo ||
      (artifact.videoUrl && !artifact.videoUrl.startsWith("mock://"))
  )
}

function hasPhotoTrack(artifact: PresentationArtifact) {
  return Boolean(artifact.coverImageUrl || (artifact.scenes?.length ?? 0) > 0)
}

function hasMeditationTrack(artifact: PresentationArtifact) {
  return Boolean(artifact.meditation?.enabled ?? artifact.breathCycle)
}
