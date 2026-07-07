import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api.js'
import './MicroChart.css'

const CYCLE_MS = 8000
const VB_W = 300
const VB_H = 80

function toPath(values, min, max) {
  const range = max - min || 1
  const step = VB_W / Math.max(values.length - 1, 1)
  return values
    .map((v, i) => `${i === 0 ? 'M' : 'L'} ${(i * step).toFixed(1)} ${(VB_H - ((v - min) / range) * VB_H).toFixed(1)}`)
    .join(' ')
}

export default function MicroChart({ names }) {
  const navigate = useNavigate()
  const [index, setIndex] = useState(0)
  const [paused, setPaused] = useState(false)
  const [rows, setRows] = useState(null)
  const timerRef = useRef(null)

  const asset = names[index % Math.max(names.length, 1)]

  useEffect(() => {
    if (names.length === 0) return undefined
    if (paused) return undefined
    timerRef.current = setInterval(() => {
      setIndex((i) => (i + 1) % names.length)
    }, CYCLE_MS)
    return () => clearInterval(timerRef.current)
  }, [names.length, paused])

  useEffect(() => {
    if (!asset) return undefined
    let cancelled = false
    setRows(null)
    api
      .history(asset, 90)
      .then((d) => !cancelled && setRows(d.rows))
      .catch(() => !cancelled && setRows([]))
    return () => {
      cancelled = true
    }
  }, [asset])

  if (!asset) return null

  const lastPrice = rows && rows.length > 0 ? rows[rows.length - 1].price : null
  let pricePath = ''
  let baselinePath = ''
  if (rows && rows.length > 1) {
    const all = rows.flatMap((r) => [r.price, r.baseline])
    const min = Math.min(...all)
    const max = Math.max(...all)
    pricePath = toPath(rows.map((r) => r.price), min, max)
    baselinePath = toPath(rows.map((r) => r.baseline), min, max)
  }

  return (
    <button
      type="button"
      className="micro-chart"
      onTouchStart={() => setPaused(true)}
      onTouchEnd={() => setPaused(false)}
      onClick={() => navigate(`/chart/${encodeURIComponent(asset)}`)}
    >
      <div className="micro-chart-overlay">
        <span className="micro-chart-name">{asset}</span>
        {lastPrice != null && (
          <span className="micro-chart-price tabular-nums">
            ${lastPrice.toLocaleString(undefined, { maximumFractionDigits: 2 })}
          </span>
        )}
      </div>
      {rows && rows.length > 1 ? (
        <svg className="micro-chart-svg" viewBox={`0 0 ${VB_W} ${VB_H}`} preserveAspectRatio="none">
          <path d={baselinePath} className="micro-chart-baseline" />
          <path d={pricePath} className="micro-chart-price-line" />
        </svg>
      ) : (
        <div className="skeleton micro-chart-skeleton" />
      )}
    </button>
  )
}
