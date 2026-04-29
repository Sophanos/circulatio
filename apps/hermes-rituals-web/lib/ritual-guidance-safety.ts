import type {
  RitualArtifactSourceRef,
  RitualCompletionBodyStatePayload,
  RitualSectionKind,
  RitualSectionPreferredLens
} from "@/lib/artifact-contract"
import type { RitualSessionEvent } from "@/hooks/use-ritual-experience"
import type {
  RitualExperienceCompletionStatus,
  RitualExperienceFrame
} from "@/lib/ritual-experience"
import {
  RITUAL_COMPANION_ACTION_APPROVAL_STATES,
  RITUAL_COMPANION_ACTION_TYPES,
  RITUAL_GUIDANCE_ALLOWED_WRITES,
  RITUAL_GUIDANCE_AVAILABLE_TRACKS,
  RITUAL_GUIDANCE_COMPLETION_STATES,
  RITUAL_GUIDANCE_PHASES,
  RITUAL_GUIDANCE_PLAYBACK_STATES,
  type RitualChatRequest,
  type RitualCompanionAction,
  type RitualCompanionActionApprovalState,
  type RitualCompanionActionDecision,
  type RitualCompanionActionType,
  type RitualGuidanceAllowedWrite,
  type RitualGuidanceAvailableTrack,
  type RitualGuidanceClientMetadata,
  type RitualGuidanceCompletionState,
  type RitualGuidanceEventEnvelope,
  type RitualGuidanceFrame,
  type RitualGuidancePlaybackState,
  type RitualGuidanceSession,
  type RitualGuidanceSessionCreateRequest
} from "@/lib/ritual-guidance-contract"

export const BLOCKED_RAW_PAYLOAD_KEYS = [
  "transcript",
  "captions",
  "rawMaterialText",
  "providerPrompt",
  "cameraData",
  "imageData",
  "audioBase64",
  "audioBlob",
  "videoFrame",
  "promptText"
] as const

const BLOCKED_KEY_SET = new Set<string>(BLOCKED_RAW_PAYLOAD_KEYS)
const GUIDANCE_ID_LIMIT = 180
const LABEL_LIMIT = 240
const TEXT_LIMIT = 4000
const PREVIEW_LIMIT = 1200
const MAX_SOURCE_REFS = 12
const MAX_EVIDENCE_IDS = 20
const DEFAULT_CLIENT_METADATA: RitualGuidanceClientMetadata = {
  surface: "hermes-rituals-web",
  version: "ritual_companion_v1"
}

const SECTION_KINDS = new Set<RitualSectionKind>([
  "arrival",
  "breath",
  "image",
  "reflection",
  "closing"
])
const LENSES = new Set<RitualSectionPreferredLens>([
  "cinema",
  "photo",
  "breath",
  "meditation",
  "body"
])
const BODY_ACTIVATIONS = new Set(["low", "moderate", "high", "overwhelming"])

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value && typeof value === "object" && !Array.isArray(value))
}

function boundedString(value: unknown, max = LABEL_LIMIT): string | undefined {
  if (typeof value !== "string") return undefined
  const text = value.trim()
  if (!text) return undefined
  return text.slice(0, max)
}

function requiredString(value: unknown, fallback: string, max = GUIDANCE_ID_LIMIT): string {
  return boundedString(value, max) ?? fallback
}

function nonNegativeMs(value: unknown, fallback = 0) {
  const number = typeof value === "number" ? value : Number(value)
  if (!Number.isFinite(number)) return fallback
  return Math.max(0, Math.round(number))
}

function optionalDuration(value: unknown) {
  const number = typeof value === "number" ? value : Number(value)
  if (!Number.isFinite(number) || number <= 0) return undefined
  return Math.round(number)
}

function oneOf<const T extends readonly string[]>(
  value: unknown,
  values: T,
  fallback: T[number]
): T[number] {
  return typeof value === "string" && values.includes(value) ? value : fallback
}

