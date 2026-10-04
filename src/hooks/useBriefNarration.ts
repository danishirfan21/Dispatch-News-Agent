import { useCallback, useEffect, useRef, useState } from 'react'
import { BriefAudioError, type BriefAudioSegment, audioResultToObjectUrl, getBriefAudio } from '../api/briefAudio'

export type NarrationState = 'idle' | 'loading' | 'playing' | 'paused' | 'finished'

function findActiveSegment(segments: BriefAudioSegment[], time: number): BriefAudioSegment | null {
  for (const segment of segments) {
    if (time >= segment.start && time < segment.end) return segment
  }
  return null
}

export function useBriefNarration() {
  const [state, setState] = useState<NarrationState>('idle')
  const [error, setError] = useState<string | null>(null)
  const [activeSegment, setActiveSegment] = useState<BriefAudioSegment | null>(null)
  const [segments, setSegments] = useState<BriefAudioSegment[]>([])

  const audioRef = useRef<HTMLAudioElement | null>(null)
  const containerRef = useRef<HTMLDivElement | null>(null)
  const objectUrlRef = useRef<string | null>(null)
  const segmentsRef = useRef<BriefAudioSegment[]>([])
  const isFetchedRef = useRef(false)

  const cleanup = useCallback(() => {
    const audio = audioRef.current
    if (audio) {
      audio.pause()
      audio.src = ''
      audio.remove()
      audioRef.current = null
    }
    if (objectUrlRef.current) {
      URL.revokeObjectURL(objectUrlRef.current)
      objectUrlRef.current = null
    }
  }, [])

  useEffect(() => cleanup, [cleanup])

  const handleTimeUpdate = useCallback(() => {
    const audio = audioRef.current
    if (!audio) return
    setActiveSegment(findActiveSegment(segmentsRef.current, audio.currentTime))
  }, [])

  const handleEnded = useCallback(() => {
    setState('finished')
    setActiveSegment(null)
  }, [])

  const loadAndPlay = useCallback(async () => {
    setError(null)
    setState('loading')
    try {
      const result = await getBriefAudio()
      segmentsRef.current = result.segments
      setSegments(result.segments)
      const url = audioResultToObjectUrl(result)
      objectUrlRef.current = url

      const audio = document.createElement('audio')
      audio.controls = true
      audio.src = url
      audio.className = 'w-full max-w-sm'
      audio.addEventListener('timeupdate', handleTimeUpdate)
      audio.addEventListener('seeked', handleTimeUpdate)
      audio.addEventListener('ended', handleEnded)
      containerRef.current?.replaceChildren(audio)
      audioRef.current = audio
      isFetchedRef.current = true

      await audio.play()
      setState('playing')
    } catch (err) {
      setError(err instanceof BriefAudioError ? err.message : 'Playback failed. Please try again.')
      setState('idle')
    }
  }, [handleTimeUpdate, handleEnded])

  const play = useCallback(() => {
    if (!isFetchedRef.current) {
      void loadAndPlay()
      return
    }
    const audio = audioRef.current
    if (!audio) return
    setError(null)
    audio
      .play()
      .then(() => setState('playing'))
      .catch(() => {
        setError('Playback failed. Please try again.')
        setState('idle')
      })
  }, [loadAndPlay])

  const pause = useCallback(() => {
    audioRef.current?.pause()
    setState('paused')
  }, [])

  const replay = useCallback(() => {
    const audio = audioRef.current
    if (!audio) return
    audio.currentTime = 0
    setError(null)
    audio
      .play()
      .then(() => setState('playing'))
      .catch(() => {
        setError('Playback failed. Please try again.')
        setState('idle')
      })
  }, [])

  const toggle = useCallback(() => {
    if (state === 'playing') {
      pause()
    } else if (state === 'finished') {
      replay()
    } else {
      play()
    }
  }, [state, pause, replay, play])

  return { state, error, activeSegment, segments, toggle, containerRef }
}
