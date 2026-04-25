"use client"

import { AlertCircle, Check, LoaderCircle, Mic, Square } from "lucide-react"
import { motion } from "motion/react"

import { cn } from "@/lib/utils"

export type VoiceButtonState = "idle" | "recording" | "processing" | "success" | "error"

const MICRO_SPRING = { type: "spring" as const, stiffness: 450, damping: 28, mass: 0.5 }

const STATE_LABELS: Record<VoiceButtonState, string> = {
  idle: "Voice",
  recording: "Listening",
  processing: "Processing",
  success: "Added",
  error: "Retry"
}

export function VoiceButton({
  label = "Voice",
  trailing,
  state,
  onPress,
  className,
  disabled
}: {
  label?: string
  trailing?: string
  state: VoiceButtonState
  onPress: () => void
  className?: string
  disabled?: boolean
}) {
  const displayLabel = state === "idle" ? label : STATE_LABELS[state]
  const isActive = state === "recording" || state === "processing"

  return (
    <motion.button
      type="button"
      disabled={disabled || state === "processing"}
      onClick={onPress}
      className={cn(
        "inline-flex h-11 items-center justify-between gap-3 rounded-full border px-4 text-sm font-medium backdrop-blur-2xl disabled:pointer-events-none disabled:opacity-40",
        isActive
          ? "border-white/20 bg-white/15 text-silver-50"
          : state === "error"
            ? "border-white/15 bg-black/35 text-silver-100"
            : "border-white/10 bg-white/10 text-silver-100",
        className
      )}
      whileHover={disabled || state === "processing" ? undefined : { scale: 1.02 }}
      whileTap={disabled || state === "processing" ? undefined : { scale: 0.98 }}
      transition={MICRO_SPRING}
    >
      <span className="flex items-center gap-2">
        <motion.span
          className="flex size-7 items-center justify-center rounded-full bg-white/10"
          animate={{ scale: state === "recording" ? 1.08 : 1 }}
          transition={MICRO_SPRING}
        >
          {state === "recording" ? (
            <Square className="size-3.5 fill-current" />
          ) : state === "processing" ? (
            <LoaderCircle className="size-4 animate-spin" />
          ) : state === "success" ? (
            <Check className="size-4" />
          ) : state === "error" ? (
            <AlertCircle className="size-4" />
          ) : (
            <Mic className="size-4" />
          )}
        </motion.span>
        <span>{displayLabel}</span>
      </span>
      {trailing ? <span className="text-[11px] text-silver-500">{trailing}</span> : null}
    </motion.button>
  )
}
