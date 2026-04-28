import { redirect } from "next/navigation"

import { getArtifactsByMode } from "@/lib/mock-artifacts"

export function generateStaticParams() {
  return getArtifactsByMode("ritual").map((artifact) => ({ artifactId: artifact.id }))
}

export default async function RitualPage({
  params
}: {
  params: Promise<{ artifactId: string }>
}) {
  const { artifactId } = await params
  redirect(`/artifacts/${artifactId}`)
}
