"use client"

import { motion } from "motion/react"
import type { ReactNode } from "react"

import { cn } from "@/lib/utils"

export const BODY_SPRING = { type: "spring" as const, stiffness: 300, damping: 30, mass: 0.8 }
export const BODY_MICRO_SPRING = {
  type: "spring" as const,
  stiffness: 450,
  damping: 28,
  mass: 0.5
}
export const BODY_FADE = { duration: 0.15, delay: 0.04 }

export function BodyChip({
  active,
  children,
  onClick,
  disabled,
  className,
  ariaLabel
}: {
  active: boolean
  children: ReactNode
  onClick: () => void
  disabled?: boolean
  className?: string
  ariaLabel?: string
}) {
  return (
    <motion.button
      type="button"
      aria-label={ariaLabel}
      disabled={disabled}
      className={cn(
        "rounded-full border px-3 py-2 text-xs font-medium backdrop-blur-xl disabled:pointer-events-none disabled:opacity-40",
        active
          ? "border-white/30 bg-white/15 text-silver-50"
          : "border-white/10 bg-white/[0.045] text-silver-400 hover:border-white/18 hover:bg-white/[0.07] hover:text-silver-200",
        className
      )}
      whileHover={disabled ? undefined : { scale: 1.02 }}
      whileTap={disabled ? undefined : { scale: 0.98 }}
      transition={BODY_MICRO_SPRING}
      onClick={onClick}
    >
      {children}
    </motion.button>
  )
}
