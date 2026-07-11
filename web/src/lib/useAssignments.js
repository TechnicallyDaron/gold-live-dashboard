import { useEffect, useState } from 'react'
import { api } from './api.js'

// Playbook assignments with validation stats — fetched once, not polled
// (assignments change on a walk-forward cadence, not intraday). Powers the
// HUB's frequency-based re-layering (signals_per_week is the sort key).
export function useAssignments() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    api
      .playbook()
      .then((d) => !cancelled && setData(d))
      .catch((err) => !cancelled && setError(err))
    return () => {
      cancelled = true
    }
  }, [])

  return { assignments: data?.assignments ?? [], error }
}
