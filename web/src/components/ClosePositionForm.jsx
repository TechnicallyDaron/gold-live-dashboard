import { useState } from 'react'
import { api } from '../lib/api.js'
import { showToast } from '../lib/toast.js'
import BottomSheet from './BottomSheet.jsx'
import './FormField.css'

export default function ClosePositionForm({ position, onClose, onSaved }) {
  const [exitPremium, setExitPremium] = useState('')
  const [thesis, setThesis] = useState('')
  const [ruleCompliant, setRuleCompliant] = useState(null)
  const [notes, setNotes] = useState('')
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  const canSubmit = exitPremium !== '' && ruleCompliant !== null && !submitting

  const submit = async () => {
    setError(null)
    setSubmitting(true)
    try {
      const body = {
        exit_premium: parseFloat(exitPremium),
        rule_compliant: ruleCompliant,
      }
      if (thesis.trim()) body.thesis = thesis.trim()
      if (notes.trim()) body.notes = notes.trim()

      const res = await api.closePosition(position.id, body)
      const pct = res.journal_entry?.pnl_pct
      showToast(
        pct != null ? `📒 Position closed — ${pct >= 0 ? '+' : ''}${pct.toFixed(1)}%` : '📒 Position closed',
        pct != null ? (pct >= 0 ? 'success' : 'error') : 'default'
      )
      if (res.persistence_warning) showToast(res.persistence_warning, 'warning')
      onSaved?.()
      onClose()
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <BottomSheet title={`Close ${position.asset} $${position.strike}${String(position.type || '').slice(0, 1).toUpperCase()}`} onClose={onClose} heightVh={70}>
      <div className="field">
        <span className="field-label">Exit Premium</span>
        <input
          className="field-input" type="number" inputMode="decimal" placeholder="1.26"
          value={exitPremium} onChange={(e) => setExitPremium(e.target.value)}
        />
      </div>

      <div className="field">
        <span className="field-label">Thesis (optional)</span>
        <input
          className="field-input" placeholder="Why you took this trade"
          value={thesis} onChange={(e) => setThesis(e.target.value)}
        />
      </div>

      <div className="field">
        <span className="field-label">Did this exit follow your plan?</span>
        <div className="field-toggle-row">
          <button
            type="button"
            className={`field-toggle ${ruleCompliant === true ? 'field-toggle--active-long' : ''}`}
            onClick={() => setRuleCompliant(true)}
          >
            Yes
          </button>
          <button
            type="button"
            className={`field-toggle ${ruleCompliant === false ? 'field-toggle--active-short' : ''}`}
            onClick={() => setRuleCompliant(false)}
          >
            No
          </button>
        </div>
      </div>

      <div className="field">
        <span className="field-label">Notes (optional)</span>
        <input
          className="field-input" placeholder="Anything worth remembering"
          value={notes} onChange={(e) => setNotes(e.target.value)}
        />
      </div>

      {error && <p className="field-error">{error}</p>}

      <button type="button" className="field-submit" disabled={!canSubmit} onClick={submit}>
        {submitting ? 'Closing…' : 'Close Position'}
      </button>
    </BottomSheet>
  )
}
