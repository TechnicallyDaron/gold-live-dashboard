import { useEffect, useState } from 'react'
import { authGateEnabled, supabase } from './supabase.js'
import { api } from './api.js'

export function useAuth() {
  const [session, setSession] = useState(null)
  const [user, setUser] = useState(null)
  const [ready, setReady] = useState(!authGateEnabled)

  useEffect(() => {
    if (!authGateEnabled) return undefined

    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session)
      setReady(true)
    })

    const { data: sub } = supabase.auth.onAuthStateChange((_event, newSession) => {
      setSession(newSession)
    })

    return () => sub.subscription.unsubscribe()
  }, [])

  useEffect(() => {
    if (!authGateEnabled) return
    if (session?.access_token) {
      // Verify once against the backend — confirms the token is actually
      // accepted, not just present. api.js attaches the bearer itself via
      // supabase.auth.getSession().
      api
        .me()
        .then((r) => setUser(r.user))
        .catch(() => setUser(null))
    } else {
      setUser(null)
    }
  }, [session])

  const signOut = () => supabase?.auth.signOut()

  return {
    gateEnabled: authGateEnabled,
    ready,
    session,
    user,
    signedIn: authGateEnabled ? !!session : true,
    signOut,
  }
}
