"use client"

import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import type { CharacterAlignmentResponseModel } from "@elevenlabs/elevenlabs-js/api/types/CharacterAlignmentResponseModel"

export type TranscriptWord = {
  kind: "word"
  text: string
  start: number
  end: number
  segmentIndex: number
}

export type TranscriptGap = {
  kind: "gap"
  text: string
  start: number
  end: number
  segmentIndex: number
}

export type TranscriptSegment = TranscriptWord | TranscriptGap

export type SegmentComposer = (words: TranscriptWord[]) => TranscriptSegment[]

export type UseTranscriptViewerArgs = {
  alignment: CharacterAlignmentResponseModel
  segmentComposer?: SegmentComposer
  hideAudioTags?: boolean
  onPlay?: () => void
  onPause?: () => void
  onTimeUpdate?: (time: number) => void
  onEnded?: () => void
  onDurationChange?: (duration: number) => void
}

export type UseTranscriptViewerResult = {
  audioRef: React.RefObject<HTMLAudioElement | null>
  isPlaying: boolean
  isScrubbing: boolean
  duration: number
  currentTime: number
  seekToTime: (time: number) => void
  startScrubbing: () => void
  endScrubbing: () => void
  play: () => Promise<void>
  pause: () => void
  segments: TranscriptSegment[]
  words: TranscriptWord[]
  spokenSegments: TranscriptSegment[]
  unspokenSegments: TranscriptSegment[]
  currentWord: TranscriptWord | null
}

function isTag(text: string) {
  return /^\[[^\]]+\]$/.test(text.trim())
}

function normalizeWordText(text: string) {
  return text.replace(/\s+/g, " ")
}

function buildWords(
  alignment: CharacterAlignmentResponseModel,
  hideAudioTags: boolean
): TranscriptWord[] {
  const words: TranscriptWord[] = []
  const { characters, characterStartTimesSeconds, characterEndTimesSeconds } = alignment
  let buffer = ""
  let start = -1
  let end = 0
  let segmentIndex = 0

  const flush = () => {
    const text = normalizeWordText(buffer)
    if (!text) {
      buffer = ""
      start = -1
      return
    }
    if (!(hideAudioTags && isTag(text))) {
      words.push({
        kind: "word",
        text,
        start: start < 0 ? end : start,
        end,
        segmentIndex
      })
      segmentIndex += 1
    }
    buffer = ""
    start = -1
  }

  characters.forEach((character, index) => {
    const charStart = characterStartTimesSeconds[index] ?? end
    const charEnd = characterEndTimesSeconds[index] ?? charStart
    const isWhitespace = /\s/.test(character)

    if (isWhitespace) {
      flush()
      return
    }

    if (start < 0) {
      start = charStart
    }
    buffer += character
    end = charEnd
  })

  flush()
  return words
}

function composeSegments(words: TranscriptWord[], alignment: CharacterAlignmentResponseModel) {
  const segments: TranscriptSegment[] = []
  const { characters, characterStartTimesSeconds, characterEndTimesSeconds } = alignment
  let wordCursor = 0
  let gapBuffer = ""
  let gapStart = 0
  let gapEnd = 0
  let segmentIndex = 0

  const flushGap = () => {
    if (!gapBuffer) return
    segments.push({
      kind: "gap",
      text: gapBuffer,
      start: gapStart,
      end: gapEnd,
      segmentIndex
    })
    segmentIndex += 1
    gapBuffer = ""
  }

  let currentWord = words[wordCursor]

  characters.forEach((character, index) => {
    const charStart = characterStartTimesSeconds[index] ?? 0
    const charEnd = characterEndTimesSeconds[index] ?? charStart

    if (/\s/.test(character)) {
      if (!gapBuffer) {
        gapStart = charStart
      }
      gapBuffer += character
      gapEnd = charEnd
      return
    }

    if (gapBuffer) {
      flushGap()
    }

    if (!currentWord) {
      return
    }

    const textAtCursor = currentWord.text
    const nextChars = characters
      .slice(index, index + textAtCursor.length)
      .join("")
      .replace(/\s+/g, "")

    if (nextChars.startsWith(textAtCursor.replace(/\s+/g, ""))) {
      segments.push({ ...currentWord, segmentIndex })
      segmentIndex += 1
      wordCursor += 1
      currentWord = words[wordCursor]
    }
  })

  flushGap()
  return segments
}

