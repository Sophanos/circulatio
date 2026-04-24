"use client"

import { useEffect, useMemo, useRef } from "react"

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

type ConvergenceTarget = PhaseProfile & {
  macro: number
  playbackTime: number
}

type AnimatedConvergenceState = ConvergenceTarget & {
  localTime: number
}

type RingTraceRender = {
  d: string
  opacity: number
}

type ConvergenceRender = {
  traces: RingTraceRender[]
}

type Point = {
  x: number
  y: number
}

const SVG_CENTER = 160
const BASE_RADIUS = 84
const RING_POINT_COUNT = 72
const MAX_FRAME_DELTA_MS = 80
const PLAYBACK_TIME_BLEND = 0.018
const CHAOS_HOLD_FRACTION = 0.18
const INTRO_MOTION_FRACTION = 0.44
const TWO_PI = Math.PI * 2

function easeOut(value: number) {
  return 1 - (1 - value) ** 3
}

function smoothstep(value: number) {
  const t = clamp01(value)
  return t * t * (3 - 2 * t)
}

function getHeldConvergenceProgress(macro: number) {
  const heldMacro = clamp01((macro - CHAOS_HOLD_FRACTION) / (1 - CHAOS_HOLD_FRACTION))
  return smoothstep(heldMacro)
}

