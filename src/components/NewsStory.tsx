import { useEffect, useState } from 'react'
import { createWatch, WatchError } from '../api/watches'
import type { BriefAudioSegment } from '../api/briefAudio'
import type { BriefStory } from '../data/mockBrief'
import { formatRelativeTime } from '../utils/relativeTime'
import { splitSentences } from '../utils/splitSentences'

type NewsStoryProps = {
  story: BriefStory
  segments?: BriefAudioSegment[]
  activeSegment?: BriefAudioSegment | null
  initiallyFollowing?: boolean
}

export function NewsStory({ story, segments, activeSegment, initiallyFollowing }: NewsStoryProps) {
  const [isFollowing, setIsFollowing] = useState(Boolean(initiallyFollowing))
  const [isSaving, setIsSaving] = useState(false)
  const [followError, setFollowError] = useState<string | null>(null)

  useEffect(() => {
    if (initiallyFollowing) setIsFollowing(true)
  }, [initiallyFollowing])

  async function handleFollowClick() {
    if (isFollowing || isSaving) return

    setIsSaving(true)
    setFollowError(null)
    try {
      await createWatch(story.id)
      setIsFollowing(true)
    } catch (error) {
      setFollowError(error instanceof WatchError ? error.message : "Couldn't follow that story. Please try again.")
    } finally {
      setIsSaving(false)
    }
  }

  const isCurrentStory = activeSegment?.story_id === story.id
  const headlineSegment = segments?.find((segment) => segment.type === 'headline')
  const summarySegments = segments?.filter((segment) => segment.type === 'summary')
  const isHeadlineActive = Boolean(headlineSegment) && activeSegment === headlineSegment
  const summarySentences = summarySegments?.length ? splitSentences(story.summary) : null

  return (
    <article className={`py-10 space-y-4 transition-colors ${isCurrentStory ? 'bg-surface-container-lowest/60 -mx-4 px-4 rounded-xl' : ''}`}>
      <div className="flex items-center justify-between gap-2">
        <span className="font-sans text-label-sm uppercase tracking-wider font-semibold text-secondary">
          {story.category}
        </span>
        <span className="font-sans text-label-sm text-on-surface-variant whitespace-nowrap">
          {formatRelativeTime(story.minutesAgo)}
        </span>
      </div>

      <h2
        className={`font-serif text-headline-md tracking-tight leading-snug transition-colors rounded px-1 -mx-1 ${
          isHeadlineActive ? 'bg-secondary/15 text-on-surface' : 'text-on-surface'
        }`}
      >
        {story.headline}
      </h2>

      <p className="font-serif text-body-lg text-on-surface leading-relaxed">
        {summarySentences
          ? summarySentences.map((sentence, index) => {
              const isActive = Boolean(summarySegments?.[index]) && activeSegment === summarySegments?.[index]
              return (
                <span
                  key={index}
                  className={`transition-colors rounded ${isActive ? 'bg-secondary/15' : ''}`}
                >
                  {sentence}
                  {index < summarySentences.length - 1 ? ' ' : ''}
                </span>
              )
            })
          : story.summary}
      </p>

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
        <div className="flex items-center gap-2">
          {followError && (
            <span role="alert" className="font-sans text-label-sm text-secondary">
              {followError}
            </span>
          )}
          <button
            type="button"
            onClick={handleFollowClick}
            disabled={isSaving || isFollowing}
            aria-pressed={isFollowing}
            className={
              isFollowing
                ? 'inline-flex items-center gap-1.5 px-4 py-1 rounded-lg font-sans text-label-md font-semibold bg-secondary text-on-primary transition-colors cursor-pointer disabled:cursor-default'
                : 'inline-flex items-center gap-1.5 px-4 py-1 rounded-lg font-sans text-label-md text-on-surface-variant hover:text-secondary transition-colors cursor-pointer disabled:opacity-60 disabled:cursor-not-allowed'
            }
          >
            <BookmarkIcon filled={isFollowing} />
            {isFollowing ? 'Following' : isSaving ? 'Following…' : 'Follow story'}
          </button>
        </div>
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