export function stripBlockedFields(value: unknown, depth = 0): unknown {
  if (depth > 16) return undefined
  if (Array.isArray(value)) {
    return value.map((item) => stripBlockedFields(item, depth + 1))
  }
  if (!isRecord(value)) return value

  const entries = Object.entries(value).flatMap(([key, item]) => {
    if (BLOCKED_KEY_SET.has(key)) return []
    const cleaned = stripBlockedFields(item, depth + 1)
    return cleaned === undefined ? [] : [[key, cleaned] as const]
  })
  return Object.fromEntries(entries)
}

export function sanitizeSourceRefs(value: unknown): RitualArtifactSourceRef[] {
  if (!Array.isArray(value)) return []
  return value.slice(0, MAX_SOURCE_REFS).flatMap((item): RitualArtifactSourceRef[] => {
    const raw = stripBlockedFields(item)
    if (!isRecord(raw)) return []
    const sourceType = boundedString(raw.sourceType, GUIDANCE_ID_LIMIT) ?? "unknown"
    const role = boundedString(raw.role, GUIDANCE_ID_LIMIT) ?? "context"
    const recordId = boundedString(raw.recordId, GUIDANCE_ID_LIMIT)
    const label = boundedString(raw.label, LABEL_LIMIT)
    const evidenceIds = Array.isArray(raw.evidenceIds)
      ? raw.evidenceIds
          .slice(0, MAX_EVIDENCE_IDS)
          .map((id) => boundedString(id, GUIDANCE_ID_LIMIT))
          .filter((id): id is string => Boolean(id))
      : undefined

    return [
      {
        sourceType,
        role,
        ...(recordId ? { recordId } : {}),
        ...(label ? { label } : {}),
        ...(evidenceIds && evidenceIds.length > 0 ? { evidenceIds } : {})
      }
    ]
  })
}

export function sanitizeClientMetadata(
  value: unknown,
  fallbackVariant?: "rail" | "live"
): RitualGuidanceClientMetadata {
  const raw = stripBlockedFields(value)
  const variant = isRecord(raw) && (raw.variant === "rail" || raw.variant === "live")
    ? raw.variant
    : fallbackVariant
  return {
    ...DEFAULT_CLIENT_METADATA,
    ...(variant ? { variant } : {})
  }
}

export function sanitizeAllowedWrites(value: unknown): RitualGuidanceAllowedWrite[] {
  const requested = Array.isArray(value) ? value : []
  const set = new Set<RitualGuidanceAllowedWrite>()
  requested.forEach((item) => {
    if (typeof item === "string" && RITUAL_GUIDANCE_ALLOWED_WRITES.includes(item as never)) {
      set.add(item as RitualGuidanceAllowedWrite)
    }
  })
  return RITUAL_GUIDANCE_ALLOWED_WRITES.filter((write) => set.has(write))
}

export function sanitizeAvailableTracks(value: unknown): RitualGuidanceAvailableTrack[] {
  const requested = Array.isArray(value) ? value : []
  const set = new Set<RitualGuidanceAvailableTrack>()
  requested.forEach((item) => {
    if (typeof item === "string" && RITUAL_GUIDANCE_AVAILABLE_TRACKS.includes(item as never)) {
      set.add(item as RitualGuidanceAvailableTrack)
    }
  })
  return RITUAL_GUIDANCE_AVAILABLE_TRACKS.filter((track) => set.has(track))
}

export function deriveGuidanceAllowedWrites(
  frame: Pick<RitualExperienceFrame, "activeSection" | "allowedWrites">,
  playbackCompleted: boolean,
  completionStatus: RitualExperienceCompletionStatus
): RitualGuidanceAllowedWrite[] {
  const internalWrites = new Set(frame.allowedWrites)
  const writes = new Set<RitualGuidanceAllowedWrite>()

  if (internalWrites.has("body_state") || playbackCompleted) writes.add("body_state")
  if (internalWrites.has("reflection_text")) writes.add("reflection")
  if (internalWrites.has("active_imagination_note")) writes.add("active_imagination_note")
  if (
    frame.activeSection?.kind === "closing" ||
    playbackCompleted ||
    completionStatus === "saved"
  ) {
    writes.add("practice_outcome")
  }

  return RITUAL_GUIDANCE_ALLOWED_WRITES.filter((write) => writes.has(write))
}

