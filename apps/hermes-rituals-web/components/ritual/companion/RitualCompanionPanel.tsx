"use client"

/* eslint-disable react-hooks/set-state-in-effect */

import { useCallback, useEffect, useMemo, useState } from "react"
import { DefaultChatTransport } from "ai"
import { useChat } from "@ai-sdk/react"
import { Maximize2, Minimize2, Pause, RotateCcw, Send, Square, Volume2 } from "lucide-react"
import { motion } from "motion/react"

import { Conversation, ConversationEmpty } from "@/components/ai-elements/conversation"
import { Message, MessageLabel, MessageText } from "@/components/ai-elements/message"
import { PromptInput, PromptInputActions } from "@/components/ai-elements/prompt-input"
import { RitualCompanionActionCard } from "@/components/ritual/companion/RitualCompanionActionCard"
import { useVoiceTranscription } from "@/components/ritual/body/useVoiceTranscription"
import { MICRO_SPRING } from "@/components/ritual/motion"
import { LiveWaveform } from "@/components/ui/live-waveform"
import { VoiceButton } from "@/components/ui/voice-button"
import type {
  RitualChatRequest,
  RitualCompanionAction,
  RitualCompanionUIMessage
} from "@/lib/ritual-guidance-contract"
import { sanitizeRitualCompanionAction } from "@/lib/ritual-guidance-safety"

type ChatStatus = "submitted" | "streaming" | "ready" | "error"

type RitualCompanionPanelProps = {
  variant?: "rail" | "live"
  guidanceSessionId: string | null
  guidanceStatus?: "idle" | "creating" | "ready" | "error"
  guidanceError?: string | null
  playbackCompleted?: boolean
  liveHref?: string | null
  onContinueLive?: () => void
  getChatContext: () => Omit<RitualChatRequest, "messages">
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value && typeof value === "object" && !Array.isArray(value))
}

function actionFromPart(part: unknown): RitualCompanionAction | null {
  if (!isRecord(part) || typeof part.type !== "string") return null
  if (part.type === "data-ritual-companion-action") {
    return sanitizeRitualCompanionAction(part.data)
  }
  if (part.type === "dynamic-tool" || part.type.startsWith("tool-")) {
    return (
      sanitizeRitualCompanionAction(part.input) ??
      sanitizeRitualCompanionAction(part.output) ??
      (isRecord(part.input) ? sanitizeRitualCompanionAction(part.input.action) : null) ??
      (isRecord(part.output) ? sanitizeRitualCompanionAction(part.output.action) : null)
    )
  }
  return null
}

function assistantText(messages: RitualCompanionUIMessage[]) {
  const lastAssistant = [...messages].reverse().find((message) => message.role === "assistant")
  if (!lastAssistant) return ""
  return lastAssistant.parts
    .flatMap((part) => (part.type === "text" ? [part.text] : []))
    .join(" ")
    .trim()
}

function statusCopy(status: ChatStatus, guidanceStatus?: RitualCompanionPanelProps["guidanceStatus"]) {
  if (status === "submitted") return "Sending"
  if (status === "streaming") return "Receiving"
  if (guidanceStatus === "creating") return "Opening session"
  if (guidanceStatus === "error") return "Local preview"
  return "Ready"
}

