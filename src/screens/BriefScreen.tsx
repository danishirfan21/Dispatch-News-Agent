import { NewsStory } from '../components/NewsStory'
import { mockBriefStories, type BriefStory } from '../data/mockBrief'

type BriefScreenProps = {
  stories?: BriefStory[]
}

export function BriefScreen({ stories }: BriefScreenProps) {
  const briefStories = stories ?? mockBriefStories

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
      </div>

      <div className="w-full bg-surface pb-10">
        <div className="max-w-3xl mx-auto px-margin-mobile md:px-margin-tablet divide-y divide-surface-container-high">
          {briefStories.map((story) => (
            <NewsStory key={story.id} story={story} />
          ))}
        </div>
      </div>
    </main>
  )
}
