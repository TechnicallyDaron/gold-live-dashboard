import { useEffect, useMemo, useRef, useState } from 'react'
import { useWatchlist } from '../lib/useWatchlist.js'
import { useWatchlistData } from '../lib/useWatchlistData.js'
import { useMacro } from '../lib/useMacro.js'
import { useMacroRadar } from '../lib/useMacroRadar.js'
import { useScreener } from '../lib/useScreener.js'
import { useNotifications } from '../lib/useNotifications.js'
import { matchAssetKey } from '../lib/matchAsset.js'
import { api } from '../lib/api.js'
import { showToast } from '../lib/toast.js'
import HealthDot from '../components/HealthDot.jsx'
import TickerTape from '../components/TickerTape.jsx'
import MacroHijackBanner from '../components/MacroHijackBanner.jsx'
import MacroWeekTrack from '../components/MacroWeekTrack.jsx'
import WatchlistGrid from '../components/WatchlistGrid.jsx'
import QuickLookModal from '../components/QuickLookModal.jsx'
import MicroChart from '../components/MicroChart.jsx'
import VoltBell from '../components/VoltBell.jsx'
import UserBadge from '../components/UserBadge.jsx'
import ConfirmDialog from '../components/ConfirmDialog.jsx'
import WatchlistAddForm from '../components/WatchlistAddForm.jsx'
import './Briefing.css'

export default function Briefing() {
  const { watchlist, error: watchlistError, setWatchlist } = useWatchlist()
  const { data: macroEvents, loading: macroLoading } = useMacro()
  const { data: radar } = useMacroRadar()
  const { hits: screenerHits } = useScreener()
  const { items: notifications } = useNotifications()
  const [quickLook, setQuickLook] = useState(null)
  const [flashKeys, setFlashKeys] = useState(new Set())
  const [removeTarget, setRemoveTarget] = useState(null)
  const [showAddForm, setShowAddForm] = useState(false)
  const maxTsSeenRef = useRef(null)

  const names = watchlist ? Object.keys(watchlist) : []
  const { data: byAsset, loading: dataLoading } = useWatchlistData(names)
  const screenerTickers = useMemo(
    () => new Set(screenerHits.map((h) => h.ticker.toUpperCase())),
    [screenerHits]
  )

  const hijack = radar?.hijack && radar?.nearest

  // Flash the matching HUB card when a NEW playbook/exhaustion event
  // arrives while this screen is mounted. Baseline on first load so the
  // whole board doesn't flash for a backlog of already-seen history.
  useEffect(() => {
    if (!notifications.length || !watchlist) return
    const maxTs = Math.max(...notifications.map((n) => n.ts))
    if (maxTsSeenRef.current === null) {
      maxTsSeenRef.current = maxTs
      return
    }
    if (maxTs <= maxTsSeenRef.current) return
    const fresh = notifications.filter(
      (n) => n.ts > maxTsSeenRef.current && (n.kind === 'playbook' || n.kind === 'exhaustion')
    )
    maxTsSeenRef.current = maxTs
    const matched = new Set()
    fresh.forEach((n) => {
      const key = matchAssetKey(n.title, watchlist)
      if (key) matched.add(key)
    })
    if (matched.size > 0) {
      setFlashKeys(matched)
      setTimeout(() => setFlashKeys(new Set()), 8000)
    }
  }, [notifications, watchlist])

  const confirmRemove = async () => {
    const name = removeTarget
    setRemoveTarget(null)
    try {
      const res = await api.removeWatchlist(name)
      setWatchlist(res.watchlist)
      showToast(`Removed ${name} from your watchlist`, 'success')
      if (res.persistence_warning) showToast(res.persistence_warning, 'warning')
    } catch (err) {
      showToast(err.message, 'error')
    }
  }

  return (
    <div className="briefing">
      {hijack ? (
        <MacroHijackBanner event={radar.nearest} />
      ) : (
        <TickerTape onSelect={setQuickLook} />
      )}

      <header className="briefing-header">
        <h1 className="briefing-title">HUB</h1>
        <div className="briefing-header-right">
          <HealthDot />
          <VoltBell />
          <UserBadge />
        </div>
      </header>

      {watchlistError && (
        <div className="briefing-error">Could not load watchlist. Pull to retry.</div>
      )}

      <MicroChart names={names} />

      <WatchlistGrid
        watchlist={watchlist || {}}
        names={names}
        byAsset={byAsset}
        loading={dataLoading}
        flashKeys={flashKeys}
        screenerTickers={screenerTickers}
        onLongPress={setRemoveTarget}
        onAddClick={() => setShowAddForm(true)}
      />

      <MacroWeekTrack events={macroEvents} loading={macroLoading} />

      {quickLook && (
        <QuickLookModal
          symbol={quickLook.symbol}
          quote={quickLook.quote}
          onClose={() => setQuickLook(null)}
        />
      )}

      {removeTarget && (
        <ConfirmDialog
          title={`Remove ${removeTarget}?`}
          body="You can add it back any time from the + tile."
          confirmLabel="Remove"
          onConfirm={confirmRemove}
          onCancel={() => setRemoveTarget(null)}
        />
      )}

      {showAddForm && (
        <WatchlistAddForm
          onClose={() => setShowAddForm(false)}
          onSaved={(wl) => setWatchlist(wl)}
        />
      )}
    </div>
  )
}
