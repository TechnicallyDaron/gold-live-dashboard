import { viabilityColorVar } from '../lib/colors.js'
import './BacktestStrip.css'

const STRATEGIES = ['meanrev', 'breakout', 'rsi']

export default function BacktestStrip({ results, loading }) {
  return (
    <div className="backtest-strip">
      <span className="backtest-strip-title">Backtest Viability</span>
      <div className="backtest-strip-row">
        {STRATEGIES.map((key) => {
          if (loading || !results) {
            return <div key={key} className="skeleton backtest-tile-skeleton" />
          }
          const entry = results[key]
          if (!entry || entry.error) {
            return (
              <div key={key} className="backtest-tile backtest-tile--down">
                <span className="backtest-tile-name">{key}</span>
                <span className="backtest-tile-verdict">FEED DOWN</span>
              </div>
            )
          }
          const { data } = entry
          const color = viabilityColorVar(data.viability.class)
          return (
            <div key={key} className="backtest-tile" style={{ borderColor: color }}>
              <span className="backtest-tile-name">{data.strategy_meta.name}</span>
              <span className="backtest-tile-verdict" style={{ color }}>
                {data.viability.verdict.replace(/^[^\s]+\s/, '')}
              </span>
              <span className="backtest-tile-meta tabular-nums">
                PF {data.viability.profit_factor ?? '∞'} · {(data.stats.strategy_return * 100).toFixed(1)}%
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
