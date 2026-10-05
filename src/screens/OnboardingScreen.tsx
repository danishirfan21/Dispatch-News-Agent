import { useEffect, useRef, useState, type ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { markOnboardingSeen } from '../utils/onboarding'
import { resolvePostLoginRoute } from '../utils/postLoginRoute'

type Slide = {
  title: string
  description: string
  preview: (isActive: boolean) => ReactNode
}

const slides: Slide[] = [
  {
    title: 'Your news, without the noise.',
    description:
      'Tell Dispatch what you care about in plain words. Receive a concise Brief tailored exclusively to you.',
    preview: () => (
      <div className="w-full max-w-2xl text-left bg-surface-container-lowest rounded-2xl p-7 sm:p-9 shadow-[0_4px_24px_rgba(0,0,0,0.04)] border border-surface-container-high">
        <div className="flex items-center justify-between mb-5">
          <span className="text-label-sm uppercase tracking-wider font-semibold text-secondary font-sans">
            Example Brief
          </span>
          <span className="text-label-sm text-on-surface-variant font-sans">4 min read</span>
        </div>
        <h3 className="font-serif text-2xl sm:text-3xl font-normal text-on-surface leading-snug mb-3.5">
          New reasoning model opens API access
        </h3>
        <p className="font-sans text-sm sm:text-base text-on-surface-variant leading-relaxed mb-6">
          The new model improves coding and long-context reasoning, with API access beginning
          this week.
        </p>
        <div className="bg-surface rounded-xl p-5 border border-surface-container-high mb-5">
          <div className="text-label-sm uppercase tracking-wider font-semibold text-secondary mb-1.5 font-sans">
            Why this matters to you
          </div>
          <p className="font-sans text-sm sm:text-[15px] text-on-surface-variant leading-normal">
            You follow frontier AI releases and developer tools.
          </p>
        </div>
        <div className="text-label-sm text-on-surface-variant font-sans">Illustrative preview</div>
      </div>
    ),
  },
  {
    title: 'Follow stories, not headlines.',
    description: 'Track developing stories and set precise conditions for when you want to be alerted.',
    preview: () => (
      <div className="w-full max-w-2xl text-left bg-surface-container-lowest rounded-2xl p-7 sm:p-9 shadow-[0_4px_24px_rgba(0,0,0,0.04)] border border-surface-container-high">
        <div className="flex items-center gap-2 mb-4">
          <span className="w-2 h-2 rounded-full bg-secondary" />
          <span className="text-label-sm uppercase tracking-wider font-semibold text-on-surface-variant font-sans">
            Active Story Watch
          </span>
        </div>
        <h3 className="font-serif text-2xl sm:text-3xl font-normal text-on-surface leading-snug mb-5">
          A new developer model
        </h3>
        <div className="bg-surface rounded-xl p-5 border border-surface-container-high mb-5">
          <div className="text-label-sm text-on-surface-variant mb-1.5 font-sans">Notify me when:</div>
          <p className="font-serif text-lg sm:text-xl text-on-surface italic font-normal leading-snug">
            &ldquo;API access is publicly available.&rdquo;
          </p>
        </div>
        <div className="flex items-center justify-between text-label-sm text-on-surface-variant font-sans pt-1">
          <span className="flex items-center gap-1.5">
            <span className="material-symbols-outlined text-[16px] text-secondary" aria-hidden="true">
              radio_button_checked
            </span>
            Watching 4 trusted sources
          </span>
          <span>0 noise alerts</span>
        </div>
      </div>
    ),
  },
  {
    title: 'Know when something actually changes.',
    description:
      'Dispatch checks new reporting against what you already know, filtering repetitive coverage so only genuine developments reach you.',
    preview: () => (
      <div className="w-full max-w-2xl text-left bg-surface-container-lowest rounded-2xl p-7 sm:p-8 shadow-[0_4px_24px_rgba(0,0,0,0.04)] border border-surface-container-high flex flex-col gap-4.5">
        <div className="p-4 sm:p-5 rounded-xl bg-surface-container-low border border-outline-variant">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[11px] uppercase tracking-wider text-on-surface-variant font-sans font-semibold">
              Routine Coverage
            </span>
            <span className="text-[11px] font-sans font-medium text-on-surface-variant bg-surface-container px-2 py-0.5 rounded">
              No meaningful change
            </span>
          </div>
          <div className="font-sans text-sm sm:text-base text-on-surface-variant line-through">
            Reports repeat earlier model-release rumors.
          </div>
          <div className="text-xs text-on-surface-variant mt-1.5 font-sans">
            Filtered out: no new confirmed information.
          </div>
        </div>
        <div className="p-5 sm:p-6 rounded-xl bg-surface border border-secondary/20 shadow-sm">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[11px] uppercase tracking-wider text-secondary font-sans font-semibold">
              Confirmed update
            </span>
            <span className="text-[11px] font-sans font-semibold text-secondary bg-secondary-fixed px-2.5 py-0.5 rounded-full">
              New development
            </span>
          </div>
          <div className="font-serif text-lg sm:text-xl text-on-surface font-normal leading-snug">
            API access officially opens to developers.
          </div>
          <div className="text-xs sm:text-sm text-on-surface-variant mt-2 font-sans">
            Pricing and availability have now been published.
          </div>
        </div>
      </div>
    ),
  },
  {
    title: 'Read it. Or listen.',
    description: 'Listen to your personalized Brief with synchronized text highlighting.',
    preview: (isActive) => <AudioPreviewCard isActive={isActive} />,
  },
]

const TOTAL_SLIDES = slides.length

function formatPlaybackTime(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) return '0:00'
  const minutes = Math.floor(seconds / 60)
  const remainder = Math.floor(seconds % 60)
  return `${minutes}:${remainder.toString().padStart(2, '0')}`
}

