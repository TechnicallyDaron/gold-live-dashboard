import { useEffect, useState } from 'react'
import { api } from './api.js'

// Daily catalyst screener output — fetched once, not polled (it only
// changes once a day). Shared by the HUB's quiet-asset collapse (is a
// ticker currently a screener hit?) and the catalyst spotlight strip.
export function useScreener() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    api
      .screener()
      .then((d) => !cancelled && setData(d))
      .catch((err) => !cancelled && setError(err))
    return () => {
      cancelled = true
    }
  }, [])

  return { hits: data?.hits ?? [], scanDate: data?.scan_date ?? null, error }
}
