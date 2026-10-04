import type { InterestProfile } from './interests'

export type Article = {
  id: string
  topic: string
  title: string
  source: string
  url: string
  published_at: string | null
  snippet: string | null
  thumbnail: string | null
}

export type NewsSearchResponse = {
  articles: Article[]
}

export class NewsSearchError extends Error {}

export async function searchNews(profile: InterestProfile): Promise<NewsSearchResponse> {
  let response: Response
  try {
    response = await fetch('/api/news/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(profile),
    })
  } catch {
    throw new NewsSearchError("Couldn't reach the server. Check your connection and try again.")
  }

  if (!response.ok) {
    const message = await response
      .json()
      .then((body) => (typeof body?.detail === 'string' ? body.detail : null))
      .catch(() => null)
    throw new NewsSearchError(message ?? 'Something went wrong fetching news. Please try again.')
  }

  try {
    return (await response.json()) as NewsSearchResponse
  } catch {
    throw new NewsSearchError("We couldn't understand the response. Please try again.")
  }
}
