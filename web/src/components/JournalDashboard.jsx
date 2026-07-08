import { useState } from 'react'
import PnlBadge from './PnlBadge.jsx'
import './JournalDashboard.css'

function fmtPct(x) {
  return x == null ? '—' : `${Math.round(x * 100)}%`
}

function fmtSignedPct(x) {
  return x == null ? '—' : `${x >= 0 ? '+' : ''}${x.toFixed(1)}%`
}

function adherenceColor(x) {
  if (x == null) return 'var(--muted)'
  if (x >= 0.8) return 'var(--long)'
  if (x >= 0.5) return 'var(--watch)'
  return 'var(--short)'
}

function JournalEntryRow({ entry }) {
  const [expanded, setExpanded] = useState(false)
  const compliant = entry.rule_compliant

  return (
    <div className="journal-entry" onClick={() => setExpanded((e) => !e)}>
      <div className="journal-entry-top">
        <div className="journal-entry-main">
          <span className="journal-entry-asset">{entry.asset}</span>
          <span className="journal-entry-dates">
            {entry.entry_date || '—'} → {entry.exit_date || '—'}
          </span>
        </div>
        <div className="journal-entry-right">
          <span
            className={
              compliant == null
                ? 'journal-entry-compliant journal-entry-compliant--na'
                : compliant
                ? 'journal-entry-compliant journal-entry-compliant--yes'
                : 'journal-entry-compliant journal-entry-compliant--no'
            }
          >
            {compliant == null ? '—' : compliant ? '✓' : '✗'}
          </span>
          <PnlBadge pnlPct={entry.pnl_pct} size="sm" />
        </div>
      </div>
      {expanded && entry.thesis && <p className="journal-entry-thesis">{entry.thesis}</p>}
      {expanded && entry.notes && <p className="journal-entry-notes">{entry.notes}</p>}
    </div>
  )
}

export default function JournalDashboard({ entries, aggregates, loading }) {
  if (loading && !entries) {
    return <div className="skeleton journal-skeleton" />
  }
  if (!entries) return null

  return (
    <section className="journal-dash">
      <span className="journal-dash-title">Journal</span>

      {entries.length === 0 ? (
        <p className="journal-empty">No closed trades yet. Close a position to start your track record.</p>
      ) : (
        <>
          <div
            className="journal-adherence"
            style={{ borderColor: adherenceColor(aggregates.rule_adherence) }}
          >
            <span className="journal-adherence-value" style={{ color: adherenceColor(aggregates.rule_adherence) }}>
              {fmtPct(aggregates.rule_adherence)}
            </span>
            <span className="journal-adherence-label">Rule Adherence — your discipline grade</span>
          </div>

          <div className="journal-stats">
            <div className="journal-stat">
              <span className="journal-stat-value">{aggregates.total_trades}</span>
              <span className="journal-stat-label">Trades</span>
            </div>
            <div className="journal-stat">
              <span className="journal-stat-value">{fmtPct(aggregates.win_rate)}</span>
              <span className="journal-stat-label">Win Rate</span>
            </div>
            <div className="journal-stat">
              <span
                className="journal-stat-value"
                style={{ color: aggregates.avg_pnl_pct >= 0 ? 'var(--long)' : 'var(--short)' }}
              >
                {fmtSignedPct(aggregates.avg_pnl_pct)}
              </span>
              <span className="journal-stat-label">Avg PnL</span>
            </div>
            <div className="journal-stat">
              <span className="journal-stat-value">
                {aggregates.avg_holding_days != null ? `${aggregates.avg_holding_days}d` : '—'}
              </span>
              <span className="journal-stat-label">Avg Hold</span>
            </div>
          </div>

          {aggregates.per_strategy && Object.keys(aggregates.per_strategy).length > 0 && (
            <div className="journal-strategy-table">
              {Object.entries(aggregates.per_strategy).map(([name, s]) => (
                <div className="journal-strategy-row" key={name}>
                  <span className="journal-strategy-name">{name}</span>
                  <span className="journal-strategy-detail tabular-nums">{s.n} trades</span>
                  <span className="journal-strategy-detail tabular-nums">{fmtPct(s.win_rate)} win</span>
                  <span
                    className="journal-strategy-detail tabular-nums"
                    style={{ color: s.avg_pnl_pct >= 0 ? 'var(--long)' : 'var(--short)' }}
                  >
                    {fmtSignedPct(s.avg_pnl_pct)}
                  </span>
                </div>
              ))}
            </div>
          )}

          <div className="journal-entries">
            {[...entries].reverse().map((e, i) => (
              <JournalEntryRow key={i} entry={e} />
            ))}
          </div>
        </>
      )}
    </section>
  )
}
