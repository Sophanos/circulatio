import { readFile } from "node:fs/promises"
import path from "node:path"

import type { RitualArtifactManifest } from "@/lib/artifact-contract"

export async function loadArtifactManifest(artifactId: string) {
  const candidates = [
    path.join(process.cwd(), "public", "artifacts", artifactId, "manifest.json"),
    path.join(
      process.cwd(),
      "apps",
      "hermes-rituals-web",
      "public",
      "artifacts",
      artifactId,
      "manifest.json"
    )
  ]

  for (const filePath of candidates) {
    try {
      const raw = await readFile(filePath, "utf-8")
      const manifest = JSON.parse(raw) as RitualArtifactManifest
      if (manifest.schemaVersion === "hermes_ritual_artifact.v1") {
        return manifest
      }
    } catch {
      continue
    }
  }

  return null
}