export function deriveGuidancePlaybackState({
  currentMs,
  isPlaying,
  playbackCompleted
}: {
  currentMs: number
  isPlaying: boolean
  playbackCompleted: boolean
}): RitualGuidancePlaybackState {
  if (playbackCompleted) return "completed"
  if (isPlaying) return "playing"
  if (currentMs <= 0) return "not_started"
  return "paused"
}

export function guidanceFrameFromExperienceFrame({
  frame,
  currentMs,
  durationMs,
  lens,
  isPlaying,
  playbackCompleted,
  completionStatus
}: {
  frame: RitualExperienceFrame
  currentMs: number
  durationMs?: number
  lens: RitualSectionPreferredLens
  isPlaying: boolean
  playbackCompleted: boolean
  completionStatus: RitualExperienceCompletionStatus
}): RitualGuidanceFrame {
  const allowedWrites = deriveGuidanceAllowedWrites(frame, playbackCompleted, completionStatus)
  return {
    phase: frame.phase,
    currentMs: nonNegativeMs(currentMs),
    ...(durationMs ? { durationMs: optionalDuration(durationMs) } : {}),
    activeSection: frame.activeSection
      ? {
          id: requiredString(frame.activeSection.id, "section", GUIDANCE_ID_LIMIT),
          kind: frame.activeSection.kind
        }
      : null,
    lens,
    availableTracks: sanitizeAvailableTracks(frame.availableTracks),
    playback: {
      state: deriveGuidancePlaybackState({ currentMs, isPlaying, playbackCompleted }),
      completed: playbackCompleted
    },
    completion: {
      state: completionStatus
    },
    allowedWrites
  }
}

export function emptyGuidanceFrame(overrides: Partial<RitualGuidanceFrame> = {}): RitualGuidanceFrame {
  const base: RitualGuidanceFrame = {
    phase: "preparing",
    currentMs: 0,
    activeSection: null,
    lens: "breath",
    availableTracks: [],
    playback: { state: "not_started", completed: false },
    completion: { state: "idle" },
    allowedWrites: []
  }

  return {
    ...base,
    ...overrides,
    playback: { ...base.playback, ...overrides.playback },
    completion: { ...base.completion, ...overrides.completion },
    availableTracks: sanitizeAvailableTracks(overrides.availableTracks ?? base.availableTracks),
    allowedWrites: sanitizeAllowedWrites(overrides.allowedWrites ?? base.allowedWrites)
  }
}

export function sanitizeGuidanceFrame(value: unknown): RitualGuidanceFrame {
  const raw = isRecord(stripBlockedFields(value)) ? (stripBlockedFields(value) as Record<string, unknown>) : {}
  const activeRaw = isRecord(raw.activeSection) ? raw.activeSection : null
  const activeKind = activeRaw && SECTION_KINDS.has(activeRaw.kind as RitualSectionKind)
    ? (activeRaw.kind as RitualSectionKind)
    : null
  const activeId = activeRaw ? boundedString(activeRaw.id, GUIDANCE_ID_LIMIT) : undefined
  const playbackRaw = isRecord(raw.playback) ? raw.playback : {}
  const completionRaw = isRecord(raw.completion) ? raw.completion : {}
  const playbackState = oneOf(
    playbackRaw.state,
    RITUAL_GUIDANCE_PLAYBACK_STATES,
    "not_started"
  ) as RitualGuidancePlaybackState
  const completionState = oneOf(
    completionRaw.state,
    RITUAL_GUIDANCE_COMPLETION_STATES,
    "idle"
  ) as RitualGuidanceCompletionState

  return {
    phase: oneOf(raw.phase, RITUAL_GUIDANCE_PHASES, "preparing"),
    currentMs: nonNegativeMs(raw.currentMs),
    ...(optionalDuration(raw.durationMs) ? { durationMs: optionalDuration(raw.durationMs) } : {}),
    activeSection: activeId && activeKind ? { id: activeId, kind: activeKind } : null,
    lens: LENSES.has(raw.lens as RitualSectionPreferredLens)
      ? (raw.lens as RitualSectionPreferredLens)
      : "breath",
    availableTracks: sanitizeAvailableTracks(raw.availableTracks),
    playback: {
      state: playbackState,
      completed: playbackRaw.completed === true || playbackState === "completed"
    },
    completion: {
      state: completionState
    },
    allowedWrites: sanitizeAllowedWrites(raw.allowedWrites)
  }
}

