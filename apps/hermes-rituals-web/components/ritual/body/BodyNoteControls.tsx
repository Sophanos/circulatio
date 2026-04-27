"use client"

import { useCallback } from "react"

import { useVoiceTranscription } from "@/components/ritual/body/useVoiceTranscription"
import { VoiceButton } from "@/components/ui/voice-button"
import { appendBodyText } from "@/components/ritual/body/body-capture-model"
import { cn } from "@/lib/utils"

export function BodyNoteControls({
  noteText,
  onNoteChange,
  disabled,
  showVoiceNote = true,
  compact
}: {
  noteText?: string
  onNoteChange: (value: string) => void
  disabled?: boolean
  showVoiceNote?: boolean
  compact?: boolean
}) {
  const handleVoiceText = useCallback(
    (text: string) => onNoteChange(appendBodyText(noteText, text)),
    [noteText, onNoteChange]
  )
  const voice = useVoiceTranscription({ onText: handleVoiceText })

  return (
    <div className="space-y-3">
      <div>
        <p className="text-[10px] font-medium uppercase tracking-[0.16em] text-silver-500">
          Optional words
        </p>
        {!compact ? (
          <p className="mt-1 text-xs leading-5 text-silver-500">
            Typed note works even when voice is unavailable.
          </p>
        ) : null}
      </div>

      <textarea
        value={noteText ?? ""}
        disabled={disabled}
        onChange={(event) => onNoteChange(event.target.value)}
        placeholder="Add the exact words, if there are any."
        className={cn(
          "w-full resize-none rounded-2xl border border-white/10 bg-white/[0.045] px-4 py-3 text-sm leading-6 text-silver-100 outline-none placeholder:text-silver-600 focus:border-white/20 disabled:pointer-events-none disabled:opacity-40",
          compact ? "min-h-20" : "min-h-28"
        )}
      />

      {showVoiceNote ? (
        <VoiceButton
          state={voice.state}
          onPress={voice.toggle}
          label="Voice"
          trailing="optional"
          className="min-w-40"
          disabled={disabled}
        />
      ) : null}
    </div>
  )
}
