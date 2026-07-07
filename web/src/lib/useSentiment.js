import { useCallback, useState } from 'react'
import { api } from './api.js'

// Module-scoped so results persist across tab switches within the
// session (News unmounts on route change; this object doesn't).
const cache = {}

export function useSentiment(asset) {
  const [, forceRender] = useState(0)
  const entry = asset ? cache[asset] : null

  const analyze = useCallback(async () => {
    if (!asset) return
    cache[asset] = { status: 'loading' }
    forceRender((t) => t + 1)
    try {
      const data = await api.sentiment(asset)
      cache[asset] = { status: 'success', data }
    } catch (err) {
      cache[asset] = { status: 'error', detail: err.message }
    }
    forceRender((t) => t + 1)
  }, [asset])

  return { entry, analyze }
}
