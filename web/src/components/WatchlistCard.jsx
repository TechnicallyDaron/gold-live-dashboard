import { useNavigate } from 'react-router-dom'
import { biasColorVar } from '../lib/colors.js'
import './WatchlistCard.css'

export default function WatchlistCard({ name, unit, entry, loading }) {
  const navigate = useNavigate()

  if (loading) {
    return <div className="skeleton watchlist-card-skeleton" />
  }

  const feedDown = !!entry?.quoteError
  const quote = entry?.quote
  const bias = entry?.bias
  const chipColor = bias ? biasColorVar(bias.color) : 'var(--muted)'
  const pct = quote?.pct ?? 0
  const pctPositive = pct > 0

  return (
    <button
      type="button"
      className={feedDown ? 'watchlist-card watchlist-card--down' : 'watchlist-card'}
      onClick={() => navigate(`/bias/${encodeURIComponent(name)}`)}
    >
      <div className="watchlist-card-main">
        <span className="watchlist-card-name">{name}</span>
        {feedDown ? (
          <span className="watchlist-card-feed-down">FEED DOWN</span>
        ) : (
          <span className="watchlist-card-price tabular-nums">
            ${quote?.price?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            {unit}
          </span>
        )}
      </div>
      <div className="watchlist-card-side">
        {!feedDown && quote && (
          <span
            className={
              pctPositive
                ? 'watchlist-card-pct watchlist-card-pct--up tabular-nums'
                : 'watchlist-card-pct watchlist-card-pct--down tabular-nums'
            }
          >
            {pctPositive ? '+' : ''}
            {pct.toFixed(2)}%
          </span>
        )}
        {bias && (
          <span className="watchlist-card-chip" style={{ color: chipColor, borderColor: chipColor }}>
            {bias.state.replace(/^[^\s]+\s/, '')}
          </span>
        )}
      </div>
    </button>
  )
}
