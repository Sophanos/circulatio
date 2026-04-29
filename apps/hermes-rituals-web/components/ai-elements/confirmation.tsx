"use client"

import { type ReactNode } from "react"
import { Check, X } from "lucide-react"
import { motion } from "motion/react"

import { MICRO_SPRING } from "@/components/ritual/motion"
import { cn } from "@/lib/utils"

export function Confirmation({
  children,
  approveLabel = "Approve",
  rejectLabel = "Reject",
  approveTestId,
  rejectTestId,
  disabled,
  onApprove,
  onReject
}: {
  children?: ReactNode
  approveLabel?: string
  rejectLabel?: string
  approveTestId?: string
  rejectTestId?: string
  disabled?: boolean
  onApprove: () => void
  onReject: () => void
}) {
  return (
    <div className="flex flex-col gap-3">
      {children}
      <div className="flex flex-wrap items-center gap-2">
        <ConfirmationButton
          tone="approve"
          testId={approveTestId}
          disabled={disabled}
          onClick={onApprove}
        >
          <Check className="size-4" />
          <span>{approveLabel}</span>
        </ConfirmationButton>
        <ConfirmationButton
          tone="reject"
          testId={rejectTestId}
          disabled={disabled}
          onClick={onReject}
        >
          <X className="size-4" />
          <span>{rejectLabel}</span>
        </ConfirmationButton>
      </div>
    </div>
  )
}

function ConfirmationButton({
  tone,
  testId,
  disabled,
  onClick,
  children
}: {
  tone: "approve" | "reject"
  testId?: string
  disabled?: boolean
  onClick: () => void
  children: ReactNode
}) {
  return (
    <motion.button
      type="button"
      data-testid={testId}
      disabled={disabled}
      onClick={onClick}
      className={cn(
        "inline-flex h-9 items-center gap-2 rounded-full px-3 text-xs font-semibold disabled:pointer-events-none disabled:opacity-40",
        tone === "approve"
          ? "bg-white text-graphite-950"
          : "border border-white/10 bg-white/[0.06] text-silver-200"
      )}
      whileHover={disabled ? undefined : { scale: 1.03 }}
      whileTap={disabled ? undefined : { scale: 0.97 }}
      transition={MICRO_SPRING}
    >
      {children}
    </motion.button>
  )
}
