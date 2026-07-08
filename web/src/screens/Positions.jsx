import { useState } from 'react'
import { useShield } from '../lib/useShield.js'
import { useWatchlist } from '../lib/useWatchlist.js'
import PositionCard from '../components/PositionCard.jsx'
import VoltBell from '../components/VoltBell.jsx'
import PositionForm from '../components/PositionForm.jsx'
import ClosePositionForm from '../components/ClosePositionForm.jsx'
import './Positions.css'

export default function Positions() {
  const { positions, error, refresh } = useShield()
  const { watchlist } = useWatchlist()
  const [showForm, setShowForm] = useState(false)
  const [closeTarget, setCloseTarget] = useState(null)

  return (
    <div className="positions-screen">
      <header className="positions-header">
        <h1 className="positions-title">Positions</h1>
        <VoltBell />
      </header>

      <button type="button" className="positions-log-btn" onClick={() => setShowForm(true)}>
        + Log Position
      </button>

      {error && !positions && (
        <div className="positions-error">Could not load positions. Pull to retry.</div>
      )}

      {!positions && !error &&
        Array.from({ length: 2 }).map((_, i) => (
          <div key={i} className="skeleton positions-card-skeleton" />
        ))}

      {positions && positions.length === 0 && (
        <p className="positions-empty">No positions on file.</p>
      )}

      {positions &&
        positions.map((p) => (
          <PositionCard key={p.id} position={p} onRequestClose={() => setCloseTarget(p)} />
        ))}

      {showForm && (
        <PositionForm
          watchlist={watchlist || {}}
          onClose={() => setShowForm(false)}
          onSaved={refresh}
        />
      )}

      {closeTarget && (
        <ClosePositionForm
          position={closeTarget}
          onClose={() => setCloseTarget(null)}
          onSaved={refresh}
        />
      )}
    </div>
  )
}
