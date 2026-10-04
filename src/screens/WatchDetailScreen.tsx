import { useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { mockWatchedStories } from '../data/mockWatches'
import { formatRelativeTime, minutesSince } from '../utils/relativeTime'

export function WatchDetailScreen() {
  const { id } = useParams()
  const story = mockWatchedStories.find((item) => item.id === id)

  // Hooks must run unconditionally, so they're declared before the
  // not-found check below and simply go unused when story is missing.
  const [watchCondition, setWatchCondition] = useState(story?.watchCondition ?? '')
  const [majorDevelopmentsOnly, setMajorDevelopmentsOnly] = useState(
    story?.majorDevelopmentsOnly ?? false,
  )
  const [isPaused, setIsPaused] = useState(false)
  const [showSavedToast, setShowSavedToast] = useState(false)
  const toastTimeoutRef = useRef<ReturnType<typeof setTimeout>>(undefined)

  useEffect(() => {
    return () => {
      if (toastTimeoutRef.current) clearTimeout(toastTimeoutRef.current)
    }
  }, [])

  if (!story) {
    return (
      <main className="w-full pt-20 bg-surface min-h-[calc(100vh-140px)]">
        <div className="max-w-3xl mx-auto px-margin-mobile md:px-margin-tablet py-12 text-center">
          <h1 className="font-serif text-display-mobile md:text-display text-on-surface tracking-tight mb-4">
            Story not found
          </h1>
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

  const relativeUpdatedAt = formatRelativeTime(minutesSince(story.updatedAt))

  function handleSaveCriteria() {
    setShowSavedToast(true)
    if (toastTimeoutRef.current) clearTimeout(toastTimeoutRef.current)
    toastTimeoutRef.current = setTimeout(() => setShowSavedToast(false), 3500)
  }

  return (
    <main className="w-full pt-20 bg-surface min-h-[calc(100vh-140px)]">
      <div className="flex flex-col w-full">
        <div className="w-full bg-surface-container-low">
          <div className="max-w-[1440px] mx-auto px-margin-mobile md:px-margin-tablet lg:px-margin py-2 flex flex-wrap items-center justify-between gap-2">
            <Link
              to="/watching"
              className="group inline-flex items-center gap-1 font-sans text-label-md text-on-surface-variant hover:text-on-surface transition-colors"
            >
              <BackArrowIcon className="group-hover:-translate-x-0.5 transition-transform" />
              <span>Back to Watching</span>
            </Link>
            <span className="font-sans text-label-sm text-on-surface-variant">
              Updated {relativeUpdatedAt}
            </span>
          </div>
        </div>

        <div className="max-w-3xl mx-auto w-full px-margin-mobile md:px-margin-tablet py-10 space-y-10">
          <header className="space-y-4">
            <div className="flex items-center gap-1 flex-wrap">
              <span className="font-sans text-label-sm uppercase tracking-widest text-on-surface-variant">
                {story.category}
              </span>
              <span className="font-sans text-label-sm text-on-surface-variant">&bull;</span>
              <span className="font-sans text-label-sm uppercase tracking-widest text-secondary font-semibold">
                Watching
              </span>
            </div>
            <h1 className="font-serif text-headline-lg text-on-surface tracking-tight leading-tight">
              {story.title}
            </h1>
            <div className="inline-flex items-center gap-1 bg-surface-container-low px-4 py-1 rounded-full">
              <span className="w-2 h-2 rounded-full bg-secondary" aria-hidden="true" />
              <span className="font-sans text-label-md text-on-surface font-medium">
                {isPaused ? 'Paused' : 'Watching'} &bull; Last checked {relativeUpdatedAt}
              </span>
            </div>
          </header>

          <section className="bg-surface-container-lowest rounded-xl p-6 shadow-sm space-y-4 border-l-2 border-secondary">
            <div className="space-y-1">
              <span className="font-sans text-label-sm text-secondary font-semibold uppercase tracking-wider">
                The Latest Meaningful Change
              </span>
              <h2 className="font-serif text-headline-sm text-on-surface">
                {story.latestMeaningfulChange.heading}
              </h2>
            </div>
            <p className="font-serif text-body-md text-on-surface">
              {story.latestMeaningfulChange.detail}
            </p>
            <div className="bg-surface-container-low rounded-lg p-4 border-l-2 border-secondary">
              <p className="font-sans text-body-sm text-on-surface">
                <span className="font-semibold text-secondary">Current Status: </span>
                {story.currentStatus}
              </p>
            </div>
          </section>

          <section className="bg-surface-container-low rounded-xl p-6 space-y-2">
            <div className="flex items-center justify-between gap-2">
              <span className="font-sans text-label-sm text-on-surface-variant uppercase tracking-wider font-semibold">
                What you already know
              </span>
              <span className="font-sans text-label-sm text-on-surface-variant">
                No redundant alerts
              </span>
            </div>
            <p className="font-sans text-body-sm text-on-surface">{story.knownContext}</p>
            <div className="pt-1">
              <p className="font-sans text-label-sm text-on-surface-variant italic">
                We won't alert you unless something meaningfully changes.
              </p>
            </div>
          </section>

          <section className="bg-surface-container-lowest rounded-xl p-6 shadow-sm space-y-6">
            <div className="space-y-1">
              <h2 className="font-serif text-headline-sm text-on-surface">Notify me when:</h2>
              <p className="font-sans text-body-sm text-on-surface-variant">
                You will only receive an update when this specific criterion is satisfied.
              </p>
            </div>

            <div className="space-y-4">
              <label className="sr-only" htmlFor="watch-condition">
                Notify me when
              </label>
              <textarea
                id="watch-condition"
                rows={3}
                value={watchCondition}
                onChange={(event) => setWatchCondition(event.target.value)}
                className="w-full bg-surface-container-low rounded-lg p-4 font-serif text-body-md text-on-surface outline-none transition-shadow shadow-inner resize-none focus:ring-1 focus:ring-secondary"
              />

              <div className="flex flex-wrap items-center justify-between gap-2 pt-1">
                <label className="inline-flex items-center gap-1 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={majorDevelopmentsOnly}
                    onChange={(event) => setMajorDevelopmentsOnly(event.target.checked)}
                    className="w-4 h-4 rounded-sm accent-primary cursor-pointer"
                  />
                  <span className="font-sans text-label-md text-on-surface">
                    Notify only on major developments
                  </span>
                </label>
              </div>
            </div>

            <div className="pt-4 border-t border-surface-container space-y-1">
              <div className="flex flex-wrap items-center justify-between gap-2 text-on-surface-variant">
                <span className="font-sans text-label-sm">
                  Monitored sources: {story.monitoredSources.join(', ')}
                </span>
                <button
                  type="button"
                  disabled
                  title="Coming soon"
                  className="font-sans text-label-sm text-secondary opacity-50 cursor-not-allowed shrink-0"
                >
                  Inspect sources
                </button>
              </div>
            </div>

            <div className="pt-4 flex flex-wrap items-center justify-between gap-4 border-t border-surface-container">
              <button
                type="button"
                onClick={handleSaveCriteria}
                className="px-6 py-2 rounded-lg bg-primary text-on-primary hover:bg-primary-container font-sans text-label-lg transition-colors flex items-center gap-1 shadow-sm"
              >
                <CheckIcon />
                <span>Save criteria</span>
              </button>

              <div className="flex items-center gap-4">
                <button
                  type="button"
                  onClick={() => setIsPaused((prev) => !prev)}
                  className="px-4 py-2 rounded-lg bg-surface-container-low text-on-surface-variant hover:text-on-surface font-sans text-label-lg transition-colors"
                >
                  {isPaused ? 'Resume watching' : 'Pause watching'}
                </button>
              </div>
            </div>
          </section>
        </div>
      </div>

      <div
        role="status"
        aria-live="polite"
        className={`fixed bottom-6 right-6 bg-primary text-on-primary px-6 py-2 rounded-lg shadow-xl flex items-center gap-2 z-50 transition-all duration-300 ${
          showSavedToast ? 'translate-y-0 opacity-100' : 'translate-y-24 opacity-0 pointer-events-none'
        }`}
      >
        <VerifiedIcon />
        <span className="font-sans text-label-md font-semibold">Watching Criteria Saved</span>
      </div>
    </main>
  )
}

function BackArrowIcon({ className = '' }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      width="16"
      height="16"
      fill="currentColor"
      className={className}
      aria-hidden="true"
    >
      <path d="M20 11H7.83l5.59-5.59L12 4l-8 8 8 8 1.41-1.41L7.83 13H20v-2Z" />
    </svg>
  )
}

function CheckIcon() {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" aria-hidden="true">
      <path d="M9 16.17 4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z" />
    </svg>
  )
}

function VerifiedIcon() {
  return (
    <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor" className="text-secondary" aria-hidden="true">
      <path d="M12 2 9.5 4.5 6 4l-.5 3.5L2 9l1.5 3L2 15l3.5 1.5L6 20l3.5-.5L12 22l2.5-2.5 3.5.5.5-3.5L22 15l-1.5-3L22 9l-3.5-1.5L18 4l-3.5.5L12 2Zm-1.2 13.8L6.9 11.9l1.27-1.27 2.63 2.62 5.03-5.03 1.27 1.27-6.3 6.31Z" />
    </svg>
  )
}
