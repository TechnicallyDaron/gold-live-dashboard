import { useEffect, useState } from 'react'

const STORAGE_KEY = 'ncore-risk-settings'
// No sensible default account size — the calculator stays hidden until the
// operator sets one. Max % per trade defaults to 25 per spec.
const DEFAULTS = { accountSize: 0, maxPct: 25 }

function load() {
  try {
    if (typeof window === 'undefined' || !window.localStorage) return DEFAULTS
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return DEFAULTS
    const parsed = JSON.parse(raw)
    // Guard against corrupted storage holding a non-object JSON value
    // (e.g. a stray "null" or "42") — parsed.accountSize would otherwise
    // throw on a primitive.
    if (!parsed || typeof parsed !== 'object') return DEFAULTS
    return {
      accountSize: Number(parsed.accountSize) || 0,
      maxPct: Number(parsed.maxPct) || DEFAULTS.maxPct,
    }
  } catch {
    return DEFAULTS
  }
}

// Client-side only, per spec — no backend endpoint for this yet.
export function useRiskSettings() {
  const [settings, setSettings] = useState(load)

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(settings))
    } catch {
      // storage unavailable — settings just won't persist across reloads
    }
  }, [settings])

  return [settings, setSettings]
}
