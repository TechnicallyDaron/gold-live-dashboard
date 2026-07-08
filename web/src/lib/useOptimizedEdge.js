import { useEffect, useState } from 'react'
import { api } from './api.js'

// Same shape as useStrategyLab: heavy per-strategy scan, fetched once per
// asset selection rather than polled.
export function useOptimizedEdge(asset) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!asset) return undefined
    let cancelled = false
    setLoading(true)
    setData(null)
    setError(null)
    api
      .optimizedEdge(asset)
      .then((d) => !cancelled && setData(d))
      .catch((err) => !cancelled && setError(err))
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [asset])

  return { data, error, loading }
}
