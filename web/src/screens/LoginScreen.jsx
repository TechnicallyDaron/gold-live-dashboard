import { useEffect, useState } from 'react'
import { supabase } from '../lib/supabase.js'
import './LoginScreen.css'

const MIN_PASSWORD_LENGTH = 8

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

export default function LoginScreen({ dissolving = false, onDissolved }) {
  const [mode, setMode] = useState('signin')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [status, setStatus] = useState('idle')
  const [error, setError] = useState(null)
  const [signupDone, setSignupDone] = useState(false)

  const isSignUp = mode === 'signup'

  // Fire once the CSS dissolve transition (see .portal-screen--dissolving)
  // has had time to play, then let the parent swap to the HUB.
  useEffect(() => {
    if (!dissolving) return undefined
    const t = setTimeout(() => onDissolved?.(), 520)
    return () => clearTimeout(t)
  }, [dissolving, onDissolved])

  const submit = async () => {
    if (!email.trim() || !password) return
    if (isSignUp && password.length < MIN_PASSWORD_LENGTH) {
      setError(`Password must be at least ${MIN_PASSWORD_LENGTH} characters.`)
      return
    }

    setStatus('submitting')
    setError(null)
    try {
      const { error: err } = isSignUp
        ? await supabase.auth.signUp({ email: email.trim(), password })
        : await supabase.auth.signInWithPassword({ email: email.trim(), password })
      if (err) throw err
      if (isSignUp) setSignupDone(true)
      setStatus('idle')
    } catch (err) {
      setError(err.message)
      setStatus('idle')
    }
  }

  const toggleMode = () => {
    setMode(isSignUp ? 'signin' : 'signup')
    setError(null)
    setSignupDone(false)
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

        {signupDone ? (
          <div className="login-sent">
            <span className="login-sent-icon">✓</span>
            <p className="login-sent-text">
              Account created for <strong>{email}</strong>. Sign in below.
            </p>
            <button type="button" className="login-submit" onClick={toggleMode}>
              Back to sign in
            </button>
          </div>
        ) : (
          <>
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
                placeholder={isSignUp ? `Password (min ${MIN_PASSWORD_LENGTH} chars)` : 'Password'}
                autoComplete={isSignUp ? 'new-password' : 'current-password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && submit()}
              />
            </div>

            {error && <p className="login-error">{error}</p>}

            <button
              type="button"
              className="login-submit"
              disabled={!email.trim() || !password || status === 'submitting'}
              onClick={submit}
            >
              {status === 'submitting'
                ? isSignUp
                  ? 'Creating account…'
                  : 'Signing in…'
                : isSignUp
                  ? 'Create account'
                  : 'Sign in'}
            </button>

            <button type="button" className="login-toggle" onClick={toggleMode}>
              {isSignUp ? 'Have an account? Sign in' : 'Create account'}
            </button>
          </>
        )}
      </div>
    </div>
  )
}
