import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import CompactWatchlistCard from './CompactWatchlistCard.jsx'
import AddTile from './AddTile.jsx'
import './WatchlistGrid.css'

const ADD_TILE = { __addTile: true }

function chunk4(items) {
  const pages = []
  for (let i = 0; i < items.length; i += 4) pages.push(items.slice(i, i + 4))
  return pages
}

// Neutral/no-trade bias (gray = "⚪ NO TRADE"), not playbook-firing, and not
// a current screener hit — nothing about this asset needs attention right
// now, so it collapses out of the paginated grid.
function isQuiet(name, watchlist, byAsset, screenerTickers) {
  const bias = byAsset?.[name]?.bias
  const isNeutral = !bias || bias.color === 'gray'
  const isFiring = !!(bias?.assigned_strategy && bias?.signaling_today)
  const ticker = (watchlist[name]?.ticker || name).toUpperCase()
  return isNeutral && !isFiring && !screenerTickers.has(ticker)
}

const EMPTY_SET = new Set()

export default function WatchlistGrid({
  watchlist, names, byAsset, loading, flashKeys, screenerTickers = EMPTY_SET, onLongPress, onAddClick,
}) {
  const navigate = useNavigate()
  const scrollRef = useRef(null)
  const [page, setPage] = useState(0)
  const [quietOpen, setQuietOpen] = useState(false)

  // Can't classify quiet vs active until bias data has loaded at least
  // once — until then, everything renders in the active grid as loading
  // skeletons (matching prior behavior) rather than guessing.
  const canClassify = !!byAsset
  const activeNames = canClassify
    ? names.filter((n) => !isQuiet(n, watchlist, byAsset, screenerTickers))
    : names
  const quietNames = canClassify
    ? names.filter((n) => isQuiet(n, watchlist, byAsset, screenerTickers))
    : []

  const pages = chunk4([...activeNames, ADD_TILE])

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

      {quietNames.length > 0 && (
        <div className="wg-quiet">
          <button type="button" className="wg-quiet-toggle" onClick={() => setQuietOpen((v) => !v)}>
            <span>😴 Quiet ({quietNames.length})</span>
            <span className={quietOpen ? 'wg-quiet-caret wg-quiet-caret--open' : 'wg-quiet-caret'}>▾</span>
          </button>
          {quietOpen && (
            <div className="wg-quiet-list">
              {quietNames.map((name) => {
                const quote = byAsset?.[name]?.quote
                return (
                  <button
                    key={name}
                    type="button"
                    className="wg-quiet-item"
                    onClick={() => navigate(`/bias/${encodeURIComponent(name)}`)}
                  >
                    <span className="wg-quiet-item-name">{name}</span>
                    {quote && (
                      <span className="wg-quiet-item-price tabular-nums">
                        ${quote.price?.toLocaleString(undefined, { maximumFractionDigits: 2 })}
                        {watchlist[name].unit}
                      </span>
                    )}
                  </button>
                )
              })}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
