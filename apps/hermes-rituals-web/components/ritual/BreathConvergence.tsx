"use client"

import { useMemo } from "react"
import { motion } from "motion/react"

import type { BreathCycle } from "@/lib/artifact-contract"
import { getBreathPhase, DEFAULT_BREATH_CYCLE } from "@/components/ritual/BreathRing"

interface ConvergenceOrb {
  radius: number
  strokeWidth: number
  baseOpacity: number
  rotationSpeed: number
  initialAngle: number
  offsetDecay: number
}

function buildOrbits(count = 8): ConvergenceOrb[] {
  return Array.from({ length: count }, (_, i) => ({
    radius: 38 + i * 16,
    strokeWidth: i === 0 ? 1.4 : 0.8 + (count - i) * 0.06,
    baseOpacity: 0.08 + (count - i) * 0.035,
    rotationSpeed: 0.00018 + i * 0.00007,
    initialAngle: (Math.PI * 2 * i) / count + i * 0.4,
    offsetDecay: 22 + i * 3.5,
  }))
}

export function BreathConvergence({
  cycle,
  currentMs,
  isPlaying,
  totalDurationMs = 60000,
}: {
  cycle?: BreathCycle
  currentMs: number
  isPlaying: boolean
  totalDurationMs?: number
}) {
  const breathCycle = cycle ?? DEFAULT_BREATH_CYCLE
  const phase = getBreathPhase(breathCycle, currentMs)
  const sessionProgress = Math.min(currentMs / totalDurationMs, 1)

  const orbits = useMemo(() => buildOrbits(8), [])

  // Breath phase intensity for center glow
  const centerIntensity = useMemo(() => {
    if (phase.label === "Inhale") return 0.35 + phase.progress * 0.45
    if (phase.label === "Hold") return 0.8
    if (phase.label === "Exhale") return 0.8 - phase.progress * 0.35
    return 0.3 + phase.progress * 0.2
  }, [phase])

  const viewBoxSize = 280
  const center = viewBoxSize / 2

  return (
    <div className="relative flex h-[22rem] w-[22rem] items-center justify-center md:h-[26rem] md:w-[26rem]">
      <svg
        viewBox={`0 0 ${viewBoxSize} ${viewBoxSize}`}
        className="h-full w-full"
        style={{ overflow: "visible" }}
        aria-hidden="true"
      >
        {orbits.map((orbit, index) => {
          const rotation = currentMs * orbit.rotationSpeed + orbit.initialAngle
          const offset = orbit.offsetDecay * (1 - sessionProgress)
          const offsetX = Math.cos(rotation) * offset
          const offsetY = Math.sin(rotation) * offset

          // Phase-based breathing pulse on the orb
          const breathPulse =
            phase.label === "Inhale"
              ? 1 + phase.progress * 0.04
              : phase.label === "Hold"
                ? 1.04
                : phase.label === "Exhale"
                  ? 1.04 - phase.progress * 0.04
                  : 1

          return (
            <motion.circle
              key={index}
              cx={center + offsetX}
              cy={center + offsetY}
              r={orbit.radius * breathPulse}
              fill="none"
              stroke={`rgba(226, 232, 240, ${orbit.baseOpacity * (isPlaying ? 1 : 0.55)})`}
              strokeWidth={orbit.strokeWidth}
              style={{
                transformOrigin: `${center}px ${center}px`,
                transform: `rotate(${rotation * (180 / Math.PI)}deg)`,
              }}
              transition={{ duration: 0.6, ease: "easeOut" }}
            />
          )
        })}

        {/* Center core — pulses with breath */}
        <motion.circle
          cx={center}
          cy={center}
          r={6 + centerIntensity * 5}
          fill={`rgba(255, 255, 255, ${0.12 + centerIntensity * 0.35})`}
          animate={{
            r: 6 + centerIntensity * 6,
            opacity: 0.2 + centerIntensity * 0.5,
          }}
          transition={{ duration: 0.5, ease: "easeOut" }}
        />

        {/* Inner glow ring */}
        <motion.circle
          cx={center}
          cy={center}
          r={16 + centerIntensity * 8}
          fill="none"
          stroke={`rgba(255, 255, 255, ${0.04 + centerIntensity * 0.1})`}
          strokeWidth={1}
          animate={{
            r: 16 + centerIntensity * 10,
          }}
          transition={{ duration: 0.5, ease: "easeOut" }}
        />
      </svg>
    </div>
  )
}
