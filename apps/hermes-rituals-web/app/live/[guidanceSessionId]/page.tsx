import { RitualGuidanceLiveClient } from "@/components/ritual/companion/RitualGuidanceLiveClient"

export default async function LivePage({
  params,
  searchParams
}: {
  params: Promise<{ guidanceSessionId: string }>
  searchParams: Promise<{ artifactId?: string }>
}) {
  const { guidanceSessionId } = await params
  const { artifactId } = await searchParams

  return <RitualGuidanceLiveClient guidanceSessionId={guidanceSessionId} artifactId={artifactId} />
}