export function useTranscriptViewer({
  alignment,
  segmentComposer,
  hideAudioTags = true,
  onPlay,
  onPause,
  onTimeUpdate,
  onEnded,
  onDurationChange
}: UseTranscriptViewerArgs): UseTranscriptViewerResult {
  const audioRef = useRef<HTMLAudioElement>(null)
  const resumeAfterScrubRef = useRef(false)
  const [isPlaying, setIsPlaying] = useState(false)
  const [isScrubbing, setIsScrubbing] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)

  const words = useMemo(
    () => buildWords(alignment, hideAudioTags),
    [alignment, hideAudioTags]
  )
  const segments = useMemo(
    () => (segmentComposer ? segmentComposer(words) : composeSegments(words, alignment)),
    [alignment, segmentComposer, words]
  )

  const currentWord = useMemo(() => {
    return (
      words.find((word) => currentTime >= word.start && currentTime < word.end) ??
      words.at(-1) ??
      null
    )
  }, [currentTime, words])

  const spokenSegments = useMemo(() => {
    return segments.filter((segment) => segment.end <= currentTime)
  }, [currentTime, segments])

  const unspokenSegments = useMemo(() => {
    return segments.filter((segment) => {
      if (currentWord && segment.segmentIndex === currentWord.segmentIndex) {
        return false
      }
      return segment.start > currentTime
    })
  }, [currentTime, currentWord, segments])

  useEffect(() => {
    const audio = audioRef.current
    if (!audio) return

    const handlePlay = () => {
      setIsPlaying(true)
      onPlay?.()
    }

    const handlePause = () => {
      setIsPlaying(false)
      onPause?.()
    }

    const handleTimeUpdate = () => {
      setCurrentTime(audio.currentTime)
      onTimeUpdate?.(audio.currentTime)
    }

    const handleDurationChange = () => {
      const nextDuration = Number.isFinite(audio.duration) ? audio.duration : 0
      setDuration(nextDuration)
      onDurationChange?.(nextDuration)
    }

    const handleEnded = () => {
      setIsPlaying(false)
      onEnded?.()
    }

    audio.addEventListener("play", handlePlay)
    audio.addEventListener("pause", handlePause)
    audio.addEventListener("timeupdate", handleTimeUpdate)
    audio.addEventListener("durationchange", handleDurationChange)
    audio.addEventListener("loadedmetadata", handleDurationChange)
    audio.addEventListener("ended", handleEnded)

    return () => {
      audio.removeEventListener("play", handlePlay)
      audio.removeEventListener("pause", handlePause)
      audio.removeEventListener("timeupdate", handleTimeUpdate)
      audio.removeEventListener("durationchange", handleDurationChange)
      audio.removeEventListener("loadedmetadata", handleDurationChange)
      audio.removeEventListener("ended", handleEnded)
    }
  }, [onDurationChange, onEnded, onPause, onPlay, onTimeUpdate])

  const play = useCallback(async () => {
    if (!audioRef.current) return
    await audioRef.current.play()
  }, [])

  const pause = useCallback(() => {
    audioRef.current?.pause()
  }, [])

  const seekToTime = useCallback((time: number) => {
    if (!audioRef.current) return
    audioRef.current.currentTime = Math.max(0, time)
    setCurrentTime(audioRef.current.currentTime)
  }, [])

  const startScrubbing = useCallback(() => {
    setIsScrubbing(true)
    resumeAfterScrubRef.current = isPlaying
    if (audioRef.current && !audioRef.current.paused) {
      audioRef.current.pause()
    }
  }, [isPlaying])

  const endScrubbing = useCallback(() => {
    setIsScrubbing(false)
    if (resumeAfterScrubRef.current) {
      void audioRef.current?.play()
    }
    resumeAfterScrubRef.current = false
  }, [])

  return {
    audioRef,
    isPlaying,
    isScrubbing,
    duration,
    currentTime,
    seekToTime,
    startScrubbing,
    endScrubbing,
    play,
    pause,
    segments,
    words,
    spokenSegments,
    unspokenSegments,
    currentWord
  }
}
