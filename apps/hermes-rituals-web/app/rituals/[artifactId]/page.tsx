import { notFound } from "next/navigation"

import { RitualArtifactClient } from "@/components/ritual/RitualArtifactClient"
import { getArtifact, getArtifactsByMode, getSession } from "@/lib/mock-artifacts"

export function generateStaticParams() {
  return getArtifactsByMode("ritual").map((artifact) => ({ artifactId: artifact.id }))
}

export default async function RitualPage({
  params
}: {
  params: Promise<{ artifactId: string }>
}) {
  const { artifactId } = await params
  const artifact = getArtifact(artifactId)

  if (!artifact || artifact.mode !== "ritual") {
    notFound()
  }

  return <RitualArtifactClient artifact={artifact} session={getSession(artifact.sessionId)} />
}
