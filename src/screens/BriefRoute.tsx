import { useLocation } from 'react-router-dom'
import type { Article } from '../api/news'
import { BriefScreen } from './BriefScreen'
import { RawNewsResults } from './RawNewsResults'

type BriefLocationState = { articles?: Article[] } | null

/**
 * Picks between the real (but temporary/unstyled) retrieved-news test view
 * and the existing polished mock Brief. Navigating here directly (no
 * articles in router state) keeps showing the mock Brief unchanged.
 */
export function BriefRoute() {
  const location = useLocation()
  const state = location.state as BriefLocationState

  if (state?.articles) {
    return <RawNewsResults articles={state.articles} />
  }

  return <BriefScreen />
}
