import type { KeyboardEvent, MouseEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import type { Watch } from '../api/watches'
import { formatRelativeTime, minutesSince } from '../utils/relativeTime'

type WatchCardProps = {
  watch: Watch
}

export function WatchCard({ watch }: WatchCardProps) {
  const navigate = useNavigate()
  const hasNewDevelopment = watch.development_status === 'new_development'
  const href = `/watching/${watch.id}`

  function goToDetail() {
    navigate(href)
  }

  function handleKeyDown(event: KeyboardEvent<HTMLElement>) {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      goToDetail()
    }
  }

  function handleViewClick(event: MouseEvent) {
    event.stopPropagation()
  }

  return (
    <article
      role="link"
      tabIndex={0}
      aria-label={watch.headline}
      onClick={goToDetail}
      onKeyDown={handleKeyDown}
      className="group relative overflow-hidden bg-surface-container-lowest p-6 rounded-xl border border-surface-container hover:border-outline-variant transition-all cursor-pointer"
    >
      {hasNewDevelopment && (
        <span
          aria-hidden="true"
          className="absolute left-0 top-0 bottom-0 w-1 bg-secondary"
        />
      )}

      <div className="flex items-center justify-between gap-4 mb-3 flex-wrap">
        <div className="flex items-center gap-2 flex-wrap">
          <span
            className={`font-sans text-label-sm uppercase tracking-wider font-semibold ${
              hasNewDevelopment ? 'text-secondary' : 'text-on-surface-variant'
            }`}
          >
            {watch.topic}
          </span>
          <span className="text-outline-variant" aria-hidden="true">
            &bull;
          </span>
          <span
            className={`font-sans text-label-sm ${
              hasNewDevelopment ? 'text-secondary font-medium' : 'text-on-surface-variant'
            }`}
          >
            Updated {formatRelativeTime(minutesSince(watch.updated_at))}
          </span>
          {watch.status === 'paused' && (
            <>
              <span className="text-outline-variant" aria-hidden="true">
                &bull;
              </span>
              <span className="font-sans text-label-sm text-on-surface-variant">Paused</span>
            </>
          )}
        </div>

        <div
          className={`inline-flex items-center gap-2 px-3 py-1 rounded-full font-sans text-label-sm uppercase tracking-wide ${
            hasNewDevelopment
              ? 'bg-secondary-fixed text-on-secondary-fixed font-semibold'
              : 'bg-surface-container text-on-surface-variant'
          }`}
        >
          <span
            aria-hidden="true"
            className={`w-1.5 h-1.5 rounded-full ${
              hasNewDevelopment ? 'bg-secondary animate-ping' : 'bg-outline-variant'
            }`}
          />
          <span>{hasNewDevelopment ? 'New development' : 'No meaningful change'}</span>
        </div>
      </div>

      <h2 className="font-serif text-headline-md text-on-surface tracking-tight mb-2 group-hover:text-primary transition-colors">
        {watch.headline}
      </h2>
      <p className="font-serif text-body-md text-on-surface-variant leading-relaxed mb-4">
        {hasNewDevelopment && watch.latest_change ? watch.latest_change.summary : watch.summary}
      </p>

      <div className="flex items-center justify-end">
        <Link
          to={href}
          onClick={handleViewClick}
          className={`inline-flex items-center gap-1 font-sans text-label-md transition-all group-hover:translate-x-0.5 ${
            hasNewDevelopment
              ? 'text-secondary font-semibold hover:opacity-80'
              : 'text-on-surface hover:text-secondary'
          }`}
        >
          <span>View</span>
          <ArrowForwardIcon />
        </Link>
      </div>
    </article>
  )
}

function ArrowForwardIcon() {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor" aria-hidden="true">
      <path d="M12 4l-1.41 1.41L16.17 11H4v2h12.17l-5.58 5.59L12 20l8-8-8-8Z" />
    </svg>
  )
}