type NarrationSentence = { text: string; start: number; end: number }

const NARRATION_SENTENCES: NarrationSentence[] = [
  { text: 'The company had previously said access would expand gradually.', start: 0, end: 3.959 },
  { text: 'API access is now available to developers on paid accounts.', start: 4.47, end: 8.673 },
  { text: 'Pricing and model limits were published alongside the release.', start: 9.114, end: 12.817 },
]

function AudioPreviewCard({ isActive }: { isActive: boolean }) {
  const audioRef = useRef<HTMLAudioElement>(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)

  const activeSentenceIndex =
    isPlaying || currentTime > 0
      ? NARRATION_SENTENCES.findIndex((sentence) => currentTime >= sentence.start && currentTime < sentence.end)
      : -1

  useEffect(() => {
    if (isActive) return
    const audio = audioRef.current
    if (audio) {
      audio.pause()
      audio.currentTime = 0
    }
    setCurrentTime(0)
  }, [isActive])

  function togglePlayback() {
    const audio = audioRef.current
    if (!audio) return
    if (audio.paused) {
      void audio.play()
    } else {
      audio.pause()
    }
  }

  const progressPercent = duration > 0 ? (currentTime / duration) * 100 : 0

  return (
    <div className="w-full max-w-2xl text-left bg-surface-container-lowest rounded-2xl p-7 sm:p-9 shadow-[0_4px_24px_rgba(0,0,0,0.04)] border border-surface-container-high">
      <audio
        ref={audioRef}
        src="/audio/onboarding-preview.mp3"
        preload="none"
        onPlay={() => setIsPlaying(true)}
        onPause={() => setIsPlaying(false)}
        onEnded={() => setIsPlaying(false)}
        onLoadedMetadata={(event) => setDuration(event.currentTarget.duration)}
        onTimeUpdate={(event) => setCurrentTime(event.currentTarget.currentTime)}
      />
      <div className="flex items-center gap-4 mb-6 pb-5 border-b border-surface-container-high">
        <button
          type="button"
          aria-label={isPlaying ? 'Pause preview' : 'Play preview'}
          aria-pressed={isPlaying}
          onClick={togglePlayback}
          className="w-11 h-11 rounded-full bg-primary text-on-primary flex items-center justify-center hover:bg-primary-container transition shadow-sm cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-secondary focus-visible:ring-offset-2"
        >
          <span className="material-symbols-outlined text-[20px]" aria-hidden="true">
            {isPlaying ? 'pause' : 'play_arrow'}
          </span>
        </button>
        <div className="flex-1">
          <div className="text-label-sm uppercase tracking-wider font-semibold text-on-surface-variant font-sans mb-1">
            Morning Audio Brief
          </div>
          <div className="w-full bg-surface-container-low rounded-full h-1.5 overflow-hidden">
            <div className="bg-secondary h-full rounded-full" style={{ width: `${progressPercent}%` }} />
          </div>
        </div>
        <span className="text-label-sm text-on-surface-variant font-sans tabular-nums">
          {formatPlaybackTime(duration > 0 ? duration - currentTime : 0)}
        </span>
      </div>
      <div className="space-y-3.5 font-serif text-lg sm:text-xl text-on-surface-variant leading-relaxed">
        {NARRATION_SENTENCES.map((sentence, sentenceIndex) => (
          <p
            key={sentence.text}
            className={
              sentenceIndex === activeSentenceIndex
                ? 'bg-secondary-fixed/45 text-on-surface px-3 py-2 rounded-lg -mx-2.5 transition-colors duration-200'
                : 'transition-colors duration-200'
            }
          >
            {sentence.text}
          </p>
        ))}
      </div>
    </div>
  )
}

