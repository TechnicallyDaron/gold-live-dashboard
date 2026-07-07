import { api } from './api.js'
import { usePolling } from './usePolling.js'

export function useBias(asset) {
  return usePolling(() => api.bias(asset), [asset], 60000, !!asset)
}
