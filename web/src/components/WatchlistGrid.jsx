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

// Below this, a playbook pair fires too rarely to earn a permanent grid
// slot on its own — it's ranked (and promotable) alongside the unassigned
// quiet assets instead.
const FREQUENT_THRESHOLD = 0.25 // signals/week

// Matches the backend's own assignment_for() lookup order: display name
// first, then raw ticker, both uppercased.
function signalsPerWeekFor(name, watchlist, signalsPerWeekByKey) {
  const ticker = (watchlist[name]?.ticker || name).toUpperCase()
  return signalsPerWeekByKey.get(name.toUpperCase()) ?? signalsPerWeekByKey.get(ticker) ?? 0
}

// Tiers 1-5 are "active" — an asset qualifying for any of them always
// belongs in the paginated grid, however many there are. Tiers 6-8 only
// matter for ranking which quiet assets get promoted to fill the grid up
// to its 4-card minimum when there aren't enough active ones.
function isActiveTier(name, watchlist, byAsset, screenerTickers, signalsPerWeekByKey) {
  const bias = byAsset?.[name]?.bias
  const ticker = (watchlist[name]?.ticker || name).toUpperCase()
  const firing = !!(bias?.assigned_strategy && bias?.signaling_today)
  const inScreener = screenerTickers.has(ticker)
  const setupLive = bias?.color === 'green' || bias?.color === 'red'
  const watch = bias?.color === 'orange'
  const frequent = signalsPerWeekFor(name, watchlist, signalsPerWeekByKey) >= FREQUENT_THRESHOLD
  return firing || inScreener || setupLive || watch || frequent
}

// The only two tiers a pin can never outrank — a live playbook signal or a
// screener hit always claims its grid slot regardless of anyone's pins.
function isSignalOrScreener(name, watchlist, byAsset, screenerTickers) {
  const bias = byAsset?.[name]?.bias
  const ticker = (watchlist[name]?.ticker || name).toUpperCase()
  const firing = !!(bias?.assigned_strategy && bias?.signaling_today)
  return firing || screenerTickers.has(ticker)
}

// Full 8-tier sort key (lower sorts first). 1-5 are boolean gates (0 = it
// qualifies for that tier); 6 ranks by playbook signal frequency; 7 breaks
// remaining ties by size of today's move; 8 falls back to the asset's
// original watchlist position.
function rankKey(name, index, watchlist, byAsset, screenerTickers, signalsPerWeekByKey) {
  const bias = byAsset?.[name]?.bias
  const ticker = (watchlist[name]?.ticker || name).toUpperCase()
  const pct = byAsset?.[name]?.quote?.pct ?? 0
  const spw = signalsPerWeekFor(name, watchlist, signalsPerWeekByKey)
  return [
    bias?.assigned_strategy && bias?.signaling_today ? 0 : 1, // 1: firing today
    screenerTickers.has(ticker) ? 0 : 1, // 2: screener hit
    bias?.color === 'green' || bias?.color === 'red' ? 0 : 1, // 3: setup live
    bias?.color === 'orange' ? 0 : 1, // 4: watch state
    spw >= FREQUENT_THRESHOLD ? 0 : 1, // 5: frequent playbook pair (>=0.25 signals/wk)
    -spw, // 6: higher signals/week ranks first (also orders the below-threshold pool)
    -Math.abs(pct), // 7: largest |day change %| tiebreak
    index, // 8: original watchlist order
  ]
}

function compareRank(a, b) {
  for (let i = 0; i < a.length; i++) {
    if (a[i] !== b[i]) return a[i] - b[i]
  }
  return 0
}

const EMPTY_SET = new Set()
const EMPTY_MAP = new Map()
const EMPTY_ARRAY = []

export default function WatchlistGrid({
  watchlist, names, byAsset, loading, flashKeys,
  screenerTickers = EMPTY_SET, signalsPerWeekByKey = EMPTY_MAP,
  pinnedNames = EMPTY_ARRAY,
  onLongPress, onAddClick, onEditPins,
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
  const pinnedSet = new Set(pinnedNames)

  if (canClassify) {
    const ranked = names
      .map((n, i) => ({
        name: n,
        key: rankKey(n, i, watchlist, byAsset, screenerTickers, signalsPerWeekByKey),
      }))
      .sort((a, b) => compareRank(a.key, b.key))
      .map((r) => r.name)
    const activeTierCount = ranked.filter((n) =>
      isActiveTier(n, watchlist, byAsset, screenerTickers, signalsPerWeekByKey)
    ).length
    // Grid capacity is unaffected by pins — only pin PRECEDENCE changes.
    // Zero pins: priorityOrder below collapses back to `ranked` exactly
    // (signal/screener tiers already sort first in `ranked` itself), so
    // this is provably identical to the pre-pin behavior.
    const gridSize = activeTierCount > 4 ? activeTierCount : 4

    // Exact precedence: live signal/screener always wins a slot, even over
    // a pin; remaining slots go to pins in pin order; anything still open
    // falls back to the existing auto-rank (tiers 3-8 of `ranked`). Drop
    // any pin whose asset no longer exists on the watchlist.
    const signalSet = new Set(
      ranked.filter((n) => isSignalOrScreener(n, watchlist, byAsset, screenerTickers))
    )
    const validPins = pinnedNames.filter((n) => names.includes(n) && !signalSet.has(n))
    const pinSet = new Set(validPins)
    const priorityOrder = [
      ...ranked.filter((n) => signalSet.has(n)),
      ...validPins,
      ...ranked.filter((n) => !signalSet.has(n) && !pinSet.has(n)),
    ]

    activeNames = priorityOrder.slice(0, gridSize)
    quietNames = priorityOrder.slice(gridSize)
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
      <div className="wg-header">
        <button type="button" className="wg-edit-pins-btn" onClick={onEditPins}>
          📌 <span className="wg-edit-pins-label">Edit Top 4</span>
        </button>
      </div>
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
                    pinned={pinnedSet.has(item)}
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
