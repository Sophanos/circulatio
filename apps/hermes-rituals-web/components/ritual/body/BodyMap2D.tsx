"use client"

import { useState } from "react"
import { motion } from "motion/react"

import { BODY_MICRO_SPRING, BODY_SPRING } from "@/components/ritual/body/BodyChip"
import {
  REGION_LABELS,
  type BodyActivation,
  type BodyRegionId,
  type BodyView
} from "@/components/ritual/body/body-capture-model"
import { cn } from "@/lib/utils"

const SILHOUETTE_PATH =
  "M160 20 C136 20 121 39 122 63 C123 83 135 97 147 105 C145 118 144 129 143 139 C120 142 95 149 76 161 C56 174 49 202 43 232 L28 337 C24 365 39 389 62 371 C76 360 79 318 85 278 C91 239 96 215 108 205 C113 226 116 250 114 274 C111 304 108 323 113 346 C118 372 128 393 135 413 L130 493 C129 515 153 518 156 497 L160 430 L164 497 C167 518 191 515 190 493 L185 413 C192 393 202 372 207 346 C212 323 209 304 206 274 C204 250 207 226 212 205 C224 215 229 239 235 278 C241 318 244 360 258 371 C281 389 296 365 292 337 L277 232 C271 202 264 174 244 161 C225 149 200 142 177 139 C176 129 175 118 173 105 C185 97 197 83 198 63 C199 39 184 20 160 20 Z"

const BACK_FIELD_PATH =
  "M112 168 C128 145 192 145 208 168 C225 193 220 228 194 248 C176 262 144 262 126 248 C100 228 95 193 112 168 Z M118 250 C132 232 188 232 202 250 C217 271 211 303 190 318 C174 330 146 330 130 318 C109 303 103 271 118 250 Z"

const FRONT_FIELD_PATH =
  "M110 168 C126 146 194 146 210 168 C226 190 220 222 194 237 C175 248 145 248 126 237 C100 222 94 190 110 168 Z M117 238 C132 220 188 220 203 238 C217 255 211 286 190 300 C174 311 146 311 130 300 C109 286 103 255 117 238 Z"

type RegionPath = Partial<Record<BodyView, string>>

