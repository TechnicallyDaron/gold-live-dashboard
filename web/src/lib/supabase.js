import { createClient } from '@supabase/supabase-js'

const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL
const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY

// Gate is entirely optional — if the operator hasn't set these envs, the
// app stays in single-operator file-mode exactly as before.
export const authGateEnabled = Boolean(SUPABASE_URL && SUPABASE_ANON_KEY)

export const supabase = authGateEnabled ? createClient(SUPABASE_URL, SUPABASE_ANON_KEY) : null
