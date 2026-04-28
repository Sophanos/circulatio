import { notFound } from "next/navigation"

import { RitualArtifactClient } from "@/components/ritual/RitualArtifactClient"
import { ritualArtifactFromManifest } from "@/lib/artifact-contract"
import { loadArtifactManifest } from "@/lib/load-artifact-manifest"
import { getArtifact, getSession } from "@/lib/mock-artifacts"

export default async function ArtifactDetailPage({
  params
}: {
  params: Promise<{ artifactId: string }>
}) {
  const { artifactId } = await params
  const manifest = await loadArtifactManifest(artifactId)

  if (manifest) {
    return <RitualArtifactClient artifact={ritualArtifactFromManifest(manifest)} />
  }

  const artifact = getArtifact(artifactId)

  if (!artifact) {
    notFound()
  }

  return <RitualArtifactClient artifact={artifact} session={getSession(artifact.sessionId)} />
}
