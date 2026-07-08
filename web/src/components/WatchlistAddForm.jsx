import { useState } from 'react'
import { api } from '../lib/api.js'
import { showToast } from '../lib/toast.js'
import BottomSheet from './BottomSheet.jsx'
import './FormField.css'

export default function WatchlistAddForm({ onClose, onSaved }) {
  const [name, setName] = useState('')
  const [ticker, setTicker] = useState('')
  const [unit, setUnit] = useState('/sh')
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  const canSubmit = name.trim() && ticker.trim() && !submitting

  const submit = async () => {
    setError(null)
    setSubmitting(true)
    try {
      const res = await api.addWatchlist({ name: name.trim(), ticker: ticker.trim(), unit })
      showToast(`✅ ${name.trim()} added to your watchlist`, 'success')
      if (res.persistence_warning) showToast(res.persistence_warning, 'warning')
      onSaved?.(res.watchlist)
      onClose()
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <BottomSheet title="Add to Watchlist" onClose={onClose} heightVh={52}>
      <div className="field">
        <span className="field-label">Display Name</span>
        <input
          className="field-input" placeholder="e.g. Palantir"
          value={name} onChange={(e) => setName(e.target.value)}
        />
      </div>
      <div className="field-row">
        <div className="field">
          <span className="field-label">Ticker</span>
          <input
            className="field-input" placeholder="e.g. PLTR" style={{ textTransform: 'uppercase' }}
            value={ticker} onChange={(e) => setTicker(e.target.value)}
          />
        </div>
        <div className="field">
          <span className="field-label">Unit</span>
          <select className="field-select" value={unit} onChange={(e) => setUnit(e.target.value)}>
            <option value="/sh">/sh</option>
            <option value="/oz">/oz</option>
            <option value="">(none)</option>
          </select>
        </div>
      </div>

      {error && <p className="field-error">{error}</p>}

      <button type="button" className="field-submit" disabled={!canSubmit} onClick={submit}>
        {submitting ? 'Adding…' : 'Add Asset'}
      </button>
    </BottomSheet>
  )
}
