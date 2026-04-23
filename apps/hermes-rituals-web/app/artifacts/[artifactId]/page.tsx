import Link from "next/link"
import { notFound } from "next/navigation"

import { Button } from "@/components/ui/button"
import { getArtifact } from "@/lib/mock-artifacts"

export default async function ArtifactDetailPage({
  params
}: {
  params: Promise<{ artifactId: string }>
}) {
  const { artifactId } = await params
  const artifact = getArtifact(artifactId)

  if (!artifact) {
    notFound()
  }

  const route = `/${artifact.mode}s/${artifact.id}`

  return (
    <section className="mx-auto max-w-[1080px] px-5 py-20 md:px-10 md:py-28 lg:px-14 lg:py-36">
      <div className="media-card p-8 md:p-10">
        <p className="text-xs font-medium tracking-[0.22em] uppercase text-graphite-500">
          Artifact detail
        </p>
        <h1 className="mt-4 text-5xl font-semibold leading-[0.9] tracking-[-0.06em] text-graphite-950">
          {artifact.title}
        </h1>
        <p className="mt-5 max-w-2xl text-sm leading-7 text-graphite-600">{artifact.summary}</p>
        <dl className="mt-8 grid gap-4 text-sm md:grid-cols-2">
          <div>
            <dt className="text-graphite-500">Mode</dt>
            <dd className="mt-1 text-graphite-950">{artifact.mode}</dd>
          </div>
          <div>
            <dt className="text-graphite-500">Session</dt>
            <dd className="mt-1 text-graphite-950">{artifact.sessionId ?? "mock-session"}</dd>
          </div>
          <div>
            <dt className="text-graphite-500">Journey</dt>
            <dd className="mt-1 text-graphite-950">{artifact.journeyId ?? "not linked yet"}</dd>
          </div>
          <div>
            <dt className="text-graphite-500">Resume</dt>
            <dd className="mt-1 text-graphite-950">{route}</dd>
          </div>
        </dl>
        <div className="mt-8">
          <Button asChild className="rounded-full px-5">
            <Link href={route}>Open render family page</Link>
          </Button>
        </div>
      </div>
    </section>
  )
}
