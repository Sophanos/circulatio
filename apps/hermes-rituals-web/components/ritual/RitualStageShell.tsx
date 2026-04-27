"use client"

import { motion } from "motion/react"

const SPRING = { type: "spring" as const, stiffness: 300, damping: 30, mass: 0.8 }

type RitualStageShellProps = {
  immersive?: boolean
  isPlaying?: boolean
  header?: React.ReactNode
  footer?: React.ReactNode
  children: React.ReactNode
}

export function RitualStageShell({
  immersive,
  isPlaying,
  header,
  footer,
  children
}: RitualStageShellProps) {
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
        <div className="flex flex-1 items-center justify-center">{children}</div>

        <motion.div
          className="flex flex-col items-center pb-8 text-center gap-1"
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: isPlaying ? 1 : 0.72, y: 0 }}
          transition={{ delay: 0.3, ...SPRING }}
        >
          {footer}
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
        {header && (
          <div className="flex items-start justify-between gap-4">{header}</div>
        )}

        <div className="flex flex-1 items-center justify-center px-4 py-4">
          {children}
        </div>

        {footer && (
          <div className="flex flex-col items-center text-center gap-1">
            {footer}
          </div>
        )}
      </div>
    </motion.div>
  )
}
