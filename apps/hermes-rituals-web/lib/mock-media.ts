import type { CharacterAlignmentResponseModel } from "@elevenlabs/elevenlabs-js/api/types/CharacterAlignmentResponseModel"

export function createCharacterAlignment(
  text: string,
  durationMs: number
): CharacterAlignmentResponseModel {
  const characters = Array.from(text)
  const durationSeconds = Math.max(durationMs / 1000, 1)
  const charDuration = durationSeconds / Math.max(characters.length, 1)

  return {
    characters,
    characterStartTimesSeconds: characters.map((_, index) => index * charDuration),
    characterEndTimesSeconds: characters.map((_, index) => (index + 1) * charDuration)
  }
}

export function buildWaveformData(text: string, bars = 72) {
  const codes = Array.from(text).map((character) => character.charCodeAt(0))
  if (codes.length === 0) {
    return Array.from({ length: bars }, () => 0.35)
  }

  return Array.from({ length: bars }, (_, index) => {
    const code = codes[index % codes.length] ?? 77
    const seeded = Math.abs(Math.sin(code * (index + 1) * 0.017))
    return 0.22 + seeded * 0.68
  })
}

export function makeSilentWavBlobUrl(durationMs: number, sampleRate = 8000) {
  const durationSeconds = Math.max(durationMs / 1000, 1)
  const channels = 1
  const bitsPerSample = 16
  const bytesPerSample = bitsPerSample / 8
  const sampleCount = Math.ceil(durationSeconds * sampleRate)
  const blockAlign = channels * bytesPerSample
  const byteRate = sampleRate * blockAlign
  const dataSize = sampleCount * blockAlign
  const buffer = new ArrayBuffer(44 + dataSize)
  const view = new DataView(buffer)

  let offset = 0
  const writeString = (value: string) => {
    for (let index = 0; index < value.length; index += 1) {
      view.setUint8(offset + index, value.charCodeAt(index))
    }
    offset += value.length
  }

  writeString("RIFF")
  view.setUint32(offset, 36 + dataSize, true)
  offset += 4
  writeString("WAVE")
  writeString("fmt ")
  view.setUint32(offset, 16, true)
  offset += 4
  view.setUint16(offset, 1, true)
  offset += 2
  view.setUint16(offset, channels, true)
  offset += 2
  view.setUint32(offset, sampleRate, true)
  offset += 4
  view.setUint32(offset, byteRate, true)
  offset += 4
  view.setUint16(offset, blockAlign, true)
  offset += 2
  view.setUint16(offset, bitsPerSample, true)
  offset += 2
  writeString("data")
  view.setUint32(offset, dataSize, true)

  return URL.createObjectURL(new Blob([buffer], { type: "audio/wav" }))
}
