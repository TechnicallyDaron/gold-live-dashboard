import { useState } from 'react'
import { api } from '../lib/api.js'
import { showToast } from '../lib/toast.js'
import { markOnboardingSkipped } from '../lib/onboarding.js'
import './OnboardingBaskets.css'

const BASKETS = [
  {
    key: 'index',
    name: 'Index ETFs',
    items: ['SPY', 'QQQ', 'IWM', 'DIA'],
  },
  {
    key: 'megacap',
    name: 'Megacap Tech',
    items: ['AAPL', 'MSFT', 'NVDA', 'AMZN', 'GOOG', 'META'],
  },
  {
    key: 'velocity',
    name: 'High-Velocity',
    items: ['TSLA', 'COIN', 'MSTR', 'PLTR', 'MARA'],
  },
  {
    key: 'commodities',
    name: 'Commodities + Rates',
    items: ['GLD', 'USO', 'TLT', 'SLV'],
  },
]

export default function OnboardingBaskets({ userId, onDone, onSkip }) {
  const [selectedBaskets, setSelectedBaskets] = useState(new Set())
  const [customTickers, setCustomTickers] = useState([])
  const [customInput, setCustomInput] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [confirmingSkip, setConfirmingSkip] = useState(false)

  const toggleBasket = (key) => {
    setSelectedBaskets((prev) => {
      const next = new Set(prev)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }

  const addCustomTicker = () => {
    const ticker = customInput.trim().toUpperCase()
    if (!ticker) return
    if (customTickers.includes(ticker)) {
      setCustomInput('')
      return
    }
    setCustomTickers((prev) => [...prev, ticker])
    setCustomInput('')
  }

  const removeCustomTicker = (ticker) => {
    setCustomTickers((prev) => prev.filter((t) => t !== ticker))
  }

  const basketTickers = BASKETS.filter((b) => selectedBaskets.has(b.key)).flatMap((b) => b.items)
  const allTickers = [...new Set([...basketTickers, ...customTickers])]
  const count = allTickers.length

  const submit = async () => {
    if (!count || submitting) return
    setSubmitting(true)
    let lastWatchlist = null
    let failures = 0
    for (const ticker of allTickers) {
      try {
        const res = await api.addWatchlist({ name: ticker, ticker, unit: '/sh' })
        lastWatchlist = res.watchlist
      } catch (err) {
        if (err.status !== 409) {
          failures += 1
          showToast(`${ticker}: ${err.message}`, 'error')
        }
      }
    }
    setSubmitting(false)
    if (lastWatchlist) {
      showToast(
        failures ? `Added what we could — ${failures} ticker(s) failed` : `🎯 HUB built — ${count - failures} tracked`,
        failures ? 'warning' : 'success'
      )
      onDone(lastWatchlist)
    } else if (failures) {
      showToast('Could not add any tickers — try again', 'error')
    }
  }

  const confirmSkip = () => {
    markOnboardingSkipped(userId)
    onSkip()
  }

  return (
    <div className="onboarding-screen">
      <div className="onboarding-card">
        <h1 className="onboarding-title">Build your HUB</h1>
        <p className="onboarding-subtitle">
          Pick a starter basket, add your own tickers, or skip and start empty.
        </p>

        <div className="onboarding-baskets">
          {BASKETS.map((b) => {
            const active = selectedBaskets.has(b.key)
            return (
              <button
                key={b.key}
                type="button"
                className={`onboarding-basket-chip ${active ? 'onboarding-basket-chip--active' : ''}`}
                onClick={() => toggleBasket(b.key)}
              >
                <span className="onboarding-basket-name">{b.name}</span>
                <span className="onboarding-basket-tickers">{b.items.join(' · ')}</span>
              </button>
            )
          })}
        </div>

        <div className="onboarding-custom">
          <span className="onboarding-custom-label">Add your own</span>
          <div className="onboarding-custom-row">
            <input
              className="onboarding-custom-input"
              placeholder="e.g. PLTR"
              value={customInput}
              onChange={(e) => setCustomInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && addCustomTicker()}
            />
            <button type="button" className="onboarding-custom-add" onClick={addCustomTicker}>
              + Add
            </button>
          </div>
          {customTickers.length > 0 && (
            <div className="onboarding-custom-pills">
              {customTickers.map((t) => (
                <button
                  key={t}
                  type="button"
                  className="onboarding-custom-pill"
                  onClick={() => removeCustomTicker(t)}
                >
                  {t} ✕
                </button>
              ))}
            </div>
          )}
        </div>

        <button
          type="button"
          className="onboarding-submit"
          disabled={!count || submitting}
          onClick={submit}
        >
          {submitting ? 'Building…' : count ? `Add ${count} to HUB` : 'Select something to add'}
        </button>

        {confirmingSkip ? (
          <div className="onboarding-skip-confirm">
            <span>Start with an empty HUB?</span>
            <div className="onboarding-skip-confirm-actions">
              <button type="button" className="onboarding-skip-cancel" onClick={() => setConfirmingSkip(false)}>
                Cancel
              </button>
              <button type="button" className="onboarding-skip-yes" onClick={confirmSkip}>
                Yes, skip
              </button>
            </div>
          </div>
        ) : (
          <button type="button" className="onboarding-skip" onClick={() => setConfirmingSkip(true)}>
            Skip for now
          </button>
        )}
      </div>
    </div>
  )
}
