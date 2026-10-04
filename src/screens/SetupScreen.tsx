import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

const PLACEHOLDER_TEXT =
  'e.g. AI frontier research, semiconductor geopolitics, macroeconomic risk. Exclude hype cycles and celebrity commentary.'

export function SetupScreen() {
  const [interests, setInterests] = useState('')
  const navigate = useNavigate()

  return (
    <main className="w-full pt-20 bg-surface min-h-[calc(100vh-140px)]">
      <div className="relative w-full overflow-hidden">
        <div className="max-w-[840px] mx-auto px-margin-mobile md:px-margin-tablet lg:px-margin py-10">
          <div className="flex flex-col items-center text-center">
            <h1 className="font-serif text-display-mobile md:text-display text-on-surface tracking-tight mb-2">
              What do you want to stay informed about?
            </h1>
            <p className="font-serif text-body-lg text-on-surface-variant max-w-[620px] mb-10 leading-relaxed">
              Describe the topics and stories you care about in plain words. Your daily brief
              will focus exclusively on what matters to you.
            </p>

            <div className="w-full bg-surface-container-lowest rounded-xl p-6 shadow-sm border border-surface-container text-left mb-4">
              <label className="sr-only" htmlFor="interest-query">
                Your topics and interests
              </label>
              <textarea
                id="interest-query"
                rows={4}
                value={interests}
                onChange={(event) => setInterests(event.target.value)}
                placeholder={PLACEHOLDER_TEXT}
                className="w-full bg-transparent font-serif text-headline-sm text-on-surface placeholder:text-outline-variant focus:outline-none resize-none leading-relaxed"
              />
              <div className="flex items-center justify-between pt-4 mt-2 border-t border-surface-container">
                <button
                  type="button"
                  disabled
                  title="Voice dictation coming soon"
                  className="group flex items-center gap-1 px-4 py-1 rounded-lg bg-surface-container-low text-on-surface opacity-50 cursor-not-allowed"
                >
                  <MicIcon className="text-secondary" />
                  <span className="font-sans text-label-md text-on-surface">
                    Dictate interests
                  </span>
                </button>
              </div>
            </div>

            <div className="flex flex-col items-center gap-4 mb-10">
              <button
                type="button"
                onClick={() => navigate('/brief')}
                className="group inline-flex items-center justify-center gap-4 px-10 py-4 bg-primary hover:bg-primary-container text-on-primary rounded-lg transition-all shadow-md hover:shadow-xl active:scale-[0.99] min-w-[280px]"
              >
                <span className="font-sans text-label-lg uppercase tracking-wider text-on-primary">
                  Continue to Your Brief
                </span>
                <ArrowForwardIcon className="text-on-primary group-hover:translate-x-1 transition-transform" />
              </button>
              <p className="font-sans text-label-sm text-on-surface-variant max-w-[420px]">
                You can change this anytime.
              </p>
            </div>
          </div>
        </div>
      </div>
    </main>
  )
}

function MicIcon({ className = '' }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      width="18"
      height="18"
      fill="currentColor"
      className={className}
      aria-hidden="true"
    >
      <path d="M12 14a3 3 0 0 0 3-3V5a3 3 0 0 0-6 0v6a3 3 0 0 0 3 3Zm5-3a5 5 0 0 1-10 0H5a7 7 0 0 0 6 6.92V21h2v-3.08A7 7 0 0 0 19 11h-2Z" />
    </svg>
  )
}

function ArrowForwardIcon({ className = '' }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      width="18"
      height="18"
      fill="currentColor"
      className={className}
      aria-hidden="true"
    >
      <path d="M12 4l-1.41 1.41L16.17 11H4v2h12.17l-5.58 5.59L12 20l8-8-8-8Z" />
    </svg>
  )
}
