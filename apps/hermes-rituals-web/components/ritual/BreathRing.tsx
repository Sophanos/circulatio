"use client"

import type { BreathCycle } from "@/lib/artifact-contract"

export type BreathPhase = {
  label: "Inhale" | "Hold" | "Exhale" | "Rest"
  progress: number
  elapsedMs: number
  durationMs: number
}

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

export function getBreathPhase(cycle: BreathCycle, currentMs: number): BreathPhase {
  const total = Math.max(
    cycle.inhaleMs + cycle.holdMs + cycle.exhaleMs + cycle.restMs,
    1
  )
  const offset = currentMs % total

  if (cycle.inhaleMs > 0 && offset < cycle.inhaleMs) {
    return {
      label: "Inhale",
      progress: offset / cycle.inhaleMs,
      elapsedMs: offset,
      durationMs: cycle.inhaleMs
    }
  }
  if (cycle.holdMs > 0 && offset < cycle.inhaleMs + cycle.holdMs) {
    return {
      label: "Hold",
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
      label: "Exhale",
      progress: (offset - cycle.inhaleMs - cycle.holdMs) / cycle.exhaleMs,
      elapsedMs: offset - cycle.inhaleMs - cycle.holdMs,
      durationMs: cycle.exhaleMs
    }
  }

  return {
    label: "Rest",
    progress:
      cycle.restMs > 0
        ? (offset - cycle.inhaleMs - cycle.holdMs - cycle.exhaleMs) / cycle.restMs
        : 0,
    elapsedMs: offset - cycle.inhaleMs - cycle.holdMs - cycle.exhaleMs,
    durationMs: Math.max(cycle.restMs, 0)
  }
}
