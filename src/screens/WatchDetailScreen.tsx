import { Link, useParams } from 'react-router-dom'
import { mockWatchedStories } from '../data/mockWatches'

export function WatchDetailScreen() {
  const { id } = useParams()
  const story = mockWatchedStories.find((item) => item.id === id)

  return (
    <main className="w-full pt-20 bg-surface min-h-[calc(100vh-140px)]">
      <div className="max-w-3xl mx-auto px-margin-mobile md:px-margin-tablet py-12 text-center">
        <span className="font-sans text-label-sm uppercase tracking-wider text-on-surface-variant font-semibold">
          {story?.category ?? 'Story Watch'}
        </span>
        <h1 className="font-serif text-display-mobile md:text-display text-on-surface tracking-tight mt-2 mb-4">
          {story?.title ?? 'Story not found'}
        </h1>
        <p className="font-serif text-body-lg text-on-surface-variant mb-8">
          The detailed watch view for this story isn't built yet.
        </p>
        <Link
          to="/watching"
          className="inline-flex items-center gap-1 font-sans text-label-md text-on-surface hover:text-secondary transition-colors"
        >
          &larr; Back to Watching
        </Link>
      </div>
    </main>
  )
}
