"use client"

import { useState } from "react"

import { Button } from "@/components/ui/button"
import { LiveWaveform } from "@/components/ui/live-waveform"
import { AgentState, Orb } from "@/components/ui/orb"
import { Textarea } from "@/components/ui/textarea"

export function SpeechCapture({ compact = false }: { compact?: boolean }) {
  const [draft, setDraft] = useState("")
  const [recording, setRecording] = useState(false)
  const [saved, setSaved] = useState(false)

  const agentState: AgentState = recording ? "listening" : null

  return (
    <article className="media-card gsap-media-card h-full p-8 md:p-10">
      <div className="flex items-start justify-between gap-6">
        <div>
          <p className="text-xs font-medium tracking-[0.22em] uppercase text-graphite-500">
            Capture
          </p>
          <h3 className="mt-3 text-3xl font-semibold tracking-[-0.05em] text-graphite-950">
            Hold the fresh material before interpretation.
          </h3>
        </div>
        <div className="h-16 w-16 overflow-hidden rounded-full border border-graphite-950/10 bg-silver-100 p-1">
          <Orb colors={["#CADCFC", "#A0B9D1"]} seed={1000} agentState={agentState} />
        </div>
      </div>

      <div className="mt-6 rounded-[1.5rem] border border-graphite-950/8 bg-silver-100/70 p-4">
        <LiveWaveform
          processing={recording}
          active={false}
          height={compact ? 56 : 76}
          barColor="#171b1f"
        />
      </div>

      <Textarea
        value={draft}
        onChange={(event) => setDraft(event.target.value)}
        placeholder="Speak or type the image as it arrived. Keep it factual, immediate, and yours."
        className="mt-6 min-h-36 resize-none"
      />

      <div className="mt-5 flex flex-wrap gap-3">
        <Button className="rounded-full px-5" onClick={() => setRecording((current) => !current)}>
          {recording ? "Stop capture" : "Start mock capture"}
        </Button>
        <Button
          variant="outline"
          className="rounded-full px-5"
          onClick={() => setSaved(true)}
        >
          Save held note
        </Button>
      </div>

      <p className="mt-5 text-sm leading-7 text-graphite-600">
        {saved
          ? "Saved with hold-first acknowledgement. Nothing has been silently interpreted."
          : "This mocked-first capture surface is ready to receive live ElevenLabs STT once the token route is wired."}
      </p>
    </article>
  )
}
