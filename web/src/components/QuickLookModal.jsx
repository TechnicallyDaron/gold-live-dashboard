import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api.js'
import { plainState } from '../lib/plainState.js'
import './QuickLookModal.css'

const DISMISS_THRESHOLD = 90

export default function QuickLookModal({ symbol, quote, onClose }) {
  const navigate = useNavigate()
  const [bias, setBias] = useState(null)
  const [error, setError] = useState(null)
  const [dragY, setDragY] = useState(0)
  const dragState = useRef(null)

  useEffect(() => {
    let cancelled = false
    setBias(null)
    setError(null)
    api
      .bias(symbol)
      .then((d) => !cancelled && setBias(d))
      .catch((err) => !cancelled && setError(err))
    return () => {
      cancelled = true
    }
  }, [symbol])

  const onTouchStart = (e) => {
    dragState.current = { startY: e.touches[0].clientY }
  }
  const onTouchMove = (e) => {
    if (!dragState.current) return
    const delta = e.touches[0].clientY - dragState.current.startY
    setDragY(Math.max(0, delta))
  }
  const onTouchEnd = () => {
    if (dragY > DISMISS_THRESHOLD) {
      onClose()
    } else {
      setDragY(0)
    }
    dragState.current = null
  }

  const plain = bias ? plainState(bias) : null

  return (
    <div className="ql-overlay" onClick={onClose}>
      <div
        className="ql-sheet"
        style={{ transform: `translateY(${dragY}px)` }}
        onClick={(e) => e.stopPropagation()}
        onTouchStart={onTouchStart}
        onTouchMove={onTouchMove}
        onTouchEnd={onTouchEnd}
      >
        <div className="ql-handle" />

        <div className="ql-header">
          <span className="ql-symbol">{symbol}</span>
          {quote && (
            <div className="ql-quote">
              <span className="ql-price tabular-nums">${quote.price?.toLocaleString()}</span>
              <span
                className={quote.pct >= 0 ? 'ql-pct ql-pct--up tabular-nums' : 'ql-pct ql-pct--down tabular-nums'}
              >
                {quote.pct >= 0 ? '+' : ''}
                {quote.pct?.toFixed(2)}%
              </span>
            </div>
          )}
        </div>

        {error && !bias && (
          <div className="ql-error">Could not load a read for {symbol}. Try again shortly.</div>
        )}

        {!bias && !error && <div className="skeleton ql-skeleton" />}

        {plain && (
          <div className="ql-plain">
            <span className="ql-plain-emoji">{plain.emoji}</span>
            <p className="ql-plain-headline">{plain.headline}</p>
            <p className="ql-plain-action">{plain.action}</p>
          </div>
        )}

        <button
          type="button"
          className="ql-full-link"
          onClick={() => {
            onClose()
            navigate(`/bias/${encodeURIComponent(symbol)}`)
          }}
        >
          Full analysis →
        </button>
      </div>
    </div>
  )
}
