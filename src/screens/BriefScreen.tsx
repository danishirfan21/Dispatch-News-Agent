import { NewsStory } from '../components/NewsStory'
import { mockBriefStories, type BriefStory } from '../data/mockBrief'
import { useBriefNarration } from '../hooks/useBriefNarration'

type BriefScreenProps = {
  stories?: BriefStory[]
}

const LISTEN_LABELS: Record<string, string> = {
  idle: 'Listen to Your Brief',
  loading: 'Preparing audio…',
  playing: 'Pause',
  paused: 'Resume',
  finished: 'Listen again',
}

export function BriefScreen({ stories }: BriefScreenProps) {
  const briefStories = stories ?? mockBriefStories
  const {
    state: narrationState,
    error: narrationError,
    activeSegment,
    segments,
    toggle,
    containerRef,
  } = useBriefNarration()

  return (
    <main className="w-full pt-20 bg-surface min-h-[calc(100vh-140px)]">
      <div className="max-w-3xl mx-auto px-margin-mobile md:px-margin-tablet pt-10 pb-6 text-center space-y-1">
        <div className="flex flex-wrap items-center justify-center gap-2 font-sans text-label-sm uppercase tracking-widest text-on-surface-variant">
          <span className="font-semibold text-secondary">Personalized Brief</span>
        </div>
        <h1 className="font-serif text-display-mobile md:text-display text-on-surface tracking-tight mt-1">
          Your Brief
        </h1>
        <p className="font-serif text-body-md text-on-surface-variant max-w-xl mx-auto pt-1">
          {briefStories.length} essential developments selected for you.
        </p>

        <div className="pt-4">
          <button
            type="button"
            onClick={toggle}
            disabled={narrationState === 'loading'}
            className="inline-flex items-center gap-2 px-5 py-2 rounded-lg bg-surface-container-low text-on-surface font-sans text-label-md hover:bg-surface-container transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
          >
            <SpeakerIcon />
            {LISTEN_LABELS[narrationState]}
          </button>
          {narrationError && (
            <p role="alert" className="font-sans text-label-sm text-secondary mt-2">
              {narrationError}
            </p>
          )}
          <div ref={containerRef} className="flex justify-center mt-2" />
        </div>
      </div>

      <div className="w-full bg-surface pb-10">
        <div className="max-w-3xl mx-auto px-margin-mobile md:px-margin-tablet divide-y divide-surface-container-high">
          {briefStories.map((story) => (
            <NewsStory
              key={story.id}
              story={story}
              segments={segments.filter((segment) => segment.story_id === story.id)}
              activeSegment={activeSegment}
            />
          ))}
        </div>
      </div>
    </main>
  )
}

function SpeakerIcon() {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor" aria-hidden="true">
      <path d="M3 10v4h4l5 5V5L7 10H3Zm13.5 2a4.5 4.5 0 0 0-2.5-4.03v8.06A4.5 4.5 0 0 0 16.5 12Z" />
    </svg>
  )
}
