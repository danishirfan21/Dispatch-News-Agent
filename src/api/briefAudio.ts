export type BriefAudioSegment = {
  story_id: string
  type: 'headline' | 'summary'
  text: string
  start: number
  end: number
}

export type BriefAudioResult = {
  audio_base64: string
  mime_type: string
  segments: BriefAudioSegment[]
}

export class BriefAudioError extends Error {}

export async function getBriefAudio(): Promise<BriefAudioResult> {
  let response: Response
  try {
    response = await fetch('/api/brief/audio', { credentials: 'include' })
  } catch {
    throw new BriefAudioError("Couldn't reach the server. Check your connection and try again.")
  }

  if (response.status === 401) {
    throw new BriefAudioError('Please log in again to listen to your brief.')
  }

  if (response.status === 404) {
    throw new BriefAudioError("You don't have a saved brief to narrate yet.")
  }

  if (!response.ok) {
    throw new BriefAudioError("Couldn't prepare the narration. Please try again.")
  }

  return (await response.json()) as BriefAudioResult
}

function base64ToBlob(base64: string, mimeType: string): Blob {
  const binary = atob(base64)
  const bytes = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i)
  }
  return new Blob([bytes], { type: mimeType })
}

export function audioResultToObjectUrl(result: BriefAudioResult): string {
  const blob = base64ToBlob(result.audio_base64, result.mime_type)
  return URL.createObjectURL(blob)
}
