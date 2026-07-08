import { useEffect, useState } from 'react'
import { api } from './api.js'

// Watchlist-wide breadth scan, independent of the currently selected
// asset — fetched once on mount, not per-asset.
export function useCandidates() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    api
      .candidates()
      .then((d) => !cancelled && setData(d))
      .catch((err) => !cancelled && setError(err))
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [])

  return { candidates: data?.candidates ?? null, note: data?.note, error, loading }
}
