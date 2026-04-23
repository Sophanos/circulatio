import { notFound } from "next/navigation"

import { CinemaArtifactClient } from "@/components/cinema/CinemaArtifactClient"
import { getArtifact, getArtifactsByMode, getSession } from "@/lib/mock-artifacts"

export function generateStaticParams() {
  return getArtifactsByMode("cinema").map((artifact) => ({ artifactId: artifact.id }))
}

export default async function CinemaPage({
  params
}: {
  params: Promise<{ artifactId: string }>
}) {
  const { artifactId } = await params
  const artifact = getArtifact(artifactId)

  if (!artifact || artifact.mode !== "cinema") {
    notFound()
  }

  return <CinemaArtifactClient artifact={artifact} session={getSession(artifact.sessionId)} />
}
