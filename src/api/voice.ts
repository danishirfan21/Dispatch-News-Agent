export type TranscribeResult = {
  text: string
  language_code: string
}

export class VoiceTranscribeError extends Error {}

export async function transcribeAudio(audioBlob: Blob): Promise<TranscribeResult> {
  const formData = new FormData()
  formData.append('file', audioBlob, 'recording.webm')

  let response: Response
  try {
    response = await fetch('/api/voice/transcribe', {
      method: 'POST',
      credentials: 'include',
      body: formData,
    })
  } catch {
    throw new VoiceTranscribeError("Couldn't reach the server. Check your connection and try again.")
  }

  if (response.status === 401) {
    throw new VoiceTranscribeError('Please log in again to use voice dictation.')
  }

  if (!response.ok) {
    throw new VoiceTranscribeError("Couldn't transcribe that recording. Please try again.")
  }

  return (await response.json()) as TranscribeResult
}
