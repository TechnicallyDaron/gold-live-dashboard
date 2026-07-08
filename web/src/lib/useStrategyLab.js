import { useEffect, useState } from 'react'
import { api } from './api.js'

// Walk-forward validation is heavy (train/test backtests per strategy) and
// server-cached — fetched once per asset selection, not polled.
export function useStrategyLab(asset) {
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
      .strategyLab(asset)
      .then((d) => !cancelled && setData(d))
      .catch((err) => !cancelled && setError(err))
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [asset])

  return { data, error, loading }
}
