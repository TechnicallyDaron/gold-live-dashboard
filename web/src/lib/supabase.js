import { createClient } from '@supabase/supabase-js'

const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL
const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY

// Gate is entirely optional — if the operator hasn't set these envs, the
// app stays in single-operator file-mode exactly as before.
export const authGateEnabled = Boolean(SUPABASE_URL && SUPABASE_ANON_KEY)

// Explicit auth config — the PWA runs installed/standalone with no browser
// chrome to carry a session between opens, so it must persist to localStorage
// itself and refresh tokens in the background rather than relying on defaults.
export const supabase = authGateEnabled
  ? createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
      auth: {
        persistSession: true,
        storage: window.localStorage,
        storageKey: 'ncore-auth',
        autoRefreshToken: true,
        detectSessionInUrl: false,
      },
    })
  : null
