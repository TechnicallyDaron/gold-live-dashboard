import { useState } from 'react'
import { useNotifications } from '../lib/useNotifications.js'
import { initPushIfNeeded } from '../lib/push.js'
import './VoltBell.css'

function relativeTime(ts) {
  const secs = Math.max(0, Math.floor(Date.now() / 1000) - ts)
  if (secs < 60) return 'just now'
  const mins = Math.floor(secs / 60)
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}

export default function VoltBell() {
  const { items, lastSeen, markSeen } = useNotifications()
  const [open, setOpen] = useState(false)
  const [mutedNote, setMutedNote] = useState(null)

  // Journal entries (position-closed events) already have their own home
  // in the Positions journal — surfacing them again here is just noise.
  // Filtered client-side so the badge count and panel list always agree.
  const visibleItems = items.filter((n) => n.kind !== 'journal')
  const unseenCount = visibleItems.filter((n) => n.ts > lastSeen).length

  const toggle = () => {
    setOpen((o) => {
      if (!o) {
        markSeen()
        initPushIfNeeded().then((r) => {
          if (r.mutedNote) setMutedNote(r.mutedNote)
        })
      }
      return !o
    })
  }

  return (
    <div className="volt-bell-wrap">
      <button type="button" className="volt-bell" onClick={toggle} aria-label="Notifications" data-tour="bell">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
          <path
            d="M18 16v-5a6 6 0 1 0-12 0v5l-1.5 2.5h15L18 16Z"
            stroke="var(--volt)" strokeWidth="1.7" strokeLinejoin="round"
          />
          <path d="M10 20a2 2 0 0 0 4 0" stroke="var(--volt)" strokeWidth="1.7" strokeLinecap="round" />
        </svg>
        {unseenCount > 0 && (
          <span className="volt-bell-badge">{unseenCount > 9 ? '9+' : unseenCount}</span>
        )}
      </button>

      {open && (
        <>
          <div className="volt-bell-backdrop" onClick={() => setOpen(false)} />
          <div className="volt-bell-panel">
            <span className="volt-bell-panel-title">Notifications</span>
            {mutedNote && <p className="volt-bell-muted-note">{mutedNote}</p>}
            {visibleItems.length === 0 && (
              <p className="volt-bell-empty">Nothing yet — the agent checks every 20 minutes.</p>
            )}
            {visibleItems.map((n, i) => (
              <div key={i} className="volt-bell-item">
                <span className="volt-bell-item-title">{n.title}</span>
                <p className="volt-bell-item-text">{n.body}</p>
                <span className="volt-bell-item-time">{relativeTime(n.ts)}</span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
