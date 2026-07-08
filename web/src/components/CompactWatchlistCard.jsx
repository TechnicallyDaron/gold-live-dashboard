import { useNavigate } from 'react-router-dom'
import { biasColorVar } from '../lib/colors.js'
import './CompactWatchlistCard.css'

function statusChip(bias) {
  if (!bias) return { icon: '😴', label: 'Quiet', color: 'var(--muted)' }
  if (bias.assigned_strategy && bias.signaling_today) {
    return { icon: '🎯', label: 'Playbook firing', color: 'var(--volt)' }
  }
  if (bias.color === 'green') return { icon: '🟢', label: 'Setup live', color: 'var(--long)' }
  if (bias.color === 'red') return { icon: '🔴', label: 'Setup live', color: 'var(--short)' }
  if (bias.color === 'orange') return { icon: '👀', label: 'Close', color: 'var(--watch)' }
  return { icon: '😴', label: 'Quiet', color: 'var(--muted)' }
}

export default function CompactWatchlistCard({ name, unit, entry, loading, flash }) {
  const navigate = useNavigate()

  if (loading) {
    return <div className="skeleton compact-card-skeleton" />
  }

  const feedDown = !!entry?.quoteError
  const quote = entry?.quote
  const bias = entry?.bias
  const chip = statusChip(bias)
  const pct = quote?.pct ?? 0
  const pctPositive = pct > 0
  const edgeColor = bias ? biasColorVar(bias.color) : 'var(--border)'

  const classes = ['compact-card']
  if (feedDown) classes.push('compact-card--down')
  if (flash) classes.push('compact-card--flash')

  return (
    <button
      type="button"
      className={classes.join(' ')}
      style={!feedDown ? { borderLeftColor: edgeColor } : undefined}
      onClick={() => navigate(`/bias/${encodeURIComponent(name)}`)}
    >
      <span className="compact-card-name">{name}</span>
      {feedDown ? (
        <span className="compact-card-feed-down">FEED DOWN</span>
      ) : (
        <>
          <span className="compact-card-price tabular-nums">
            ${quote?.price?.toLocaleString(undefined, { maximumFractionDigits: 2 })}
            {unit}
          </span>
          <span
            className={
              pctPositive
                ? 'compact-card-pct compact-card-pct--up tabular-nums'
                : 'compact-card-pct compact-card-pct--down tabular-nums'
            }
          >
            {pctPositive ? '+' : ''}
            {pct.toFixed(2)}%
          </span>
        </>
      )}
      <span className="compact-card-chip" style={{ color: chip.color }}>
        {chip.icon} {chip.label}
      </span>
    </button>
  )
}
