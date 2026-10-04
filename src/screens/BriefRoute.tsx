import { useLocation } from 'react-router-dom'
import type { BriefStoryResponse } from '../api/brief'
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
 * Navigating here directly (no stories in router state) keeps showing the
 * mock Brief unchanged.
 */
export function BriefRoute() {
  const location = useLocation()
  const state = location.state as BriefLocationState

  if (state?.stories) {
    return <BriefScreen stories={state.stories.map(toBriefStory)} />
  }

  return <BriefScreen />
}
