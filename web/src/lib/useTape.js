import { api } from './api.js'
import { usePolling } from './usePolling.js'

export function useTape() {
  return usePolling(() => api.tape(), [], 120000)
}
