import { useEffect, useState } from 'react'
import { authGateEnabled, supabase } from './supabase.js'

// Supabase's detectSessionInUrl stays OFF globally (see supabase.js) — this
// is a controlled, one-shot manual parse of the auth fragment Supabase
// appends after an invite/recovery link redirects here, not a config flip.
// Runs once on app load: on type=invite or type=recovery, establishes the
// session from the tokens and flags that the Set Your Password screen is
// needed before the user can proceed (they have a session but no password
// yet — invite — or are here specifically to replace one — recovery).
export function useAuthHashHandler() {
  const [pendingPasswordType, setPendingPasswordType] = useState(null)
  const [hashError, setHashError] = useState(null)
  const [processed, setProcessed] = useState(!authGateEnabled)

  useEffect(() => {
    if (!authGateEnabled) return

    const hash = window.location.hash
    if (!hash || hash.length < 2) {
      setProcessed(true)
      return
    }

    const params = new URLSearchParams(hash.slice(1))
    const clearHash = () => {
      window.history.replaceState(null, '', window.location.pathname + window.location.search)
    }

    const errorDescription = params.get('error_description')
    if (errorDescription) {
      clearHash()
      setHashError(errorDescription.replace(/\+/g, ' '))
      setProcessed(true)
      return
    }

    const accessToken = params.get('access_token')
    const refreshToken = params.get('refresh_token')
    const type = params.get('type')

    if (!accessToken || !refreshToken) {
      setProcessed(true)
      return
    }

    supabase.auth.setSession({ access_token: accessToken, refresh_token: refreshToken }).then(({ error }) => {
      clearHash()
      if (!error && (type === 'invite' || type === 'recovery')) {
        setPendingPasswordType(type)
      } else if (error) {
        setHashError(error.message)
      }
      setProcessed(true)
    })
  }, [])

  return {
    processed,
    pendingPasswordType,
    hashError,
    clearPendingPassword: () => setPendingPasswordType(null),
  }
}
