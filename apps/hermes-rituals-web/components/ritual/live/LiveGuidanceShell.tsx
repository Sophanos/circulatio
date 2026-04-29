"use client"

import { useCallback, useState } from "react"
import { Camera, CameraOff, Check, Pause, Square } from "lucide-react"
import { motion } from "motion/react"

import { RitualCompanionPanel } from "@/components/ritual/companion/RitualCompanionPanel"
import { MICRO_SPRING, PANEL_SPRING } from "@/components/ritual/motion"
import type {
  RitualChatRequest,
  RitualGuidanceSession
} from "@/lib/ritual-guidance-contract"
import { cn } from "@/lib/utils"

type LiveStatus = "creating" | "ready" | "error"
type LiveFocusMode = "breath" | "meditation" | "image" | "movement" | "companion_cue"
type LiveSensorState =
  | "live_no_camera"
  | "camera_preflight"
  | "camera_requested"
  | "camera_denied"
  | "sensor_unavailable"
  | "sensor_ready"
  | "guidance_paused"
  | "user_stopped"
  | "live_completed"

const FOCUS_MODES: Array<{ id: LiveFocusMode; label: string }> = [
  { id: "breath", label: "Breath" },
  { id: "meditation", label: "Meditation" },
  { id: "image", label: "Image" },
  { id: "movement", label: "Movement" },
  { id: "companion_cue", label: "Companion" }
]

function sensorCopy(state: LiveSensorState) {
  switch (state) {
    case "camera_preflight":
      return "Camera stays off until you enable it."
    case "camera_requested":
      return "Waiting for camera permission."
    case "camera_denied":
      return "Camera was not enabled. Continue without it."
    case "sensor_unavailable":
      return "Camera is unavailable here. Continue without it."
    case "sensor_ready":
      return "Camera permission is ready for a local mirror."
    case "guidance_paused":
      return "Guidance is paused."
    case "user_stopped":
      return "Live guidance was stopped."
    case "live_completed":
      return "Live guidance was completed."
    case "live_no_camera":
      return "No-camera guidance is active."
  }
}

