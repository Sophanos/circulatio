"use client"

import type { BreathPhase } from "@/components/ritual/BreathRing"

type BreathPacerProps = {
  phase: BreathPhase
}

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value))
}

function clamp01(value: number) {
  return clamp(value, 0, 1)
}

function smoothstep(value: number) {
  const t = clamp01(value)
  return t * t * (3 - 2 * t)
}

function getPacerGeometry(phase: BreathPhase) {
  const progress = clamp01(phase.progress)
  const minRadius = 58
  const maxRadius = 84
  const span = maxRadius - minRadius

  if (phase.label === "Inhale") {
    const edgeArrival = smoothstep((progress - 0.86) / 0.14)
    return {
      label: "Inhale",
      radius: progress > 0.985 ? maxRadius : minRadius + span * smoothstep(progress),
      opacity: 0.24 + progress * 0.13,
      strokeWidth: 18 + progress * 5,
      edgePulse: edgeArrival,
      vibration: 0
    }
  }

  if (phase.label === "Hold") {
    const entryPulse = 1 - smoothstep(phase.elapsedMs / 900)
    return {
      label: "Hold",
      radius: maxRadius,
      opacity: 0.39,
      strokeWidth: 23,
      edgePulse: 0.55 + entryPulse * 0.45,
      vibration: 0
    }
  }

  if (phase.label === "Exhale") {
    const release = smoothstep(progress)
    const edgeRelease = 1 - smoothstep(progress / 0.16)
    return {
      label: "Exhale",
      radius: maxRadius - span * release,
      opacity: 0.38 - progress * 0.15,
      strokeWidth: 23 - progress * 5,
      edgePulse: edgeRelease * 0.65,
      vibration: 0
    }
  }

  return {
    label: "Rest",
    radius: minRadius + (1 - progress) * 2,
    opacity: 0.2,
    strokeWidth: 17,
    edgePulse: 0,
    vibration: 0
  }
}

export function BreathPacer({ phase }: BreathPacerProps) {
  const geometry = getPacerGeometry(phase)
  const radius = geometry.radius + geometry.vibration
  const edgeRadius = radius + 13 + geometry.edgePulse * 7

  return (
    <div className="flex h-[19rem] w-[19rem] items-center justify-center">
      <svg viewBox="0 0 320 320" className="h-full w-full overflow-visible" aria-hidden="true">
        <circle
          cx="160"
          cy="160"
          r="104"
          fill="none"
          stroke="rgba(255,255,255,0.13)"
          strokeWidth="1.6"
        />
        <circle
          cx="160"
          cy="160"
          r={edgeRadius}
          fill="none"
          stroke="rgba(255,255,255,0.22)"
          strokeWidth="1"
          opacity={geometry.edgePulse * 0.28}
        />
        <circle
          cx="160"
          cy="160"
          r={radius}
          fill="none"
          stroke={`rgba(255,255,255,${geometry.opacity})`}
          strokeWidth={geometry.strokeWidth}
        />
      </svg>
    </div>
  )
}
