import { api } from './api.js'
import { usePolling } from './usePolling.js'

export function useMacroRadar() {
  return usePolling(() => api.macroRadar(), [], 60000)
}
