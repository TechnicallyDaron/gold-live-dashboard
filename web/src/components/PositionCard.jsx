import './PositionCard.css'

function fmt(n) {
  return typeof n === 'number'
    ? n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
    : n ?? '—'
}

export default function PositionCard({ position }) {
  const {
    asset, strike, type, expiration, premium_paid: premiumPaid,
    premium_stop: premiumStop, time_stop: timeStop,
    invalidation_above: invalAbove, invalidation_below: invalBelow, notes,
  } = position

  const typeLabel = type ? String(type).slice(0, 1).toUpperCase() : ''
  const invalidation = invalAbove ?? invalBelow ?? null

  return (
    <div className="position-card">
      <div className="position-card-header">
        <span className="position-card-title">
          {asset} ${fmt(strike)}{typeLabel}
        </span>
        <span className="position-card-exp">exp {expiration}</span>
      </div>

      {premiumPaid != null && (
        <div className="position-card-row">
          <span className="position-card-label">Premium Paid</span>
          <span className="position-card-value tabular-nums">${fmt(premiumPaid)}</span>
        </div>
      )}
      <div className="position-card-row">
        <span className="position-card-label">Stop</span>
        <span className="position-card-value position-card-value--short tabular-nums">
          ${fmt(premiumStop)}
        </span>
      </div>
      <div className="position-card-row">
        <span className="position-card-label">Time Stop</span>
        <span className="position-card-value tabular-nums">{timeStop || '—'}</span>
      </div>
      <div className="position-card-row">
        <span className="position-card-label">Invalidation</span>
        <span className="position-card-value position-card-value--short tabular-nums">
          {invalidation != null ? `$${fmt(invalidation)}` : '—'}
        </span>
      </div>

      {notes && <p className="position-card-notes">{notes}</p>}
    </div>
  )
}
