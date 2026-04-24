"use client"

import { motion } from "motion/react"

import { BreathPacer } from "@/components/ritual/BreathPacer"
import {
  DEFAULT_BREATH_CYCLE,
  getBreathPhase,
  type BreathPhase
} from "@/components/ritual/BreathRing"
import type { BreathCycle, BreathVisualForm } from "@/lib/artifact-contract"

const SPRING = { type: "spring" as const, stiffness: 300, damping: 30, mass: 0.8 }
const PREPARATION_MS = 2600

function titleCase(value: string) {
  return value
    .split("_")
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(" ")
}

function formatDuration(ms: number) {
  const seconds = ms / 1000
  return Number.isInteger(seconds) ? `${seconds.toFixed(0)}s` : `${seconds.toFixed(1)}s`
}

function buildWavePath({
  baseline,
  amplitude,
  currentMs,
  index
}: {
  baseline: number
  amplitude: number
  currentMs: number
  index: number
}) {
  const points: string[] = []

  for (let x = 0; x <= 320; x += 16) {
    const wave =
      Math.sin(x * 0.032 + currentMs * 0.003 + index * 0.45) * amplitude +
      Math.cos(x * 0.015 - currentMs * 0.0016 + index * 0.22) * amplitude * 0.42
    const y = baseline + wave
    points.push(`${x === 0 ? "M" : "L"} ${x} ${y}`)
  }

  return points.join(" ")
}

function BreathWave({
  currentMs,
  intensity
}: {
  currentMs: number
  intensity: number
}) {
  const lines = Array.from({ length: 7 }, (_, index) => {
    const baseline = 54 + index * 34
    const amplitude = intensity * (1 - index * 0.08)
    return {
      baseline,
      amplitude,
      opacity: 0.12 + (6 - index) * 0.05
    }
  })

  return (
    <div className="flex h-[18rem] w-[18rem] items-center justify-center">
      <svg
        viewBox="0 0 320 320"
        className="h-full w-full overflow-visible"
        aria-hidden="true"
      >
        {lines.map((line, index) => (
          <path
            key={line.baseline}
            d={buildWavePath({
              baseline: line.baseline,
              amplitude: line.amplitude,
              currentMs,
              index
            })}
            fill="none"
            stroke={`rgba(226, 232, 240, ${line.opacity})`}
            strokeWidth={index === 3 ? 1.8 : 1.1}
            strokeLinecap="round"
          />
        ))}
      </svg>
    </div>
  )
}

function BreathMandala({
  currentMs,
  intensity
}: {
  currentMs: number
  intensity: number
}) {
  const rotation = currentMs * 0.0022
  const rings = [52, 78, 104, 130]

  return (
    <div className="flex h-[18rem] w-[18rem] items-center justify-center">
      <svg viewBox="0 0 320 320" className="h-full w-full" aria-hidden="true">
        <g transform={`rotate(${rotation} 160 160)`}>
          {rings.map((radius, index) => (
            <circle
              key={radius}
              cx="160"
              cy="160"
              r={radius + intensity * (index + 1) * 0.14}
              fill="none"
              stroke={`rgba(226, 232, 240, ${0.1 + index * 0.06})`}
              strokeWidth={index === 0 ? 1.3 : 0.9}
            />
          ))}
          {Array.from({ length: 12 }, (_, index) => {
            const angle = (Math.PI * 2 * index) / 12
            const inner = 34
            const outer = 138 + intensity * 0.32
            const x1 = 160 + Math.cos(angle) * inner
            const y1 = 160 + Math.sin(angle) * inner
            const x2 = 160 + Math.cos(angle) * outer
            const y2 = 160 + Math.sin(angle) * outer

            return (
              <line
                key={index}
                x1={x1}
                y1={y1}
                x2={x2}
                y2={y2}
                stroke={`rgba(226, 232, 240, ${0.08 + (index % 2) * 0.04})`}
                strokeWidth="0.8"
              />
            )
          })}
        </g>
        <circle
          cx="160"
          cy="160"
          r={20 + intensity * 0.22}
          fill="rgba(255,255,255,0.06)"
          stroke="rgba(255,255,255,0.2)"
          strokeWidth="1"
        />
      </svg>
    </div>
  )
}

