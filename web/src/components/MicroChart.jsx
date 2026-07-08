import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api.js'
import './MicroChart.css'

const CYCLE_MS = 8000
const FADE_MS = 1400
const VB_W = 300
const VB_H = 80

function toPath(values, min, max) {
  const range = max - min || 1
  const step = VB_W / Math.max(values.length - 1, 1)
  return values
    .map((v, i) => `${i === 0 ? 'M' : 'L'} ${(i * step).toFixed(1)} ${(VB_H - ((v - min) / range) * VB_H).toFixed(1)}`)
    .join(' ')
}

function toPaths(rows) {
  if (!rows || rows.length < 2) return null
  const all = rows.flatMap((r) => [r.price, r.baseline])
  const min = Math.min(...all)
  const max = Math.max(...all)
  return {
    price: toPath(rows.map((r) => r.price), min, max),
    baseline: toPath(rows.map((r) => r.baseline), min, max),
    lastPrice: rows[rows.length - 1].price,
  }
}

// One asset's chart, absolutely stacked with its sibling layer so the two
// can crossfade. The line itself drifts slowly inside its own clipped
// bounds — the "ticker tape" feel — independent of the crossfade.
function ChartLayer({ name, rows, active }) {
  const d = toPaths(rows)
  return (
    <div className={`micro-chart-layer${active ? ' micro-chart-layer--active' : ''}`}>
      <div className="micro-chart-overlay">
        <span className="micro-chart-name">{name}</span>
        {d && (
          <span className="micro-chart-price tabular-nums">
            ${d.lastPrice.toLocaleString(undefined, { maximumFractionDigits: 2 })}
          </span>
        )}
      </div>
      {d ? (
        <div className="micro-chart-pan" key={name}>
          <svg className="micro-chart-svg" viewBox={`0 0 ${VB_W} ${VB_H}`} preserveAspectRatio="none">
            <path d={d.baseline} className="micro-chart-baseline" />
            <path d={d.price} className="micro-chart-price-line" />
          </svg>
        </div>
      ) : (
        <div className="skeleton micro-chart-skeleton" />
      )}
    </div>
  )
}

export default function MicroChart({ names }) {
  const navigate = useNavigate()
  const [index, setIndex] = useState(0)
  const [paused, setPaused] = useState(false)
  const [transitioning, setTransitioning] = useState(false)
  const [incomingActive, setIncomingActive] = useState(false)
  const cacheRef = useRef(new Map())
  const [, bump] = useState(0)
  const cycleRef = useRef(null)
  const fadeRef = useRef(null)
  const rafRef = useRef(null)

  const count = names.length
  const asset = names[index % Math.max(count, 1)]
  const nextAsset = count > 1 ? names[(index + 1) % count] : null

  const load = (name) => {
    if (!name || cacheRef.current.has(name)) return
    cacheRef.current.set(name, undefined)
    api
      .history(name, 90)
      .then((d) => {
        cacheRef.current.set(name, d.rows)
        bump((v) => v + 1)
      })
      .catch(() => {
        cacheRef.current.set(name, [])
        bump((v) => v + 1)
      })
  }

  useEffect(() => {
    load(asset)
  }, [asset])

  useEffect(() => {
    if (nextAsset) load(nextAsset)
  }, [nextAsset])

  // Drive the cycle: cross into the (pre-fetched) next asset every
  // CYCLE_MS, then hand off to it once the fade completes.
  useEffect(() => {
    if (count < 2 || paused) return undefined
    cycleRef.current = setInterval(() => setTransitioning(true), CYCLE_MS)
    return () => clearInterval(cycleRef.current)
  }, [count, paused])

  useEffect(() => {
    if (!transitioning) return undefined
    rafRef.current = requestAnimationFrame(() => setIncomingActive(true))
    fadeRef.current = setTimeout(() => {
      setIndex((i) => (i + 1) % Math.max(count, 1))
      setTransitioning(false)
      setIncomingActive(false)
    }, FADE_MS)
    return () => {
      cancelAnimationFrame(rafRef.current)
      clearTimeout(fadeRef.current)
    }
  }, [transitioning, count])

  if (!asset) return null

  const currentRows = cacheRef.current.get(asset)
  const nextRows = nextAsset ? cacheRef.current.get(nextAsset) : null

  return (
    <button
      type="button"
      className="micro-chart"
      onTouchStart={() => setPaused(true)}
      onTouchEnd={() => setPaused(false)}
      onClick={() => navigate(`/chart/${encodeURIComponent(asset)}`)}
    >
      <ChartLayer name={asset} rows={currentRows} active={!transitioning} />
      {transitioning && nextAsset && (
        <ChartLayer name={nextAsset} rows={nextRows} active={incomingActive} />
      )}
    </button>
  )
}
