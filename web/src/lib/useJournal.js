import { useCallback, useEffect, useState } from 'react'
import { api } from './api.js'

export function useJournal() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  const refresh = useCallback(() => {
    return api
      .journal()
      .then((d) => setData(d))
      .catch((err) => setError(err))
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  return { entries: data?.entries ?? null, aggregates: data?.aggregates ?? null, error, refresh }
}
