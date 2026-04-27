"use client"

import { Check } from "lucide-react"
import { AnimatePresence, motion } from "motion/react"

import { BODY_FADE, BODY_MICRO_SPRING } from "@/components/ritual/body/BodyChip"
import type { BodyCompletionStatus } from "@/components/ritual/body/body-capture-model"

export function BodySubmitControls({
  canSubmit,
  completionStatus,
  submitError,
  endpointAvailable,
  disabled,
  onSubmit
}: {
  canSubmit: boolean
  completionStatus: BodyCompletionStatus
  submitError?: string | null
  endpointAvailable: boolean
  disabled?: boolean
  onSubmit?: () => void
}) {
  if (!onSubmit) return null

  const buttonDisabled = !canSubmit || completionStatus === "submitting" || completionStatus === "saved"

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <motion.button
          type="button"
          disabled={buttonDisabled || disabled}
          onClick={onSubmit}
          className="h-11 rounded-full border border-white/15 bg-white/10 px-5 text-sm font-medium text-silver-50 backdrop-blur-xl disabled:pointer-events-none disabled:opacity-40"
          whileHover={buttonDisabled || disabled ? undefined : { scale: 1.02 }}
          whileTap={buttonDisabled || disabled ? undefined : { scale: 0.98 }}
          transition={BODY_MICRO_SPRING}
        >
          {completionStatus === "submitting"
            ? "Saving"
            : completionStatus === "saved"
              ? "Held"
              : "Hold body note"}
        </motion.button>

        {completionStatus === "saved" ? (
          <div className="flex items-center gap-2 text-sm font-medium text-silver-200">
            <span className="flex size-7 items-center justify-center rounded-full bg-white/15">
              <Check className="size-4" />
            </span>
            Held with the ritual.
          </div>
        ) : null}
      </div>

      <AnimatePresence>
        {completionStatus === "error" || !endpointAvailable ? (
          <motion.p
            className="text-xs leading-5 text-silver-500"
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={BODY_FADE}
          >
            {submitError ?? "Completion sync is not available for this artifact."}
          </motion.p>
        ) : null}
      </AnimatePresence>
    </div>
  )
}
