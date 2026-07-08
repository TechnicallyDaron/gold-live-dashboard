import ReasonChips from './ReasonChips.jsx'
import './StrategyLabSection.css'

export default function StrategyLabSection({ data, loading }) {
  if (loading) return <div className="skeleton strategy-lab-skeleton" />
  if (!data) return null

  return (
    <section className="strategy-lab">
      <span className="strategy-lab-title">Strategy Lab — walk-forward validated</span>

      {data.flag === 'STRATEGY_ASSIGNED' ? (
        <div className="strategy-lab-verdict strategy-lab-verdict--assigned">
          <span className="strategy-lab-verdict-badge">✅ Assigned: {data.assigned.name}</span>
          <span className="strategy-lab-verdict-detail">
            {(data.assigned.test.win_rate * 100).toFixed(0)}% win rate · PF{' '}
            {data.assigned.test.profit_factor ?? '∞'} ·{' '}
            {data.assigned.test.expectancy_pct >= 0 ? '+' : ''}
            {data.assigned.test.expectancy_pct}% per trade (held-out 30% of history)
          </span>
        </div>
      ) : (
        <div className="strategy-lab-verdict strategy-lab-verdict--nothing">
          <span className="strategy-lab-verdict-badge">⚪ NOTHING_VALIDATED — standing aside</span>
          <span className="strategy-lab-verdict-detail">
            No strategy cleared the bar on held-out data. Here's exactly why each one failed:
          </span>
        </div>
      )}

      <div className="strategy-lab-results">
        {data.results.map((r) => (
          <div key={r.strategy} className="strategy-lab-result">
            <div className="strategy-lab-result-head">
              <span className="strategy-lab-result-name">{r.name}</span>
              <span
                className={
                  r.validated
                    ? 'strategy-lab-result-tag strategy-lab-result-tag--pass'
                    : 'strategy-lab-result-tag strategy-lab-result-tag--fail'
                }
              >
                {r.validated ? 'VALIDATED' : 'FAILED'}
              </span>
            </div>
            {!r.validated && <ReasonChips reasons={r.fail_reasons} />}
          </div>
        ))}
      </div>
    </section>
  )
}