const REGION_PATHS: Partial<Record<BodyRegionId, RegionPath>> = {
  head_face: {
    front: "M160 27 C139 27 128 43 129 63 C130 82 142 96 160 96 C178 96 190 82 191 63 C192 43 181 27 160 27 Z",
    back: "M160 27 C139 27 128 43 129 63 C130 82 142 96 160 96 C178 96 190 82 191 63 C192 43 181 27 160 27 Z"
  },
  jaw_throat: {
    front: "M136 89 C150 104 170 104 184 89 C183 116 176 136 160 137 C144 136 137 116 136 89 Z"
  },
  neck: {
    front: "M143 104 C154 113 166 113 177 104 C178 129 174 147 160 148 C146 147 142 129 143 104 Z",
    back: "M143 104 C154 113 166 113 177 104 C178 129 174 147 160 148 C146 147 142 129 143 104 Z"
  },
  shoulders: {
    front: "M76 161 C102 143 133 139 160 139 C187 139 218 143 244 161 C234 183 197 194 160 194 C123 194 86 183 76 161 Z",
    back: "M76 161 C102 143 133 139 160 139 C187 139 218 143 244 161 C234 183 197 194 160 194 C123 194 86 183 76 161 Z"
  },
  chest: {
    front: "M112 169 C128 148 192 148 208 169 C224 190 218 221 193 237 C174 249 146 249 127 237 C102 221 96 190 112 169 Z"
  },
  upper_back: {
    back: "M112 169 C128 148 192 148 208 169 C224 190 218 226 192 249 C174 264 146 264 128 249 C102 226 96 190 112 169 Z"
  },
  belly: {
    front: "M118 238 C132 220 188 220 202 238 C217 257 211 288 190 302 C174 313 146 313 130 302 C109 288 103 257 118 238 Z"
  },
  lower_back: {
    back: "M119 249 C133 231 187 231 201 249 C216 269 211 303 190 320 C173 333 147 333 130 320 C109 303 104 269 119 249 Z"
  },
  pelvis: {
    front: "M113 306 C129 288 191 288 207 306 C219 320 212 346 190 360 C173 371 147 371 130 360 C108 346 101 320 113 306 Z",
    back: "M113 306 C129 288 191 288 207 306 C219 320 212 346 190 360 C173 371 147 371 130 360 C108 346 101 320 113 306 Z"
  },
  left_arm: {
    front: "M86 193 C100 195 108 206 106 222 L83 352 C80 371 59 375 53 357 L72 239 C76 213 78 199 86 193 Z",
    back: "M86 193 C100 195 108 206 106 222 L83 352 C80 371 59 375 53 357 L72 239 C76 213 78 199 86 193 Z"
  },
  right_arm: {
    front: "M234 193 C220 195 212 206 214 222 L237 352 C240 371 261 375 267 357 L248 239 C244 213 242 199 234 193 Z",
    back: "M234 193 C220 195 212 206 214 222 L237 352 C240 371 261 375 267 357 L248 239 C244 213 242 199 234 193 Z"
  },
  left_hand: {
    front: "M60 334 C75 329 89 338 90 354 C91 369 78 381 63 378 C48 374 42 355 50 344 C53 340 56 337 60 334 Z",
    back: "M60 334 C75 329 89 338 90 354 C91 369 78 381 63 378 C48 374 42 355 50 344 C53 340 56 337 60 334 Z"
  },
  right_hand: {
    front: "M260 334 C245 329 231 338 230 354 C229 369 242 381 257 378 C272 374 278 355 270 344 C267 340 264 337 260 334 Z",
    back: "M260 334 C245 329 231 338 230 354 C229 369 242 381 257 378 C272 374 278 355 270 344 C267 340 264 337 260 334 Z"
  },
  left_leg: {
    front: "M135 358 C146 351 158 358 158 373 L154 493 C153 513 130 512 130 492 L134 414 C124 391 124 369 135 358 Z",
    back: "M135 358 C146 351 158 358 158 373 L154 493 C153 513 130 512 130 492 L134 414 C124 391 124 369 135 358 Z"
  },
  right_leg: {
    front: "M185 358 C174 351 162 358 162 373 L166 493 C167 513 190 512 190 492 L186 414 C196 391 196 369 185 358 Z",
    back: "M185 358 C174 351 162 358 162 373 L166 493 C167 513 190 512 190 492 L186 414 C196 391 196 369 185 358 Z"
  },
  left_foot: {
    front: "M129 484 C140 480 154 482 158 493 C162 506 149 515 132 512 C120 510 115 499 122 491 C124 488 126 486 129 484 Z",
    back: "M129 484 C140 480 154 482 158 493 C162 506 149 515 132 512 C120 510 115 499 122 491 C124 488 126 486 129 484 Z"
  },
  right_foot: {
    front: "M191 484 C180 480 166 482 162 493 C158 506 171 515 188 512 C200 510 205 499 198 491 C196 488 194 486 191 484 Z",
    back: "M191 484 C180 480 166 482 162 493 C158 506 171 515 188 512 C200 510 205 499 198 491 C196 488 194 486 191 484 Z"
  }
}

type HitZone = {
  id: BodyRegionId
  views: BodyView[]
  left: number
  top: number
  width: number
  height: number
  radius?: string
}

