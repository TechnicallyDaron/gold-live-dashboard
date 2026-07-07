import { useEffect, useRef, useState } from 'react'

// Runs `fetcher` immediately, then every `intervalMs`, pausing while the
// tab is hidden. Pass `enabled: false` to skip fetching (e.g. while a
// required param like the selected asset isn't ready yet).
// Returns { data, error, loading }.
export function usePolling(fetcher, deps = [], intervalMs = 60000, enabled = true) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)
  const fetcherRef = useRef(fetcher)
  fetcherRef.current = fetcher

  useEffect(() => {
    if (!enabled) return undefined
    let cancelled = false
    let timer = null

    const run = async () => {
      try {
        const result = await fetcherRef.current()
        if (!cancelled) {
          setData(result)
          setError(null)
        }
      } catch (err) {
        if (!cancelled) setError(err)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    const schedule = () => {
      clearTimeout(timer)
      timer = setTimeout(async () => {
        if (document.visibilityState === 'visible') {
          await run()
        }
        schedule()
      }, intervalMs)
    }

    run()
    schedule()

    const onVisibility = () => {
      if (document.visibilityState === 'visible') run()
    }
    document.addEventListener('visibilitychange', onVisibility)

    return () => {
      cancelled = true
      clearTimeout(timer)
      document.removeEventListener('visibilitychange', onVisibility)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, enabled])

  return { data, error, loading }
}
