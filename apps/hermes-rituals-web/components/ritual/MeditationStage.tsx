"use client"

import { motion } from "motion/react"

import { BreathConvergence } from "@/components/ritual/BreathConvergence"
import { DEFAULT_BREATH_CYCLE, getBreathPhase } from "@/components/ritual/BreathRing"
import type { BreathCycle } from "@/lib/artifact-contract"

const SPRING = { type: "spring" as const, stiffness: 300, damping: 30, mass: 0.8 }

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value))
}

function formatTimestamp(ms: number) {
  const totalSeconds = Math.max(Math.ceil(ms / 1000), 0)
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return `${minutes}:${seconds.toString().padStart(2, "0")}`
}

export function MeditationStage({
  cycle,
  currentMs,
  durationMs
}: {
  cycle?: BreathCycle
  currentMs: number
  durationMs: number
}) {
  const breathCycle = cycle ?? DEFAULT_BREATH_CYCLE
  const phase = getBreathPhase(breathCycle, currentMs)
  const sessionProgress = clamp(currentMs / Math.max(durationMs, 1), 0, 1)
  const remainingMs = Math.max(durationMs - currentMs, 0)

  return (
    <motion.div
      className="relative flex h-full w-full overflow-hidden rounded-3xl bg-white/[0.03]"
      layout
      initial={{ opacity: 0, scale: 0.985 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 1.01 }}
      transition={SPRING}
    >
      <div className="absolute inset-0 bg-[linear-gradient(180deg,rgba(16,19,23,0.06)_0%,rgba(16,19,23,0.62)_100%)]" />

      <div className="relative z-10 flex h-full w-full flex-col justify-between p-4 md:p-5">
        <div className="flex items-start justify-between gap-4">
          <div className="flex flex-col gap-1">
            <span className="text-[10px] font-medium uppercase tracking-[0.18em] text-silver-400">
              Meditation
            </span>
            <span className="text-sm font-medium text-silver-100">Coherence convergence</span>
            <span className="text-[11px] text-silver-500">Session-level settling</span>
          </div>

          <div className="rounded-full bg-black/20 px-3 py-1.5 text-[10px] font-medium uppercase tracking-[0.18em] text-silver-300 backdrop-blur-xl">
            orb
          </div>
        </div>

        <div className="flex flex-1 items-center justify-center px-4 py-4">
          <BreathConvergence
            currentMs={currentMs}
            sessionProgress={sessionProgress}
            phase={phase}
          />
        </div>

        <div className="flex flex-col items-center gap-1">
          <span className="text-[10px] font-medium uppercase tracking-[0.18em] text-silver-400">
            Settling
          </span>
          <span className="text-2xl font-semibold tabular-nums tracking-tight text-silver-50">
            {formatTimestamp(remainingMs)}
          </span>
        </div>
      </div>
    </motion.div>
  )
}
