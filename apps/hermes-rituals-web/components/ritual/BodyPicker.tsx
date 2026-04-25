"use client"

import { useEffect, useMemo, useRef, useState, type ReactNode } from "react"
import { Check, PencilLine } from "lucide-react"
import { AnimatePresence, motion } from "motion/react"

import { VoiceButton, type VoiceButtonState } from "@/components/ui/voice-button"
import { cn } from "@/lib/utils"

export type BodyRegionId =
  | "head_face"
  | "jaw_throat"
  | "neck"
  | "shoulders"
  | "chest"
  | "upper_back"
  | "belly"
  | "pelvis"
  | "lower_back"
  | "left_arm"
  | "right_arm"
  | "left_hand"
  | "right_hand"
  | "left_leg"
  | "right_leg"
  | "left_foot"
  | "right_foot"
  | "whole_body"
  | "unclear"

export type BodyActivation = "low" | "moderate" | "high" | "overwhelming"
export type BodyCompletionStatus = "idle" | "submitting" | "saved" | "error"

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

const SPRING = { type: "spring" as const, stiffness: 300, damping: 30, mass: 0.8 }
const MICRO_SPRING = { type: "spring" as const, stiffness: 450, damping: 28, mass: 0.5 }
const FADE = { duration: 0.15, delay: 0.04 }

