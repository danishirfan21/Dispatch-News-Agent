import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { BriefGenerateError, generateBrief } from '../api/brief'
import { InterestParseError, parseInterests, type InterestProfile } from '../api/interests'
import { NewsSearchError, searchNews } from '../api/news'
import { ProfileError, getProfile, putProfile } from '../api/profile'
import { useVoiceDictation } from '../hooks/useVoiceDictation'

const PLACEHOLDER_TEXT =
  'e.g. New AI models and developer tools, major cybersecurity news, NVIDIA and semiconductor updates. Skip celebrity news and speculation.'

export function SetupScreen() {
  const [interests, setInterests] = useState('')
  const [profile, setProfile] = useState<InterestProfile | null>(null)
  const [isLoadingSavedProfile, setIsLoadingSavedProfile] = useState(true)
  const [isLoading, setIsLoading] = useState(false)
  const [isBuildingBrief, setIsBuildingBrief] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const navigate = useNavigate()

  const {
    state: dictationState,
    error: dictationError,
    toggle: toggleDictation,
  } = useVoiceDictation((transcript) => {
    setInterests((current) => {
      const trimmed = current.trim()
      return trimmed ? `${trimmed} ${transcript}` : transcript
    })
  })

  useEffect(() => {
    getProfile()
      .then((saved) => {
        if (!saved) return
        setInterests(saved.raw_interest_text)
        setProfile({ interests: saved.interests, excluded_topics: saved.excluded_topics })
      })
      .catch(() => undefined)
      .finally(() => setIsLoadingSavedProfile(false))
  }, [])

  async function handleContinue() {
    const text = interests.trim()
    if (!text) {
      setError('Tell us a bit about what you want to follow first.')
      return
    }

    setIsLoading(true)
    setError(null)
    try {
      const result = await parseInterests(text)
      setProfile(result)
    } catch (err) {
      setError(err instanceof InterestParseError ? err.message : 'Something went wrong. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  function handleEdit() {
    setProfile(null)
    setError(null)
  }

  async function handleConfirm() {
    if (!profile) return

    setIsBuildingBrief(true)
    setError(null)
    try {
      await putProfile(interests.trim(), profile.interests, profile.excluded_topics)
      const { articles } = await searchNews(profile)
      const { stories } = await generateBrief(profile, articles)
      navigate('/brief', { state: { stories } })
    } catch (err) {
      if (err instanceof NewsSearchError || err instanceof BriefGenerateError || err instanceof ProfileError) {
        setError(err.message)
      } else {
        setError('Something went wrong. Please try again.')
      }
    } finally {
      setIsBuildingBrief(false)
    }
  }

  if (isLoadingSavedProfile) {
    return <main className="w-full pt-20 bg-surface min-h-[calc(100vh-140px)]" />
  }

  return (
    <main className="w-full pt-20 bg-surface min-h-[calc(100vh-140px)]">
      <div className="relative w-full overflow-hidden">
        <div className="max-w-[840px] mx-auto px-margin-mobile md:px-margin-tablet lg:px-margin pt-8 pb-16">
          <div className="flex flex-col items-center text-center">
            <h1 className="font-serif text-display-mobile md:text-display text-on-surface tracking-tight mb-2">
              What do you want to stay informed about?
            </h1>
            <p className="font-serif text-body-lg text-on-surface-variant max-w-[620px] mb-8 leading-relaxed">
              Describe the topics and stories you care about in plain words. Your Brief
              will focus on the topics and developing stories that matter to you.
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
                disabled={profile !== null}
                className="w-full bg-transparent font-serif text-headline-sm text-on-surface placeholder:text-outline-variant focus:outline-none resize-none leading-relaxed disabled:opacity-60"
              />
              <div className="flex items-center justify-between pt-4 mt-2 border-t border-surface-container">
                <button
                  type="button"
                  onClick={toggleDictation}
                  disabled={dictationState === 'transcribing' || profile !== null}
                  className={`group flex items-center gap-1 px-4 py-1 rounded-lg transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed ${
                    dictationState === 'recording'
                      ? 'bg-secondary text-on-primary'
                      : 'bg-surface-container-low text-on-surface'
                  }`}
                >
                  <MicIcon className={dictationState === 'recording' ? 'text-on-primary' : 'text-secondary'} />
                  <span className="font-sans text-label-md">
                    {dictationState === 'recording'
                      ? 'Listening… Stop'
                      : dictationState === 'transcribing'
                        ? 'Transcribing…'
                        : 'Dictate interests'}
                  </span>
                </button>
              </div>
            </div>

            {(error || dictationError) && (
              <p role="alert" className="font-sans text-label-md text-secondary mb-4 max-w-[480px]">
                {error || dictationError}
              </p>
            )}

            {profile && (
              <div className="w-full bg-surface-container-lowest rounded-xl p-6 shadow-sm border border-surface-container text-left mb-6">
                <h2 className="font-serif text-headline-sm text-on-surface mb-4">
                  What I understood
                </h2>
                <ul className="flex flex-wrap gap-2 mb-4">
                  {profile.interests.map((interest) => (
                    <li
                      key={interest.topic}
                      className="px-4 py-1 rounded-full bg-surface-container-low text-on-surface font-sans text-label-md"
                    >
                      {interest.topic}
                    </li>
                  ))}
                </ul>
                {profile.excluded_topics.length > 0 && (
                  <div className="pt-4 border-t border-surface-container">
                    <span className="font-sans text-label-sm text-on-surface-variant uppercase tracking-wider">
                      Muted
                    </span>
                    <ul className="flex flex-wrap gap-2 mt-2">
                      {profile.excluded_topics.map((topic) => (
                        <li
                          key={topic}
                          className="px-4 py-1 rounded-full bg-surface-container-low text-on-surface-variant font-sans text-label-md opacity-60"
                        >
                          {topic}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}

            <div className="flex flex-col items-center gap-4 mb-6">
              {profile ? (
                <div className="flex flex-wrap items-center justify-center gap-4">
                  <button
                    type="button"
                    onClick={handleEdit}
                    disabled={isBuildingBrief}
                    className="px-6 py-3 rounded-lg bg-surface-container-low text-on-surface-variant hover:text-on-surface font-sans text-label-lg transition-colors cursor-pointer disabled:opacity-60 disabled:cursor-not-allowed"
                  >
                    Edit
                  </button>
                  <button
                    type="button"
                    onClick={handleConfirm}
                    disabled={isBuildingBrief}
                    className="group inline-flex items-center justify-center gap-4 px-10 py-4 bg-primary hover:bg-primary-container text-on-primary rounded-lg transition-all shadow-md hover:shadow-xl active:scale-[0.99] min-w-[280px] cursor-pointer disabled:opacity-60 disabled:cursor-not-allowed"
                  >
                    <span className="font-sans text-label-lg uppercase tracking-wider text-on-primary">
                      {isBuildingBrief ? 'Building your brief…' : 'Looks right → Continue'}
                    </span>
                  </button>
                </div>
              ) : (
                <button
                  type="button"
                  onClick={handleContinue}
                  disabled={isLoading}
                  className="group inline-flex items-center justify-center gap-4 px-10 py-4 bg-primary hover:bg-primary-container text-on-primary rounded-lg transition-all shadow-md hover:shadow-xl active:scale-[0.99] min-w-[280px] cursor-pointer disabled:opacity-60 disabled:cursor-not-allowed"
                >
                  <span className="font-sans text-label-lg uppercase tracking-wider text-on-primary">
                    {isLoading ? 'Thinking…' : 'Continue to Your Brief'}
                  </span>
                  {!isLoading && (
                    <ArrowForwardIcon className="text-on-primary group-hover:translate-x-1 transition-transform" />
                  )}
                </button>
              )}
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
