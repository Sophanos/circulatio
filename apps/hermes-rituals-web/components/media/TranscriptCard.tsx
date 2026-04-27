"use client"

import { useEffect, useMemo, useState } from "react"

import {
  TranscriptViewerAudio,
  TranscriptViewerContainer,
  TranscriptViewerPlayPauseButton,
  TranscriptViewerScrubBar,
  TranscriptViewerWords
} from "@/components/ui/transcript-viewer"
import type { PresentationArtifact } from "@/lib/artifact-contract"
import { createCharacterAlignment, makeSilentWavBlobUrl } from "@/lib/mock-media"

function audioTypeForSource(src: string) {
  if (src.endsWith(".mp3")) return "audio/mpeg"
  if (src.endsWith(".ogg")) return "audio/ogg"
  if (src.endsWith(".m4a")) return "audio/m4a"
  if (src.endsWith(".aac")) return "audio/aac"
  if (src.endsWith(".webm")) return "audio/webm"
  return "audio/wav"
}

export function TranscriptCard({ artifact }: { artifact: PresentationArtifact }) {
  const transcript = artifact.transcript ?? artifact.summary
  const durationMs = artifact.captions?.at(-1)?.endMs ?? 60000
  const alignment = useMemo(
    () => createCharacterAlignment(transcript, durationMs),
    [durationMs, transcript]
  )
  const [audioUrl, setAudioUrl] = useState("")

  useEffect(() => {
    if (artifact.audioUrl) {
      setAudioUrl(artifact.audioUrl)
      return
    }
    const url = makeSilentWavBlobUrl(durationMs)
    setAudioUrl(url)
    return () => URL.revokeObjectURL(url)
  }, [artifact.audioUrl, durationMs])

  if (!audioUrl) return null

  return (
    <section className="media-card gsap-media-card p-8 md:p-10">
      <div className="mb-8 flex items-end justify-between gap-6">
        <div>
          <p className="text-xs font-medium tracking-[0.22em] uppercase text-graphite-500">
            Transcript
          </p>
          <h3 className="mt-3 text-4xl font-semibold tracking-[-0.06em] text-graphite-950">
            Live captions, not a dead document.
          </h3>
        </div>
      </div>

      <TranscriptViewerContainer
        audioSrc={audioUrl}
        audioType={audioTypeForSource(audioUrl)}
        alignment={alignment}
        className="rounded-[1.5rem] border border-graphite-950/8 bg-silver-100/75 p-6 md:p-8"
      >
        <TranscriptViewerAudio />
        <TranscriptViewerWords
          className="text-[1.05rem] leading-8"
          wordClassNames="rounded-sm"
          gapClassNames="whitespace-pre-wrap"
        />
        <div className="mt-8 flex items-center gap-4">
          <TranscriptViewerPlayPauseButton className="rounded-full" />
          <TranscriptViewerScrubBar
            className="flex-1"
            trackClassName="bg-graphite-950/10"
            progressClassName="[&>div]:bg-graphite-950"
            thumbClassName="bg-graphite-950"
          />
        </div>
      </TranscriptViewerContainer>
    </section>
  )
}