export function stableGuidanceSessionId({
  hostSessionId,
  artifactId,
  userId
}: {
  hostSessionId: string
  artifactId: string
  userId?: string
}) {
  const seed = `${hostSessionId}:${artifactId}:${userId || "anonymous"}`
  let hash = 2166136261
  for (let index = 0; index < seed.length; index += 1) {
    hash ^= seed.charCodeAt(index)
    hash = Math.imul(hash, 16777619)
  }
  return `guidance_${(hash >>> 0).toString(36)}`
}

export function sanitizeGuidanceSessionCreateRequest(
  value: unknown
): RitualGuidanceSessionCreateRequest | null {
  const raw = isRecord(stripBlockedFields(value)) ? (stripBlockedFields(value) as Record<string, unknown>) : null
  if (!raw) return null
  const hostSessionId = boundedString(raw.hostSessionId, GUIDANCE_ID_LIMIT)
  const artifactId = boundedString(raw.artifactId, GUIDANCE_ID_LIMIT)
  if (!hostSessionId || !artifactId) return null

  return {
    guidanceSessionId: boundedString(raw.guidanceSessionId, GUIDANCE_ID_LIMIT),
    hostSessionId,
    artifactId,
    ritualPlanId: boundedString(raw.ritualPlanId, GUIDANCE_ID_LIMIT),
    userId: boundedString(raw.userId, GUIDANCE_ID_LIMIT),
    privacyClass: boundedString(raw.privacyClass, GUIDANCE_ID_LIMIT),
    sourceRefs: sanitizeSourceRefs(raw.sourceRefs),
    currentFrame: sanitizeGuidanceFrame(raw.currentFrame),
    clientMetadata: sanitizeClientMetadata(raw.clientMetadata)
  }
}

export function buildLocalGuidanceSession(
  request: RitualGuidanceSessionCreateRequest,
  now = new Date().toISOString()
): RitualGuidanceSession {
  const guidanceSessionId =
    request.guidanceSessionId ??
    stableGuidanceSessionId({
      hostSessionId: request.hostSessionId,
      artifactId: request.artifactId,
      userId: request.userId
    })
  return {
    guidanceSessionId,
    hostSessionId: request.hostSessionId,
    artifactId: request.artifactId,
    ritualPlanId: request.ritualPlanId,
    userId: request.userId ?? "anonymous",
    privacyClass: request.privacyClass,
    sourceRefs: request.sourceRefs ?? [],
    currentFrame: request.currentFrame,
    allowedWrites: request.currentFrame.allowedWrites,
    mode: "local_stub",
    createdAt: now,
    localPreview: true,
    durableWritesEnabled: false
  }
}

export function normalizeGuidanceSession(
  value: unknown,
  fallback: RitualGuidanceSessionCreateRequest
): RitualGuidanceSession {
  const raw = isRecord(stripBlockedFields(value)) ? (stripBlockedFields(value) as Record<string, unknown>) : {}
  const frame = sanitizeGuidanceFrame(raw.currentFrame ?? fallback.currentFrame)
  const mode = raw.mode === "local_stub" ? "local_stub" : "hermes"
  return {
    guidanceSessionId: requiredString(
      raw.guidanceSessionId,
      fallback.guidanceSessionId ??
        stableGuidanceSessionId({
          hostSessionId: fallback.hostSessionId,
          artifactId: fallback.artifactId,
          userId: fallback.userId
        })
    ),
    hostSessionId: requiredString(raw.hostSessionId, fallback.hostSessionId),
    artifactId: requiredString(raw.artifactId, fallback.artifactId),
    ritualPlanId: boundedString(raw.ritualPlanId, GUIDANCE_ID_LIMIT) ?? fallback.ritualPlanId,
    userId: boundedString(raw.userId, GUIDANCE_ID_LIMIT) ?? fallback.userId ?? "anonymous",
    privacyClass: boundedString(raw.privacyClass, GUIDANCE_ID_LIMIT) ?? fallback.privacyClass,
    sourceRefs: sanitizeSourceRefs(raw.sourceRefs).length > 0
      ? sanitizeSourceRefs(raw.sourceRefs)
      : fallback.sourceRefs ?? [],
    currentFrame: frame,
    allowedWrites: frame.allowedWrites,
    mode,
    createdAt: boundedString(raw.createdAt, GUIDANCE_ID_LIMIT) ?? new Date().toISOString(),
    resumedAt: boundedString(raw.resumedAt, GUIDANCE_ID_LIMIT),
    localPreview: mode === "local_stub" ? raw.localPreview !== false : raw.localPreview === true,
    durableWritesEnabled: raw.durableWritesEnabled === true && mode === "hermes"
  }
}

