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

// Tiers 1-4 are "active" — an asset qualifying for any of them always
// belongs in the paginated grid, however many there are. Tiers 5-7 only
// matter for ranking which quiet assets get promoted to fill the grid up
// to its 4-card minimum when there aren't enough active ones.
function isActiveTier(name, watchlist, byAsset, screenerTickers) {
  const bias = byAsset?.[name]?.bias
  const ticker = (watchlist[name]?.ticker || name).toUpperCase()
  const firing = !!(bias?.assigned_strategy && bias?.signaling_today)
  const inScreener = screenerTickers.has(ticker)
  const setupLive = bias?.color === 'green' || bias?.color === 'red'
  const watch = bias?.color === 'orange'
  return firing || inScreener || setupLive || watch
}

// Full 7-tier sort key (lower sorts first). 1-5 are boolean gates (0 = it
// qualifies for that tier); 6 breaks remaining ties by size of today's
// move; 7 falls back to the asset's original watchlist position.
function rankKey(name, index, watchlist, byAsset, screenerTickers) {
  const bias = byAsset?.[name]?.bias
  const ticker = (watchlist[name]?.ticker || name).toUpperCase()
  const pct = byAsset?.[name]?.quote?.pct ?? 0
  return [
    bias?.assigned_strategy && bias?.signaling_today ? 0 : 1, // 1: firing today
    screenerTickers.has(ticker) ? 0 : 1, // 2: screener hit
    bias?.color === 'green' || bias?.color === 'red' ? 0 : 1, // 3: setup live
    bias?.color === 'orange' ? 0 : 1, // 4: watch state
    bias?.assigned_strategy ? 0 : 1, // 5: playbook-assigned, even if quiet
    -Math.abs(pct), // 6: largest |day change %| first
    index, // 7: original watchlist order
  ]
}

function compareRank(a, b) {
  for (let i = 0; i < a.length; i++) {
    if (a[i] !== b[i]) return a[i] - b[i]
  }
  return 0
}

const EMPTY_SET = new Set()

export default function WatchlistGrid({
  watchlist, names, byAsset, loading, flashKeys, screenerTickers = EMPTY_SET, onLongPress, onAddClick,
}) {
  const navigate = useNavigate()
  const scrollRef = useRef(null)
  const [page, setPage] = useState(0)
  const [quietOpen, setQuietOpen] = useState(false)

  // Can't rank until bias data has loaded at least once — until then,
  // everything renders in the active grid as loading skeletons (matching
  // prior behavior) rather than guessing.
  const canClassify = !!byAsset
  let activeNames = names
  let quietNames = []

  if (canClassify) {
    const ranked = names
      .map((n, i) => ({ name: n, key: rankKey(n, i, watchlist, byAsset, screenerTickers) }))
      .sort((a, b) => compareRank(a.key, b.key))
      .map((r) => r.name)
    const activeTierCount = ranked.filter((n) => isActiveTier(n, watchlist, byAsset, screenerTickers)).length

    if (activeTierCount > 4) {
      // More than 4 assets genuinely need attention — show all of them,
      // paginated; only the truly quiet ones (tiers 5-7) collapse.
      activeNames = ranked.filter((n) => isActiveTier(n, watchlist, byAsset, screenerTickers))
      quietNames = ranked.filter((n) => !isActiveTier(n, watchlist, byAsset, screenerTickers))
    } else {
      // Fewer than 4 (or zero) active assets — the grid never goes below
      // 4 cards (or the full watchlist, if smaller): top-ranked quiet
      // assets get promoted to fill it, so it's never empty on a quiet day.
      activeNames = ranked.slice(0, 4)
      quietNames = ranked.slice(4)
    }
  }

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
