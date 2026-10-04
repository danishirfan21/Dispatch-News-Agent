import { NewsStory } from '../components/NewsStory'
import { mockBriefStories } from '../data/mockBrief'

const weekdayFormatter = new Intl.DateTimeFormat(undefined, { weekday: 'long' })
const timeFormatter = new Intl.DateTimeFormat(undefined, { hour: 'numeric', minute: '2-digit' })

export function BriefScreen() {
  const now = new Date()

  return (
    <main className="w-full pt-20 bg-surface min-h-[calc(100vh-140px)]">
      <div className="max-w-3xl mx-auto px-margin-mobile md:px-margin-tablet pt-10 pb-6 text-center space-y-1">
        <div className="flex flex-wrap items-center justify-center gap-2 font-sans text-label-sm uppercase tracking-widest text-on-surface-variant">
          <span className="font-semibold text-secondary">Morning Digest</span>
          <span aria-hidden="true">·</span>
          <span>{weekdayFormatter.format(now)} Edition</span>
          <span aria-hidden="true">·</span>
          <span>Updated {timeFormatter.format(now)}</span>
        </div>
        <h1 className="font-serif text-display-mobile md:text-display text-on-surface tracking-tight mt-1">
          Your Brief
        </h1>
        <p className="font-serif text-body-md text-on-surface-variant max-w-xl mx-auto pt-1">
          {mockBriefStories.length} essential developments curated for your morning reading.
        </p>
      </div>

      <div className="w-full bg-surface pb-10">
        <div className="max-w-3xl mx-auto px-margin-mobile md:px-margin-tablet divide-y divide-surface-container-high">
          {mockBriefStories.map((story) => (
            <NewsStory key={story.id} story={story} />
          ))}
        </div>
      </div>
    </main>
  )
}
