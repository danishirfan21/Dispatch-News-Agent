const ONBOARDING_SEEN_KEY = 'dispatch_onboarding_seen'

/** Whether this browser has already completed or skipped onboarding.
 * Falls back to `false` if localStorage is unavailable (private browsing,
 * disabled storage, etc.) so onboarding simply shows again rather than
 * crashing the app. */
export function hasSeenOnboarding(): boolean {
  try {
    return localStorage.getItem(ONBOARDING_SEEN_KEY) === 'true'
  } catch {
    return false
  }
}

export function markOnboardingSeen(): void {
  try {
    localStorage.setItem(ONBOARDING_SEEN_KEY, 'true')
  } catch {
    // Storage unavailable -- onboarding will reappear next visit, which is fine.
  }
}
