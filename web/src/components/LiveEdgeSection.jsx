import ReasonChips from './ReasonChips.jsx'
import './LiveEdgeSection.css'

export default function LiveEdgeSection({ data, loading }) {
  if (loading) return <div className="skeleton live-edge-skeleton" />
  if (!data) return null

  const found = data.flag === 'EDGE_FOUND'
  const candidateKeys = new Set((data.candidates || []).map((c) => c.strategy))
  const firing = (data.scanned || []).filter((s) => s.signal_today && !candidateKeys.has(s.strategy))

  return (
    <section className="live-edge">
      <span className="live-edge-title">Live Edge Check — is a validated setup firing today?</span>

      <div className={found ? 'live-edge-verdict live-edge-verdict--found' : 'live-edge-verdict live-edge-verdict--none'}>
        <span className="live-edge-verdict-badge">
          {found ? '🎯 EDGE_FOUND' : '⚪ NO_EDGE'}
        </span>
        {found ? (
          <div className="live-edge-candidates">
            {data.candidates.map((c) => (
              <div key={c.strategy} className="live-edge-candidate">
                <span className="live-edge-candidate-name">
                  {c.name} — {c.signal_today}
                </span>
                <span className="live-edge-candidate-stat tabular-nums">
                  {(c.win_rate_5y * 100).toFixed(0)}% win · {c.trades_5y} trades
                </span>
              </div>
            ))}
          </div>
        ) : (
          <>
            <span className="live-edge-verdict-detail">
              Nothing signaling today clears the bar (
              {(data.thresholds.win_rate * 100).toFixed(0)}%+ win rate, {data.thresholds.min_trades}+ trades, 5yr history).
            </span>
            {firing.length > 0 && (
              <ReasonChips
                reasons={firing.map(
                  (s) =>
                    `${s.name}: signaling ${s.signal_today} today, but only ${(s.win_rate_5y * 100).toFixed(0)}% win rate over ${s.trades_5y} trades historically`
                )}
              />
            )}
          </>
        )}
      </div>

      <p className="live-edge-regime">
        Regime: <strong>{data.regime.label}</strong> · {data.regime.drift_pct >= 0 ? '+' : ''}
        {data.regime.drift_pct}% over {data.regime.window_days}d · {data.regime.note}
      </p>
    </section>
  )
}
