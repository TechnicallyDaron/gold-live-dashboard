import { useEffect, useState } from 'react'
import { api } from './api.js'

// News is cached server-side for 30 minutes — fetched once per asset
// selection rather than polled like quotes/bias.
export function useNews(asset) {
  const [items, setItems] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!asset) return undefined
    let cancelled = false
    setLoading(true)
    setItems(null)
    setError(null)

    api
      .news(asset)
      .then((data) => !cancelled && setItems(data))
      .catch((err) => !cancelled && setError(err))
      .finally(() => !cancelled && setLoading(false))

    return () => {
      cancelled = true
    }
  }, [asset])

  return { items, error, loading }
}
