"use client"

import type { BreathPhase } from "@/components/ritual/BreathRing"

type BreathConvergenceProps = {
  currentMs: number
  sessionProgress: number
  phase: BreathPhase
}

type TraceBlueprint = {
  startOffsetX: number
  startOffsetY: number
  startRadiusDelta: number
  driftAmp: number
  speed: number
  phaseOffset: number
  baseOpacity: number
  strokeWidth: number
}

type PhaseProfile = {
  sharedRadiusShift: number
  coherenceBoost: number
  driftMultiplier: number
  coreOpacity: number
  traceOpacityBoost: number
}

const TRACE_BLUEPRINTS: TraceBlueprint[] = [
  {
    startOffsetX: -26,
    startOffsetY: 18,
    startRadiusDelta: 13,
    driftAmp: 4.4,
    speed: 0.00042,
    phaseOffset: 0.2,
    baseOpacity: 0.32,
    strokeWidth: 1.3
  },
  {
    startOffsetX: -11,
    startOffsetY: -24,
    startRadiusDelta: -12,
    driftAmp: 3.6,
    speed: 0.00051,
    phaseOffset: 0.9,
    baseOpacity: 0.42,
    strokeWidth: 1.1
  },
  {
    startOffsetX: 17,
    startOffsetY: -18,
    startRadiusDelta: 15,
    driftAmp: 4.1,
    speed: 0.00039,
    phaseOffset: 1.6,
    baseOpacity: 0.38,
    strokeWidth: 1.55
  },
  {
    startOffsetX: 29,
    startOffsetY: 6,
    startRadiusDelta: -9,
    driftAmp: 3.1,
    speed: 0.00047,
    phaseOffset: 2.1,
    baseOpacity: 0.47,
    strokeWidth: 1.25
  },
  {
    startOffsetX: 12,
    startOffsetY: 27,
    startRadiusDelta: 8,
    driftAmp: 3.8,
    speed: 0.00044,
    phaseOffset: 2.8,
    baseOpacity: 0.29,
    strokeWidth: 1.7
  },
  {
    startOffsetX: -21,
    startOffsetY: -7,
    startRadiusDelta: -15,
    driftAmp: 2.9,
    speed: 0.00058,
    phaseOffset: 3.4,
    baseOpacity: 0.36,
    strokeWidth: 1.2
  },
  {
    startOffsetX: 7,
    startOffsetY: 13,
    startRadiusDelta: 5,
    driftAmp: 2.4,
    speed: 0.00063,
    phaseOffset: 4,
    baseOpacity: 0.51,
    strokeWidth: 1.45
  },
  {
    startOffsetX: -15,
    startOffsetY: 9,
    startRadiusDelta: -4,
    driftAmp: 2.1,
    speed: 0.00069,
    phaseOffset: 4.7,
    baseOpacity: 0.33,
    strokeWidth: 1.35
  },
  {
    startOffsetX: 22,
    startOffsetY: -3,
    startRadiusDelta: 10,
    driftAmp: 2.7,
    speed: 0.00054,
    phaseOffset: 5.2,
    baseOpacity: 0.4,
    strokeWidth: 1.15
  }
]

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value))
}

function clamp01(value: number) {
  return clamp(value, 0, 1)
}

function getPhaseProfile(phase: BreathPhase): PhaseProfile {
  const progress = clamp01(phase.progress)

  if (phase.label === "Inhale") {
    return {
      sharedRadiusShift: -2.4 * progress,
      coherenceBoost: 0.05 * progress,
      driftMultiplier: 0.95 - 0.15 * progress,
      coreOpacity: 0.05 + 0.08 * progress,
      traceOpacityBoost: 0.02 + 0.04 * progress
    }
  }

  if (phase.label === "Hold") {
    return {
      sharedRadiusShift: -2.4,
      coherenceBoost: 0.08,
      driftMultiplier: 0.55,
      coreOpacity: 0.13,
      traceOpacityBoost: 0.08
    }
  }

  if (phase.label === "Exhale") {
    return {
      sharedRadiusShift: -2.4 + 3.2 * progress,
      coherenceBoost: 0.04 * (1 - progress),
      driftMultiplier: 0.7 + 0.1 * progress,
      coreOpacity: 0.11 - 0.05 * progress,
      traceOpacityBoost: 0.05 - 0.02 * progress
    }
  }

  return {
    sharedRadiusShift: 0.4 * (1 - progress),
    coherenceBoost: 0.01,
    driftMultiplier: 0.6,
    coreOpacity: 0.04,
    traceOpacityBoost: 0.01
  }
}

export function BreathConvergence({
  currentMs,
  sessionProgress,
  phase
}: BreathConvergenceProps) {
  const macro = clamp01(sessionProgress)
  const baseConvergence = 1 - (1 - macro) ** 2
  const phaseProfile = getPhaseProfile(phase)
  const convergence = Math.min(
    0.985,
    baseConvergence + phaseProfile.coherenceBoost * (1 - baseConvergence)
  )
  const chaos = 1 - convergence

  return (
    <div className="flex h-[19rem] w-[19rem] items-center justify-center">
      <svg viewBox="0 0 320 320" className="h-full w-full overflow-visible" aria-hidden="true">
        <circle
          cx="160"
          cy="160"
          r="18"
          fill="rgba(255,255,255,1)"
          opacity={phaseProfile.coreOpacity}
        />
        {TRACE_BLUEPRINTS.map((trace, index) => {
          const t = currentMs * trace.speed + trace.phaseOffset
          const driftScale = (0.18 + chaos * 0.82) * phaseProfile.driftMultiplier
          const liveDrift = trace.driftAmp * driftScale
          const cx = 160 + trace.startOffsetX * chaos + Math.cos(t) * liveDrift
          const cy =
            160 +
            trace.startOffsetY * chaos +
            Math.sin(t * 1.07 + trace.phaseOffset) * liveDrift
          const radiusJitter =
            Math.sin(t * 0.73 + trace.phaseOffset) * (0.22 + chaos * 0.58)
          const radius =
            84 + trace.startRadiusDelta * chaos + phaseProfile.sharedRadiusShift + radiusJitter
          const opacity = clamp(
            trace.baseOpacity + phaseProfile.traceOpacityBoost + baseConvergence * 0.04,
            0.18,
            0.72
          )

          return (
            <circle
              key={index}
              cx={cx}
              cy={cy}
              r={radius}
              fill="none"
              stroke={`rgba(255,255,255,${opacity})`}
              strokeWidth={trace.strokeWidth}
              strokeLinecap="round"
            />
          )
        })}
      </svg>
    </div>
  )
}
