// Notifications carry only a free-text title/body, no structured asset
// field. Backend titles embed either the watchlist display name or the
// resolved ticker's full name (e.g. "GLD" vs "SPDR Gold Shares") depending
// on which code path fired — so match against key, ticker, and name.
export function matchAssetKey(text, watchlist) {
  if (!watchlist) return null
  for (const [key, entry] of Object.entries(watchlist)) {
    if (text.includes(key) || text.includes(entry.ticker) || text.includes(entry.name)) {
      return key
    }
  }
  return null
}
