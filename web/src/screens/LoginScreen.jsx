import { useState } from 'react'
import { supabase } from '../lib/supabase.js'
import './LoginScreen.css'

const MIN_PASSWORD_LENGTH = 8

export default function LoginScreen() {
  const [mode, setMode] = useState('signin')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [status, setStatus] = useState('idle')
  const [error, setError] = useState(null)
  const [signupDone, setSignupDone] = useState(false)

  const isSignUp = mode === 'signup'

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
    <div className="login-screen">
      <div className="login-card">
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
