import { useState } from 'react'
import './FullBacktestSection.css'

const STRATEGIES = ['meanrev', 'breakout', 'rsi']

function pct(n) {
  return `${n >= 0 ? '+' : ''}${(n * 100).toFixed(1)}%`
}

function DirectionStats({ label, block }) {
  return (
    <div className="fb-dir-row">
      <span className="fb-dir-label">{label}</span>
      <span className="fb-dir-value tabular-nums">{block.n} trades</span>
      <span className="fb-dir-value tabular-nums">{(block.win_rate * 100).toFixed(0)}% win</span>
      <span className="fb-dir-value fb-dir-value--long tabular-nums">
        {pct(block.avg_win)}
      </span>
      <span className="fb-dir-value fb-dir-value--short tabular-nums">
        {pct(block.avg_loss)}
      </span>
    </div>
  )
}

function TradeRow({ trade }) {
  const win = trade.return_pct >= 0
  return (
    <div className={win ? 'fb-trade fb-trade--win' : 'fb-trade fb-trade--loss'}>
      <div className="fb-trade-main">
        <span className="fb-trade-type">{trade.direction === 'long' ? 'LONG' : 'SHORT'}</span>
        <span className="fb-trade-dates">
          {trade.entry_date} → {trade.exit_date}
        </span>
      </div>
      <span className={win ? 'fb-trade-badge fb-trade-badge--win tabular-nums' : 'fb-trade-badge fb-trade-badge--loss tabular-nums'}>
        {trade.return_pct >= 0 ? '+' : ''}
        {trade.return_pct.toFixed(1)}%
      </span>
    </div>
  )
}

export default function FullBacktestSection({ results, loading }) {
  const [open, setOpen] = useState(false)
  const [strategy, setStrategy] = useState('meanrev')

  const entry = results?.[strategy]
  const data = entry?.data

  return (
    <section className="fb-section">
      <button type="button" className="fb-toggle" onClick={() => setOpen((o) => !o)}>
        <span>Full Backtest</span>
        <span className={open ? 'fb-toggle-chevron fb-toggle-chevron--open' : 'fb-toggle-chevron'}>
          ▾
        </span>
      </button>

      {open && (
        <div className="fb-body">
          <div className="fb-strategy-pills">
            {STRATEGIES.map((key) => (
              <button
                key={key}
                type="button"
                className={key === strategy ? 'fb-pill fb-pill--active' : 'fb-pill'}
                onClick={() => setStrategy(key)}
              >
                {results?.[key]?.data?.strategy_meta.name ?? key}
              </button>
            ))}
          </div>

          {loading && <div className="skeleton fb-skeleton" />}

          {!loading && (!data || entry.error) && (
            <div className="fb-feed-down">FEED DOWN — could not load this strategy.</div>
          )}

          {data && (
            <>
              <div className="fb-returns-row">
                <div className="fb-return-tile">
                  <span className="fb-return-label">Strategy Return</span>
                  <span
                    className="fb-return-value tabular-nums"
                    style={{ color: data.stats.strategy_return >= 0 ? 'var(--long)' : 'var(--short)' }}
                  >
                    {pct(data.stats.strategy_return)}
                  </span>
                </div>
                <div className="fb-return-tile">
                  <span className="fb-return-label">Buy & Hold</span>
                  <span className="fb-return-value tabular-nums">
                    {pct(data.stats.buy_hold_return)}
                  </span>
                </div>
                <div className="fb-return-tile">
                  <span className="fb-return-label">Max Drawdown</span>
                  <span className="fb-return-value fb-return-value--short tabular-nums">
                    {pct(data.stats.max_drawdown)}
                  </span>
                </div>
              </div>

              <div className="fb-dir-table">
                <DirectionStats label="All" block={data.stats.all} />
                <DirectionStats label="Long" block={data.stats.long} />
                <DirectionStats label="Short" block={data.stats.short} />
              </div>

              <span className="fb-trades-title">Last {Math.min(15, data.trades.length)} Trades</span>
              <div className="fb-trades-list">
                {data.trades.slice(-15).reverse().map((t, i) => (
                  <TradeRow key={i} trade={t} />
                ))}
                {data.trades.length === 0 && (
                  <p className="fb-trades-empty">No trades in this window.</p>
                )}
              </div>
            </>
          )}
        </div>
      )}
    </section>
  )
}
