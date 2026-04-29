import type { UIMessage } from "ai"

import type {
  RitualArtifactSourceRef,
  RitualCompletionBodyStatePayload,
  RitualSectionKind,
  RitualSectionPreferredLens
} from "@/lib/artifact-contract"
import type { RitualSessionEvent } from "@/hooks/use-ritual-experience"

export const RITUAL_GUIDANCE_ALLOWED_WRITES = [
  "body_state",
  "reflection",
  "practice_outcome",
  "active_imagination_note"
] as const
export type RitualGuidanceAllowedWrite = (typeof RITUAL_GUIDANCE_ALLOWED_WRITES)[number]

export const RITUAL_GUIDANCE_PHASES = [
  "preparing",
  "arrival",
  "ritual",
  "closing",
  "complete"
] as const
export type RitualGuidancePhase = (typeof RITUAL_GUIDANCE_PHASES)[number]

export const RITUAL_GUIDANCE_AVAILABLE_TRACKS = [
  "cinema",
  "photo",
  "breath",
  "meditation",
  "body_map",
  "captions",
  "voice"
] as const
export type RitualGuidanceAvailableTrack = (typeof RITUAL_GUIDANCE_AVAILABLE_TRACKS)[number]

export const RITUAL_GUIDANCE_PLAYBACK_STATES = [
  "not_started",
  "playing",
  "paused",
  "completed",
  "abandoned"
] as const
export type RitualGuidancePlaybackState = (typeof RITUAL_GUIDANCE_PLAYBACK_STATES)[number]

export const RITUAL_GUIDANCE_COMPLETION_STATES = [
  "idle",
  "submitting",
  "saved",
  "error"
] as const
export type RitualGuidanceCompletionState = (typeof RITUAL_GUIDANCE_COMPLETION_STATES)[number]

export const RITUAL_COMPANION_ACTION_TYPES = [
  "store_body_state",
  "store_reflection",
  "record_practice_outcome",
  "active_imagination_capture"
] as const
export type RitualCompanionActionType = (typeof RITUAL_COMPANION_ACTION_TYPES)[number]

export const RITUAL_COMPANION_ACTION_APPROVAL_STATES = [
  "proposed",
  "approved",
  "rejected",
  "executing",
  "executed",
  "failed"
] as const
export type RitualCompanionActionApprovalState =
  (typeof RITUAL_COMPANION_ACTION_APPROVAL_STATES)[number]

export type RitualGuidanceClientMetadata = {
  surface: "hermes-rituals-web"
  version: "ritual_companion_v1"
  variant?: "rail" | "live"
}

export type RitualGuidanceFrame = {
  phase: RitualGuidancePhase
  currentMs: number
  durationMs?: number
  activeSection: null | {
    id: string
    kind: RitualSectionKind
  }
  lens: RitualSectionPreferredLens
  availableTracks: RitualGuidanceAvailableTrack[]
  playback: {
    state: RitualGuidancePlaybackState
    completed: boolean
  }
  completion: {
    state: RitualGuidanceCompletionState
  }
  allowedWrites: RitualGuidanceAllowedWrite[]
}

export type RitualGuidanceSession = {
  guidanceSessionId: string
  hostSessionId: string
  artifactId: string
  ritualPlanId?: string
  userId: string
  privacyClass?: string
  sourceRefs: RitualArtifactSourceRef[]
  currentFrame: RitualGuidanceFrame
  allowedWrites: RitualGuidanceAllowedWrite[]
  mode: "hermes" | "local_stub"
  createdAt: string
  resumedAt?: string
  localPreview?: boolean
  durableWritesEnabled: boolean
}

export type RitualGuidanceSessionCreateRequest = {
  guidanceSessionId?: string
  hostSessionId: string
  artifactId: string
  ritualPlanId?: string
  userId?: string
  privacyClass?: string
  sourceRefs?: RitualArtifactSourceRef[]
  currentFrame: RitualGuidanceFrame
  clientMetadata?: RitualGuidanceClientMetadata
}

export type RitualGuidanceEventEnvelope = {
  guidanceSessionId: string
  hostSessionId: string
  artifactId: string
  eventId: string
  event: RitualSessionEvent
  frame: RitualGuidanceFrame
  sourceRefs: RitualArtifactSourceRef[]
  privacyClass?: string
  occurredAt: string
  clientMetadata?: RitualGuidanceClientMetadata
}

export type RitualCompanionAction = {
  actionId: string
  guidanceSessionId: string
  type: RitualCompanionActionType
  previewText: string
  sourceRefs: RitualArtifactSourceRef[]
  idempotencyKey: string
  approvalState: RitualCompanionActionApprovalState
  proposedAt: string
  decidedAt?: string
  frame: RitualGuidanceFrame
  payload:
    | { type: "store_body_state"; bodyState: RitualCompletionBodyStatePayload }
    | { type: "store_reflection"; text: string }
    | { type: "record_practice_outcome"; note: string; practiceSessionId?: string }
    | { type: "active_imagination_capture"; noteText: string }
  rejectionFinal?: boolean
  error?: string
}

export type RitualCompanionActionDecision = {
  action: RitualCompanionAction
  decision: "approve" | "reject"
}

export type RitualCompanionDataParts = {
  "ritual-companion-action": RitualCompanionAction
  "ritual-companion-status": {
    mode: "hermes" | "local_stub"
    durableWritesEnabled: boolean
    message?: string
  }
}

export type RitualCompanionUIMessage = UIMessage<unknown, RitualCompanionDataParts>

export type RitualChatRequest = {
  guidanceSessionId: string
  hostSessionId: string
  artifactId: string
  ritualPlanId?: string
  userId?: string
  privacyClass?: string
  sourceRefs: RitualArtifactSourceRef[]
  currentFrame: RitualGuidanceFrame
  messages: RitualCompanionUIMessage[]
  actionStates?: RitualCompanionAction[]
  clientMetadata?: RitualGuidanceClientMetadata
}
