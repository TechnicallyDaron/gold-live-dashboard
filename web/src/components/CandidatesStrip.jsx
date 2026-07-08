import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useCandidates } from '../lib/useCandidates.js'
import './CandidatesStrip.css'

export default function CandidatesStrip() {
  const { candidates, note, loading } = useCandidates()
  const [open, setOpen] = useState(false)
  const navigate = useNavigate()

  return (
    <section className="candidates-strip">
      <button type="button" className="candidates-toggle" onClick={() => setOpen((o) => !o)}>
        <span>🔎 Velocity leads{candidates ? ` (${candidates.length})` : ''}</span>
        <span className={open ? 'candidates-chevron candidates-chevron--open' : 'candidates-chevron'}>▾</span>
      </button>

      {open && (
        <div className="candidates-body">
          {note && <p className="candidates-note">{note}</p>}

          {loading && <div className="skeleton candidates-skeleton" />}

          {!loading && candidates && candidates.length === 0 && (
            <p className="candidates-empty">No fast-family signals firing across the watchlist right now.</p>
          )}

          {candidates &&
            candidates.map((c, i) => (
              <button
                key={i}
                type="button"
                className="candidates-row"
                onClick={() => navigate(`/bias/${encodeURIComponent(c.asset)}`)}
              >
                <div className="candidates-row-main">
                  <span className="candidates-row-asset">{c.asset}</span>
                  <span className="candidates-row-detail">
                    {c.family_name} · {c.side} · ${c.price?.toLocaleString()}
                  </span>
                </div>
                {c.validated ? (
                  <span className="candidates-validated-chip">✅ validated</span>
                ) : (
                  <span className="candidates-unvalidated-chip">⚠️ UNVALIDATED — run Lab first</span>
                )}
              </button>
            ))}
        </div>
      )}
    </section>
  )
}
