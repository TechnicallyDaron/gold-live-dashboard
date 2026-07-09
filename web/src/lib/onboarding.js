// Tracks whether a user explicitly skipped the basket picker, so it doesn't
// nag them again on every reload while their watchlist stays empty. Backend
// has no onboarding-state column, so this is a local-only proxy — a fresh
// browser/device will show the picker again if the watchlist is still empty.
const SKIP_KEY_PREFIX = 'ncore-onboarding-skipped:'

export function isOnboardingSkipped(userId) {
  if (!userId) return false
  try {
    return localStorage.getItem(SKIP_KEY_PREFIX + userId) === '1'
  } catch {
    return false
  }
}

export function markOnboardingSkipped(userId) {
  if (!userId) return
  try {
    localStorage.setItem(SKIP_KEY_PREFIX + userId, '1')
  } catch {
    // storage unavailable — worst case the picker reappears next session
  }
}
