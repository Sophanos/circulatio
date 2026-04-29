"use client"

import { useMemo, useState } from "react"
import { Check } from "lucide-react"
import { AnimatePresence, motion } from "motion/react"

import { BodyActivationControls } from "@/components/ritual/body/BodyActivationControls"
import { BodyMap2D } from "@/components/ritual/body/BodyMap2D"
import { BodyMapFallback } from "@/components/ritual/body/BodyMapFallback"
import { BodyNoteControls } from "@/components/ritual/body/BodyNoteControls"
import { BodyRegionSummary } from "@/components/ritual/body/BodyRegionSummary"
import { BodySensationControls } from "@/components/ritual/body/BodySensationControls"
import { BodySubmitControls } from "@/components/ritual/body/BodySubmitControls"
import { BodyToneControls } from "@/components/ritual/body/BodyToneControls"
import { BODY_FADE, BODY_MICRO_SPRING, BODY_SPRING } from "@/components/ritual/body/BodyChip"
import {
  DEFAULT_REGION_VIEW,
  cleanBodyDraft,
  type BodyActivation,
  type BodyCompletionStatus,
  type BodyMapMode,
  type BodyRegionId,
  type BodyStateDraft,
  type BodyView
} from "@/components/ritual/body/body-capture-model"
import { cn } from "@/lib/utils"

export type {
  BodyActivation,
  BodyCompletionStatus,
  BodyMapMode,
  BodyRegionId,
  BodyStateDraft
} from "@/components/ritual/body/body-capture-model"
export { EMPTY_BODY_STATE_DRAFT } from "@/components/ritual/body/body-capture-model"