const REGION_LABELS: Record<BodyRegionId, string> = {
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

const SENSATIONS = [
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
]

const TONES = ["steady", "charged", "soft", "distant", "clear", "raw"]

const ACTIVATIONS: Array<{ id: BodyActivation; label: string }> = [
  { id: "low", label: "Low" },
  { id: "moderate", label: "Moderate" },
  { id: "high", label: "High" },
  { id: "overwhelming", label: "Overwhelming" }
]

type MapRegion = {
  id: BodyRegionId
  view: "front" | "back"
  x: number
  y: number
  w: number
  h: number
  radius?: number
}

const MAP_REGIONS: MapRegion[] = [
  { id: "head_face", view: "front", x: 44, y: 4, w: 12, h: 12, radius: 999 },
  { id: "jaw_throat", view: "front", x: 42, y: 16, w: 16, h: 9, radius: 14 },
  { id: "neck", view: "front", x: 45, y: 24, w: 10, h: 7, radius: 10 },
  { id: "shoulders", view: "front", x: 25, y: 29, w: 50, h: 9, radius: 16 },
  { id: "chest", view: "front", x: 33, y: 37, w: 34, h: 13, radius: 18 },
  { id: "belly", view: "front", x: 36, y: 50, w: 28, h: 14, radius: 18 },
  { id: "pelvis", view: "front", x: 36, y: 64, w: 28, h: 12, radius: 18 },
  { id: "left_arm", view: "front", x: 18, y: 38, w: 12, h: 28, radius: 18 },
  { id: "right_arm", view: "front", x: 70, y: 38, w: 12, h: 28, radius: 18 },
  { id: "left_hand", view: "front", x: 12, y: 64, w: 11, h: 11, radius: 999 },
  { id: "right_hand", view: "front", x: 77, y: 64, w: 11, h: 11, radius: 999 },
  { id: "left_leg", view: "front", x: 36, y: 76, w: 11, h: 17, radius: 18 },
  { id: "right_leg", view: "front", x: 53, y: 76, w: 11, h: 17, radius: 18 },
  { id: "left_foot", view: "front", x: 31, y: 92, w: 15, h: 6, radius: 999 },
  { id: "right_foot", view: "front", x: 54, y: 92, w: 15, h: 6, radius: 999 },
  { id: "head_face", view: "back", x: 44, y: 4, w: 12, h: 12, radius: 999 },
  { id: "neck", view: "back", x: 45, y: 17, w: 10, h: 8, radius: 10 },
  { id: "shoulders", view: "back", x: 25, y: 28, w: 50, h: 10, radius: 16 },
  { id: "upper_back", view: "back", x: 33, y: 38, w: 34, h: 17, radius: 18 },
  { id: "lower_back", view: "back", x: 36, y: 55, w: 28, h: 12, radius: 18 },
  { id: "pelvis", view: "back", x: 36, y: 67, w: 28, h: 10, radius: 18 },
  { id: "left_arm", view: "back", x: 18, y: 38, w: 12, h: 28, radius: 18 },
  { id: "right_arm", view: "back", x: 70, y: 38, w: 12, h: 28, radius: 18 },
  { id: "left_hand", view: "back", x: 12, y: 64, w: 11, h: 11, radius: 999 },
  { id: "right_hand", view: "back", x: 77, y: 64, w: 11, h: 11, radius: 999 },
  { id: "left_leg", view: "back", x: 36, y: 76, w: 11, h: 17, radius: 18 },
  { id: "right_leg", view: "back", x: 53, y: 76, w: 11, h: 17, radius: 18 },
  { id: "left_foot", view: "back", x: 31, y: 92, w: 15, h: 6, radius: 999 },
  { id: "right_foot", view: "back", x: 54, y: 92, w: 15, h: 6, radius: 999 }
]

function cleanDraft(value: BodyStateDraft) {
  return {
    ...value,
    sensation: value.sensation.trim(),
    tone: value.tone?.trim() || undefined,
    noteText: value.noteText?.trim() || undefined
  }
}

function appendText(current: string | undefined, next: string) {
  const existing = current?.trim()
  return existing ? `${existing} ${next}` : next
}

function BodySilhouette({ view }: { view: "front" | "back" }) {
  return (
    <svg viewBox="0 0 100 140" className="absolute inset-0 h-full w-full" aria-hidden="true">
      <defs>
        <radialGradient id={`body-glow-${view}`} cx="50%" cy="36%" r="60%">
          <stop offset="0%" stopColor="rgba(255,255,255,0.18)" />
          <stop offset="100%" stopColor="rgba(255,255,255,0.02)" />
        </radialGradient>
      </defs>
      <path
        d="M50 8 C42 8 37 14 38 22 C39 29 43 32 45 36 L55 36 C57 32 61 29 62 22 C63 14 58 8 50 8 Z"
        fill={`url(#body-glow-${view})`}
        stroke="rgba(255,255,255,0.25)"
        strokeWidth="1"
      />
      <path
        d="M34 39 C28 41 24 49 22 61 L16 91 C15 97 20 100 24 96 L31 67 L36 97 L32 129 C31 135 39 137 42 131 L49 101 L51 101 L58 131 C61 137 69 135 68 129 L64 97 L69 67 L76 96 C80 100 85 97 84 91 L78 61 C76 49 72 41 66 39 C61 37 57 36 55 36 L45 36 C43 36 39 37 34 39 Z"
        fill="rgba(255,255,255,0.055)"
        stroke="rgba(255,255,255,0.18)"
        strokeWidth="1"
      />
      {view === "back" ? (
        <path
          d="M50 41 L50 78 M39 46 C44 43 56 43 61 46 M38 72 C45 76 55 76 62 72"
          fill="none"
          stroke="rgba(255,255,255,0.16)"
          strokeWidth="1"
          strokeLinecap="round"
        />
      ) : (
        <path
          d="M39 46 C44 50 56 50 61 46 M40 62 C46 65 54 65 60 62 M50 71 L50 74"
          fill="none"
          stroke="rgba(255,255,255,0.14)"
          strokeWidth="1"
          strokeLinecap="round"
        />
      )}
    </svg>
  )
}

function BodyMap({
  selected,
  onSelect,
  compact
}: {
  selected?: BodyRegionId
  onSelect: (region: BodyRegionId) => void
  compact?: boolean
}) {
  return (
    <div className="grid grid-cols-2 gap-3">
      {(["front", "back"] as const).map((view) => (
        <motion.div
          key={view}
          className={cn(
            "relative overflow-hidden rounded-3xl border border-white/10 bg-black/25 backdrop-blur-xl",
            compact ? "aspect-[0.62] min-h-64" : "aspect-[0.62] min-h-72"
          )}
          layout
          transition={SPRING}
        >
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(255,255,255,0.08),transparent_48%)]" />
          <BodySilhouette view={view} />
          {MAP_REGIONS.filter((region) => region.view === view).map((region) => {
            const active = selected === region.id
            return (
              <motion.button
                key={`${view}-${region.id}`}
                type="button"
                aria-label={REGION_LABELS[region.id]}
                className={cn(
                  "absolute border backdrop-blur-md",
                  active
                    ? "border-white/45 bg-white/25"
                    : "border-white/0 bg-white/[0.015] hover:bg-white/10"
                )}
                style={{
                  left: `${region.x}%`,
                  top: `${region.y}%`,
                  width: `${region.w}%`,
                  height: `${region.h}%`,
                  borderRadius: region.radius ?? 18
                }}
                animate={{
                  boxShadow: active
                    ? "0 0 28px rgba(255,255,255,0.28)"
                    : "0 0 0 rgba(255,255,255,0)"
                }}
                whileHover={{ scale: 1.03 }}
                whileTap={{ scale: 0.97 }}
                transition={MICRO_SPRING}
                onClick={() => onSelect(region.id)}
              />
            )
          })}
          <div className="pointer-events-none absolute inset-x-0 bottom-3 flex justify-center">
            <span className="rounded-full bg-black/35 px-3 py-1 text-[10px] font-medium uppercase tracking-[0.16em] text-silver-500 backdrop-blur-xl">
              {view}
            </span>
          </div>
        </motion.div>
      ))}
    </div>
  )
}

