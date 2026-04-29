import { spawn } from "node:child_process"
import { existsSync } from "node:fs"
import path from "node:path"

import type {
  RitualArtifactSourceRef,
  RitualCompletionBodyStatePayload
} from "@/lib/artifact-contract"

export type HermesCompletionPayload = {
  artifactId: string
  manifestVersion: string
  idempotencyKey: string
  completedAt: string
  playbackState: "completed" | "partial" | "abandoned"
  planId?: string
  sourceRefs: RitualArtifactSourceRef[]
  durationMs?: number
  completedSections: string[]
  reflectionText?: string
  practiceFeedback?: Record<string, unknown>
  bodyState?: RitualCompletionBodyStatePayload
  clientMetadata?: Record<string, unknown>
}

type CompletionForwardResult = {
  ok: boolean
  status: number
  body: Record<string, unknown>
}

function repoRoot() {
  if (process.env.CIRCULATIO_REPO_ROOT) return process.env.CIRCULATIO_REPO_ROOT
  const cwd = process.cwd()
  if (existsSync(path.join(cwd, "scripts", "record_ritual_completion.py"))) return cwd
  return path.resolve(cwd, "../..")
}

function localPython(root: string) {
  if (process.env.CIRCULATIO_PYTHON) return process.env.CIRCULATIO_PYTHON
  const venvPython = path.join(root, ".venv", "bin", "python")
  return existsSync(venvPython) ? venvPython : "python3"
}

function localCompletionScript(root: string) {
  return (
    process.env.CIRCULATIO_RITUAL_COMPLETION_SCRIPT ??
    path.join(root, "scripts", "record_ritual_completion.py")
  )
}

async function forwardLocalCompletion(
  payload: HermesCompletionPayload
): Promise<CompletionForwardResult> {
  const root = repoRoot()
  const script = localCompletionScript(root)
  if (!existsSync(script)) {
    return {
      ok: false,
      status: 503,
      body: { error: "local_completion_bridge_not_found" }
    }
  }

  const timeoutMs = Number(process.env.CIRCULATIO_RITUAL_COMPLETION_TIMEOUT_MS ?? 15000)
  const child = spawn(localPython(root), [script], {
    cwd: root,
    env: { ...process.env, PYTHONUNBUFFERED: "1" },
    stdio: ["pipe", "pipe", "pipe"]
  })
  let stdout = ""
  let stderr = ""
  let timedOut = false

  const timer = setTimeout(() => {
    timedOut = true
    child.kill("SIGTERM")
  }, Number.isFinite(timeoutMs) && timeoutMs > 0 ? timeoutMs : 15000)

  child.stdout?.on("data", (chunk: Buffer) => {
    stdout += chunk.toString("utf8")
  })
  child.stderr?.on("data", (chunk: Buffer) => {
    stderr += chunk.toString("utf8")
  })

  if (!child.stdin) {
    clearTimeout(timer)
    return {
      ok: false,
      status: 502,
      body: { error: "local_completion_bridge_unavailable" }
    }
  }
  child.stdin.write(JSON.stringify(payload))
  child.stdin.end()

  const exitCode = await new Promise<number | null>((resolve, reject) => {
    child.once("error", reject)
    child.once("close", resolve)
  }).catch(() => null)
  clearTimeout(timer)

  if (timedOut) {
    return {
      ok: false,
      status: 504,
      body: { error: "local_completion_bridge_timeout" }
    }
  }
  if (exitCode !== 0) {
    return {
      ok: false,
      status: 502,
      body: {
        error: stderr.trim() ? "local_completion_bridge_failed" : "local_completion_bridge_unavailable"
      }
    }
  }

  try {
    const parsed = JSON.parse(stdout || "{}")
    return {
      ok: true,
      status: 200,
      body:
        parsed && typeof parsed === "object" && !Array.isArray(parsed)
          ? (parsed as Record<string, unknown>)
          : { result: parsed }
    }
  } catch {
    return {
      ok: false,
      status: 502,
      body: { error: "local_completion_bridge_invalid_response" }
    }
  }
}

export async function forwardRitualCompletion(
  payload: HermesCompletionPayload
): Promise<CompletionForwardResult> {
  const endpoint = process.env.HERMES_RITUAL_COMPLETION_URL
  if (!endpoint) {
    return forwardLocalCompletion(payload)
  }

  const response = await fetch(endpoint, {
    method: "POST",
    headers: {
      "content-type": "application/json",
      "idempotency-key": payload.idempotencyKey
    },
    body: JSON.stringify(payload),
    cache: "no-store"
  })

  const body = await response.json().catch(() => ({}))
  return {
    ok: response.ok,
    status: response.status,
    body: body && typeof body === "object" && !Array.isArray(body) ? body : { result: body }
  }
}