function BreathHorizon({
  currentMs,
  intensity
}: {
  currentMs: number
  intensity: number
}) {
  const shimmer = Math.sin(currentMs * 0.0024) * 0.5 + 0.5

  return (
    <div className="relative flex h-[18rem] w-[18rem] items-center justify-center">
      <div className="absolute inset-0 rounded-full bg-[radial-gradient(circle,rgba(255,255,255,0.08),transparent_62%)]" />
      {[-2, -1, 0, 1, 2].map((offset) => {
        const scale = 1 + intensity * 0.002 + Math.abs(offset) * 0.02
        return (
          <motion.div
            key={offset}
            className="absolute left-1/2 top-1/2 h-px w-[15rem] -translate-x-1/2 -translate-y-1/2 rounded-full bg-white/20"
            animate={{
              scaleX: scale,
              y: offset * 24,
              opacity: offset === 0 ? 0.8 : 0.18 + shimmer * 0.18
            }}
            transition={SPRING}
          />
        )
      })}
      <motion.div
        className="absolute h-4 w-4 rounded-full bg-white/60"
        animate={{
          scale: 0.8 + intensity * 0.01,
          opacity: 0.35 + shimmer * 0.35
        }}
        transition={SPRING}
      />
    </div>
  )
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

function BreathVisual({
  cycle,
  currentMs,
  phase
}: {
  cycle: BreathCycle
  currentMs: number
  phase: BreathPhase
}) {
  const intensity =
    phase.label === "Inhale"
      ? 24 + phase.progress * 48
      : phase.label === "Hold"
        ? 62
        : phase.label === "Exhale"
          ? 62 - phase.progress * 34
          : 18 + phase.progress * 12
  const form: BreathVisualForm = cycle.visualForm ?? "orb"

  if (form === "wave") {
    return <BreathWave currentMs={currentMs} intensity={intensity} />
  }
  if (form === "mandala") {
    return <BreathMandala currentMs={currentMs} intensity={intensity} />
  }
  if (form === "horizon") {
    return <BreathHorizon currentMs={currentMs} intensity={intensity} />
  }

  return <BreathPacer phase={phase} />
}

export function BreathStage({
  cycle,
  currentMs,
  isPlaying,
  immersive
}: {
  cycle?: BreathCycle
  currentMs: number
  isPlaying: boolean
  immersive?: boolean
  totalDurationMs?: number
}) {
  const breathCycle = cycle ?? DEFAULT_BREATH_CYCLE
  const phase = getPreparedBreathPhase(breathCycle, currentMs)
  const remainingMs = Math.max(phase.durationMs - phase.elapsedMs, 0)
  const patternLabel = titleCase(breathCycle.pattern ?? DEFAULT_BREATH_CYCLE.pattern ?? "steadying")
  const techniqueName = breathCycle.techniqueName ?? patternLabel
  const visualForm = breathCycle.visualForm ?? DEFAULT_BREATH_CYCLE.visualForm ?? "orb"

  if (immersive) {
    return (
      <motion.div
        className="relative flex h-full w-full flex-col items-center justify-center"
        layout
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={SPRING}
      >
        <div className="flex flex-1 items-center justify-center">
          <BreathVisual cycle={breathCycle} currentMs={currentMs} phase={phase} />
        </div>

        <motion.div
          className="flex flex-col items-center gap-1 pb-8"
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: isPlaying ? 1 : 0.72, y: 0 }}
          transition={{ delay: 0.3, ...SPRING }}
        >
          <span className="text-[10px] font-medium uppercase tracking-[0.2em] text-silver-500">
            {phase.label}
          </span>
          <span className="text-3xl font-light tabular-nums tracking-tight text-silver-100">
            {formatDuration(remainingMs)}
          </span>
        </motion.div>
      </motion.div>
    )
  }

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
              Breath Container
            </span>
            <span className="text-sm font-medium text-silver-100">{techniqueName}</span>
            <span className="text-[11px] text-silver-500">
              {patternLabel} {breathCycle.cycles ? `· ${breathCycle.cycles} cycles` : ""}
            </span>
          </div>

          <div className="rounded-full bg-black/20 px-3 py-1.5 text-[10px] font-medium uppercase tracking-[0.18em] text-silver-300 backdrop-blur-xl">
            {visualForm}
          </div>
        </div>

        <div className="flex flex-1 items-center justify-center px-4 py-4">
          <BreathVisual cycle={breathCycle} currentMs={currentMs} phase={phase} />
        </div>

        <div className="flex flex-col items-center gap-1">
          <span className="text-[10px] font-medium uppercase tracking-[0.18em] text-silver-400">
            {phase.label}
          </span>
          <span className="text-2xl font-semibold tabular-nums tracking-tight text-silver-50">
            {formatDuration(remainingMs)}
          </span>
        </div>
      </div>
    </motion.div>
  )
}
