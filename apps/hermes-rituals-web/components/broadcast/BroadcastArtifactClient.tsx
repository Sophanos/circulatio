import { ArtifactActions } from "@/components/artifacts/ArtifactActions"
import { SessionHeader } from "@/components/artifacts/SessionHeader"
import { ThreadSummary } from "@/components/artifacts/ThreadSummary"
import { BroadcastDeck } from "@/components/broadcast/BroadcastDeck"
import { TranscriptCard } from "@/components/media/TranscriptCard"
import { ArtifactScrollMotion } from "@/components/motion/ArtifactScrollMotion"
import type { PresentationArtifact, SessionShell } from "@/lib/artifact-contract"

export function BroadcastArtifactClient({
  artifact,
  session
}: {
  artifact: PresentationArtifact
  session?: SessionShell
}) {
  return (
    <ArtifactScrollMotion>
      <SessionHeader artifact={artifact} session={session} />
      <section className="mx-auto max-w-[1440px] px-5 py-24 md:px-10 md:py-36 lg:px-14 lg:py-48">
        <BroadcastDeck artifact={artifact} />
      </section>
      <section className="mx-auto max-w-[1440px] px-5 py-24 md:px-10 md:py-36 lg:px-14 lg:py-48">
        <ThreadSummary artifact={artifact} session={session} />
      </section>
      <section className="mx-auto max-w-[1440px] px-5 py-24 md:px-10 md:py-36 lg:px-14 lg:py-48">
        <TranscriptCard artifact={artifact} />
      </section>
      <section className="mx-auto max-w-[1440px] px-5 pb-28 pt-8 md:px-10 md:pb-36 lg:px-14 lg:pb-48">
        <ArtifactActions artifact={artifact} />
      </section>
    </ArtifactScrollMotion>
  )
}
