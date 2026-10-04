export type WatchSource = {
  name: string
  url: string
}

export type WatchStatus = 'active' | 'paused'
export type WatchDevelopmentStatus = 'no_change' | 'new_development'

export type WatchLatestChange = {
  summary: string
  detected_at: string
  sources: WatchSource[]
}

export type Watch = {
  id: string
  story_id: string
  topic: string
  headline: string
  summary: string
  sources: WatchSource[]
  published_at: string | null
  known_state: string
  known_state_updated_at: string
  watch_condition: string
  major_developments_only: boolean
  status: WatchStatus
  development_status: WatchDevelopmentStatus
  latest_change: WatchLatestChange | null
  last_checked_at: string | null
  created_at: string
  updated_at: string
}

export type WatchCheckResult = {
  material_change: boolean
  condition_satisfied: boolean
  change_summary: string | null
  checked_at: string
  sources: WatchSource[]
}

export type WatchCheckResponse = {
  watch: Watch
  check: WatchCheckResult
}

export class WatchError extends Error {}

export async function createWatch(storyId: string): Promise<Watch> {
  let response: Response
  try {
    response = await fetch('/api/watches', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ story_id: storyId }),
    })
  } catch {
    throw new WatchError("Couldn't reach the server. Check your connection and try again.")
  }

  if (response.status === 404) {
    throw new WatchError("That story isn't in your saved brief.")
  }

  if (!response.ok) {
    throw new WatchError("Couldn't follow that story. Please try again.")
  }

  return (await response.json()) as Watch
}

export async function listWatches(): Promise<Watch[]> {
  let response: Response
  try {
    response = await fetch('/api/watches', { credentials: 'include' })
  } catch {
    throw new WatchError("Couldn't reach the server. Check your connection and try again.")
  }

  if (!response.ok) {
    throw new WatchError("Couldn't load your watches. Please try again.")
  }

  return (await response.json()) as Watch[]
}

export async function getWatch(watchId: string): Promise<Watch | null> {
  let response: Response
  try {
    response = await fetch(`/api/watches/${watchId}`, { credentials: 'include' })
  } catch {
    throw new WatchError("Couldn't reach the server. Check your connection and try again.")
  }

  if (response.status === 404) return null

  if (!response.ok) {
    throw new WatchError("Couldn't load that watch. Please try again.")
  }

  return (await response.json()) as Watch
}

export async function patchWatch(
  watchId: string,
  updates: { watch_condition?: string; major_developments_only?: boolean; status?: WatchStatus },
): Promise<Watch> {
  let response: Response
  try {
    response = await fetch(`/api/watches/${watchId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify(updates),
    })
  } catch {
    throw new WatchError("Couldn't reach the server. Check your connection and try again.")
  }

  if (!response.ok) {
    throw new WatchError("Couldn't save your changes. Please try again.")
  }

  return (await response.json()) as Watch
}

export async function checkWatch(watchId: string): Promise<WatchCheckResponse> {
  let response: Response
  try {
    response = await fetch(`/api/watches/${watchId}/check`, {
      method: 'POST',
      credentials: 'include',
    })
  } catch {
    throw new WatchError("Couldn't reach the server. Check your connection and try again.")
  }

  if (response.status === 404) {
    throw new WatchError('Watch not found.')
  }

  if (response.status === 409) {
    throw new WatchError('This watch is paused. Resume it to check for updates.')
  }

  if (!response.ok) {
    throw new WatchError("Couldn't check for updates right now. Please try again.")
  }

  return (await response.json()) as WatchCheckResponse
}

export async function deleteWatch(watchId: string): Promise<void> {
  let response: Response
  try {
    response = await fetch(`/api/watches/${watchId}`, {
      method: 'DELETE',
      credentials: 'include',
    })
  } catch {
    throw new WatchError("Couldn't reach the server. Check your connection and try again.")
  }

  if (!response.ok) {
    throw new WatchError("Couldn't remove that watch. Please try again.")
  }
}
