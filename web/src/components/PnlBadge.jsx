import './PnlBadge.css'

export default function PnlBadge({ pnlPct, note, size = 'md' }) {
  if (pnlPct == null) {
    return (
      <span className={`pnl-badge pnl-badge--${size} pnl-badge--unavailable`} title={note || 'PnL unavailable'}>
        PNL UNAVAILABLE
      </span>
    )
  }
  const positive = pnlPct > 0
  return (
    <span className={`pnl-badge pnl-badge--${size} ${positive ? 'pnl-badge--positive' : 'pnl-badge--negative'}`}>
      {positive ? '+' : ''}
      {pnlPct.toFixed(1)}%
    </span>
  )
}