export function LiveGuidanceShell({
  chatContext,
  session,
  status,
  error,
  getChatContext
}: {
  chatContext: Omit<RitualChatRequest, "messages">
  session: RitualGuidanceSession | null
  status: LiveStatus
  error: string | null
  getChatContext: () => Omit<RitualChatRequest, "messages">
}) {
  const [focusMode, setFocusMode] = useState<LiveFocusMode>("breath")
  const [sensorState, setSensorState] = useState<LiveSensorState>("live_no_camera")

  const requestCamera = useCallback(async () => {
    if (typeof navigator === "undefined" || !navigator.mediaDevices?.getUserMedia) {
      setSensorState("sensor_unavailable")
      return
    }

    setSensorState("camera_requested")
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false })
      stream.getTracks().forEach((track) => track.stop())
      setSensorState("sensor_ready")
    } catch {
      setSensorState("camera_denied")
    }
  }, [])

  const localPreview = session?.mode !== "hermes"
  const stopped = sensorState === "user_stopped" || sensorState === "live_completed"

  return (
    <main
      data-testid="live-guidance-shell"
      data-guidance-session-id={chatContext.guidanceSessionId}
      data-artifact-id={chatContext.artifactId}
      data-live-status={status}
      className="flex min-h-[100dvh] flex-col bg-graphite-950 text-silver-50"
    >
      <div className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-5 px-4 py-5 md:px-8 md:py-8">
        <header className="flex flex-wrap items-start justify-between gap-3 border-b border-white/10 pb-4">
          <div className="min-w-0">
            <div className="text-[10px] font-medium uppercase tracking-[0.14em] text-silver-500">
              Live guidance
            </div>
            <h1 className="mt-2 truncate text-xl font-semibold text-silver-100">
              {chatContext.artifactId}
            </h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-silver-500">
              Continue from the ritual with one focus at a time.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2 text-[11px] text-silver-400">
            <span className="rounded-full bg-white/[0.06] px-3 py-1.5">
              {chatContext.privacyClass ?? "session"}
            </span>
            <span className="rounded-full bg-white/[0.06] px-3 py-1.5">
              {localPreview ? "Local preview" : "Hermes"}
            </span>
          </div>
        </header>

        <motion.section
          className="grid gap-4 md:grid-cols-[minmax(0,1fr)_minmax(360px,420px)]"
          layout
          transition={PANEL_SPRING}
        >
          <motion.div
            className="flex min-h-[420px] flex-col gap-4 rounded-3xl border border-white/10 bg-black/30 p-4 backdrop-blur-2xl md:p-5"
            layout
            transition={PANEL_SPRING}
          >
            <div className="flex flex-wrap items-center gap-2">
              {FOCUS_MODES.map((mode) => {
                const active = focusMode === mode.id
                return (
                  <motion.button
                    key={mode.id}
                    type="button"
                    data-testid={`live-focus-${mode.id}`}
                    aria-pressed={active}
                    disabled={stopped}
                    onClick={() => setFocusMode(mode.id)}
                    className={cn(
                      "h-10 rounded-full border px-4 text-sm font-medium",
                      active
                        ? "border-white/20 bg-white/15 text-silver-50"
                        : "border-white/10 bg-white/[0.04] text-silver-300",
                      stopped ? "pointer-events-none opacity-40" : ""
                    )}
                    whileHover={stopped ? undefined : { scale: 1.02 }}
                    whileTap={stopped ? undefined : { scale: 0.98 }}
                    transition={MICRO_SPRING}
                  >
                    {mode.label}
                  </motion.button>
                )
              })}
            </div>

            <div className="flex flex-1 flex-col justify-between rounded-[1.45rem] border border-white/10 bg-black/25 p-4">
              <div>
                <div className="text-[10px] font-medium uppercase tracking-[0.14em] text-silver-500">
                  Current focus
                </div>
                <div
                  data-testid="live-current-focus"
                  className="mt-2 text-3xl font-medium capitalize text-silver-50"
                >
                  {focusMode.replace("_", " ")}
                </div>
                <p
                  data-testid="live-sensor-state"
                  data-sensor-state={sensorState}
                  className="mt-3 max-w-xl text-sm leading-6 text-silver-400"
                >
                  {sensorCopy(sensorState)}
                </p>
              </div>

              <div className="mt-8 grid gap-3 sm:grid-cols-2">
                <motion.button
                  type="button"
                  data-testid="live-camera-preflight"
                  disabled={stopped}
                  onClick={() => setSensorState("camera_preflight")}
                  className="inline-flex h-11 items-center justify-center gap-2 rounded-full border border-white/10 bg-white/[0.06] px-4 text-sm font-medium text-silver-100 disabled:pointer-events-none disabled:opacity-40"
                  whileHover={stopped ? undefined : { scale: 1.02 }}
                  whileTap={stopped ? undefined : { scale: 0.98 }}
                  transition={MICRO_SPRING}
                >
                  <Camera className="size-4" />
                  <span>Camera preflight</span>
                </motion.button>
                <motion.button
                  type="button"
                  data-testid="live-no-camera"
                  disabled={stopped}
                  onClick={() => setSensorState("live_no_camera")}
                  className="inline-flex h-11 items-center justify-center gap-2 rounded-full border border-white/10 bg-white/[0.06] px-4 text-sm font-medium text-silver-100 disabled:pointer-events-none disabled:opacity-40"
                  whileHover={stopped ? undefined : { scale: 1.02 }}
                  whileTap={stopped ? undefined : { scale: 0.98 }}
                  transition={MICRO_SPRING}
                >
                  <CameraOff className="size-4" />
                  <span>No camera</span>
                </motion.button>
              </div>

              {sensorState === "camera_preflight" ? (
                <div className="mt-4 rounded-2xl border border-white/10 bg-white/[0.04] p-3 text-sm leading-6 text-silver-400">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <span>Camera is optional and local-first.</span>
                    <motion.button
                      type="button"
                      data-testid="live-camera-enable"
                      onClick={requestCamera}
                      className="h-9 rounded-full bg-white px-4 text-xs font-semibold text-graphite-950"
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      transition={MICRO_SPRING}
                    >
                      Enable camera
                    </motion.button>
                  </div>
                </div>
              ) : null}

              <div className="mt-4 flex flex-wrap items-center gap-2">
                <motion.button
                  type="button"
                  data-testid="live-pause"
                  disabled={stopped}
                  onClick={() => setSensorState("guidance_paused")}
                  className="inline-flex h-10 items-center gap-2 rounded-full border border-white/10 bg-white/[0.04] px-4 text-sm font-medium text-silver-300 disabled:pointer-events-none disabled:opacity-40"
                  whileHover={stopped ? undefined : { scale: 1.02 }}
                  whileTap={stopped ? undefined : { scale: 0.98 }}
                  transition={MICRO_SPRING}
                >
                  <Pause className="size-4" />
                  <span>Pause</span>
                </motion.button>
                <motion.button
                  type="button"
                  data-testid="live-stop"
                  disabled={stopped}
                  onClick={() => setSensorState("user_stopped")}
                  className="inline-flex h-10 items-center gap-2 rounded-full border border-white/10 bg-white/[0.04] px-4 text-sm font-medium text-silver-300 disabled:pointer-events-none disabled:opacity-40"
                  whileHover={stopped ? undefined : { scale: 1.02 }}
                  whileTap={stopped ? undefined : { scale: 0.98 }}
                  transition={MICRO_SPRING}
                >
                  <Square className="size-4" />
                  <span>Stop</span>
                </motion.button>
                <motion.button
                  type="button"
                  data-testid="live-complete"
                  disabled={stopped}
                  onClick={() => setSensorState("live_completed")}
                  className="inline-flex h-10 items-center gap-2 rounded-full bg-white px-4 text-sm font-semibold text-graphite-950 disabled:pointer-events-none disabled:opacity-40"
                  whileHover={stopped ? undefined : { scale: 1.02 }}
                  whileTap={stopped ? undefined : { scale: 0.98 }}
                  transition={MICRO_SPRING}
                >
                  <Check className="size-4" />
                  <span>Complete</span>
                </motion.button>
              </div>
            </div>
          </motion.div>

          <section
            data-testid="live-companion-section"
            className="min-h-[420px] rounded-3xl border border-white/10 bg-black/30 p-4 backdrop-blur-2xl md:p-5"
          >
            <RitualCompanionPanel
              variant="live"
              guidanceSessionId={chatContext.guidanceSessionId}
              guidanceStatus={status}
              guidanceError={error}
              getChatContext={getChatContext}
            />
          </section>
        </motion.section>
      </div>
    </main>
  )
}