export function RitualCompanionPanel({
  variant = "rail",
  guidanceSessionId,
  guidanceStatus,
  guidanceError,
  playbackCompleted,
  liveHref,
  onContinueLive,
  getChatContext
}: RitualCompanionPanelProps) {
  const [input, setInput] = useState("")
  const [actions, setActions] = useState<Record<string, RitualCompanionAction>>({})
  const [paused, setPaused] = useState(false)
  const [minimized, setMinimized] = useState(false)
  const [canSpeak] = useState(
    () => typeof window !== "undefined" && "speechSynthesis" in window
  )
  const actionStates = useMemo(() => Object.values(actions), [actions])

  const transport = useMemo(
    () =>
      new DefaultChatTransport<RitualCompanionUIMessage>({
        api: "/api/ritual-chat",
        prepareSendMessagesRequest: ({ id, messages, trigger, messageId }) => {
          const context = getChatContext()
          return {
            body: {
              ...context,
              clientMetadata: {
                ...context.clientMetadata,
                variant
              },
              messages: messages.slice(-20),
              actionStates,
              trigger,
              messageId,
              id
            }
          }
        }
      }),
    [actionStates, getChatContext, variant]
  )

  const { messages, status, sendMessage, stop, regenerate, error } =
    useChat<RitualCompanionUIMessage>({
      id: guidanceSessionId ?? undefined,
      transport
    })

  useEffect(() => {
    const nextActions = messages
      .flatMap((message) => message.parts.flatMap(actionFromPart))
      .filter((action): action is RitualCompanionAction => Boolean(action))
    if (nextActions.length === 0) return

    setActions((previous) => {
      let changed = false
      const next = { ...previous }
      nextActions.forEach((action) => {
        if (!next[action.actionId]) {
          next[action.actionId] = action
          changed = true
        }
      })
      return changed ? next : previous
    })
  }, [messages])

  const voice = useVoiceTranscription({
    onText: (text) => {
      setInput((current) => [current, text].filter(Boolean).join(current ? " " : ""))
    }
  })

  const busy = status === "submitted" || status === "streaming"
  const normalizedStatus = status as ChatStatus

  const handleSubmit = useCallback(() => {
    const text = input.trim()
    if (!text || busy || paused) return
    setInput("")
    void sendMessage({ text })
  }, [busy, input, paused, sendMessage])

  const updateAction = useCallback((action: RitualCompanionAction) => {
    setActions((previous) => ({ ...previous, [action.actionId]: action }))
  }, [])

  const decideAction = useCallback(
    async (action: RitualCompanionAction, decision: "approve" | "reject") => {
      const decidedAction: RitualCompanionAction = {
        ...action,
        approvalState: decision === "approve" ? "executing" : "rejected",
        decidedAt: new Date().toISOString(),
        rejectionFinal: decision === "reject" ? true : action.rejectionFinal
      }
      updateAction(decidedAction)

      try {
        const response = await fetch(
          `/api/guidance-sessions/${encodeURIComponent(action.guidanceSessionId)}/actions`,
          {
            method: "POST",
            headers: { "content-type": "application/json" },
            body: JSON.stringify({ action, decision })
          }
        )
        const payload = (await response.json().catch(() => ({}))) as Record<string, unknown>
        if (!response.ok) throw new Error("action_decision_failed")

        const returnedAction = sanitizeRitualCompanionAction(payload.action)
        if (returnedAction) {
          updateAction(
            payload.executed === true
              ? { ...returnedAction, approvalState: "executed" }
              : returnedAction
          )
          return
        }

        if (decision === "reject") {
          updateAction({ ...decidedAction, approvalState: "rejected", rejectionFinal: true })
          return
        }

        updateAction(
          payload.executed === true
            ? { ...decidedAction, approvalState: "executed" }
            : {
                ...decidedAction,
                approvalState: "approved",
                error: "Local preview: no durable write executed"
              }
        )
      } catch {
        updateAction({ ...decidedAction, approvalState: "failed", error: "Approval failed" })
      }
    },
    [updateAction]
  )

  const readLastResponse = useCallback(() => {
    if (!canSpeak || typeof window === "undefined") return
    const text = assistantText(messages)
    if (!text) return
    window.speechSynthesis.cancel()
    window.speechSynthesis.speak(new SpeechSynthesisUtterance(text))
  }, [canSpeak, messages])

  const messageCount = messages.length
  const hasActions = Object.keys(actions).length > 0
  const lastResponseText = assistantText(messages)

  return (
    <div className="flex h-full min-h-0 flex-col gap-3">
      <div className="flex shrink-0 items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-[10px] font-medium uppercase tracking-[0.14em] text-silver-500">
            Companion
          </div>
          <div className="mt-1 text-sm font-medium text-silver-100">
            {paused ? "Paused" : statusCopy(normalizedStatus, guidanceStatus)}
          </div>
          {guidanceError ? (
            <div className="mt-1 text-xs text-silver-500">{guidanceError.replaceAll("_", " ")}</div>
          ) : null}
        </div>
        <div className="flex shrink-0 flex-wrap items-center gap-2">
          <motion.button
            type="button"
            aria-pressed={paused}
            onClick={() => setPaused((next) => !next)}
            className="inline-flex h-9 items-center gap-2 rounded-full border border-white/10 bg-white/[0.06] px-3 text-xs font-medium text-silver-200"
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.97 }}
            transition={MICRO_SPRING}
          >
            <Pause className="size-4" />
            <span>{paused ? "Resume" : "Pause"}</span>
          </motion.button>
          <motion.button
            type="button"
            aria-pressed={minimized}
            onClick={() => setMinimized((next) => !next)}
            className="inline-flex h-9 items-center gap-2 rounded-full border border-white/10 bg-white/[0.06] px-3 text-xs font-medium text-silver-200"
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.97 }}
            transition={MICRO_SPRING}
          >
            <Minimize2 className="size-4" />
            <span>{minimized ? "Open" : "Minimize"}</span>
          </motion.button>
          {variant === "rail" && playbackCompleted && liveHref ? (
            <motion.button
              type="button"
              onClick={onContinueLive}
              className="inline-flex h-9 shrink-0 items-center gap-2 rounded-full bg-white px-3 text-xs font-semibold text-graphite-950"
              whileHover={{ scale: 1.03 }}
              whileTap={{ scale: 0.97 }}
              transition={MICRO_SPRING}
            >
              <Maximize2 className="size-4" />
              <span>Continue live</span>
            </motion.button>
          ) : null}
        </div>
      </div>

      {minimized ? (
        <div className="rounded-2xl border border-white/10 bg-black/25 px-3 py-3 text-sm leading-6 text-silver-400">
          Companion minimized.
        </div>
      ) : (
        <>
      <Conversation className={variant === "live" ? "min-h-[45dvh]" : "min-h-[220px]"}>
        {messageCount === 0 && !hasActions ? (
          <ConversationEmpty>
            Ask a follow-up about this ritual frame. Durable writes require approval.
          </ConversationEmpty>
        ) : null}
        {messages.map((message) => (
          <Message key={message.id} role={message.role}>
            <MessageLabel>{message.role === "user" ? "You" : "Hermes"}</MessageLabel>
            {message.parts.map((part, index) => {
              if (part.type === "text") {
                return (
                  <MessageText key={`${message.id}:text:${index}`}>{part.text}</MessageText>
                )
              }
              const action = actionFromPart(part)
              if (action) {
                const currentAction = actions[action.actionId] ?? action
                return (
                  <div key={`${message.id}:action:${action.actionId}`} className="mt-3">
                    <RitualCompanionActionCard
                      action={currentAction}
                      onApprove={(nextAction) => void decideAction(nextAction, "approve")}
                      onReject={(nextAction) => void decideAction(nextAction, "reject")}
                    />
                  </div>
                )
              }
              return null
            })}
          </Message>
        ))}
        {Object.values(actions)
          .filter(
            (action) =>
              !messages.some((message) =>
                message.parts.some((part) => actionFromPart(part)?.actionId === action.actionId)
              )
          )
          .map((action) => (
            <RitualCompanionActionCard
              key={action.actionId}
              action={action}
              onApprove={(nextAction) => void decideAction(nextAction, "approve")}
              onReject={(nextAction) => void decideAction(nextAction, "reject")}
            />
          ))}
      </Conversation>

      {voice.state === "recording" || voice.state === "processing" ? (
        <div className="h-10 text-silver-300">
          <LiveWaveform
            active={voice.state === "recording"}
            processing={voice.state === "processing"}
            height={40}
            mode="static"
            className="text-silver-300"
          />
        </div>
      ) : null}

      {error ? (
        <div className="rounded-2xl border border-white/10 bg-black/25 px-3 py-2 text-xs text-silver-400">
          Companion response failed.
        </div>
      ) : null}

      <PromptInput
        value={input}
        disabled={busy || paused}
        placeholder="Ask without storing anything yet"
        onChange={setInput}
        onSubmit={handleSubmit}
      >
        <PromptInputActions>
          <VoiceButton label="Voice" state={voice.state} onPress={voice.toggle} />
          {canSpeak && lastResponseText ? (
            <motion.button
              type="button"
              onClick={readLastResponse}
              className="inline-flex h-11 items-center gap-2 rounded-full border border-white/10 bg-white/10 px-4 text-sm font-medium text-silver-100"
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              transition={MICRO_SPRING}
            >
              <Volume2 className="size-4" />
              <span>Read</span>
            </motion.button>
          ) : null}
        </PromptInputActions>
        <PromptInputActions>
          {status === "streaming" ? (
            <motion.button
              type="button"
              onClick={stop}
              className="inline-flex h-11 items-center gap-2 rounded-full border border-white/10 bg-white/[0.06] px-4 text-sm font-semibold text-silver-100"
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              transition={MICRO_SPRING}
            >
              <Square className="size-4 fill-current" />
              <span>Stop</span>
            </motion.button>
          ) : error ? (
            <motion.button
              type="button"
              onClick={() => void regenerate()}
              className="inline-flex h-11 items-center gap-2 rounded-full border border-white/10 bg-white/[0.06] px-4 text-sm font-semibold text-silver-100"
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              transition={MICRO_SPRING}
            >
              <RotateCcw className="size-4" />
              <span>Retry</span>
            </motion.button>
          ) : (
            <motion.button
              type="submit"
              disabled={busy || input.trim().length === 0}
              className="inline-flex h-11 items-center gap-2 rounded-full bg-white px-4 text-sm font-semibold text-graphite-950 disabled:pointer-events-none disabled:opacity-40"
              whileHover={busy ? undefined : { scale: 1.02 }}
              whileTap={busy ? undefined : { scale: 0.98 }}
              transition={MICRO_SPRING}
            >
              <Send className="size-4" />
              <span>Send</span>
            </motion.button>
          )}
        </PromptInputActions>
      </PromptInput>
        </>
      )}
    </div>
  )
}
