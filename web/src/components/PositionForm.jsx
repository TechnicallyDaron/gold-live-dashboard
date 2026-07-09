import { useState } from 'react'
import { api } from '../lib/api.js'
import { showToast } from '../lib/toast.js'
import { useRiskSettings } from '../lib/useRiskSettings.js'
import BottomSheet from './BottomSheet.jsx'
import './FormField.css'
import './PositionForm.css'

const todayISO = () => new Date().toISOString().slice(0, 10)

export default function PositionForm({ watchlist, onClose, onSaved }) {
  const names = Object.keys(watchlist || {})
  const [asset, setAsset] = useState(names[0] ? watchlist[names[0]].ticker : '')
  const [strike, setStrike] = useState('')
  const [contractType, setContractType] = useState('call')
  const [entryPremium, setEntryPremium] = useState('')
  const [entryDate, setEntryDate] = useState(todayISO())
  const [expiration, setExpiration] = useState('')
  const [premiumStop, setPremiumStop] = useState('')
  const [timeStop, setTimeStop] = useState('')
  const [invalAbove, setInvalAbove] = useState('')
  const [invalBelow, setInvalBelow] = useState('')
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [riskSettings, setRiskSettings] = useRiskSettings()
  const [settingsOpen, setSettingsOpen] = useState(false)

  const canSubmit = asset && strike && entryPremium && entryDate && expiration && !submitting

  // Purely informational — never gates canSubmit above.
  const premiumNum = parseFloat(entryPremium)
  const maxDollarRisk = riskSettings.accountSize * (riskSettings.maxPct / 100)
  const maxContracts =
    riskSettings.accountSize > 0 && premiumNum > 0 ? Math.floor(maxDollarRisk / (premiumNum * 100)) : null

  const submit = async () => {
    setError(null)
    setSubmitting(true)
    try {
      const body = {
        asset,
        strike: parseFloat(strike),
        contract_type: contractType,
        entry_premium: parseFloat(entryPremium),
        entry_date: entryDate,
        expiration,
      }
      if (premiumStop) body.premium_stop = parseFloat(premiumStop)
      if (timeStop) body.time_stop = timeStop
      if (invalAbove) body.invalidation_above = parseFloat(invalAbove)
      if (invalBelow) body.invalidation_below = parseFloat(invalBelow)

      const res = await api.addPosition(body)
      showToast('🛡 Guardian armed', 'success')
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
    <BottomSheet title="Log Position" onClose={onClose}>
      <button
        type="button"
        className="ps-settings-toggle"
        onClick={() => setSettingsOpen((v) => !v)}
      >
        <span>⚙️ Risk settings</span>
        <span className="ps-settings-summary tabular-nums">
          ${riskSettings.accountSize.toLocaleString()} · {riskSettings.maxPct}% max
        </span>
      </button>

      {settingsOpen && (
        <div className="ps-settings-panel field-row">
          <div className="field">
            <span className="field-label">Account Size</span>
            <input
              className="field-input" type="number" inputMode="decimal" placeholder="10000"
              value={riskSettings.accountSize || ''}
              onChange={(e) =>
                setRiskSettings((s) => ({ ...s, accountSize: parseFloat(e.target.value) || 0 }))
              }
            />
          </div>
          <div className="field">
            <span className="field-label">Max % / Trade</span>
            <input
              className="field-input" type="number" inputMode="decimal" placeholder="25"
              value={riskSettings.maxPct || ''}
              onChange={(e) =>
                setRiskSettings((s) => ({ ...s, maxPct: parseFloat(e.target.value) || 0 }))
              }
            />
          </div>
        </div>
      )}

      <div className="field">
        <span className="field-label">Asset</span>
        <select className="field-select" value={asset} onChange={(e) => setAsset(e.target.value)}>
          {names.map((n) => (
            <option key={n} value={watchlist[n].ticker}>
              {n}
            </option>
          ))}
        </select>
      </div>

      <div className="field-row">
        <div className="field">
          <span className="field-label">Strike</span>
          <input
            className="field-input" type="number" inputMode="decimal" placeholder="17.50"
            value={strike} onChange={(e) => setStrike(e.target.value)}
          />
        </div>
        <div className="field">
          <span className="field-label">Type</span>
          <div className="field-toggle-row">
            <button
              type="button"
              className={`field-toggle ${contractType === 'call' ? 'field-toggle--active-long' : ''}`}
              onClick={() => setContractType('call')}
            >
              Call
            </button>
            <button
              type="button"
              className={`field-toggle ${contractType === 'put' ? 'field-toggle--active-short' : ''}`}
              onClick={() => setContractType('put')}
            >
              Put
            </button>
          </div>
        </div>
      </div>

      <div className="field">
        <span className="field-label">Premium Paid</span>
        <input
          className="field-input" type="number" inputMode="decimal" placeholder="1.04"
          value={entryPremium} onChange={(e) => setEntryPremium(e.target.value)}
        />
        {maxContracts !== null && (
          maxContracts > 0 ? (
            <p className="ps-size-hint">
              Max: {maxContracts} contract{maxContracts === 1 ? '' : 's'} (≤ $
              {maxDollarRisk.toLocaleString(undefined, { maximumFractionDigits: 2 })} of your $
              {riskSettings.accountSize.toLocaleString()} account)
            </p>
          ) : (
            <p className="ps-size-hint ps-size-hint--warn">
              This contract exceeds your risk settings.
            </p>
          )
        )}
      </div>

      <div className="field-row">
        <div className="field">
          <span className="field-label">Entry Date</span>
          <input
            className="field-input" type="date"
            value={entryDate} onChange={(e) => setEntryDate(e.target.value)}
          />
        </div>
        <div className="field">
          <span className="field-label">Expiration</span>
          <input
            className="field-input" type="date"
            value={expiration} onChange={(e) => setExpiration(e.target.value)}
          />
        </div>
      </div>

      <div className="field-row">
        <div className="field">
          <span className="field-label">Premium Stop (optional)</span>
          <input
            className="field-input" type="number" inputMode="decimal" placeholder="0.52"
            value={premiumStop} onChange={(e) => setPremiumStop(e.target.value)}
          />
        </div>
        <div className="field">
          <span className="field-label">Time Stop (optional)</span>
          <input
            className="field-input" type="date"
            value={timeStop} onChange={(e) => setTimeStop(e.target.value)}
          />
        </div>
      </div>

      <div className="field-row">
        <div className="field">
          <span className="field-label">Invalidation Above (optional)</span>
          <input
            className="field-input" type="number" inputMode="decimal" placeholder="19.17"
            value={invalAbove} onChange={(e) => setInvalAbove(e.target.value)}
          />
        </div>
        <div className="field">
          <span className="field-label">Invalidation Below (optional)</span>
          <input
            className="field-input" type="number" inputMode="decimal"
            value={invalBelow} onChange={(e) => setInvalBelow(e.target.value)}
          />
        </div>
      </div>

      {error && <p className="field-error">{error}</p>}

      <button type="button" className="field-submit" disabled={!canSubmit} onClick={submit}>
        {submitting ? 'Arming…' : 'Log Position'}
      </button>
    </BottomSheet>
  )
}
