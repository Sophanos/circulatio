"use client"

import { useEffect, useMemo, useState } from "react"

import {
  AudioPlayerButton,
  AudioPlayerDuration,
  AudioPlayerProgress,
  AudioPlayerProvider,
  AudioPlayerSpeed,
  AudioPlayerTime,
  useAudioPlayer
} from "@/components/ui/audio-player"
import { StaticWaveform } from "@/components/ui/waveform"
import type { PresentationArtifact } from "@/lib/artifact-contract"
import { buildWaveformData, makeSilentWavBlobUrl } from "@/lib/mock-media"

function BroadcastTrackLoader({ src, title }: { src: string; title: string }) {
  const { setActiveItem } = useAudioPlayer<{ title: string }>()

  useEffect(() => {
    void setActiveItem({
      id: title,
      src,
      data: { title }
    })
  }, [setActiveItem, src, title])

  return null
}

export function BroadcastDeck({ artifact }: { artifact: PresentationArtifact }) {
  const durationMs = artifact.captions?.at(-1)?.endMs ?? 60000
  const [audioUrl, setAudioUrl] = useState("")
  const waveform = useMemo(
    () => buildWaveformData(artifact.transcript ?? artifact.summary, 70),
    [artifact.summary, artifact.transcript]
  )

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
    <AudioPlayerProvider>
      <BroadcastTrackLoader src={audioUrl} title={artifact.title} />
      <section className="grid gap-6 lg:grid-cols-[0.78fr_1.22fr]">
        <div className="media-card gsap-media-card overflow-hidden">
          <div
            className="aspect-square bg-cover bg-center grayscale contrast-125"
            style={{ backgroundImage: `url(${artifact.coverImageUrl})` }}
          />
        </div>
        <div className="media-card gsap-media-card p-8 md:p-10">
          <p className="text-xs font-medium tracking-[0.22em] uppercase text-graphite-500">
            Broadcast deck
          </p>
          <h2 className="mt-3 text-5xl font-semibold leading-[0.92] tracking-[-0.06em] text-graphite-950">
            {artifact.title}
          </h2>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-graphite-600">{artifact.summary}</p>

          <div className="mt-8 rounded-[1.5rem] border border-graphite-950/8 bg-silver-100/75 p-6">
            <StaticWaveform data={waveform} height={88} barColor="#171b1f" className="w-full" />
            <div className="mt-6 flex flex-wrap items-center gap-4">
              <AudioPlayerButton className="rounded-full" />
              <AudioPlayerProgress className="flex-1" />
              <AudioPlayerTime />
              <span className="text-muted-foreground">/</span>
              <AudioPlayerDuration />
              <AudioPlayerSpeed />
            </div>
          </div>

          <div className="mt-8 grid gap-4 md:grid-cols-2">
            {(artifact.scenes ?? []).map((scene) => (
              <article key={scene.id} className="rounded-[1.5rem] border border-graphite-950/8 bg-silver-100/75 p-5">
                <p className="text-xs font-medium tracking-[0.18em] uppercase text-graphite-500">
                  Chapter
                </p>
                <h3 className="mt-3 text-xl font-semibold tracking-[-0.04em] text-graphite-950">
                  {scene.title}
                </h3>
                <p className="mt-3 text-sm leading-7 text-graphite-600">{scene.prompt}</p>
              </article>
            ))}
          </div>
        </div>
      </section>
    </AudioPlayerProvider>
  )
}