const TRACE_BLUEPRINTS: TraceBlueprint[] = [
  {
    startOffsetX: -26,
    startOffsetY: 18,
    startRadiusDelta: 13,
    driftAmp: 6.1,
    speed: 0.00058,
    phaseOffset: 0.2,
    baseOpacity: 0.32,
    strokeWidth: 1.3
  },
  {
    startOffsetX: -11,
    startOffsetY: -24,
    startRadiusDelta: -12,
    driftAmp: 5.3,
    speed: 0.0007,
    phaseOffset: 0.9,
    baseOpacity: 0.42,
    strokeWidth: 1.1
  },
  {
    startOffsetX: 17,
    startOffsetY: -18,
    startRadiusDelta: 15,
    driftAmp: 5.9,
    speed: 0.00055,
    phaseOffset: 1.6,
    baseOpacity: 0.38,
    strokeWidth: 1.55
  },
  {
    startOffsetX: 29,
    startOffsetY: 6,
    startRadiusDelta: -9,
    driftAmp: 4.7,
    speed: 0.00066,
    phaseOffset: 2.1,
    baseOpacity: 0.47,
    strokeWidth: 1.25
  },
  {
    startOffsetX: 12,
    startOffsetY: 27,
    startRadiusDelta: 8,
    driftAmp: 5.6,
    speed: 0.00062,
    phaseOffset: 2.8,
    baseOpacity: 0.29,
    strokeWidth: 1.7
  },
  {
    startOffsetX: -21,
    startOffsetY: -7,
    startRadiusDelta: -15,
    driftAmp: 4.4,
    speed: 0.00078,
    phaseOffset: 3.4,
    baseOpacity: 0.36,
    strokeWidth: 1.2
  },
  {
    startOffsetX: 7,
    startOffsetY: 13,
    startRadiusDelta: 5,
    driftAmp: 3.8,
    speed: 0.00086,
    phaseOffset: 4,
    baseOpacity: 0.51,
    strokeWidth: 1.45
  },
  {
    startOffsetX: -15,
    startOffsetY: 9,
    startRadiusDelta: -4,
    driftAmp: 3.4,
    speed: 0.00093,
    phaseOffset: 4.7,
    baseOpacity: 0.33,
    strokeWidth: 1.35
  },
  {
    startOffsetX: 22,
    startOffsetY: -3,
    startRadiusDelta: 10,
    driftAmp: 4.2,
    speed: 0.00075,
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

function damp(current: number, target: number, smoothing: number, deltaSeconds: number) {
  const amount = 1 - Math.exp(-smoothing * deltaSeconds)
  return current + (target - current) * amount
}

function formatSvgNumber(value: number) {
  return value.toFixed(2)
}

function formatOpacity(value: number) {
  return clamp(value, 0, 1).toFixed(3)
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

function createConvergenceTarget({
  currentMs,
  sessionProgress,
  phase
}: BreathConvergenceProps): ConvergenceTarget {
  const phaseProfile = getPhaseProfile(phase)
  const playbackTime = Number.isFinite(currentMs) ? Math.max(currentMs, 0) / 1000 : 0

  return {
    macro: clamp01(sessionProgress),
    playbackTime,
    ...phaseProfile
  }
}

function createInitialState(target: ConvergenceTarget): AnimatedConvergenceState {
  return {
    localTime: 0,
    ...target
  }
}

function buildSmoothClosedPath(points: Point[]) {
  const first = points[0]
  let d = `M ${formatSvgNumber(first.x)} ${formatSvgNumber(first.y)}`

  points.forEach((point, index) => {
    const previous = points[(index - 1 + points.length) % points.length]
    const next = points[(index + 1) % points.length]
    const following = points[(index + 2) % points.length]
    const controlOne = {
      x: point.x + (next.x - previous.x) / 6,
      y: point.y + (next.y - previous.y) / 6
    }
    const controlTwo = {
      x: next.x - (following.x - point.x) / 6,
      y: next.y - (following.y - point.y) / 6
    }

    d += ` C ${formatSvgNumber(controlOne.x)} ${formatSvgNumber(controlOne.y)} ${formatSvgNumber(
      controlTwo.x
    )} ${formatSvgNumber(controlTwo.y)} ${formatSvgNumber(next.x)} ${formatSvgNumber(next.y)}`
  })

  return `${d} Z`
}

function buildOrganicRingPath({
  centerX,
  centerY,
  radius,
  liquidTime,
  chaos,
  phaseOffset,
  index
}: {
  centerX: number
  centerY: number
  radius: number
  liquidTime: number
  chaos: number
  phaseOffset: number
  index: number
}) {
  const points: Point[] = []
  const edgeAmp = 0.52 + chaos * 1.05
  const radialBreath = Math.sin(liquidTime * 0.33 + phaseOffset) * (0.22 + chaos * 0.18)

  for (let pointIndex = 0; pointIndex < RING_POINT_COUNT; pointIndex += 1) {
    const angle = (TWO_PI * pointIndex) / RING_POINT_COUNT
    const slowAngle =
      angle + Math.sin(angle * 2.0 + liquidTime * 0.12 + phaseOffset) * edgeAmp * 0.002
    const radialNoise =
      Math.sin(angle * 2 + liquidTime * 0.42 + phaseOffset) * 0.55 +
      Math.sin(angle * 3 - liquidTime * 0.31 + phaseOffset * 1.31) * 0.36 +
      Math.sin(angle * 5 + liquidTime * 0.17 + index * 0.73) * 0.2
    const liveRadius = radius + radialBreath + radialNoise * edgeAmp

    points.push({
      x: centerX + Math.cos(slowAngle) * liveRadius,
      y: centerY + Math.sin(slowAngle) * liveRadius
    })
  }

  return buildSmoothClosedPath(points)
}

function buildRenderState(state: AnimatedConvergenceState): ConvergenceRender {
  const macro = clamp01(state.macro)
  const baseConvergence = getHeldConvergenceProgress(macro)
  const convergence = Math.min(
    0.985,
    baseConvergence + state.coherenceBoost * (1 - baseConvergence)
  )
  const chaos = 1 - convergence
  const introMotion = 1 - easeOut(clamp01(macro / INTRO_MOTION_FRACTION))
  const flowTime = (state.localTime + state.playbackTime * PLAYBACK_TIME_BLEND) *
    (1.28 + introMotion * 0.54)

  return {
    traces: TRACE_BLUEPRINTS.map((trace, index) => {
      const t = flowTime * trace.speed * 920 + trace.phaseOffset
      const driftScale = (0.28 + chaos * 0.98 + introMotion * 0.42) * state.driftMultiplier
      const liveDrift = trace.driftAmp * driftScale
      const cx =
        SVG_CENTER +
        trace.startOffsetX * chaos +
        Math.cos(t) * liveDrift +
        Math.sin(flowTime * 0.14 + trace.phaseOffset) * (chaos + introMotion * 0.52) * 0.82
      const cy =
        SVG_CENTER +
        trace.startOffsetY * chaos +
        Math.sin(t * 1.07 + trace.phaseOffset) * liveDrift +
        Math.cos(flowTime * 0.12 + trace.phaseOffset * 1.4) * (chaos + introMotion * 0.52) * 0.82
      const radiusJitter = Math.sin(t * 0.73 + trace.phaseOffset) *
        (0.32 + chaos * 0.74 + introMotion * 0.36)
      const radius =
        BASE_RADIUS + trace.startRadiusDelta * chaos + state.sharedRadiusShift + radiusJitter
      const opacity = clamp(
        trace.baseOpacity + state.traceOpacityBoost + baseConvergence * 0.04,
        0.18,
        0.72
      )
      const liquidTime = flowTime * (0.92 + introMotion * 0.22 + index * 0.032) + trace.phaseOffset

      return {
        d: buildOrganicRingPath({
          centerX: cx,
          centerY: cy,
          radius,
          liquidTime,
          chaos,
          phaseOffset: trace.phaseOffset,
          index
        }),
        opacity
      }
    })
  }
}

function paintConvergence({
  traces,
  state
}: {
  traces: Array<SVGPathElement | null>
  state: AnimatedConvergenceState
}) {
  const render = buildRenderState(state)

  render.traces.forEach((trace, index) => {
    const path = traces[index]
    if (!path) return

    path.setAttribute("d", trace.d)
    path.setAttribute("stroke", `rgba(255,255,255,${formatOpacity(trace.opacity)})`)
  })
}

export function BreathConvergence({
  currentMs,
  sessionProgress,
  phase
}: BreathConvergenceProps) {
  const target = useMemo(
    () => createConvergenceTarget({ currentMs, sessionProgress, phase }),
    [currentMs, phase, sessionProgress]
  )
  const targetRef = useRef(target)
  const animatedRef = useRef<AnimatedConvergenceState>(createInitialState(target))
  const traceRefs = useRef<Array<SVGPathElement | null>>([])
  const traceRefCallbacks = useMemo(
    () =>
      TRACE_BLUEPRINTS.map(
        (_, index) => (element: SVGPathElement | null) => {
          traceRefs.current[index] = element
        }
      ),
    []
  )
  const initialRenderRef = useRef<ConvergenceRender | null>(null)
  const initialRender = initialRenderRef.current ?? buildRenderState(animatedRef.current)

  if (initialRenderRef.current === null) {
    initialRenderRef.current = initialRender
  }

  useEffect(() => {
    targetRef.current = target
  }, [target])

  useEffect(() => {
    let animationFrame = 0
    let lastFrameMs: number | null = null

    const tick = (now: number) => {
      const previousFrameMs = lastFrameMs ?? now
      const deltaMs = clamp(now - previousFrameMs, 0, MAX_FRAME_DELTA_MS)
      const deltaSeconds = deltaMs / 1000
      const animated = animatedRef.current
      const nextTarget = targetRef.current

      lastFrameMs = now
      animated.localTime += deltaSeconds
      animated.playbackTime = damp(animated.playbackTime, nextTarget.playbackTime, 0.9, deltaSeconds)
      animated.macro = damp(animated.macro, nextTarget.macro, 1.65, deltaSeconds)
      animated.sharedRadiusShift = damp(
        animated.sharedRadiusShift,
        nextTarget.sharedRadiusShift,
        4.8,
        deltaSeconds
      )
      animated.coherenceBoost = damp(
        animated.coherenceBoost,
        nextTarget.coherenceBoost,
        4.8,
        deltaSeconds
      )
      animated.driftMultiplier = damp(
        animated.driftMultiplier,
        nextTarget.driftMultiplier,
        4.8,
        deltaSeconds
      )
      animated.coreOpacity = damp(animated.coreOpacity, nextTarget.coreOpacity, 4.8, deltaSeconds)
      animated.traceOpacityBoost = damp(
        animated.traceOpacityBoost,
        nextTarget.traceOpacityBoost,
        4.8,
        deltaSeconds
      )

      paintConvergence({
        traces: traceRefs.current,
        state: animated
      })

      animationFrame = requestAnimationFrame(tick)
    }

    animationFrame = requestAnimationFrame(tick)

    return () => {
      cancelAnimationFrame(animationFrame)
      lastFrameMs = null
    }
  }, [])

  return (
    <div className="flex h-[19rem] w-[19rem] items-center justify-center">
      <svg viewBox="0 0 320 320" className="h-full w-full overflow-visible" aria-hidden="true">
        {initialRender.traces.map((trace, index) => (
          <path
            key={index}
            ref={traceRefCallbacks[index]}
            d={trace.d}
            fill="none"
            stroke={`rgba(255,255,255,${formatOpacity(trace.opacity)})`}
            strokeWidth={TRACE_BLUEPRINTS[index].strokeWidth}
            strokeLinecap="round"
            strokeLinejoin="round"
            vectorEffect="non-scaling-stroke"
          />
        ))}
      </svg>
    </div>
  )
}