const SWIPE_THRESHOLD_PX = 40

export function OnboardingScreen() {
  const [activeIndex, setActiveIndex] = useState(0)
  const navigate = useNavigate()
  const { user, isLoading } = useAuth()
  const touchStartX = useRef<number | null>(null)

  const isLastSlide = activeIndex === TOTAL_SLIDES - 1

  useEffect(() => {
    if (isLoading || !user) return
    resolvePostLoginRoute().then((destination) => navigate(destination, { replace: true }))
  }, [isLoading, user, navigate])

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'ArrowRight') {
        setActiveIndex((index) => Math.min(index + 1, TOTAL_SLIDES - 1))
      } else if (event.key === 'ArrowLeft') {
        setActiveIndex((index) => Math.max(index - 1, 0))
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  // Authenticated users are redirected away above; render nothing meanwhile
  // rather than flashing the carousel.
  if (isLoading || user) return null

  function goToSlide(nextIndex: number) {
    setActiveIndex(Math.min(Math.max(nextIndex, 0), TOTAL_SLIDES - 1))
  }

  function finishOnboarding() {
    markOnboardingSeen()
    navigate('/login', { replace: true })
  }

  function handleNext() {
    if (isLastSlide) {
      finishOnboarding()
    } else {
      goToSlide(activeIndex + 1)
    }
  }

  function handleTouchStart(event: React.TouchEvent) {
    touchStartX.current = event.touches[0].clientX
  }

  function handleTouchEnd(event: React.TouchEvent) {
    const startX = touchStartX.current
    touchStartX.current = null
    if (startX === null) return
    const deltaX = event.changedTouches[0].clientX - startX
    if (deltaX > SWIPE_THRESHOLD_PX) {
      goToSlide(activeIndex - 1)
    } else if (deltaX < -SWIPE_THRESHOLD_PX) {
      goToSlide(activeIndex + 1)
    }
  }

  return (
    <div className="w-full h-dvh min-h-dvh overflow-y-auto bg-surface flex flex-col">
      <header className="w-full max-w-5xl mx-auto px-margin-mobile pt-4 sm:pt-6 flex items-center justify-end shrink-0">
        <button
          type="button"
          onClick={finishOnboarding}
          className="font-sans text-label-md text-on-surface-variant hover:text-on-surface transition-colors font-medium rounded min-h-11 px-3 flex items-center -mr-3 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-secondary"
        >
          Skip
        </button>
      </header>

      <main
        className="w-full max-w-4xl mx-auto px-margin-mobile py-3 sm:py-5 flex-1 min-h-0 flex flex-col justify-center"
        onTouchStart={handleTouchStart}
        onTouchEnd={handleTouchEnd}
      >
        <div
          className="relative w-full"
          role="group"
          aria-roledescription="carousel"
          aria-label="Dispatch introduction"
        >
          {slides.map((slide, slideIndex) => {
            const isActive = slideIndex === activeIndex
            return (
              <section
                key={slide.title}
                aria-hidden={!isActive}
                inert={!isActive}
                aria-label={`Slide ${slideIndex + 1} of ${TOTAL_SLIDES}`}
                className={`flex flex-col items-center text-center transition-all duration-300 ease-out motion-reduce:transition-none motion-reduce:duration-0 ${
                  isActive
                    ? 'relative opacity-100 translate-y-0'
                    : 'absolute inset-0 top-0 opacity-0 translate-y-2.5 pointer-events-none'
                }`}
              >
                <h1 className="font-serif text-3xl sm:text-4xl md:text-5xl font-normal tracking-tight text-on-surface mb-2 sm:mb-3">
                  {slide.title}
                </h1>
                <p className="font-sans text-base sm:text-lg text-on-surface-variant font-normal leading-relaxed mb-5 sm:mb-6 max-w-xl">
                  {slide.description}
                </p>
                {slide.preview(isActive)}
              </section>
            )
          })}
        </div>
      </main>

      <footer className="w-full max-w-2xl mx-auto px-margin-mobile pb-5 sm:pb-7 pt-3 flex items-center justify-between shrink-0">
        <div className="w-28 flex justify-start">
          {activeIndex > 0 && (
            <button
              type="button"
              onClick={() => goToSlide(activeIndex - 1)}
              aria-label="Back to previous slide"
              className="text-sm font-sans text-on-surface-variant hover:text-on-surface transition font-medium flex items-center gap-1 min-h-11 -ml-3 px-3 rounded cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-secondary"
            >
              <span className="material-symbols-outlined text-[16px]" aria-hidden="true">
                west
              </span>
              Back
            </button>
          )}
        </div>

        <div className="flex items-center gap-2" role="tablist" aria-label="Slide indicators">
          {slides.map((_, dotIndex) => {
            const isActive = dotIndex === activeIndex
            return (
              <button
                key={dotIndex}
                type="button"
                role="tab"
                aria-label={`Go to slide ${dotIndex + 1} of ${TOTAL_SLIDES}`}
                aria-selected={isActive}
                onClick={() => goToSlide(dotIndex)}
                className="min-h-11 min-w-11 flex items-center justify-center rounded-full cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-secondary"
              >
                <span
                  className={`block h-1.5 rounded-full transition-all duration-300 motion-reduce:transition-none motion-reduce:duration-0 ${
                    isActive ? 'w-6 bg-primary' : 'w-2 bg-outline-variant hover:bg-outline'
                  }`}
                />
              </button>
            )
          })}
        </div>

        <div className="w-28 flex justify-end">
          <button
            type="button"
            onClick={handleNext}
            className="px-5 min-h-11 rounded-full bg-primary text-on-primary hover:bg-primary-container transition font-sans text-sm font-medium flex items-center justify-center gap-1.5 shadow-sm whitespace-nowrap cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-secondary focus-visible:ring-offset-2"
          >
            {isLastSlide ? (
              'Get started'
            ) : (
              <>
                Next
                <span className="material-symbols-outlined text-[16px]" aria-hidden="true">
                  east
                </span>
              </>
            )}
          </button>
        </div>
      </footer>
    </div>
  )
}
