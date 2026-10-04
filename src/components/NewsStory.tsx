import { useState } from 'react'
import type { BriefStory } from '../data/mockBrief'
import { formatRelativeTime } from '../utils/relativeTime'

type NewsStoryProps = {
  story: BriefStory
}

export function NewsStory({ story }: NewsStoryProps) {
  const [isFollowing, setIsFollowing] = useState(false)

  return (
    <article className="py-10 space-y-4">
      <div className="flex items-center justify-between gap-2">
        <span className="font-sans text-label-sm uppercase tracking-wider font-semibold text-secondary">
          {story.category}
        </span>
        <span className="font-sans text-label-sm text-on-surface-variant whitespace-nowrap">
          {formatRelativeTime(story.minutesAgo)}
        </span>
      </div>

      <h2 className="font-serif text-headline-md text-on-surface tracking-tight leading-snug">
        {story.headline}
      </h2>

      <p className="font-serif text-body-lg text-on-surface leading-relaxed">{story.summary}</p>

      <div className="bg-surface-container-low p-4 rounded-lg space-y-1">
        <span className="block font-sans text-label-sm uppercase font-semibold text-secondary tracking-wider">
          Why this matters to you
        </span>
        <p className="font-serif text-body-md text-on-surface-variant">{story.whyItMatters}</p>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-2 pt-1">
        <span className="font-sans text-label-sm text-on-surface-variant">
          {story.sources.map((source, index) => (
            <span key={source.name}>
              {index > 0 && ' · '}
              {source.url ? (
                <a
                  href={source.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-secondary underline-offset-2 hover:underline"
                >
                  {source.name}
                </a>
              ) : (
                source.name
              )}
            </span>
          ))}
        </span>
        <button
          type="button"
          onClick={() => setIsFollowing((prev) => !prev)}
          aria-pressed={isFollowing}
          className={
            isFollowing
              ? 'inline-flex items-center gap-1.5 px-4 py-1 rounded-lg font-sans text-label-md font-semibold bg-secondary text-on-primary transition-colors'
              : 'inline-flex items-center gap-1.5 px-4 py-1 rounded-lg font-sans text-label-md text-on-surface-variant hover:text-secondary transition-colors'
          }
        >
          <BookmarkIcon filled={isFollowing} />
          {isFollowing ? 'Following' : 'Follow story'}
        </button>
      </div>
    </article>
  )
}

function BookmarkIcon({ filled }: { filled: boolean }) {
  return (
    <svg
      viewBox="0 0 24 24"
      width="16"
      height="16"
      aria-hidden="true"
      fill={filled ? 'currentColor' : 'none'}
      stroke={filled ? 'none' : 'currentColor'}
      strokeWidth={1.8}
    >
      <path d="M6 3h12a1 1 0 0 1 1 1v17l-7-4-7 4V4a1 1 0 0 1 1-1Z" />
    </svg>
  )
}
