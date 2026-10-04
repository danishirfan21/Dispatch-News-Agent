import { useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { getLatestBrief, type BriefStoryResponse } from '../api/brief'
import type { BriefStory } from '../data/mockBrief'
import { minutesSince } from '../utils/relativeTime'
import { BriefScreen } from './BriefScreen'

type BriefLocationState = { stories?: BriefStoryResponse[] } | null

function toBriefStory(story: BriefStoryResponse): BriefStory {
  return {
    id: story.id,
    category: story.topic,
    minutesAgo: story.published_at ? minutesSince(story.published_at) : 0,
    headline: story.headline,
    summary: story.summary,
    whyItMatters: story.why_this_matters_to_you,
    sources: story.sources,
  }
}

/**
 * Picks between the real curated brief and the existing polished mock Brief.
 * A freshly generated brief arrives via router state. Otherwise, the
 * authenticated user's latest saved brief is loaded from the backend so it
 * survives refreshes and logout/login. Only falls back to the mock brief
 * when the user has no saved brief yet.
 */
export function BriefRoute() {
  const location = useLocation()
  const state = location.state as BriefLocationState

  const [savedStories, setSavedStories] = useState<BriefStoryResponse[] | null>(null)
  const [isLoading, setIsLoading] = useState(!state?.stories)

  useEffect(() => {
    if (state?.stories) return

    getLatestBrief()
      .then((latest) => setSavedStories(latest?.stories ?? null))
      .finally(() => setIsLoading(false))
  }, [state])

  if (state?.stories) {
    return <BriefScreen stories={state.stories.map(toBriefStory)} />
  }

  if (isLoading) {
    return <main className="w-full pt-20 bg-surface min-h-[calc(100vh-140px)]" />
  }

  if (savedStories) {
    return <BriefScreen stories={savedStories.map(toBriefStory)} />
  }

  return <BriefScreen />
}
