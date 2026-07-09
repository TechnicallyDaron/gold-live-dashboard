import { useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import './CatalystSpotlight.css'

export default function CatalystSpotlight({ hits }) {
  const navigate = useNavigate()
  const scrollRef = useRef(null)
  const [page, setPage] = useState(0)

  if (!hits || hits.length === 0) return null

  const onScroll = () => {
    const el = scrollRef.current
    if (!el || el.clientWidth === 0) return
    setPage(Math.round(el.scrollLeft / el.clientWidth))
  }

  return (
    <div className="catalyst-spotlight">
      <div className="catalyst-scroll" ref={scrollRef} onScroll={onScroll}>
        {hits.map((hit) => (
          <button
            key={hit.ticker}
            type="button"
            className="catalyst-card"
            onClick={() => navigate(`/bias/${encodeURIComponent(hit.ticker)}`)}
          >
            🚀 Catalyst: <strong>{hit.ticker}</strong>{' '}
            <span className="tabular-nums">
              ${hit.price?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>{' '}
            — <span className="tabular-nums">{hit.rvol?.toFixed(1)}×</span> volume, fresh 52-wk breakout
          </button>
        ))}
      </div>
      {hits.length > 1 && (
        <div className="catalyst-dots">
          {hits.map((hit, i) => (
            <span key={hit.ticker} className={i === page ? 'catalyst-dot catalyst-dot--active' : 'catalyst-dot'} />
          ))}
        </div>
      )}
    </div>
  )
}
