import { api } from './api.js'
import { usePolling } from './usePolling.js'

export function useHistory(asset, days) {
  return usePolling(() => api.history(asset, days), [asset, days], 60000, !!asset)
}
