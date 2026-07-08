import { usePositions } from '../lib/usePositions.js'
import PositionCard from '../components/PositionCard.jsx'
import VoltBell from '../components/VoltBell.jsx'
import './Positions.css'

export default function Positions() {
  const { positions, error } = usePositions()
  const ids = positions ? Object.keys(positions) : []

  return (
    <div className="positions-screen">
      <header className="positions-header">
        <h1 className="positions-title">Positions</h1>
        <VoltBell />
      </header>

      {error && !positions && (
        <div className="positions-error">Could not load positions. Pull to retry.</div>
      )}

      {!positions && !error &&
        Array.from({ length: 2 }).map((_, i) => (
          <div key={i} className="skeleton positions-card-skeleton" />
        ))}

      {positions && ids.length === 0 && (
        <p className="positions-empty">No positions on file.</p>
      )}

      {positions &&
        ids.map((id) => <PositionCard key={id} position={positions[id]} />)}
    </div>
  )
}
