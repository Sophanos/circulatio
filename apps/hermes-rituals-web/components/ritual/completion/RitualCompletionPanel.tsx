"use client"

import { useMemo, useState } from "react"
import { Check } from "lucide-react"
import { AnimatePresence, motion } from "motion/react"

import {
  BodyPicker,
  type BodyCompletionStatus,
  type BodyMapMode,
  type BodyStateDraft
} from "@/components/ritual/BodyPicker"
import { BODY_FADE, BODY_MICRO_SPRING, BODY_SPRING } from "@/components/ritual/body/BodyChip"
import { cleanBodyDraft } from "@/components/ritual/body/body-capture-model"
import { cn } from "@/lib/utils"

export type RitualCompletionSubmitPayload = {
  includeBodyState: boolean
  reflectionText?: string
  practiceFeedback?: {
    feedback: "helpful"
    note: string
  }
}

export function RitualCompletionPanel({
  bodyDraft,
  onBodyDraftChange,
  completionPrompt,
  completionStatus = "idle",
  submitError,
  endpointAvailable = true,
  disabled,
  mapMode = "compact2d",
  captureReflection = true,
  capturePracticeFeedback = true,
  onSubmit,
  testId = "ritual-completion-panel"
}: {
  bodyDraft: BodyStateDraft
  onBodyDraftChange: (value: BodyStateDraft) => void
  completionPrompt?: string
  completionStatus?: BodyCompletionStatus
  submitError?: string | null
  endpointAvailable?: boolean
  disabled?: boolean
  mapMode?: BodyMapMode
  captureReflection?: boolean
  capturePracticeFeedback?: boolean
  onSubmit: (payload: RitualCompletionSubmitPayload) => void
  testId?: string
}) {
  const [reflectionOpen, setReflectionOpen] = useState(false)
  const [practiceOpen, setPracticeOpen] = useState(false)
  const [reflectionText, setReflectionText] = useState("")
  const [practiceNote, setPracticeNote] = useState("")
  const cleanedBody = useMemo(() => cleanBodyDraft(bodyDraft), [bodyDraft])
  const isSaved = completionStatus === "saved"
  const isSubmitting = completionStatus === "submitting"
  const isDisabled = disabled || isSaved || isSubmitting
  const includeBodyState = Boolean(cleanedBody.sensation)
  const trimmedReflection = reflectionText.trim()
  const trimmedPracticeNote = practiceNote.trim()
  const buttonLabel = isSubmitting
    ? "Saving"
    : isSaved
      ? "Held"
      : includeBodyState
        ? "Hold body note"
        : "Complete ritual"
  const canSubmit = endpointAvailable && !isDisabled

  return (
    <motion.div
      data-testid={testId}
      className="flex h-full min-h-0 flex-col gap-4"
      layout
      transition={BODY_SPRING}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="text-[10px] font-medium uppercase tracking-[0.16em] text-silver-500">
            Completion
          </p>
          <h3 className="mt-1 text-lg font-medium text-silver-100">
            {completionPrompt ?? "What should be held from here?"}
          </h3>
          <p className="mt-2 text-sm leading-6 text-silver-500">
            Finish quietly, with words or body detail only if you want them saved.
          </p>
        </div>
        <AnimatePresence>
          {isSaved ? (
            <motion.div
              className="flex size-8 shrink-0 items-center justify-center rounded-full bg-white/15 text-silver-50"
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              transition={BODY_MICRO_SPRING}
            >
              <Check className="size-4" />
            </motion.div>
          ) : null}
        </AnimatePresence>
      </div>

      <div className="rounded-[1.45rem] border border-white/10 bg-black/25 p-3 backdrop-blur-xl">
        <BodyPicker
          value={bodyDraft}
          onChange={onBodyDraftChange}
          variant="rail"
          completionPrompt="Body detail"
          completionStatus={completionStatus}
          submitError={submitError}
          endpointAvailable={endpointAvailable}
          disabled={isDisabled}
          mapMode={mapMode}
          showVoiceNote={false}
          onSubmit={undefined}
        />
      </div>

      <div className="grid gap-2 sm:grid-cols-2">
        {captureReflection ? (
          <button
            type="button"
            disabled={isDisabled}
            onClick={() => setReflectionOpen((open) => !open)}
            className={cn(
              "h-10 rounded-full border px-4 text-sm font-medium",
              reflectionOpen || trimmedReflection
                ? "border-white/15 bg-white/15 text-silver-50"
                : "border-white/10 bg-white/[0.04] text-silver-300",
              isDisabled ? "pointer-events-none opacity-40" : ""
            )}
          >
            Words
          </button>
        ) : null}
        {capturePracticeFeedback ? (
          <button
            type="button"
            disabled={isDisabled}
            onClick={() => setPracticeOpen((open) => !open)}
            className={cn(
              "h-10 rounded-full border px-4 text-sm font-medium",
              practiceOpen || trimmedPracticeNote
                ? "border-white/15 bg-white/15 text-silver-50"
                : "border-white/10 bg-white/[0.04] text-silver-300",
              isDisabled ? "pointer-events-none opacity-40" : ""
            )}
          >
            Practice note
          </button>
        ) : null}
      </div>

      <AnimatePresence initial={false}>
        {reflectionOpen ? (
          <motion.label
            key="reflection-text"
            className="flex flex-col gap-2"
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={BODY_FADE}
          >
            <span className="text-[10px] font-medium uppercase tracking-[0.14em] text-silver-500">
              Words
            </span>
            <textarea
              value={reflectionText}
              disabled={isDisabled}
              onChange={(event) => setReflectionText(event.target.value)}
              rows={3}
              className="min-h-24 resize-none rounded-2xl border border-white/10 bg-black/25 px-3 py-3 text-sm leading-6 text-silver-100 outline-none placeholder:text-silver-600 focus:border-white/20 disabled:opacity-50"
              placeholder="A few words from the closing"
            />
          </motion.label>
        ) : null}
        {practiceOpen ? (
          <motion.label
            key="practice-note"
            className="flex flex-col gap-2"
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={BODY_FADE}
          >
            <span className="text-[10px] font-medium uppercase tracking-[0.14em] text-silver-500">
              Practice note
            </span>
            <textarea
              value={practiceNote}
              disabled={isDisabled}
              onChange={(event) => setPracticeNote(event.target.value)}
              rows={3}
              className="min-h-24 resize-none rounded-2xl border border-white/10 bg-black/25 px-3 py-3 text-sm leading-6 text-silver-100 outline-none placeholder:text-silver-600 focus:border-white/20 disabled:opacity-50"
              placeholder="What helped or did not help"
            />
          </motion.label>
        ) : null}
      </AnimatePresence>

      <div className="space-y-3 border-t border-white/8 pt-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <motion.button
            type="button"
            data-testid="ritual-completion-submit"
            disabled={!canSubmit}
            onClick={() =>
              onSubmit({
                includeBodyState,
                reflectionText: trimmedReflection || undefined,
                practiceFeedback: trimmedPracticeNote
                  ? { feedback: "helpful", note: trimmedPracticeNote }
                  : undefined
              })
            }
            className="inline-flex h-11 items-center gap-2 rounded-full border border-white/15 bg-white/10 px-5 text-sm font-medium text-silver-50 backdrop-blur-xl disabled:pointer-events-none disabled:opacity-40"
            whileHover={!canSubmit ? undefined : { scale: 1.02 }}
            whileTap={!canSubmit ? undefined : { scale: 0.98 }}
            transition={BODY_MICRO_SPRING}
          >
            {isSaved ? <Check className="size-4" /> : null}
            <span>{buttonLabel}</span>
          </motion.button>

          {isSaved ? (
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
    </motion.div>
  )
}
