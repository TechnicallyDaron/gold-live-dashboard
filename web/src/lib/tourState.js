// Tracks whether a user has already been through (or dismissed) the
// first-run tour, so the auto-prompt never shows twice. Completing and
// skipping both count — the whole point is "don't nag again" — Replay in
// settings is the only way back in after that.
const SEEN_KEY_PREFIX = 'ncore-tour-seen:'

export function hasSeenTour(userId) {
  if (!userId) return false
  try {
    return localStorage.getItem(SEEN_KEY_PREFIX + userId) === '1'
  } catch {
    return false
  }
}

export function markTourSeen(userId) {
  if (!userId) return
  try {
    localStorage.setItem(SEEN_KEY_PREFIX + userId, '1')
  } catch {
    // storage unavailable — worst case the prompt reappears next session
  }
}
