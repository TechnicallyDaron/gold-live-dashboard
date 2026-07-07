import { useEffect, useState } from 'react'
import { api } from './api.js'

const STRATEGIES = ['meanrev', 'breakout', 'rsi']

// Backtests are heavy (5y history) and cached server-side for 5 minutes —
// fetched once per asset selection rather than polled like quotes/bias.
export function useBacktestStrip(asset) {
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!asset) return undefined
    let cancelled = false
    setLoading(true)
    setResults(null)

    Promise.all(
      STRATEGIES.map(async (strategy) => {
        try {
          const data = await api.backtest(asset, strategy)
          return { strategy, data, error: null }
        } catch (error) {
          return { strategy, data: null, error }
        }
      })
    ).then((entries) => {
      if (cancelled) return
      setResults(Object.fromEntries(entries.map((e) => [e.strategy, e])))
      setLoading(false)
    })

    return () => {
      cancelled = true
    }
  }, [asset])

  return { results, loading }
}
