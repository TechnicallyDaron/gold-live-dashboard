import { useState } from 'react'
import { api } from '../lib/api.js'
import { showToast } from '../lib/toast.js'
import BottomSheet from './BottomSheet.jsx'
import './FormField.css'

export default function WatchlistAddForm({ onClose, onSaved }) {
  const [ticker, setTicker] = useState('')
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [addedName, setAddedName] = useState(null)

  const canSubmit = ticker.trim() && !submitting

  const submit = async () => {
    setError(null)
    setSubmitting(true)
    try {
      const tickerUpper = ticker.trim().toUpperCase()
      const res = await api.addWatchlist({ ticker: tickerUpper })
      // The backend resolves the company name server-side — find the entry
      // it just created by matching the ticker back against the returned
      // watchlist rather than assuming any particular key.
      const resolvedName =
        Object.keys(res.watchlist).find((n) => res.watchlist[n].ticker === tickerUpper) || tickerUpper
      onSaved?.(res.watchlist)
      showToast(`✅ ${resolvedName} added to your watchlist`, 'success')
      if (res.persistence_warning) showToast(res.persistence_warning, 'warning')
      setAddedName(resolvedName)
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <BottomSheet title="Add to Watchlist" onClose={onClose} heightVh={addedName ? 38 : 42}>
      {addedName ? (
        <div className="field-success">
          <span className="field-success-icon">✓</span>
          <p className="field-success-text">
            <strong>{addedName}</strong> added to your watchlist.
          </p>
          <button type="button" className="field-submit" onClick={onClose}>
            Done
          </button>
        </div>
      ) : (
        <>
          <div className="field">
            <span className="field-label">Ticker</span>
            <input
              className="field-input" placeholder="e.g. PLTR" style={{ textTransform: 'uppercase' }}
              value={ticker} onChange={(e) => setTicker(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && submit()}
            />
          </div>

          {error && <p className="field-error">{error}</p>}

          <button type="button" className="field-submit" disabled={!canSubmit} onClick={submit}>
            {submitting ? 'Adding…' : 'Add Asset'}
          </button>
        </>
      )}
    </BottomSheet>
  )
}
