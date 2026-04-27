"use client"

import { useCallback, useEffect, useRef, useState } from "react"

import type { VoiceButtonState } from "@/components/ui/voice-button"

export function useVoiceTranscription({
  onText,
  endpoint = "/api/voice/transcribe"
}: {
  onText: (text: string) => void
  endpoint?: string
}) {
  const [state, setState] = useState<VoiceButtonState>("idle")
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const resetTimeoutRef = useRef<number | null>(null)

  const clearResetTimeout = useCallback(() => {
    if (!resetTimeoutRef.current) return
    window.clearTimeout(resetTimeoutRef.current)
    resetTimeoutRef.current = null
  }, [])

  const stopStream = useCallback(() => {
    streamRef.current?.getTracks().forEach((track) => track.stop())
    streamRef.current = null
  }, [])

  const transcribeRecording = useCallback(
    async (mimeType: string) => {
      clearResetTimeout()
      setState("processing")
      stopStream()

      const blob = new Blob(chunksRef.current, { type: mimeType })
      chunksRef.current = []

      if (blob.size <= 0) {
        setState("error")
        return
      }

      try {
        const formData = new FormData()
        formData.append("audio", blob, "body-note.webm")
        const response = await fetch(endpoint, {
          method: "POST",
          body: formData
        })
        const payload = (await response.json().catch(() => ({}))) as Record<string, unknown>
        const text = typeof payload.text === "string" ? payload.text.trim() : ""
        if (!response.ok || !text) {
          throw new Error("transcription_failed")
        }
        onText(text)
        setState("success")
        resetTimeoutRef.current = window.setTimeout(() => setState("idle"), 1400)
      } catch {
        setState("error")
      }
    },
    [clearResetTimeout, endpoint, onText, stopStream]
  )

  const start = useCallback(async () => {
    clearResetTimeout()
    if (
      typeof navigator === "undefined" ||
      !navigator.mediaDevices ||
      typeof MediaRecorder === "undefined"
    ) {
      setState("error")
      return
    }

    try {
      chunksRef.current = []
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream
      const mimeType = MediaRecorder.isTypeSupported("audio/webm") ? "audio/webm" : undefined
      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined)
      mediaRecorderRef.current = recorder
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data)
      }
      recorder.onstop = () => {
        void transcribeRecording(mimeType ?? "audio/webm")
      }
      recorder.start()
      setState("recording")
    } catch {
      setState("error")
      stopStream()
    }
  }, [clearResetTimeout, stopStream, transcribeRecording])

  const stop = useCallback(() => {
    const recorder = mediaRecorderRef.current
    if (recorder && recorder.state !== "inactive") {
      recorder.stop()
      return
    }
    stopStream()
  }, [stopStream])

  const toggle = useCallback(() => {
    if (state === "recording") {
      stop()
      return
    }
    if (state === "processing") return
    void start()
  }, [start, state, stop])

  useEffect(() => {
    return () => {
      clearResetTimeout()
      const recorder = mediaRecorderRef.current
      if (recorder && recorder.state !== "inactive") recorder.stop()
      stopStream()
    }
  }, [clearResetTimeout, stopStream])

  return { state, start, stop, toggle }
}
