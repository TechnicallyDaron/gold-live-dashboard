import { useState } from 'react'
import { supabase } from '../lib/supabase.js'
import './LoginScreen.css'

const MIN_PASSWORD_LENGTH = 8

export default function SetPasswordScreen({ mode = 'invite', onComplete }) {
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [status, setStatus] = useState('idle')
  const [error, setError] = useState(null)
  const [done, setDone] = useState(false)

  const submit = async () => {
    setError(null)
    if (password.length < MIN_PASSWORD_LENGTH) {
      setError(`Password must be at least ${MIN_PASSWORD_LENGTH} characters.`)
      return
    }
    if (password !== confirm) {
      setError('Passwords do not match.')
      return
    }

    setStatus('submitting')
    try {
      const { error: err } = await supabase.auth.updateUser({ password })
      if (err) throw err
      setDone(true)
      setStatus('idle')
    } catch (err) {
      setError(err.message)
      setStatus('idle')
    }
  }

  return (
    <div className="portal-screen">
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

      <div className="portal-frame" aria-hidden="true">
        <span className="portal-frame-corner portal-frame-corner--tl" />
        <span className="portal-frame-corner portal-frame-corner--tr" />
        <span className="portal-frame-corner portal-frame-corner--bl" />
        <span className="portal-frame-corner portal-frame-corner--br" />
      </div>

      <div className="portal-card">
        <span className="login-mark">N</span>
        <h1 className="login-title">N-CORE⚡️</h1>
        <p className="login-subtitle">{mode === 'recovery' ? 'Reset your password' : 'Set your password'}</p>

        {done ? (
          <div className="login-sent">
            <span className="login-sent-icon">✓</span>
            <p className="login-sent-text">
              Password set. Add this app to your home screen for the full experience, or continue in the browser.
            </p>
            <button type="button" className="login-submit" onClick={onComplete}>
              Continue
            </button>
          </div>
        ) : (
          <>
            <div className="login-field">
              <input
                className="login-input"
                type="password"
                placeholder={`Password (min ${MIN_PASSWORD_LENGTH} chars)`}
                autoComplete="new-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && submit()}
              />
            </div>

            <div className="login-field">
              <input
                className="login-input"
                type="password"
                placeholder="Confirm password"
                autoComplete="new-password"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && submit()}
              />
            </div>

            {error && <p className="login-error">{error}</p>}

            <button
              type="button"
              className="login-submit"
              disabled={!password || !confirm || status === 'submitting'}
              onClick={submit}
            >
              {status === 'submitting' ? 'Setting…' : 'Set password'}
            </button>
          </>
        )}
      </div>

      <p className="portal-disclaimer">
        Educational tool. Not financial advice. Trade at your own risk.
      </p>
    </div>
  )
}