function sanitizeSessionEvent(value: unknown): RitualSessionEvent | null {
  const raw = isRecord(stripBlockedFields(value)) ? (stripBlockedFields(value) as Record<string, unknown>) : null
  if (!raw || typeof raw.type !== "string") return null
  const artifactId = boundedString(raw.artifactId, GUIDANCE_ID_LIMIT)
  if (!artifactId) return null
  const atMs = nonNegativeMs(raw.atMs)

  switch (raw.type) {
    case "ritual_started":
      return { type: "ritual_started", artifactId, atMs }
    case "section_entered": {
      const sectionId = boundedString(raw.sectionId, GUIDANCE_ID_LIMIT)
      const sectionKind = SECTION_KINDS.has(raw.sectionKind as RitualSectionKind)
        ? (raw.sectionKind as RitualSectionKind)
        : null
      return sectionId && sectionKind
        ? { type: "section_entered", artifactId, atMs, sectionId, sectionKind }
        : null
    }
    case "lens_changed": {
      const lens = LENSES.has(raw.lens as RitualSectionPreferredLens)
        ? (raw.lens as RitualSectionPreferredLens)
        : null
      return lens
        ? {
            type: "lens_changed",
            artifactId,
            atMs,
            lens,
            sectionId: boundedString(raw.sectionId, GUIDANCE_ID_LIMIT)
          }
        : null
    }
    case "body_response_captured":
      return {
        type: "body_response_captured",
        artifactId,
        atMs,
        sectionId: boundedString(raw.sectionId, GUIDANCE_ID_LIMIT)
      }
    case "active_imagination_note_created":
      return {
        type: "active_imagination_note_created",
        artifactId,
        atMs,
        sectionId: boundedString(raw.sectionId, GUIDANCE_ID_LIMIT)
      }
    case "ritual_completed":
      return { type: "ritual_completed", artifactId, atMs }
    default:
      return null
  }
}

export function sanitizeGuidanceEventEnvelope(
  value: unknown,
  routeGuidanceSessionId?: string
): RitualGuidanceEventEnvelope | null {
  const raw = isRecord(stripBlockedFields(value)) ? (stripBlockedFields(value) as Record<string, unknown>) : null
  if (!raw) return null
  const event = sanitizeSessionEvent(raw.event)
  if (!event) return null
  const guidanceSessionId =
    boundedString(routeGuidanceSessionId, GUIDANCE_ID_LIMIT) ??
    boundedString(raw.guidanceSessionId, GUIDANCE_ID_LIMIT)
  const hostSessionId = boundedString(raw.hostSessionId, GUIDANCE_ID_LIMIT)
  const artifactId = boundedString(raw.artifactId, GUIDANCE_ID_LIMIT) ?? event.artifactId
  if (!guidanceSessionId || !hostSessionId || !artifactId) return null

  return {
    guidanceSessionId,
    hostSessionId,
    artifactId,
    eventId:
      boundedString(raw.eventId, GUIDANCE_ID_LIMIT) ??
      `${guidanceSessionId}:${event.type}:${Math.round(event.atMs)}`,
    event,
    frame: sanitizeGuidanceFrame(raw.frame),
    sourceRefs: sanitizeSourceRefs(raw.sourceRefs),
    privacyClass: boundedString(raw.privacyClass, GUIDANCE_ID_LIMIT),
    occurredAt: boundedString(raw.occurredAt, GUIDANCE_ID_LIMIT) ?? new Date().toISOString(),
    clientMetadata: sanitizeClientMetadata(raw.clientMetadata)
  }
}

