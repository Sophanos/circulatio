"use client"

import { ShieldCheck } from "lucide-react"

import { Confirmation } from "@/components/ai-elements/confirmation"
import { Tool } from "@/components/ai-elements/tool"
import type { RitualCompanionAction } from "@/lib/ritual-guidance-contract"

function sourceSummary(action: RitualCompanionAction) {
  if (action.sourceRefs.length === 0) return "Ritual frame"
  return action.sourceRefs
    .slice(0, 2)
    .map((source) => source.label ?? source.recordId ?? source.sourceType)
    .join(" + ")
}

function actionLabel(type: RitualCompanionAction["type"]) {
  switch (type) {
    case "store_body_state":
      return "Body state"
    case "store_reflection":
      return "Reflection"
    case "record_practice_outcome":
      return "Practice outcome"
    case "active_imagination_capture":
      return "Active imagination"
  }
}

function persistenceLabel(action: RitualCompanionAction) {
  switch (action.type) {
    case "store_body_state":
      return "Saves body detail"
    case "store_reflection":
      return "Saves your words"
    case "record_practice_outcome":
      return "Saves practice feedback"
    case "active_imagination_capture":
      return "Saves imaginal note"
  }
}

function approvalLabel(action: RitualCompanionAction) {
  if (action.error) return action.error
  switch (action.approvalState) {
    case "proposed":
      return "Awaiting approval"
    case "approved":
      return "Approved"
    case "rejected":
      return "Rejected"
    case "executing":
      return "Sending to Hermes"
    case "executed":
      return "Recorded by Hermes"
    case "failed":
      return "Approval failed"
  }
}

export function RitualCompanionActionCard({
  action,
  onApprove,
  onReject
}: {
  action: RitualCompanionAction
  onApprove: (action: RitualCompanionAction) => void
  onReject: (action: RitualCompanionAction) => void
}) {
  const final =
    action.approvalState === "executed" ||
    action.approvalState === "rejected" ||
    action.rejectionFinal
  const busy = action.approvalState === "executing"

  return (
    <Tool title={actionLabel(action.type)}>
      <div className="flex flex-col gap-3">
        <div className="flex items-start gap-3 text-sm leading-6 text-silver-200">
          <span className="mt-1 flex size-7 shrink-0 items-center justify-center rounded-full bg-white/10 text-silver-100">
            <ShieldCheck className="size-4" />
          </span>
          <p className="min-w-0 flex-1 whitespace-pre-wrap break-words">{action.previewText}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-[11px] text-silver-500">
          <span className="rounded-full bg-white/[0.06] px-2 py-1">{sourceSummary(action)}</span>
          <span className="rounded-full bg-white/[0.06] px-2 py-1">
            {persistenceLabel(action)}
          </span>
          <span className="rounded-full bg-white/[0.06] px-2 py-1">
            {approvalLabel(action)}
          </span>
        </div>
        {final ? null : (
          <Confirmation
            approveLabel={busy ? "Sending" : "Approve"}
            rejectLabel="Reject"
            disabled={busy}
            onApprove={() => onApprove(action)}
            onReject={() => onReject(action)}
          />
        )}
      </div>
    </Tool>
  )
}
