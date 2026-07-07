import { useState } from 'react'
import { useTape } from '../lib/useTape.js'
import './TickerTape.css'

function TapeItem({ item }) {
  const q = item.quote
  return (
    <span className="tape-item">
      <span className="tape-symbol">{item.symbol}</span>
      {q ? (
        <>
          <span className="tape-price tabular-nums">${q.price.toLocaleString()}</span>
          <span
            className={
              q.pct >= 0 ? 'tape-pct tape-pct--up tabular-nums' : 'tape-pct tape-pct--down tabular-nums'
            }
          >
            {q.pct >= 0 ? '+' : ''}
            {q.pct.toFixed(2)}%
          </span>
        </>
      ) : (
        <span className="tape-dash">—</span>
      )}
    </span>
  )
}

export default function TickerTape() {
  const { data, loading } = useTape()
  const [paused, setPaused] = useState(false)

  if (loading && !data) {
    return <div className="skeleton ticker-tape-skeleton" />
  }
  if (!data || data.length === 0) return null

  const renderItems = (keyPrefix) => (
    <>
      {data.map((item, i) => (
        <span className="tape-group" key={`${keyPrefix}-${item.symbol}`}>
          <TapeItem item={item} />
          {i < data.length - 1 && <span className="tape-sep">⚡</span>}
        </span>
      ))}
    </>
  )

  return (
    <div
      className="ticker-tape"
      onTouchStart={() => setPaused(true)}
      onTouchEnd={() => setPaused(false)}
    >
      <div className={paused ? 'tape-track tape-track--paused' : 'tape-track'}>
        {renderItems('a')}
        <span className="tape-sep">⚡</span>
        {renderItems('b')}
      </div>
    </div>
  )
}
