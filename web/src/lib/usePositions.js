import { useEffect, useState } from 'react'
import { api } from './api.js'

export function usePositions() {
  const [positions, setPositions] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    api
      .positions()
      .then((p) => !cancelled && setPositions(p))
      .catch((err) => !cancelled && setError(err))
    return () => {
      cancelled = true
    }
  }, [])

  return { positions, error }
}
