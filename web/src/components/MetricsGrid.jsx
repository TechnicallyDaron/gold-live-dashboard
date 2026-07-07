import './MetricsGrid.css'

function fmt(n) {
  return n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

export default function MetricsGrid({ bias, unit }) {
  const trendUp = bias.trend.startsWith('BULLISH')

  return (
    <div className="metrics-grid">
      <div className="metric-tile">
        <span className="metric-label">Spot</span>
        <span className="metric-value tabular-nums">
          ${fmt(bias.price)}
          {unit}
        </span>
      </div>
      <div className="metric-tile">
        <span className="metric-label">Z-Score</span>
        <span className="metric-value tabular-nums">{bias.z >= 0 ? '+' : ''}{bias.z.toFixed(2)}σ</span>
      </div>
      <div className="metric-tile">
        <span className="metric-label">20 EMA</span>
        <span className="metric-value tabular-nums">
          ${fmt(bias.baseline)}
          {unit}
        </span>
      </div>
      <div className="metric-tile">
        <span className="metric-label">Trend</span>
        <span
          className="metric-value"
          style={{ color: trendUp ? 'var(--long)' : 'var(--short)' }}
        >
          {trendUp ? 'BULLISH' : 'BEARISH'}
        </span>
      </div>
      <div className="metric-tile metric-tile--wide">
        <span className="metric-label">Bands (Lower – Upper)</span>
        <span className="metric-value tabular-nums">
          ${fmt(bias.lower)} – ${fmt(bias.upper)}
          {unit}
        </span>
      </div>
    </div>
  )
}
