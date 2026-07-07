import { useEffect, useState } from 'react'
import { api } from './api.js'

// Watchlist composition barely changes — fetch once, not polled.
export function useWatchlist() {
  const [watchlist, setWatchlist] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    api
      .watchlist()
      .then((wl) => !cancelled && setWatchlist(wl))
      .catch((err) => !cancelled && setError(err))
    return () => {
      cancelled = true
    }
  }, [])

  return { watchlist, error }
}
