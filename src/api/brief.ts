import type { InterestProfile } from './interests'
import type { Article } from './news'

export type BriefStorySource = {
  name: string
  url: string
}

export type BriefStoryImportance = 'high' | 'medium' | 'low'

export type BriefStoryResponse = {
  id: string
  topic: string
  headline: string
  summary: string
  why_this_matters_to_you: string
  source_article_ids: string[]
  sources: BriefStorySource[]
  published_at: string | null
  importance: BriefStoryImportance
}

export type BriefGenerateResponse = {
  stories: BriefStoryResponse[]
}

export type LatestBriefResponse = {
  generated_at: string
  stories: BriefStoryResponse[]
}

export class BriefGenerateError extends Error {}

export async function generateBrief(
  interestProfile: InterestProfile,
  articles: Article[],
): Promise<BriefGenerateResponse> {
  let response: Response
  try {
    response = await fetch('/api/brief/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ interest_profile: interestProfile, articles }),
    })
  } catch {
    throw new BriefGenerateError("Couldn't reach the server. Check your connection and try again.")
  }

  if (!response.ok) {
    const message = await response
      .json()
      .then((body) => (typeof body?.detail === 'string' ? body.detail : null))
      .catch(() => null)
    throw new BriefGenerateError(message ?? "Couldn't build your brief. Please try again.")
  }

  try {
    return (await response.json()) as BriefGenerateResponse
  } catch {
    throw new BriefGenerateError("We couldn't understand the response. Please try again.")
  }
}

export async function getLatestBrief(): Promise<LatestBriefResponse | null> {
  const response = await fetch('/api/brief/latest', { credentials: 'include' }).catch(() => null)
  if (!response || response.status === 404 || !response.ok) return null
  return (await response.json()) as LatestBriefResponse
}
