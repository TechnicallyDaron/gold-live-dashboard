import { useEffect, useRef, useState } from 'react'
import CompactWatchlistCard from './CompactWatchlistCard.jsx'
import AddTile from './AddTile.jsx'
import './WatchlistGrid.css'

const ADD_TILE = { __addTile: true }

function chunk4(items) {
  const pages = []
  for (let i = 0; i < items.length; i += 4) pages.push(items.slice(i, i + 4))
  return pages
}

export default function WatchlistGrid({
  watchlist, names, byAsset, loading, flashKeys, onLongPress, onAddClick,
}) {
  const scrollRef = useRef(null)
  const [page, setPage] = useState(0)
  const pages = chunk4([...names, ADD_TILE])

  const onScroll = () => {
    const el = scrollRef.current
    if (!el || el.clientWidth === 0) return
    setPage(Math.round(el.scrollLeft / el.clientWidth))
  }

  // Jump to whichever page holds a newly-flashing asset so the alert is
  // actually visible, not silently pulsing on a page the user isn't on.
  useEffect(() => {
    if (!flashKeys || flashKeys.size === 0) return
    const pi = pages.findIndex((p) => p.some((n) => typeof n === 'string' && flashKeys.has(n)))
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
          {pages.map((pageItems, pi) => (
            <div className="wg-page" key={pi}>
              {pageItems.map((item) =>
                item === ADD_TILE ? (
                  <AddTile key="add-tile" onClick={onAddClick} />
                ) : (
                  <CompactWatchlistCard
                    key={item}
                    name={item}
                    unit={watchlist[item].unit}
                    entry={byAsset?.[item]}
                    loading={!byAsset && loading}
                    flash={flashKeys?.has(item)}
                    onLongPress={onLongPress}
                  />
                )
              )}
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
