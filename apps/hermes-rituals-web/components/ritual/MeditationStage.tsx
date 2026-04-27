"use client"

import { RitualStageShell } from "@/components/ritual/RitualStageShell"
import { BreathConvergence } from "@/components/ritual/BreathConvergence"
import {
  DEFAULT_BREATH_CYCLE,
  getBreathPhase,
  type BreathPhase
} from "@/components/ritual/BreathRing"
import type { BreathCycle } from "@/lib/artifact-contract"

const PREPARATION_MS = 5000

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value))
}

function formatTimestamp(ms: number) {
  const totalSeconds = Math.max(Math.ceil(ms / 1000), 0)
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return `${minutes}:${seconds.toString().padStart(2, "0")}`
}

function getPreparedBreathPhase(cycle: BreathCycle, currentMs: number): BreathPhase {
  if (currentMs < PREPARATION_MS) {
    return {
      label: "Get ready",
      progress: currentMs / PREPARATION_MS,
      elapsedMs: currentMs,
      durationMs: PREPARATION_MS
    }
  }
  return getBreathPhase(cycle, currentMs - PREPARATION_MS)
}

export function MeditationStage({
  cycle,
  currentMs,
  durationMs,
  immersive,
  isPlaying
}: {
  cycle?: BreathCycle
  currentMs: number
  durationMs: number
  immersive?: boolean
  isPlaying?: boolean
}) {
  const breathCycle = cycle ?? DEFAULT_BREATH_CYCLE
  const phase = getPreparedBreathPhase(breathCycle, currentMs)
  const sessionProgress = clamp(currentMs / Math.max(durationMs, 1), 0, 1)
  const remainingMs = Math.max(durationMs - currentMs, 0)
  const isPreparing = phase.label === "Get ready"

  const header = (
    <>
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
    </>
  )

  const footer = isPreparing
    ? immersive
      ? (
        <div className="flex flex-col items-center gap-4">
          <span className="text-2xl font-semibold tracking-tight text-silver-100 md:text-3xl">
            Get comfortable
          </span>
          <span className="max-w-xs text-sm font-medium leading-snug text-silver-500 md:text-base">
            Find a still position and let attention begin to settle
          </span>
        </div>
      )
      : (
        <div className="flex flex-col items-center gap-2">
          <span className="text-base font-semibold tracking-tight text-silver-100 md:text-lg">
            Get comfortable
          </span>
          <span className="max-w-xs text-xs font-medium leading-snug text-silver-500 md:text-sm">
            Find a still position and let attention begin to settle
          </span>
        </div>
      )
    : immersive
      ? (
        <>
          <span className="text-[10px] font-medium uppercase tracking-[0.2em] text-silver-500">
            Settling
          </span>
          <span className="text-3xl font-light tabular-nums tracking-tight text-silver-100">
            {formatTimestamp(remainingMs)}
          </span>
        </>
      )
      : (
        <>
          <span className="text-[10px] font-medium uppercase tracking-[0.18em] text-silver-400">
            Settling
          </span>
          <span className="text-2xl font-semibold tabular-nums tracking-tight text-silver-50">
            {formatTimestamp(remainingMs)}
          </span>
        </>
      )

  return (
    <RitualStageShell
      immersive={immersive}
      isPlaying={isPlaying}
      header={immersive ? undefined : header}
      footer={footer}
    >
      <BreathConvergence
        currentMs={currentMs}
        sessionProgress={sessionProgress}
        phase={phase}
      />
    </RitualStageShell>
  )
}