function sanitizeBodyState(value: unknown): RitualCompletionBodyStatePayload | null {
  const raw = isRecord(stripBlockedFields(value)) ? (stripBlockedFields(value) as Record<string, unknown>) : null
  if (!raw) return null
  const sensation = boundedString(raw.sensation, TEXT_LIMIT)
  if (!sensation) return null
  const activation = boundedString(raw.activation, GUIDANCE_ID_LIMIT)
  return {
    sensation,
    bodyRegion: boundedString(raw.bodyRegion, GUIDANCE_ID_LIMIT),
    activation: activation && BODY_ACTIVATIONS.has(activation)
      ? (activation as RitualCompletionBodyStatePayload["activation"])
      : undefined,
    tone: boundedString(raw.tone, LABEL_LIMIT),
    temporalContext: boundedString(raw.temporalContext, LABEL_LIMIT),
    noteText: boundedString(raw.noteText, TEXT_LIMIT),
    privacyClass: boundedString(raw.privacyClass, GUIDANCE_ID_LIMIT)
  }
}

export function sanitizeRitualCompanionAction(value: unknown): RitualCompanionAction | null {
  const raw = isRecord(stripBlockedFields(value)) ? (stripBlockedFields(value) as Record<string, unknown>) : null
  if (!raw) return null
  const actionId = boundedString(raw.actionId, GUIDANCE_ID_LIMIT)
  const guidanceSessionId = boundedString(raw.guidanceSessionId, GUIDANCE_ID_LIMIT)
  const actionType =
    typeof raw.type === "string" &&
    RITUAL_COMPANION_ACTION_TYPES.includes(raw.type as RitualCompanionActionType)
      ? (raw.type as RitualCompanionActionType)
      : undefined
  const approvalState: RitualCompanionActionApprovalState =
    typeof raw.approvalState === "string" &&
    RITUAL_COMPANION_ACTION_APPROVAL_STATES.includes(
      raw.approvalState as RitualCompanionActionApprovalState
    )
      ? (raw.approvalState as RitualCompanionActionApprovalState)
      : "proposed"
  const idempotencyKey = boundedString(raw.idempotencyKey, GUIDANCE_ID_LIMIT)
  const payloadRaw = isRecord(raw.payload) ? raw.payload : null
  if (!actionId || !guidanceSessionId || !actionType || !idempotencyKey || !payloadRaw) return null

  let payload: RitualCompanionAction["payload"] | null = null
  if (actionType === "store_body_state" && payloadRaw.type === "store_body_state") {
    const bodyState = sanitizeBodyState(payloadRaw.bodyState)
    if (bodyState) payload = { type: "store_body_state", bodyState }
  } else if (actionType === "store_reflection" && payloadRaw.type === "store_reflection") {
    const text = boundedString(payloadRaw.text, TEXT_LIMIT)
    if (text) payload = { type: "store_reflection", text }
  } else if (
    actionType === "record_practice_outcome" &&
    payloadRaw.type === "record_practice_outcome"
  ) {
    const note = boundedString(payloadRaw.note, TEXT_LIMIT)
    if (note) {
      payload = {
        type: "record_practice_outcome",
        note,
        practiceSessionId: boundedString(payloadRaw.practiceSessionId, GUIDANCE_ID_LIMIT)
      }
    }
  } else if (
    actionType === "active_imagination_capture" &&
    payloadRaw.type === "active_imagination_capture"
  ) {
    const noteText = boundedString(payloadRaw.noteText, TEXT_LIMIT)
    if (noteText) payload = { type: "active_imagination_capture", noteText }
  }
  if (!payload) return null

  return {
    actionId,
    guidanceSessionId,
    type: actionType,
    previewText: boundedString(raw.previewText, PREVIEW_LIMIT) ?? "Proposed ritual write",
    sourceRefs: sanitizeSourceRefs(raw.sourceRefs),
    idempotencyKey,
    approvalState,
    proposedAt: boundedString(raw.proposedAt, GUIDANCE_ID_LIMIT) ?? new Date().toISOString(),
    decidedAt: boundedString(raw.decidedAt, GUIDANCE_ID_LIMIT),
    frame: sanitizeGuidanceFrame(raw.frame),
    payload,
    rejectionFinal: raw.rejectionFinal === true,
    error: boundedString(raw.error, PREVIEW_LIMIT)
  }
}

