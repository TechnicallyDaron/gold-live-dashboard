import { useEffect, useRef, useState } from 'react'
import CompactWatchlistCard from './CompactWatchlistCard.jsx'
import './WatchlistGrid.css'

function chunk4(arr) {
  const pages = []
  for (let i = 0; i < arr.length; i += 4) pages.push(arr.slice(i, i + 4))
  return pages
}

export default function WatchlistGrid({ watchlist, names, byAsset, loading, flashKeys }) {
  const scrollRef = useRef(null)
  const [page, setPage] = useState(0)
  const pages = chunk4(names)

  const onScroll = () => {
    const el = scrollRef.current
    if (!el || el.clientWidth === 0) return
    setPage(Math.round(el.scrollLeft / el.clientWidth))
  }

  // Jump to whichever page holds a newly-flashing asset so the alert is
  // actually visible, not silently pulsing on a page the user isn't on.
  useEffect(() => {
    if (!flashKeys || flashKeys.size === 0) return
    const pi = pages.findIndex((p) => p.some((n) => flashKeys.has(n)))
    const el = scrollRef.current
    if (pi >= 0 && el) {
      el.scrollTo({ left: pi * el.clientWidth, behavior: 'smooth' })
      setPage(pi)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [flashKeys])

  if (names.length === 0) {
    return (
      <div className="watchlist-grid-wrap">
        <div className="wg-inner">
          <div className="wg-page">
            {Array.from({ length: 4 }).map((_, i) => (
              <CompactWatchlistCard key={i} loading />
            ))}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="watchlist-grid-wrap">
      <div className="wg-inner">
        <div className="wg-scroll" ref={scrollRef} onScroll={onScroll}>
          {pages.map((pageNames, pi) => (
            <div className="wg-page" key={pi}>
              {pageNames.map((name) => (
                <CompactWatchlistCard
                  key={name}
                  name={name}
                  unit={watchlist[name].unit}
                  entry={byAsset?.[name]}
                  loading={!byAsset && loading}
                  flash={flashKeys?.has(name)}
                />
              ))}
            </div>
          ))}
        </div>
        {pages.length > 1 && (
          <div className="wg-dots">
            {pages.map((_, i) => (
              <span key={i} className={i === page ? 'wg-dot wg-dot--active' : 'wg-dot'} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