function Chip({
  active,
  children,
  onClick,
  disabled
}: {
  active: boolean
  children: ReactNode
  onClick: () => void
  disabled?: boolean
}) {
  return (
    <motion.button
      type="button"
      disabled={disabled}
      className={cn(
        "rounded-full border px-3 py-2 text-xs font-medium backdrop-blur-xl disabled:pointer-events-none disabled:opacity-40",
        active
          ? "border-white/30 bg-white/15 text-silver-50"
          : "border-white/8 bg-white/[0.04] text-silver-400"
      )}
      whileHover={disabled ? undefined : { scale: 1.02 }}
      whileTap={disabled ? undefined : { scale: 0.98 }}
      transition={MICRO_SPRING}
      onClick={onClick}
    >
      {children}
    </motion.button>
  )
}

export function BodyPicker({
  value,
  onChange,
  variant = "rail",
  completionPrompt,
  completionStatus = "idle",
  submitError,
  endpointAvailable = true,
  disabled,
  onSubmit
}: {
  value: BodyStateDraft
  onChange: (value: BodyStateDraft) => void
  variant?: "stage" | "rail"
  completionPrompt?: string
  completionStatus?: BodyCompletionStatus
  submitError?: string | null
  endpointAvailable?: boolean
  disabled?: boolean
  onSubmit?: () => void
}) {
  const [customSensation, setCustomSensation] = useState("")
  const [voiceState, setVoiceState] = useState<VoiceButtonState>("idle")
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const compact = variant === "stage"
  const cleaned = useMemo(() => cleanDraft(value), [value])
  const selectedRegion = value.bodyRegion
  const canSubmit = Boolean(cleaned.sensation) && endpointAvailable && !disabled

  const update = (patch: Partial<BodyStateDraft>) => {
    onChange({ ...value, ...patch })
  }

  const chooseSensation = (sensation: string) => {
    update({ sensation })
    setCustomSensation("")
  }

  const startRecording = async () => {
    if (typeof MediaRecorder === "undefined") {
      setVoiceState("error")
      return
    }
    try {
      chunksRef.current = []
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream
      const mimeType = MediaRecorder.isTypeSupported("audio/webm") ? "audio/webm" : undefined
      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined)
      mediaRecorderRef.current = recorder
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data)
      }
      recorder.onstop = () => {
        void transcribeRecording(mimeType ?? "audio/webm")
      }
      recorder.start()
      setVoiceState("recording")
    } catch {
      setVoiceState("error")
      streamRef.current?.getTracks().forEach((track) => track.stop())
      streamRef.current = null
    }
  }

  const stopRecording = () => {
    const recorder = mediaRecorderRef.current
    if (recorder && recorder.state !== "inactive") {
      recorder.stop()
    }
  }

  const transcribeRecording = async (mimeType: string) => {
    setVoiceState("processing")
    streamRef.current?.getTracks().forEach((track) => track.stop())
    streamRef.current = null
    const blob = new Blob(chunksRef.current, { type: mimeType })
    chunksRef.current = []
    if (blob.size <= 0) {
      setVoiceState("error")
      return
    }

    try {
      const formData = new FormData()
      formData.append("audio", blob, "body-note.webm")
      const response = await fetch("/api/voice/transcribe", {
        method: "POST",
        body: formData
      })
      const payload = (await response.json().catch(() => ({}))) as Record<string, unknown>
      if (!response.ok || typeof payload.text !== "string") {
        throw new Error("transcription_failed")
      }
      update({ noteText: appendText(value.noteText, payload.text.trim()) })
      setVoiceState("success")
      window.setTimeout(() => setVoiceState("idle"), 1400)
    } catch {
      setVoiceState("error")
    }
  }

  const handleVoicePress = () => {
    if (voiceState === "recording") {
      stopRecording()
      return
    }
    if (voiceState === "processing") return
    void startRecording()
  }

  useEffect(() => {
    return () => {
      const recorder = mediaRecorderRef.current
      if (recorder && recorder.state !== "inactive") recorder.stop()
      streamRef.current?.getTracks().forEach((track) => track.stop())
    }
  }, [])

  return (
    <motion.div
      className={cn("flex h-full min-h-0 flex-col", compact ? "p-4" : "gap-5")}
      layout
      transition={SPRING}
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-[10px] font-medium uppercase tracking-[0.16em] text-silver-500">
            Body
          </p>
          <h3 className={cn("mt-1 font-medium text-silver-100", compact ? "text-sm" : "text-lg")}>
            {completionPrompt ?? "What did you notice in your body or attention?"}
          </h3>
        </div>
        <AnimatePresence>
          {completionStatus === "saved" ? (
            <motion.div
              className="flex size-8 items-center justify-center rounded-full bg-white/15 text-silver-50"
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              transition={MICRO_SPRING}
            >
              <Check className="size-4" />
            </motion.div>
          ) : null}
        </AnimatePresence>
      </div>

      <BodyMap
        selected={selectedRegion}
        onSelect={(bodyRegion) => update({ bodyRegion })}
        compact={compact}
      />

      <div className="mt-3 flex flex-wrap gap-2">
        <Chip
          active={value.bodyRegion === "whole_body"}
          onClick={() => update({ bodyRegion: "whole_body" })}
          disabled={disabled}
        >
          Whole body
        </Chip>
        <Chip
          active={value.bodyRegion === "unclear"}
          onClick={() => update({ bodyRegion: "unclear" })}
          disabled={disabled}
        >
          Unclear
        </Chip>
      </div>

      <motion.div
        className={cn(
          "mt-3 rounded-2xl border border-white/8 bg-black/25 p-3 backdrop-blur-xl",
          compact ? "space-y-3" : "space-y-4"
        )}
        layout
        transition={SPRING}
      >
        <div className="flex items-center justify-between gap-3">
          <span className="text-[10px] font-medium uppercase tracking-[0.16em] text-silver-500">
            Area
          </span>
          <span className="truncate text-sm font-medium text-silver-100">
            {selectedRegion ? REGION_LABELS[selectedRegion] : "Not marked"}
          </span>
        </div>

        <div className="flex flex-wrap gap-2">
          {(compact ? SENSATIONS.slice(0, 8) : SENSATIONS).map((sensation) => (
            <Chip
              key={sensation}
              active={cleaned.sensation === sensation}
              onClick={() => chooseSensation(sensation)}
              disabled={disabled}
            >
              {sensation}
            </Chip>
          ))}
        </div>

        {!compact && (
          <div className="flex items-center gap-2 rounded-full border border-white/8 bg-white/[0.04] px-3 py-2">
            <PencilLine className="size-4 text-silver-500" />
            <input
              value={customSensation}
              disabled={disabled}
              onChange={(event) => setCustomSensation(event.target.value)}
              onBlur={() => {
                const next = customSensation.trim()
                if (next) chooseSensation(next)
              }}
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  event.preventDefault()
                  const next = customSensation.trim()
                  if (next) chooseSensation(next)
                }
              }}
              placeholder="Custom sensation"
              className="min-w-0 flex-1 bg-transparent text-sm text-silver-100 outline-none placeholder:text-silver-600"
            />
          </div>
        )}

        <div className="grid grid-cols-2 gap-2">
          {ACTIVATIONS.map((activation) => (
            <Chip
              key={activation.id}
              active={value.activation === activation.id}
              onClick={() => update({ activation: activation.id })}
              disabled={disabled}
            >
              {activation.label}
            </Chip>
          ))}
        </div>

        {!compact && (
          <>
            <div className="flex flex-wrap gap-2">
              {TONES.map((tone) => (
                <Chip
                  key={tone}
                  active={value.tone === tone}
                  onClick={() => update({ tone })}
                  disabled={disabled}
                >
                  {tone}
                </Chip>
              ))}
            </div>

            <textarea
              value={value.noteText ?? ""}
              disabled={disabled}
              onChange={(event) => update({ noteText: event.target.value })}
              placeholder="Add the exact words, if there are any."
              className="min-h-28 w-full resize-none rounded-2xl border border-white/8 bg-white/[0.04] px-4 py-3 text-sm leading-6 text-silver-100 outline-none placeholder:text-silver-600 focus:border-white/20"
            />

            <div className="flex flex-wrap items-center justify-between gap-3">
              <VoiceButton
                state={voiceState}
                onPress={handleVoicePress}
                label="Voice"
                trailing="optional"
                className="min-w-40"
                disabled={disabled}
              />
              {onSubmit ? (
                <motion.button
                  type="button"
                  disabled={!canSubmit || completionStatus === "submitting" || completionStatus === "saved"}
                  onClick={onSubmit}
                  className="h-11 rounded-full border border-white/15 bg-white/10 px-5 text-sm font-medium text-silver-50 backdrop-blur-xl disabled:pointer-events-none disabled:opacity-40"
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  transition={MICRO_SPRING}
                >
                  {completionStatus === "submitting"
                    ? "Saving"
                    : completionStatus === "saved"
                      ? "Held"
                      : "Hold body note"}
                </motion.button>
              ) : null}
            </div>

            <AnimatePresence>
              {completionStatus === "error" || !endpointAvailable ? (
                <motion.p
                  className="text-xs leading-5 text-silver-500"
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -4 }}
                  transition={FADE}
                >
                  {submitError ?? "Completion sync is not available for this artifact."}
                </motion.p>
              ) : null}
            </AnimatePresence>
          </>
        )}
      </motion.div>
    </motion.div>
  )
}
