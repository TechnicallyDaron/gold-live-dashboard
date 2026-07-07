import { api } from './api.js'
import { usePolling } from './usePolling.js'

export function useMacro() {
  return usePolling(() => api.macro(), [], 120000)
}
