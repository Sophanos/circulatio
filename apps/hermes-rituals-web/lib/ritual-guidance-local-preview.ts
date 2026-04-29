import type {
  RitualChatRequest,
  RitualCompanionAction,
  RitualCompanionActionType,
  RitualGuidanceAllowedWrite
} from "@/lib/ritual-guidance-contract"
import {
  sanitizeRitualCompanionAction,
  sanitizeSourceRefs,
  stripBlockedFields
} from "@/lib/ritual-guidance-safety"

export type LocalPreviewActionBuildResult = {
  action: RitualCompanionAction | null
  reason:
    | "built"
    | "no_user_text"
    | "no_storage_intent"
    | "write_not_allowed"
    | "unsupported_intent"
}

const TEXT_LIMIT = 4000
const PREVIEW_LIMIT = 1200
const WRITE_VERBS = ["save", "store", "record", "hold", "remember", "capture"] as const

type IntentMatch = {
  type: RitualCompanionActionType
  write: RitualGuidanceAllowedWrite
}

function latestUserText(request: RitualChatRequest) {
  const message = [...request.messages].reverse().find((item) => item.role === "user")
  if (!message) return ""
  return message.parts
    .flatMap((part) => (part.type === "text" ? [part.text] : []))
    .join(" ")
    .trim()
    .slice(0, TEXT_LIMIT)
}

function hasExplicitWriteVerb(text: string) {
  const lowered = text.toLowerCase()
  return WRITE_VERBS.some((verb) => new RegExp(`\\b${verb}\\b`, "i").test(lowered))
}

function matchIntent(text: string): IntentMatch | null {
  const lowered = text.toLowerCase()
  if (/\b(practice|outcome|feedback|landed|fit|helped|did not help)\b/i.test(lowered)) {
    return { type: "record_practice_outcome", write: "practice_outcome" }
  }
  if (/\b(active imagination|imaginal|image note|inner image|dream image)\b/i.test(lowered)) {
    return { type: "active_imagination_capture", write: "active_imagination_note" }
  }
  if (/\b(reflection|note|words?|thought|meaning|memory)\b/i.test(lowered)) {
    return { type: "store_reflection", write: "reflection" }
  }
  if (/\b(body|sensation|felt sense|chest|belly|throat|shoulder|breath)\b/i.test(lowered)) {
    return { type: "store_body_state", write: "body_state" }
  }
  return null
}

function base36Fnv1a(input: string) {
  let hash = 2166136261
  for (let index = 0; index < input.length; index += 1) {
    hash ^= input.charCodeAt(index)
    hash = Math.imul(hash, 16777619)
  }
  return (hash >>> 0).toString(36)
}

function cleanText(value: string, max = TEXT_LIMIT) {
  const cleaned = stripBlockedFields({ text: value })
  const text =
    cleaned && typeof cleaned === "object" && !Array.isArray(cleaned)
      ? (cleaned as Record<string, unknown>).text
      : value
  return typeof text === "string" ? text.trim().slice(0, max) : ""
}

function stripCommandPhrase(text: string) {
  return text
    .replace(
      /^\s*(?:please\s+)?(?:save|store|record|hold|remember|capture)(?:\s+this)?(?:\s+(?:reflection|body state|body note|practice outcome|practice feedback|active imagination|imaginal note|note|words?))?\s*[:\-]?\s*/i,
      ""
    )
    .trim()
}

function previewText(type: RitualCompanionActionType, extractedText: string) {
  switch (type) {
    case "store_body_state":
      return `Propose saving this body detail: ${extractedText}`.slice(0, PREVIEW_LIMIT)
    case "store_reflection":
      return `Propose saving these words: ${extractedText}`.slice(0, PREVIEW_LIMIT)
    case "record_practice_outcome":
      return `Propose saving this practice feedback: ${extractedText}`.slice(0, PREVIEW_LIMIT)
    case "active_imagination_capture":
      return `Propose saving this imaginal note: ${extractedText}`.slice(0, PREVIEW_LIMIT)
  }
}

function payloadFor(
  type: RitualCompanionActionType,
  extractedText: string,
  request: RitualChatRequest
): RitualCompanionAction["payload"] {
  switch (type) {
    case "store_body_state":
      return {
        type,
        bodyState: {
          sensation: extractedText,
          temporalContext: "ritual_companion_local_preview",
          privacyClass: request.privacyClass
        }
      }
    case "store_reflection":
      return { type, text: extractedText }
    case "record_practice_outcome":
      return { type, note: extractedText }
    case "active_imagination_capture":
      return { type, noteText: extractedText }
  }
}

export function buildLocalPreviewCompanionAction(
  request: RitualChatRequest,
  now = new Date().toISOString()
): LocalPreviewActionBuildResult {
  const userText = latestUserText(request)
  if (!userText) return { action: null, reason: "no_user_text" }
  if (!hasExplicitWriteVerb(userText)) return { action: null, reason: "no_storage_intent" }

  const intent = matchIntent(userText)
  if (!intent) return { action: null, reason: "unsupported_intent" }
  if (!request.currentFrame.allowedWrites.includes(intent.write)) {
    return { action: null, reason: "write_not_allowed" }
  }

  const extractedText = cleanText(stripCommandPhrase(userText)) || cleanText(userText)
  if (!extractedText) return { action: null, reason: "no_user_text" }

  const actionId = `local_action_${base36Fnv1a(
    `${request.guidanceSessionId}:${intent.type}:${userText.trim().toLowerCase()}`
  )}`
  const action = sanitizeRitualCompanionAction({
    actionId,
    guidanceSessionId: request.guidanceSessionId,
    type: intent.type,
    previewText: previewText(intent.type, extractedText),
    sourceRefs: sanitizeSourceRefs(request.sourceRefs),
    idempotencyKey: `${request.guidanceSessionId}:${actionId}`,
    approvalState: "proposed",
    proposedAt: now,
    frame: request.currentFrame,
    payload: payloadFor(intent.type, extractedText, request)
  })

  return action ? { action, reason: "built" } : { action: null, reason: "unsupported_intent" }
}