export function BodyPicker({
  value,
  onChange,
  variant = "rail",
  completionPrompt,
  completionStatus = "idle",
  submitError,
  endpointAvailable = true,
  disabled,
  onSubmit,
  mapMode,
  showVoiceNote,
  showTypedNote
}: {
  value: BodyStateDraft
  onChange: (value: BodyStateDraft) => void
  variant?: "stage" | "rail"
  completionPrompt?: string
  completionStatus?: BodyCompletionStatus
  submitError?: string | null
  endpointAvailable?: boolean
  disabled?: boolean
  onSubmit?: () => void
  mapMode?: BodyMapMode
  showVoiceNote?: boolean
  showTypedNote?: boolean
}) {
  const [customSensation, setCustomSensation] = useState("")
  const [manualBodyView, setManualBodyView] = useState<BodyView>(() => {
    return (value.bodyRegion && DEFAULT_REGION_VIEW[value.bodyRegion]) || "front"
  })
  const [wordsOpen, setWordsOpen] = useState(false)
  const compact = variant === "stage"
  const resolvedMapMode = mapMode ?? (compact ? "full2d" : "compact2d")
  const cleaned = useMemo(() => cleanBodyDraft(value), [value])
  const isDisabled = disabled || completionStatus === "submitting" || completionStatus === "saved"
  const canSubmit = Boolean(cleaned.sensation) && endpointAvailable && !isDisabled
  const typedNoteVisible = showTypedNote ?? (!compact || wordsOpen || Boolean(value.noteText?.trim()))
  const voiceNoteVisible = showVoiceNote ?? !compact
  const preferredBodyView = value.bodyRegion ? DEFAULT_REGION_VIEW[value.bodyRegion] : undefined
  const bodyView = preferredBodyView ?? manualBodyView

  const update = (patch: Partial<BodyStateDraft>) => {
    onChange({ ...value, ...patch })
  }

  const chooseSensation = (sensation: string) => {
    update({ sensation })
    setCustomSensation("")
  }

  const chooseRegion = (bodyRegion: BodyRegionId) => {
    const preferredView = DEFAULT_REGION_VIEW[bodyRegion]
    if (preferredView) setManualBodyView(preferredView)
    update({ bodyRegion })
  }

  const mapSurface =
    resolvedMapMode === "summary" ? (
      <BodyRegionSummary
        selectedRegion={value.bodyRegion}
        view={bodyView}
        onViewChange={setManualBodyView}
        onRegionSelect={chooseRegion}
        disabled={isDisabled}
        compact={compact}
        surface="card"
      />
    ) : resolvedMapMode === "fallback" ? (
      <BodyMapFallback
        selectedRegion={value.bodyRegion}
        view={bodyView}
        onViewChange={setManualBodyView}
        onRegionSelect={chooseRegion}
        disabled={isDisabled}
        compact={compact}
      />
    ) : (
      <BodyMap2D
        selectedRegion={value.bodyRegion}
        activation={value.activation}
        disabled={isDisabled}
        compact={resolvedMapMode === "compact2d"}
        view={bodyView}
        onViewChange={setManualBodyView}
        onRegionSelect={chooseRegion}
      />
    )

  return (
    <motion.div
      data-testid="ritual-body-picker"
      data-body-picker-variant={variant}
      className={cn("flex h-full min-h-0 flex-col", compact ? "gap-4 p-4 md:p-5" : "gap-4")}
      layout
      transition={BODY_SPRING}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="text-[10px] font-medium uppercase tracking-[0.16em] text-silver-500">
            Body
          </p>
          <h3 className={cn("mt-1 font-medium text-silver-100", compact ? "text-sm" : "text-lg")}>
            {completionPrompt ?? "What did you notice in your body or attention?"}
          </h3>
        </div>
        <AnimatePresence>
          {completionStatus === "saved" ? (
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

      {mapSurface}

      <motion.div
        className={cn(
          "rounded-[1.45rem] border border-white/10 bg-black/25 backdrop-blur-xl",
          compact ? "space-y-4 p-3" : "space-y-5 p-4"
        )}
        layout
        transition={BODY_SPRING}
      >
        {resolvedMapMode !== "summary" ? (
          <BodyRegionSummary
            selectedRegion={value.bodyRegion}
            view={bodyView}
            onViewChange={setManualBodyView}
            onRegionSelect={chooseRegion}
            disabled={isDisabled}
            compact={compact}
          />
        ) : null}

        <BodySensationControls
          sensation={cleaned.sensation}
          customSensation={customSensation}
          onCustomSensationChange={setCustomSensation}
          onChoose={chooseSensation}
          disabled={isDisabled}
          compact={compact}
        />

        <BodyActivationControls
          activation={value.activation}
          onChoose={(activation) => update({ activation })}
          disabled={isDisabled}
          compact={compact}
        />

        {!compact ? (
          <BodyToneControls
            tone={value.tone}
            onChoose={(tone) => update({ tone })}
            disabled={isDisabled}
          />
        ) : null}

        {compact ? (
          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-white/8 pt-3">
            <button
              type="button"
              disabled={isDisabled}
              onClick={() => setWordsOpen((open) => !open)}
              className="rounded-full border border-white/10 bg-white/[0.045] px-3 py-2 text-xs font-medium text-silver-300 disabled:pointer-events-none disabled:opacity-40"
            >
              {wordsOpen || value.noteText ? "Hide words" : "Add words"}
            </button>
            {onSubmit ? (
              <BodySubmitControls
                canSubmit={canSubmit}
                completionStatus={completionStatus}
                submitError={submitError}
                endpointAvailable={endpointAvailable}
                disabled={disabled}
                onSubmit={onSubmit}
              />
            ) : (
              <span className="text-xs leading-5 text-silver-500">Save from the side panel.</span>
            )}
          </div>
        ) : null}

        <AnimatePresence initial={false}>
          {typedNoteVisible ? (
            <motion.div
              key="body-note-controls"
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -4 }}
              transition={BODY_FADE}
            >
              <BodyNoteControls
                noteText={value.noteText}
                onNoteChange={(noteText) => update({ noteText })}
                disabled={isDisabled}
                showVoiceNote={voiceNoteVisible}
                compact={compact}
              />
            </motion.div>
          ) : null}
        </AnimatePresence>

        {!compact ? (
          <BodySubmitControls
            canSubmit={canSubmit}
            completionStatus={completionStatus}
            submitError={submitError}
            endpointAvailable={endpointAvailable}
            disabled={disabled}
            onSubmit={onSubmit}
          />
        ) : null}

        <AnimatePresence>
          {compact && completionStatus === "error" ? (
            <motion.p
              className="text-xs leading-5 text-silver-500"
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -4 }}
              transition={BODY_FADE}
            >
              {submitError ?? "The body note was not held yet. You can retry in the rail."}
            </motion.p>
          ) : null}
        </AnimatePresence>
      </motion.div>
    </motion.div>
  )
}
