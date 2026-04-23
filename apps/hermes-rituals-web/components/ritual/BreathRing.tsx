"use client"

import { useMemo } from "react"

import { AgentState, Orb } from "@/components/ui/orb"
import type { BreathCycle } from "@/lib/artifact-contract"

function getPhase(cycle: BreathCycle, currentMs: number) {
  const total = cycle.inhaleMs + cycle.holdMs + cycle.exhaleMs + cycle.restMs
  const offset = currentMs % total

  if (offset < cycle.inhaleMs) {
    return { label: "Inhale", progress: offset / cycle.inhaleMs }
  }
  if (offset < cycle.inhaleMs + cycle.holdMs) {
    return {
      label: "Hold",
      progress: (offset - cycle.inhaleMs) / cycle.holdMs
    }
  }
  if (offset < cycle.inhaleMs + cycle.holdMs + cycle.exhaleMs) {
    return {
      label: "Exhale",
      progress: (offset - cycle.inhaleMs - cycle.holdMs) / cycle.exhaleMs
    }
  }

  return {
    label: "Rest",
    progress: (offset - cycle.inhaleMs - cycle.holdMs - cycle.exhaleMs) / cycle.restMs
  }
}

export function BreathRing({
  cycle,
  currentMs,
  isPlaying
}: {
  cycle?: BreathCycle
  currentMs: number
  isPlaying: boolean
}) {
  const breathCycle = cycle ?? {
    inhaleMs: 4200,
    holdMs: 1800,
    exhaleMs: 6400,
    restMs: 2200
  }
  const phase = getPhase(breathCycle, currentMs)

  const ringScale = useMemo(() => {
    if (phase.label === "Inhale") return 0.88 + phase.progress * 0.28
    if (phase.label === "Hold") return 1.16
    if (phase.label === "Exhale") return 1.16 - phase.progress * 0.34
    return 0.82 + phase.progress * 0.06
  }, [phase])

  const agentState: AgentState = !isPlaying
    ? null
    : phase.label === "Inhale"
      ? "listening"
      : "talking"

  return (
    <div className="relative flex h-[19rem] w-[19rem] items-center justify-center">
      <div
        className="absolute inset-0 rounded-full border border-white/30 transition-transform duration-500"
        style={{ transform: `scale(${ringScale})` }}
      />
      <div className="absolute inset-[10%] rounded-full border border-white/10" />
      <div className="absolute inset-[21%] rounded-full border border-white/20" />
      <div className="relative h-[11rem] w-[11rem] overflow-hidden rounded-full border border-white/12 bg-white/5 p-1 shadow-[inset_0_2px_12px_rgba(255,255,255,0.08)]">
        <div className="h-full w-full overflow-hidden rounded-full bg-black/10">
          <Orb
            colors={["#E5E7EB", "#9CA3AF"]}
            seed={1000}
            agentState={agentState}
          />
        </div>
      </div>
      <div className="absolute bottom-[-0.5rem] text-center">
        <p className="text-xs font-medium tracking-[0.22em] uppercase text-silver-400">
          {phase.label}
        </p>
      </div>
    </div>
  )
}
