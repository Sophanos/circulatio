import { createUIMessageStream, createUIMessageStreamResponse } from "ai"

import {
  forwardRitualChatStream,
  safeStreamingHeaders
} from "@/lib/hermes-guidance-adapter"
import type { RitualCompanionUIMessage } from "@/lib/ritual-guidance-contract"
import { sanitizeRitualChatRequest } from "@/lib/ritual-guidance-safety"

function localPreviewStream(message: string, originalMessages: RitualCompanionUIMessage[] = []) {
  const textId = "local-preview-text"
  const stream = createUIMessageStream<RitualCompanionUIMessage>({
    originalMessages,
    execute: ({ writer }) => {
      writer.write({ type: "start" })
      writer.write({
        type: "data-ritual-companion-status",
        id: "local-preview-status",
        data: {
          mode: "local_stub",
          durableWritesEnabled: false,
          message: "Local preview"
        },
        transient: true
      })
      writer.write({ type: "text-start", id: textId })
      writer.write({ type: "text-delta", id: textId, delta: message })
      writer.write({ type: "text-end", id: textId })
      writer.write({ type: "finish", finishReason: "stop" })
    }
  })
  return createUIMessageStreamResponse({ stream })
}

export async function POST(request: Request) {
  const body = await request.json().catch(() => null)
  const chatRequest = sanitizeRitualChatRequest(body)

  if (!chatRequest) {
    return localPreviewStream(
      "Companion unavailable in local preview. I can show the ritual frame, but no durable writes will be made."
    )
  }

  if (!process.env.HERMES_RITUAL_CHAT_URL) {
    return localPreviewStream(
      "Companion unavailable in local preview. I can show the ritual frame, but no durable writes will be made.",
      chatRequest.messages
    )
  }

  try {
    const forwarded = await forwardRitualChatStream(chatRequest, request.signal)
    if (forwarded?.ok && forwarded.body) {
      return new Response(forwarded.body, {
        status: forwarded.status,
        headers: safeStreamingHeaders(forwarded.headers)
      })
    }
  } catch {
    // Fall through to the bounded local stream below.
  }

  return localPreviewStream(
    "Companion stream is unavailable in local preview. No durable writes will be made.",
    chatRequest.messages
  )
}
