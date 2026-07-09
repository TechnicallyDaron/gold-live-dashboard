import { useEffect, useState } from 'react'
import { supabase } from '../lib/supabase.js'
import './LoginScreen.css'

// Decorative only — static sample data, no live fetch pre-auth. Rendered as
// slow-drifting, low-opacity rows behind the portal card.
const DRIFT_ROWS = [
  'AAPL 231.42 +0.84%     MSFT 441.20 -0.32%     SPY 601.77 +0.41%     TLT 89.14 -0.18%',
  'GOLD 2,041.30 +1.12%     BTC 71,204 -2.05%     TSLA 248.55 +3.21%     USO 71.06 +0.55%',
  'QQQ 512.90 +0.65%     NVDA 128.44 +1.98%     DXY 104.21 -0.11%     IWM 218.33 -0.72%',
  'AMZN 198.11 +0.29%     META 612.87 +1.44%     COIN 214.90 -1.63%     DIA 421.05 +0.19%',
]

function MarketDrift() {
  return (
    <div className="portal-drift" aria-hidden="true">
      {DRIFT_ROWS.map((row, i) => (
        <div key={i} className={`portal-drift-row portal-drift-row--${i % 4}`}>
          {row}&nbsp;&nbsp;&nbsp;&nbsp;{row}
        </div>
      ))}
    </div>
  )
}

export default function LoginScreen({ dissolving = false, onDissolved, initialError = null }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [status, setStatus] = useState('idle')
  const [error, setError] = useState(initialError)
  const [resetSent, setResetSent] = useState(false)

  // Fire once the CSS dissolve transition (see .portal-screen--dissolving)
  // has had time to play, then let the parent swap to the HUB.
  useEffect(() => {
    if (!dissolving) return undefined
    const t = setTimeout(() => onDissolved?.(), 520)
    return () => clearTimeout(t)
  }, [dissolving, onDissolved])

  const submit = async () => {
    if (!email.trim() || !password) return
    setStatus('submitting')
    setError(null)
    try {
      const { error: err } = await supabase.auth.signInWithPassword({ email: email.trim(), password })
      if (err) throw err
      setStatus('idle')
    } catch (err) {
      setError(err.message)
      setStatus('idle')
    }
  }

  const requestReset = async () => {
    setResetSent(false)
    if (!email.trim()) {
      setError('Enter your email above, then tap "Forgot password?" again.')
      return
    }
    setError(null)
    try {
      const { error: err } = await supabase.auth.resetPasswordForEmail(email.trim(), {
        redirectTo: window.location.origin,
      })
      if (err) throw err
      setResetSent(true)
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div className={`portal-screen ${dissolving ? 'portal-screen--dissolving' : ''}`}>
      {!dissolving && (
        <div className="portal-app-ghost" aria-hidden="true">
          <div className="portal-ghost-header" />
          <div className="portal-ghost-tape" />
          <div className="portal-ghost-grid">
            <div className="portal-ghost-card" />
            <div className="portal-ghost-card" />
            <div className="portal-ghost-card" />
            <div className="portal-ghost-card" />
          </div>
        </div>
      )}

      <MarketDrift />

      <div className="portal-frame" aria-hidden="true">
        <span className="portal-frame-corner portal-frame-corner--tl" />
        <span className="portal-frame-corner portal-frame-corner--tr" />
        <span className="portal-frame-corner portal-frame-corner--bl" />
        <span className="portal-frame-corner portal-frame-corner--br" />
      </div>

      <div className="portal-card">
        <span className="login-mark">N</span>
        <h1 className="login-title">N-CORE</h1>
        <p className="login-subtitle">Nyarko's Trade Manager</p>

        <div className="login-field">
          <input
            className="login-input"
            type="email"
            placeholder="you@example.com"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && submit()}
          />
        </div>

        <div className="login-field">
          <input
            className="login-input"
            type="password"
            placeholder="Password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && submit()}
          />
        </div>

        {error && <p className="login-error">{error}</p>}
        {resetSent && <p className="login-reset-sent">Password reset email sent — check your inbox.</p>}

        <button
          type="button"
          className="login-submit"
          disabled={!email.trim() || !password || status === 'submitting'}
          onClick={submit}
        >
          {status === 'submitting' ? 'Signing in…' : 'Sign in'}
        </button>

        <button type="button" className="login-toggle" onClick={requestReset}>
          Forgot password?
        </button>

        <p className="portal-invite-only">Access is currently invite-only.</p>
      </div>

      <p className="portal-disclaimer">
        Educational tool. Not financial advice. Trade at your own risk.
      </p>
    </div>
  )
}
