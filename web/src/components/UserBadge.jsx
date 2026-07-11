import { useState } from 'react'
import { useAuth } from '../lib/useAuth.js'
import { isStandalone } from '../lib/platform.js'
import { startTour } from '../lib/tourBus.js'
import './UserBadge.css'

export default function UserBadge() {
  const { gateEnabled, signedIn, user, signOut } = useAuth()
  const [open, setOpen] = useState(false)

  if (!gateEnabled || !signedIn) return null

  const email = user?.email || '…'
  const initial = email[0]?.toUpperCase() || '?'

  return (
    <div className="user-badge-wrap">
      <button type="button" className="user-badge" onClick={() => setOpen((o) => !o)}>
        {initial}
      </button>

      {open && (
        <>
          <div className="user-badge-backdrop" onClick={() => setOpen(false)} />
          <div className="user-badge-panel">
            <span className="user-badge-email">{email}</span>
            <button
              type="button"
              className="user-badge-action"
              onClick={() => {
                setOpen(false)
                startTour()
              }}
            >
              Replay tour
            </button>
            {!isStandalone() && <span className="user-badge-hint">Install app for the full-screen experience</span>}
            <button type="button" className="user-badge-signout" onClick={signOut}>
              Sign out
            </button>
          </div>
        </>
      )}
    </div>
  )
}
