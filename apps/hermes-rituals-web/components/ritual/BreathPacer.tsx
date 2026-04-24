"use client"

import { motion } from "motion/react"

import type { BreathPhase } from "@/components/ritual/BreathRing"

type BreathPacerProps = {
  phase: BreathPhase
}

type PacerGeometry = {
  radius: number
  opacity: number
  strokeWidth: number
  edgePulse: number
  guideOpacity: number
  loadingProgress?: number
}

const CENTER = 160
const INNER_GUIDE_RADIUS = 58
const OUTER_GUIDE_RADIUS = 104
const MIN_STROKE_WIDTH = 18
const MAX_STROKE_WIDTH = 23
const REST_RING_RADIUS = INNER_GUIDE_RADIUS
const REST_STROKE_WIDTH = 2.2
const REST_OPACITY = 0.18
const MIN_RING_RADIUS = INNER_GUIDE_RADIUS + MIN_STROKE_WIDTH / 2
const LOADING_STROKE_WIDTH = 2.4
const MAX_RING_RADIUS = OUTER_GUIDE_RADIUS - MAX_STROKE_WIDTH / 2
const RING_SPAN = MAX_RING_RADIUS - MIN_RING_RADIUS
const MORPH_TRANSITION = {
  type: "spring" as const,
  stiffness: 92,
  damping: 22,
  mass: 0.9
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

function inhaleProgress(value: number) {
  return smoothstep(value)
}

function exhaleProgress(value: number) {
  const progress = clamp01(value)

  if (progress > 0.965) {
    return 1
  }

  return smoothstep(progress)
}

function getPacerGeometry(phase: BreathPhase): PacerGeometry {
  const progress = clamp01(phase.progress)

  if (phase.label === "Get ready") {
    return {
      radius: MIN_RING_RADIUS,
      opacity: 0.2,
      strokeWidth: LOADING_STROKE_WIDTH,
      edgePulse: 0,
      guideOpacity: 0,
      loadingProgress: progress
    }
  }

  if (phase.label === "Inhale") {
    const easedProgress = inhaleProgress(progress)
    const edgeArrival = smoothstep((progress - 0.8) / 0.2)
    return {
      radius: MIN_RING_RADIUS + RING_SPAN * easedProgress,
      opacity: 0.24 + progress * 0.14,
      strokeWidth: MIN_STROKE_WIDTH + progress * (MAX_STROKE_WIDTH - MIN_STROKE_WIDTH),
      edgePulse: edgeArrival,
      guideOpacity: 0.15
    }
  }

  if (phase.label === "Hold") {
    const entryPulse = 1 - smoothstep(phase.elapsedMs / 900)
    return {
      radius: MAX_RING_RADIUS,
      opacity: 0.39,
      strokeWidth: MAX_STROKE_WIDTH,
      edgePulse: 0.55 + entryPulse * 0.45,
      guideOpacity: 0.16
    }
  }

  if (phase.label === "Exhale") {
    const release = exhaleProgress(progress)
    const edgeRelease = 1 - smoothstep(progress / 0.16)
    const settle = smoothstep((progress - 0.68) / 0.32)
    const activeRadius = MAX_RING_RADIUS - RING_SPAN * release
    const activeOpacity = 0.38 - progress * 0.15
    const activeStrokeWidth = MAX_STROKE_WIDTH - progress * (MAX_STROKE_WIDTH - MIN_STROKE_WIDTH)

    return {
      radius: activeRadius + (REST_RING_RADIUS - activeRadius) * settle,
      opacity: activeOpacity + (REST_OPACITY - activeOpacity) * settle,
      strokeWidth: activeStrokeWidth + (REST_STROKE_WIDTH - activeStrokeWidth) * settle,
      edgePulse: edgeRelease * 0.65 * (1 - settle),
      guideOpacity: 0.15 + (0.18 - 0.15) * settle
    }
  }

  if (phase.label === "Rest") {
    return {
      radius: REST_RING_RADIUS,
      opacity: REST_OPACITY,
      strokeWidth: REST_STROKE_WIDTH,
      edgePulse: 0,
      guideOpacity: 0.18
    }
  }

  return {
    radius: MIN_RING_RADIUS,
    opacity: 0.18,
    strokeWidth: MIN_STROKE_WIDTH,
    edgePulse: 0,
    guideOpacity: 0.12
  }
}

export function BreathPacer({ phase }: BreathPacerProps) {
  const geometry = getPacerGeometry(phase)
  const edgeRadius = geometry.radius + geometry.strokeWidth / 2 + 1 + geometry.edgePulse * 5
  const loadingProgress = geometry.loadingProgress

  return (
    <div className="flex h-[19rem] w-[19rem] items-center justify-center">
      <svg viewBox="0 0 320 320" className="h-full w-full overflow-visible" aria-hidden="true">
        <motion.circle
          cx={CENTER}
          cy={CENTER}
          r={OUTER_GUIDE_RADIUS}
          fill="none"
          stroke="rgba(255,255,255,0.13)"
          strokeWidth="1.6"
          animate={{ opacity: geometry.guideOpacity }}
          transition={MORPH_TRANSITION}
        />
        <motion.circle
          cx={CENTER}
          cy={CENTER}
          r={INNER_GUIDE_RADIUS}
          fill="none"
          stroke="rgba(255,255,255,0.12)"
          strokeWidth="1.4"
          animate={{ opacity: geometry.guideOpacity * 0.86 }}
          transition={MORPH_TRANSITION}
        />
        <motion.circle
          cx={CENTER}
          cy={CENTER}
          fill="none"
          stroke="rgba(255,255,255,0.22)"
          strokeWidth="1"
          initial={false}
          animate={{
            r: edgeRadius,
            opacity: geometry.edgePulse * 0.28
          }}
          transition={MORPH_TRANSITION}
        />
        <motion.circle
          cx={CENTER}
          cy={CENTER}
          fill="none"
          stroke={`rgba(255,255,255,${geometry.opacity})`}
          initial={false}
          animate={{
            r: geometry.radius,
            strokeWidth: geometry.strokeWidth
          }}
          transition={MORPH_TRANSITION}
        />
        {loadingProgress !== undefined && (
          <motion.circle
            cx={CENTER}
            cy={CENTER}
            fill="none"
            stroke="rgba(255,255,255,0.74)"
            strokeLinecap="round"
            pathLength={1}
            strokeDasharray="1"
            transform={`rotate(-90 ${CENTER} ${CENTER})`}
            initial={false}
            animate={{
              r: geometry.radius,
              strokeWidth: geometry.strokeWidth,
              strokeDashoffset: 1 - loadingProgress,
              opacity: 0.82
            }}
            transition={MORPH_TRANSITION}
          />
        )}
      </svg>
    </div>
  )
}
