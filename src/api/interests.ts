export type InterestPriority = 'high' | 'medium' | 'low'

export type Interest = {
  topic: string
  priority: InterestPriority
  search_terms: string[]
}

export type InterestProfile = {
  interests: Interest[]
  excluded_topics: string[]
}

export class InterestParseError extends Error {}

export async function parseInterests(text: string): Promise<InterestProfile> {
  let response: Response
  try {
    response = await fetch('/api/interests/parse', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    })
  } catch {
    throw new InterestParseError("Couldn't reach the server. Check your connection and try again.")
  }

  if (!response.ok) {
    const message = await response
      .json()
      .then((body) => (typeof body?.detail === 'string' ? body.detail : null))
      .catch(() => null)
    throw new InterestParseError(message ?? 'Something went wrong. Please try again.')
  }

  try {
    return (await response.json()) as InterestProfile
  } catch {
    throw new InterestParseError("We couldn't understand the response. Please try again.")
  }
}