export function sanitizeActionDecisionRequest(value: unknown): RitualCompanionActionDecision | null {
  const raw = isRecord(stripBlockedFields(value)) ? (stripBlockedFields(value) as Record<string, unknown>) : null
  if (!raw) return null
  const decision = raw.decision === "approve" || raw.decision === "reject" ? raw.decision : null
  const action = sanitizeRitualCompanionAction(raw.action)
  if (!decision || !action) return null
  return { decision, action }
}

function sanitizeMessagePart(part: unknown): unknown | null {
  const raw = isRecord(stripBlockedFields(part)) ? (stripBlockedFields(part) as Record<string, unknown>) : null
  if (!raw || typeof raw.type !== "string") return null
  if (raw.type === "text") {
    const text = boundedString(raw.text, TEXT_LIMIT * 2)
    return text ? { type: "text", text } : null
  }
  if (raw.type === "step-start") return { type: "step-start" }
  if (raw.type === "data-ritual-companion-action") {
    const action = sanitizeRitualCompanionAction(raw.data)
    return action ? { type: raw.type, id: boundedString(raw.id, GUIDANCE_ID_LIMIT), data: action } : null
  }
  if (raw.type === "data-ritual-companion-status") {
    const data = isRecord(raw.data) ? raw.data : {}
    return {
      type: raw.type,
      id: boundedString(raw.id, GUIDANCE_ID_LIMIT),
      data: {
        mode: data.mode === "hermes" ? "hermes" : "local_stub",
        durableWritesEnabled: data.durableWritesEnabled === true,
        message: boundedString(data.message, PREVIEW_LIMIT)
      }
    }
  }
  if (raw.type.startsWith("tool-") || raw.type === "dynamic-tool") {
    return raw
  }
  return null
}

export function sanitizeChatMessages(value: unknown): RitualChatRequest["messages"] {
  if (!Array.isArray(value)) return []
  return value.slice(-50).flatMap((item) => {
    const raw = isRecord(stripBlockedFields(item)) ? (stripBlockedFields(item) as Record<string, unknown>) : null
    if (!raw) return []
    const role = raw.role === "system" || raw.role === "user" || raw.role === "assistant"
      ? raw.role
      : null
    if (!role) return []
    const parts = Array.isArray(raw.parts)
      ? raw.parts.map(sanitizeMessagePart).filter((part): part is NonNullable<typeof part> => Boolean(part))
      : []
    if (parts.length === 0) return []
    return [
      {
        id: requiredString(raw.id, `msg_${parts.length}`, GUIDANCE_ID_LIMIT),
        role,
        parts
      } as RitualChatRequest["messages"][number]
    ]
  })
}

export function sanitizeRitualChatRequest(value: unknown): RitualChatRequest | null {
  const raw = isRecord(stripBlockedFields(value)) ? (stripBlockedFields(value) as Record<string, unknown>) : null
  if (!raw) return null
  const guidanceSessionId = boundedString(raw.guidanceSessionId, GUIDANCE_ID_LIMIT)
  const hostSessionId = boundedString(raw.hostSessionId, GUIDANCE_ID_LIMIT)
  const artifactId = boundedString(raw.artifactId, GUIDANCE_ID_LIMIT)
  if (!guidanceSessionId || !hostSessionId || !artifactId) return null

  const actionStates = Array.isArray(raw.actionStates)
    ? raw.actionStates
        .map(sanitizeRitualCompanionAction)
        .filter((action): action is RitualCompanionAction => Boolean(action))
    : undefined

  return {
    guidanceSessionId,
    hostSessionId,
    artifactId,
    ritualPlanId: boundedString(raw.ritualPlanId, GUIDANCE_ID_LIMIT),
    userId: boundedString(raw.userId, GUIDANCE_ID_LIMIT),
    privacyClass: boundedString(raw.privacyClass, GUIDANCE_ID_LIMIT),
    sourceRefs: sanitizeSourceRefs(raw.sourceRefs),
    currentFrame: sanitizeGuidanceFrame(raw.currentFrame),
    messages: sanitizeChatMessages(raw.messages),
    actionStates,
    clientMetadata: sanitizeClientMetadata(raw.clientMetadata)
  }
}
