import { useEffect, useState } from 'react'
import { api } from './api.js'

// Watchlist composition barely changes — fetch once, not polled. Callers
// that mutate it (add/remove) get back the server's updated watchlist
// directly in the response, so `setWatchlist` lets them apply it in place
// instead of forcing a refetch.
// `enabled` defaults to true for callers mounted only after auth already
// resolved (Briefing, Positions). App.jsx uses this hook before sign-in
// completes, so it passes enabled=false until a session exists — otherwise
// the one-shot fetch fires with no bearer token, 401s, and never retries.
export function useWatchlist(enabled = true) {
  const [watchlist, setWatchlist] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!enabled) return undefined
    let cancelled = false
    api
      .watchlist()
      .then((wl) => !cancelled && setWatchlist(wl))
      .catch((err) => !cancelled && setError(err))
    return () => {
      cancelled = true
    }
  }, [enabled])

  return { watchlist, error, setWatchlist }
}
