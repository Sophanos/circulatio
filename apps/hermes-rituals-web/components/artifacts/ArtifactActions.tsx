import Link from "next/link"
import { Download, ExternalLink, Layers2, Sparkles } from "lucide-react"

import { Button } from "@/components/ui/button"
import type { PresentationArtifact } from "@/lib/artifact-contract"

export function ArtifactActions({ artifact }: { artifact: PresentationArtifact }) {
  return (
    <div className="flex flex-wrap gap-3">
      <Button asChild className="rounded-full px-5">
        <Link href={`/artifacts/${artifact.id}`}>
          <Layers2 className="size-4" />
          Open artifact
        </Link>
      </Button>
      <Button asChild variant="outline" className="rounded-full px-5">
        <Link href={`/broadcasts/broadcast-myth-weather-0422`}>
          <Sparkles className="size-4" />
          Broadcast reuse
        </Link>
      </Button>
      <Button asChild variant="outline" className="rounded-full px-5">
        <Link href={`/cinema/cinema-river-gate`}>
          <ExternalLink className="size-4" />
          Cinema reuse
        </Link>
      </Button>
      <Button variant="outline" className="rounded-full px-5">
        <Download className="size-4" />
        Export notes
      </Button>
    </div>
  )
}
