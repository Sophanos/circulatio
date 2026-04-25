import { NextResponse } from "next/server"

const MAX_AUDIO_BYTES = 12 * 1024 * 1024
const WHISPER_TRANSCRIBE_URL = "https://chutes-whisper-large-v3.chutes.ai/transcribe"

function findTranscriptText(value: unknown): string | undefined {
  if (typeof value === "string") {
    const text = value.trim()
    return text || undefined
  }

  if (Array.isArray(value)) {
    for (const item of value) {
      const found = findTranscriptText(item)
      if (found) return found
    }
    return undefined
  }

  if (!value || typeof value !== "object") return undefined
  const record = value as Record<string, unknown>
  for (const key of ["text", "transcript", "transcription", "output_text", "result"]) {
    const found = findTranscriptText(record[key])
    if (found) return found
  }
  for (const item of Object.values(record)) {
    const found = findTranscriptText(item)
    if (found) return found
  }
  return undefined
}

export async function POST(request: Request) {
  const token = process.env.CHUTES_API_TOKEN
  if (!token) {
    return NextResponse.json({ error: "chutes_provider_missing_api_token" }, { status: 503 })
  }

  const formData = await request.formData().catch(() => null)
  const audio = formData?.get("audio")
  if (!(audio instanceof File)) {
    return NextResponse.json({ error: "audio_file_required" }, { status: 400 })
  }
  if (audio.size <= 0) {
    return NextResponse.json({ error: "audio_file_empty" }, { status: 400 })
  }
  if (audio.size > MAX_AUDIO_BYTES) {
    return NextResponse.json({ error: "audio_file_too_large" }, { status: 413 })
  }

  const language = formData ? String(formData.get("language") || "").trim() : ""
  const audioBase64 = Buffer.from(await audio.arrayBuffer()).toString("base64")

  const response = await fetch(WHISPER_TRANSCRIBE_URL, {
    method: "POST",
    headers: {
      authorization: `Bearer ${token}`,
      accept: "application/json",
      "content-type": "application/json"
    },
    body: JSON.stringify({
      language: language || null,
      audio_b64: audioBase64
    }),
    cache: "no-store",
    signal: AbortSignal.timeout(180000)
  }).catch((error: unknown) => {
    const message = error instanceof Error ? error.message : "unknown_error"
    return NextResponse.json({ error: "chutes_transcription_failed", detail: message }, { status: 502 })
  })

  if (response instanceof NextResponse) {
    return response
  }

  const payload = (await response.json().catch(() => ({}))) as Record<string, unknown>
  if (!response.ok) {
    return NextResponse.json(
      { error: "chutes_transcription_failed", status: response.status, detail: payload },
      { status: 502 }
    )
  }

  const text = findTranscriptText(payload)
  if (!text) {
    return NextResponse.json({ error: "transcription_text_missing" }, { status: 502 })
  }

  return NextResponse.json({
    text,
    provider: "chutes",
    model: "chutes-whisper-large-v3"
  })
}
