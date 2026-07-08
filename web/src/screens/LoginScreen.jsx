import { useState } from 'react'
import { supabase } from '../lib/supabase.js'
import './LoginScreen.css'

export default function LoginScreen() {
  const [email, setEmail] = useState('')
  const [status, setStatus] = useState('idle')
  const [error, setError] = useState(null)

  const sendLink = async () => {
    if (!email.trim()) return
    setStatus('sending')
    setError(null)
    try {
      const { error: err } = await supabase.auth.signInWithOtp({
        email: email.trim(),
        options: { emailRedirectTo: window.location.origin },
      })
      if (err) throw err
      setStatus('sent')
    } catch (err) {
      setError(err.message)
      setStatus('idle')
    }
  }

  return (
    <div className="login-screen">
      <div className="login-card">
        <span className="login-mark">N</span>
        <h1 className="login-title">N-CORE</h1>
        <p className="login-subtitle">Nyarko's Trade Manager</p>

        {status === 'sent' ? (
          <div className="login-sent">
            <span className="login-sent-icon">✉️</span>
            <p className="login-sent-text">
              Magic link sent to <strong>{email}</strong>. Check your inbox.
            </p>
          </div>
        ) : (
          <>
            <div className="login-field">
              <input
                className="login-input"
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && sendLink()}
              />
            </div>

            {error && <p className="login-error">{error}</p>}

            <button
              type="button"
              className="login-submit"
              disabled={!email.trim() || status === 'sending'}
              onClick={sendLink}
            >
              {status === 'sending' ? 'Sending…' : 'Send magic link'}
            </button>

            <button type="button" className="login-google" disabled>
              Continue with Google (soon)
            </button>
          </>
        )}
      </div>
    </div>
  )
}
