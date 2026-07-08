import { useCallback, useEffect, useState } from 'react'
import { api } from './api.js'

// GET /api/shield is a superset of GET /api/positions — each entry carries
// the raw position fields plus a `shield` object (ATR-based time horizon,
// exhaustion %, status). Exposes `refresh` so the position form can pull
// the list forward immediately after a successful submit.
export function useShield() {
  const [positions, setPositions] = useState(null)
  const [error, setError] = useState(null)

  const refresh = useCallback(() => {
    return api
      .shield()
      .then((data) => setPositions(data))
      .catch((err) => setError(err))
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  return { positions, error, refresh }
}
