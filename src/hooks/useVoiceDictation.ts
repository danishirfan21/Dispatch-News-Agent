import { useCallback, useRef, useState } from 'react'
import { VoiceTranscribeError, transcribeAudio } from '../api/voice'

export type DictationState = 'idle' | 'recording' | 'transcribing'

const MIN_RECORDING_MS = 400

export function useVoiceDictation(onTranscript: (text: string) => void) {
  const [state, setState] = useState<DictationState>('idle')
  const [error, setError] = useState<string | null>(null)
  const recorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const streamRef = useRef<MediaStream | null>(null)
  const startedAtRef = useRef(0)

  const stopStream = useCallback(() => {
    streamRef.current?.getTracks().forEach((track) => track.stop())
    streamRef.current = null
  }, [])

  const start = useCallback(async () => {
    setError(null)

    if (typeof MediaRecorder === 'undefined') {
      setError('Voice dictation is not supported in this browser.')
      return
    }

    let stream: MediaStream
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    } catch {
      setError('Microphone access was denied. Please allow microphone access and try again.')
      return
    }

    streamRef.current = stream
    chunksRef.current = []

    const recorder = new MediaRecorder(stream)
    recorderRef.current = recorder

    recorder.ondataavailable = (event) => {
      if (event.data.size > 0) chunksRef.current.push(event.data)
    }

    recorder.onstop = async () => {
      stopStream()
      const elapsedMs = Date.now() - startedAtRef.current
      const blob = new Blob(chunksRef.current, { type: recorder.mimeType || 'audio/webm' })
      chunksRef.current = []

      if (elapsedMs < MIN_RECORDING_MS || blob.size === 0) {
        setError('That recording was too short. Please try again.')
        setState('idle')
        return
      }

      setState('transcribing')
      try {
        const result = await transcribeAudio(blob)
        onTranscript(result.text)
        setState('idle')
      } catch (err) {
        setError(err instanceof VoiceTranscribeError ? err.message : 'Something went wrong. Please try again.')
        setState('idle')
      }
    }

    startedAtRef.current = Date.now()
    recorder.start()
    setState('recording')
  }, [onTranscript, stopStream])

  const stop = useCallback(() => {
    recorderRef.current?.stop()
  }, [])

  const toggle = useCallback(() => {
    if (state === 'recording') {
      stop()
    } else if (state === 'idle') {
      void start()
    }
  }, [state, start, stop])

  return { state, error, toggle }
}
