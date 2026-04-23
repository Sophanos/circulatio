import { notFound } from "next/navigation"

import { BroadcastArtifactClient } from "@/components/broadcast/BroadcastArtifactClient"
import { getArtifact, getArtifactsByMode, getSession } from "@/lib/mock-artifacts"

export function generateStaticParams() {
  return getArtifactsByMode("broadcast").map((artifact) => ({ artifactId: artifact.id }))
}

export default async function BroadcastPage({
  params
}: {
  params: Promise<{ artifactId: string }>
}) {
  const { artifactId } = await params
  const artifact = getArtifact(artifactId)

  if (!artifact || artifact.mode !== "broadcast") {
    notFound()
  }

  return <BroadcastArtifactClient artifact={artifact} session={getSession(artifact.sessionId)} />
}