const HIT_ZONES: HitZone[] = [
  { id: "head_face", views: ["front", "back"], left: 42, top: 4, width: 16, height: 16, radius: "999px" },
  { id: "jaw_throat", views: ["front"], left: 39, top: 17, width: 22, height: 10, radius: "18px" },
  { id: "neck", views: ["front", "back"], left: 43, top: 22, width: 14, height: 11, radius: "16px" },
  { id: "shoulders", views: ["front", "back"], left: 22, top: 28, width: 56, height: 13, radius: "999px" },
  { id: "chest", views: ["front"], left: 31, top: 38, width: 38, height: 16, radius: "24px" },
  { id: "upper_back", views: ["back"], left: 30, top: 37, width: 40, height: 20, radius: "24px" },
  { id: "belly", views: ["front"], left: 33, top: 53, width: 34, height: 15, radius: "24px" },
  { id: "lower_back", views: ["back"], left: 33, top: 54, width: 34, height: 17, radius: "22px" },
  { id: "pelvis", views: ["front", "back"], left: 32, top: 67, width: 36, height: 14, radius: "22px" },
  { id: "left_arm", views: ["front", "back"], left: 17, top: 39, width: 17, height: 32, radius: "22px" },
  { id: "right_arm", views: ["front", "back"], left: 66, top: 39, width: 17, height: 32, radius: "22px" },
  { id: "left_hand", views: ["front", "back"], left: 12, top: 68, width: 17, height: 12, radius: "999px" },
  { id: "right_hand", views: ["front", "back"], left: 71, top: 68, width: 17, height: 12, radius: "999px" },
  { id: "left_leg", views: ["front", "back"], left: 34, top: 77, width: 15, height: 18, radius: "18px" },
  { id: "right_leg", views: ["front", "back"], left: 51, top: 77, width: 15, height: 18, radius: "18px" },
  { id: "left_foot", views: ["front", "back"], left: 28, top: 93, width: 21, height: 7, radius: "999px" },
  { id: "right_foot", views: ["front", "back"], left: 51, top: 93, width: 21, height: 7, radius: "999px" }
]

const ACTIVATION_OPACITY: Record<BodyActivation, number> = {
  low: 0.24,
  moderate: 0.32,
  high: 0.4,
  overwhelming: 0.48
}

