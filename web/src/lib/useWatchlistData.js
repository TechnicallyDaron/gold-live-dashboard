import { api } from './api.js'
import { usePolling } from './usePolling.js'

// Fetches quote + bias for every asset name in `names`, in parallel, every
// poll cycle. Per-asset failures (e.g. feed down) don't take down the rest —
// each entry carries its own `quoteError` / `biasError`.
export function useWatchlistData(names) {
  const key = names.join(',')
  return usePolling(
    async () => {
      const entries = await Promise.all(
        names.map(async (name) => {
          const [quoteResult, biasResult] = await Promise.allSettled([
            api.quote(name),
            api.bias(name),
          ])
          return [
            name,
            {
              quote: quoteResult.status === 'fulfilled' ? quoteResult.value : null,
              quoteError: quoteResult.status === 'rejected' ? quoteResult.reason : null,
              bias: biasResult.status === 'fulfilled' ? biasResult.value : null,
              biasError: biasResult.status === 'rejected' ? biasResult.reason : null,
            },
          ]
        })
      )
      return Object.fromEntries(entries)
    },
    [key],
    60000
  )
}
