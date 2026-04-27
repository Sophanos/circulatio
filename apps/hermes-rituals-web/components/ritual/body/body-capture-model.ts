export const CANONICAL_BODY_REGION_IDS = [
  "head_face",
  "jaw_throat",
  "neck",
  "shoulders",
  "chest",
  "upper_back",
  "belly",
  "pelvis",
  "lower_back",
  "left_arm",
  "right_arm",
  "left_hand",
  "right_hand",
  "left_leg",
  "right_leg",
  "left_foot",
  "right_foot",
  "whole_body",
  "unclear"
] as const

export type BodyRegionId = (typeof CANONICAL_BODY_REGION_IDS)[number]
export type BodyActivation = "low" | "moderate" | "high" | "overwhelming"
export type BodyCompletionStatus = "idle" | "submitting" | "saved" | "error"
export type BodyView = "front" | "back"
export type BodyMapMode = "full2d" | "compact2d" | "summary" | "fallback"

export type BodyStateDraft = {
  sensation: string
  bodyRegion?: BodyRegionId
  activation?: BodyActivation
  tone?: string
  temporalContext?: string
  noteText?: string
  privacyClass?: string
}

export const EMPTY_BODY_STATE_DRAFT: BodyStateDraft = {
  bodyRegion: undefined,
  sensation: "",
  activation: undefined,
  tone: "",
  temporalContext: "post_ritual_completion",
  noteText: ""
}

export const REGION_LABELS: Record<BodyRegionId, string> = {
  head_face: "Head / face",
  jaw_throat: "Jaw / throat",
  neck: "Neck",
  shoulders: "Shoulders",
  chest: "Chest",
  upper_back: "Upper back",
  belly: "Belly",
  pelvis: "Pelvis",
  lower_back: "Lower back",
  left_arm: "Left arm",
  right_arm: "Right arm",
  left_hand: "Left hand",
  right_hand: "Right hand",
  left_leg: "Left leg",
  right_leg: "Right leg",
  left_foot: "Left foot",
  right_foot: "Right foot",
  whole_body: "Whole body",
  unclear: "Unclear"
}

export const SENSATIONS = [
  "tightness",
  "pressure",
  "warmth",
  "coolness",
  "tingling",
  "numbness",
  "heaviness",
  "lightness",
  "pulsing",
  "trembling",
  "expansion",
  "contraction",
  "ache",
  "openness",
  "blankness"
] as const

export const TONES = ["steady", "charged", "soft", "distant", "clear", "raw"] as const

export const ACTIVATIONS: Array<{ id: BodyActivation; label: string }> = [
  { id: "low", label: "Low" },
  { id: "moderate", label: "Moderate" },
  { id: "high", label: "High" },
  { id: "overwhelming", label: "Overwhelming" }
]

export const FRONT_BODY_REGION_IDS: BodyRegionId[] = [
  "head_face",
  "jaw_throat",
  "neck",
  "shoulders",
  "chest",
  "belly",
  "pelvis",
  "left_arm",
  "right_arm",
  "left_hand",
  "right_hand",
  "left_leg",
  "right_leg",
  "left_foot",
  "right_foot"
]

export const BACK_BODY_REGION_IDS: BodyRegionId[] = [
  "head_face",
  "neck",
  "shoulders",
  "upper_back",
  "lower_back",
  "pelvis",
  "left_arm",
  "right_arm",
  "left_hand",
  "right_hand",
  "left_leg",
  "right_leg",
  "left_foot",
  "right_foot"
]

export const DEFAULT_REGION_VIEW: Partial<Record<BodyRegionId, BodyView>> = {
  jaw_throat: "front",
  chest: "front",
  belly: "front",
  upper_back: "back",
  lower_back: "back"
}

export function isCanonicalBodyRegionId(value: unknown): value is BodyRegionId {
  return (
    typeof value === "string" &&
    (CANONICAL_BODY_REGION_IDS as readonly string[]).includes(value)
  )
}

export function cleanBodyDraft(value: BodyStateDraft) {
  return {
    ...value,
    sensation: value.sensation.trim(),
    tone: value.tone?.trim() || undefined,
    noteText: value.noteText?.trim() || undefined
  }
}

export function appendBodyText(current: string | undefined, next: string) {
  const incoming = next.trim()
  if (!incoming) return current ?? ""
  const existing = current?.trim()
  return existing ? `${existing} ${incoming}` : incoming
}