export function BodyMap2D({
  selectedRegion,
  activation,
  disabled,
  compact,
  view,
  onRegionSelect,
  onViewChange
}: {
  selectedRegion?: BodyRegionId
  activation?: BodyActivation
  disabled?: boolean
  compact?: boolean
  view: BodyView
  onRegionSelect: (region: BodyRegionId) => void
  onViewChange: (view: BodyView) => void
}) {
  const [hoveredRegion, setHoveredRegion] = useState<BodyRegionId | undefined>()
  const activeRegion = hoveredRegion ?? selectedRegion
  const highlightPath = activeRegion ? REGION_PATHS[activeRegion]?.[view] : undefined
  const wholeBody = selectedRegion === "whole_body"
  const unclear = selectedRegion === "unclear"
  const label = hoveredRegion
    ? REGION_LABELS[hoveredRegion]
    : selectedRegion
      ? REGION_LABELS[selectedRegion]
      : "Tap the area that noticed it"
  const highlightOpacity = activation ? ACTIVATION_OPACITY[activation] : 0.34

  return (
    <motion.div
      className={cn(
        "relative overflow-hidden rounded-[1.75rem] border border-white/10 bg-black/25 backdrop-blur-xl",
        compact ? "h-[15.5rem]" : "h-[min(54dvh,34rem)] min-h-[21rem]"
      )}
      layout
      transition={BODY_SPRING}
    >
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(255,255,255,0.12),transparent_58%)]" />
      <div className="absolute inset-x-4 top-4 z-20 flex items-center justify-between gap-3">
        <button
          type="button"
          disabled={disabled}
          onClick={() => onViewChange(view === "front" ? "back" : "front")}
          aria-label={`Show ${view === "front" ? "back" : "front"} body view`}
          aria-pressed={view === "back"}
          className="rounded-full bg-black/45 px-4 py-2 text-[10px] font-medium uppercase tracking-[0.22em] text-silver-200 backdrop-blur-xl disabled:pointer-events-none disabled:opacity-40"
        >
          {view === "front" ? "Front" : "Back"}
        </button>
        {!compact ? (
          <span className="rounded-full bg-black/30 px-4 py-2 text-[10px] font-medium uppercase tracking-[0.22em] text-silver-500 backdrop-blur-xl">
            Tap an area
          </span>
        ) : null}
      </div>

      <svg
        viewBox="0 0 320 520"
        className={cn(
          "pointer-events-none absolute inset-0 z-10 h-full w-full transition-opacity",
          unclear && "opacity-45 blur-[1px]"
        )}
        aria-hidden="true"
        preserveAspectRatio="xMidYMid meet"
      >
        <defs>
          <linearGradient id={`body-surface-${view}`} x1="0" x2="1" y1="0" y2="1">
            <stop offset="0%" stopColor="rgba(255,255,255,0.42)" />
            <stop offset="46%" stopColor="rgba(255,255,255,0.18)" />
            <stop offset="100%" stopColor="rgba(255,255,255,0.34)" />
          </linearGradient>
          <radialGradient id={`body-inner-light-${view}`} cx="50%" cy="43%" r="58%">
            <stop offset="0%" stopColor="rgba(255,255,255,0.34)" />
            <stop offset="58%" stopColor="rgba(255,255,255,0.08)" />
            <stop offset="100%" stopColor="rgba(255,255,255,0)" />
          </radialGradient>
          <filter id={`body-soft-glow-${view}`} x="-40%" y="-40%" width="180%" height="180%">
            <feGaussianBlur stdDeviation="10" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        <motion.g
          key={view}
          initial={{ opacity: 0, scale: 0.985 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={BODY_MICRO_SPRING}
          style={{ transformOrigin: "160px 260px" }}
        >
          <path
            d={SILHOUETTE_PATH}
            fill={`url(#body-surface-${view})`}
            opacity="0.48"
            filter={`url(#body-soft-glow-${view})`}
          />
          <path d={SILHOUETTE_PATH} fill={`url(#body-inner-light-${view})`} opacity="0.48" />
          <path
            d={view === "back" ? BACK_FIELD_PATH : FRONT_FIELD_PATH}
            fill="rgba(255,255,255,0.12)"
            opacity="0.75"
          />
          {wholeBody ? (
            <motion.path
              d={SILHOUETTE_PATH}
              fill="rgba(255,255,255,0.24)"
              filter={`url(#body-soft-glow-${view})`}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={BODY_MICRO_SPRING}
            />
          ) : null}
          {highlightPath ? (
            <motion.path
              key={`${view}-${activeRegion}`}
              d={highlightPath}
              fill="rgba(255,255,255,0.78)"
              opacity={highlightOpacity}
              filter={`url(#body-soft-glow-${view})`}
              initial={{ opacity: 0 }}
              animate={{ opacity: highlightOpacity }}
              transition={BODY_MICRO_SPRING}
            />
          ) : null}
        </motion.g>
      </svg>

      {HIT_ZONES.filter((zone) => zone.views.includes(view)).map((zone) => (
        <button
          key={`${view}-${zone.id}`}
          type="button"
          aria-label={`Choose ${REGION_LABELS[zone.id]}`}
          aria-pressed={selectedRegion === zone.id}
          disabled={disabled}
          onMouseEnter={() => setHoveredRegion(zone.id)}
          onMouseLeave={() => setHoveredRegion(undefined)}
          onFocus={() => setHoveredRegion(zone.id)}
          onBlur={() => setHoveredRegion(undefined)}
          onClick={() => onRegionSelect(zone.id)}
          className={cn(
            "group absolute z-30 outline-none disabled:pointer-events-none",
            "focus-visible:ring-2 focus-visible:ring-white/35",
            selectedRegion === zone.id
              ? "bg-white/10 ring-1 ring-white/30"
              : "bg-white/0 hover:bg-white/[0.055] hover:ring-1 hover:ring-white/18"
          )}
          style={{
            left: `${zone.left}%`,
            top: `${zone.top}%`,
            width: `${zone.width}%`,
            height: `${zone.height}%`,
            borderRadius: zone.radius ?? "24px"
          }}
        >
          <span
            className={cn(
              "absolute left-1/2 top-1/2 size-1.5 -translate-x-1/2 -translate-y-1/2 rounded-full transition",
              selectedRegion === zone.id
                ? "bg-white/80 shadow-[0_0_14px_rgba(255,255,255,0.45)]"
                : "bg-white/22 opacity-60 group-hover:bg-white/55 group-hover:opacity-100 group-focus-visible:bg-white/70 group-focus-visible:opacity-100"
            )}
          />
        </button>
      ))}

      <div className="pointer-events-none absolute inset-x-4 bottom-4 z-20 flex justify-center">
        <span className="max-w-full truncate rounded-full bg-black/45 px-4 py-2 text-xs font-medium text-silver-100 backdrop-blur-xl">
          {label}
        </span>
      </div>
    </motion.div>
  )
}
