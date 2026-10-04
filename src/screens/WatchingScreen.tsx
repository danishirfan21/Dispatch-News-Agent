import { WatchCard } from '../components/WatchCard'
import { mockWatchedStories } from '../data/mockWatches'

export function WatchingScreen() {
  return (
    <main className="w-full pt-20 bg-surface min-h-[calc(100vh-140px)]">
      <div className="max-w-3xl mx-auto px-margin-mobile md:px-margin-tablet py-12">
        <header className="mb-10">
          <h1 className="font-serif text-display-mobile md:text-display text-on-surface tracking-tight leading-none mb-2">
            Watching
          </h1>
          <p className="font-serif text-body-lg text-on-surface-variant">
            Stories you're following
          </p>
        </header>

        <div className="space-y-4">
          {mockWatchedStories.map((story) => (
            <WatchCard key={story.id} story={story} />
          ))}
        </div>

        <div className="mt-8 pt-6 border-t border-surface-container flex justify-center">
          <button
            type="button"
            disabled
            title="Tracking new topics coming soon"
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-surface-container text-on-surface font-sans text-label-md opacity-50 cursor-not-allowed"
          >
            <PlusIcon />
            <span>Track new topic</span>
          </button>
        </div>
      </div>
    </main>
  )
}

function PlusIcon() {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" aria-hidden="true">
      <path d="M11 5h2v6h6v2h-6v6h-2v-6H5v-2h6V5Z" />
    </svg>
  )
}
