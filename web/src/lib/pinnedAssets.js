// Per-user pinned-assets list for the HUB grid ("Edit Top 4"). Order
// matters — pins fill grid slots in the order they were pinned — so this
// is a JSON array, not a Set. localStorage-only for now, same pattern as
// onboarding.js / tourState.js.
const PINS_KEY_PREFIX = 'ncore-pinned-assets:'

export function getPins(userId) {
  if (!userId) return []
  try {
    const raw = localStorage.getItem(PINS_KEY_PREFIX + userId)
    const parsed = raw ? JSON.parse(raw) : []
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

export function setPins(userId, names) {
  if (!userId) return
  try {
    localStorage.setItem(PINS_KEY_PREFIX + userId, JSON.stringify(names))
  } catch {
    // storage unavailable — pins just won't persist this session
  }
}

// Called when an asset is deleted from the watchlist entirely — drops it
// from the pin list if present, a no-op otherwise.
export function removePin(userId, name) {
  if (!userId) return
  const pins = getPins(userId)
  if (!pins.includes(name)) return
  setPins(userId, pins.filter((n) => n !== name))
}
