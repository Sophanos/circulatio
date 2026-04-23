"use client"

import { useMemo } from "react"
import { motion } from "motion/react"

import type { BreathCycle } from "@/lib/artifact-contract"

const SPRING = { type: "spring" as const, stiffness: 300, damping: 28, mass: 0.7 }

export const DEFAULT_BREATH_CYCLE: BreathCycle = {
  inhaleMs: 4200,
  holdMs: 1800,
  exhaleMs: 6400,
  restMs: 2200,
  pattern: "lengthened_exhale",
  techniqueName: "Steadying",
  preferenceSource: "host_default",
  visualForm: "orb"
}

export function getBreathPhase(cycle: BreathCycle, currentMs: number) {
  const total = Math.max(
    cycle.inhaleMs + cycle.holdMs + cycle.exhaleMs + cycle.restMs,
    1
  )
  const offset = currentMs % total

  if (cycle.inhaleMs > 0 && offset < cycle.inhaleMs) {
    return {
      label: "Inhale" as const,
      progress: offset / cycle.inhaleMs,
      elapsedMs: offset,
      durationMs: cycle.inhaleMs
    }
  }
  if (cycle.holdMs > 0 && offset < cycle.inhaleMs + cycle.holdMs) {
    return {
      label: "Hold" as const,
      progress: (offset - cycle.inhaleMs) / cycle.holdMs,
      elapsedMs: offset - cycle.inhaleMs,
      durationMs: cycle.holdMs
    }
  }
  if (
    cycle.exhaleMs > 0 &&
    offset < cycle.inhaleMs + cycle.holdMs + cycle.exhaleMs
  ) {
    return {
      label: "Exhale" as const,
      progress: (offset - cycle.inhaleMs - cycle.holdMs) / cycle.exhaleMs,
      elapsedMs: offset - cycle.inhaleMs - cycle.holdMs,
      durationMs: cycle.exhaleMs
    }
  }

  return {
    label: "Rest" as const,
    progress:
      cycle.restMs > 0
        ? (offset - cycle.inhaleMs - cycle.holdMs - cycle.exhaleMs) / cycle.restMs
        : 0,
    elapsedMs: offset - cycle.inhaleMs - cycle.holdMs - cycle.exhaleMs,
    durationMs: Math.max(cycle.restMs, 0)
  }
}

export function BreathRing({
  cycle,
  currentMs,
  isPlaying,
  showLabel = true
}: {
  cycle?: BreathCycle
  currentMs: number
  isPlaying: boolean
  showLabel?: boolean
}) {
  const breathCycle = cycle ?? DEFAULT_BREATH_CYCLE
  const phase = getBreathPhase(breathCycle, currentMs)

  const ringScale = useMemo(() => {
    if (phase.label === "Inhale") return 0.88 + phase.progress * 0.28
    if (phase.label === "Hold") return 1.16
    if (phase.label === "Exhale") return 1.16 - phase.progress * 0.34
    return 0.82 + phase.progress * 0.06
  }, [phase])

  const coreScale = useMemo(() => {
    if (phase.label === "Inhale") return 0.9 + phase.progress * 0.18
    if (phase.label === "Hold") return 1.08
    if (phase.label === "Exhale") return 1.08 - phase.progress * 0.16
    return 0.92 + phase.progress * 0.04
  }, [phase])
  const haloOpacity = isPlaying ? 0.34 : 0.18

  return (
    <div className="relative flex h-[19rem] w-[19rem] items-center justify-center">
      <motion.div
        className="absolute inset-0 rounded-full border border-white/30"
        animate={{ scale: ringScale }}
        transition={SPRING}
      />
      <motion.div
        className="absolute inset-[10%] rounded-full border border-white/10"
        animate={{ scale: 0.98 + phase.progress * 0.025, opacity: 0.18 + haloOpacity * 0.3 }}
        transition={SPRING}
      />
      <motion.div
        className="absolute inset-[21%] rounded-full border border-white/20"
        animate={{ scale: 0.96 + phase.progress * 0.04, opacity: 0.22 + haloOpacity * 0.45 }}
        transition={SPRING}
      />
      <motion.div
        className="relative h-[11rem] w-[11rem] rounded-full border border-white/12"
        animate={{ scale: coreScale }}
        transition={SPRING}
      >
        <div className="absolute inset-[16%] rounded-full border border-white/10" />
        <div className="absolute inset-[30%] rounded-full border border-white/12" />
        <motion.div
          className="absolute inset-[44%] rounded-full bg-white/55"
          animate={{ scale: 0.94 + phase.progress * 0.08, opacity: 0.45 + haloOpacity * 0.35 }}
          transition={SPRING}
        />
      </motion.div>
      {showLabel && (
        <div className="absolute bottom-[-0.5rem] text-center">
          <p className="text-xs font-medium tracking-[0.22em] uppercase text-silver-400">
            {phase.label}
          </p>
        </div>
      )}
    </div>
  )
}
