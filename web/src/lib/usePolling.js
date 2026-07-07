import { useEffect, useRef, useState } from 'react'

// Runs `fetcher` immediately, then every `intervalMs`, pausing while the
// tab is hidden. Returns { data, error, loading }.
export function usePolling(fetcher, deps = [], intervalMs = 60000) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)
  const fetcherRef = useRef(fetcher)
  fetcherRef.current = fetcher

  useEffect(() => {
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
  }, deps)

  return { data, error, loading }
}
