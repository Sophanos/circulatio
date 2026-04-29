"use client"

/* eslint-disable react-hooks/set-state-in-effect */

import { useCallback, useEffect, useMemo, useState } from "react"

import { LiveGuidanceShell } from "@/components/ritual/live/LiveGuidanceShell"
import type {
  RitualChatRequest,
  RitualGuidanceSession
} from "@/lib/ritual-guidance-contract"
import {
  emptyGuidanceFrame,
  normalizeGuidanceSession,
  sanitizeRitualChatRequest
} from "@/lib/ritual-guidance-safety"

type LiveStatus = "creating" | "ready" | "error"

type HandoffSnapshot = {
  session?: RitualGuidanceSession | null
  chatContext?: Omit<RitualChatRequest, "messages">
}

export function RitualGuidanceLiveClient({
  guidanceSessionId,
  artifactId
}: {
  guidanceSessionId: string
  artifactId?: string
}) {
  const fallbackContext = useMemo<Omit<RitualChatRequest, "messages">>(
    () => ({
      guidanceSessionId,
      hostSessionId: `live:${guidanceSessionId}`,
      artifactId: artifactId ?? "unknown-artifact",
      sourceRefs: [],
      currentFrame: emptyGuidanceFrame(),
      clientMetadata: {
        surface: "hermes-rituals-web",
        version: "ritual_companion_v1",
        variant: "live"
      }
    }),
    [artifactId, guidanceSessionId]
  )
  const [chatContext, setChatContext] = useState<Omit<RitualChatRequest, "messages">>(fallbackContext)
  const [session, setSession] = useState<RitualGuidanceSession | null>(null)
  const [status, setStatus] = useState<LiveStatus>("creating")
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    const key = `hermes:ritual-guidance:${guidanceSessionId}`
    const raw = window.sessionStorage.getItem(key)

    if (raw) {
      try {
        const parsed = JSON.parse(raw) as HandoffSnapshot
        const request = sanitizeRitualChatRequest({
          ...parsed.chatContext,
          messages: []
        })
        if (request) {
          setChatContext({
            ...request,
            clientMetadata: {
              surface: "hermes-rituals-web",
              version: "ritual_companion_v1",
              ...request.clientMetadata,
              variant: "live"
            }
          })
          setSession(parsed.session ?? null)
          setStatus("ready")
          return
        }
      } catch {
        // Fall back to a bounded session request.
      }
    }

    void (async () => {
      const createRequest = {
        guidanceSessionId,
        hostSessionId: fallbackContext.hostSessionId,
        artifactId: fallbackContext.artifactId,
        sourceRefs: [],
        currentFrame: fallbackContext.currentFrame,
        clientMetadata: fallbackContext.clientMetadata
      }
      try {
        const response = await fetch("/api/guidance-sessions", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify(createRequest)
        })
        const payload = await response.json().catch(() => ({}))
        if (!response.ok) throw new Error("guidance_session_resume_failed")
        if (cancelled) return
        const nextSession = normalizeGuidanceSession(payload, createRequest)
        setSession(nextSession)
        setChatContext({
          ...fallbackContext,
          guidanceSessionId: nextSession.guidanceSessionId,
          hostSessionId: nextSession.hostSessionId,
          artifactId: nextSession.artifactId,
          privacyClass: nextSession.privacyClass,
          sourceRefs: nextSession.sourceRefs,
          currentFrame: nextSession.currentFrame
        })
        setStatus("ready")
      } catch (caught) {
        if (cancelled) return
        setStatus("error")
        setError(caught instanceof Error ? caught.message : "guidance_session_resume_failed")
      }
    })()

    return () => {
      cancelled = true
    }
  }, [fallbackContext, guidanceSessionId])

  const getChatContext = useCallback(() => chatContext, [chatContext])

  return (
    <LiveGuidanceShell
      chatContext={chatContext}
      session={session}
      status={status}
      error={error}
      getChatContext={getChatContext}
    />
  )
}
