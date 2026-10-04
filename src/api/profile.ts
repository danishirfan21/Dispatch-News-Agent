import type { Interest } from './interests'

export type Profile = {
  raw_interest_text: string
  interests: Interest[]
  excluded_topics: string[]
  updated_at: string
}

export class ProfileError extends Error {}

export async function getProfile(): Promise<Profile | null> {
  let response: Response
  try {
    response = await fetch('/api/profile', { credentials: 'include' })
  } catch {
    throw new ProfileError("Couldn't reach the server. Check your connection and try again.")
  }

  if (response.status === 404) return null

  if (!response.ok) {
    throw new ProfileError("Couldn't load your saved profile. Please try again.")
  }

  return (await response.json()) as Profile
}

export async function putProfile(
  rawInterestText: string,
  interests: Interest[],
  excludedTopics: string[],
): Promise<Profile> {
  let response: Response
  try {
    response = await fetch('/api/profile', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({
        raw_interest_text: rawInterestText,
        interests,
        excluded_topics: excludedTopics,
      }),
    })
  } catch {
    throw new ProfileError("Couldn't reach the server. Check your connection and try again.")
  }

  if (!response.ok) {
    throw new ProfileError("Couldn't save your profile. Please try again.")
  }

  return (await response.json()) as Profile
}
