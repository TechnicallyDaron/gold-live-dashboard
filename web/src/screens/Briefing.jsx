import { useEffect, useRef, useState } from 'react'
import { useWatchlist } from '../lib/useWatchlist.js'
import { useWatchlistData } from '../lib/useWatchlistData.js'
import { useMacro } from '../lib/useMacro.js'
import { useMacroRadar } from '../lib/useMacroRadar.js'
import { useNotifications } from '../lib/useNotifications.js'
import { matchAssetKey } from '../lib/matchAsset.js'
import HealthDot from '../components/HealthDot.jsx'
import TickerTape from '../components/TickerTape.jsx'
import MacroHijackBanner from '../components/MacroHijackBanner.jsx'
import MacroWeekTrack from '../components/MacroWeekTrack.jsx'
import WatchlistGrid from '../components/WatchlistGrid.jsx'
import QuickLookModal from '../components/QuickLookModal.jsx'
import MicroChart from '../components/MicroChart.jsx'
import VoltBell from '../components/VoltBell.jsx'
import './Briefing.css'

export default function Briefing() {
  const { watchlist, error: watchlistError } = useWatchlist()
  const { data: macroEvents, loading: macroLoading } = useMacro()
  const { data: radar } = useMacroRadar()
  const { items: notifications } = useNotifications()
  const [quickLook, setQuickLook] = useState(null)
  const [flashKeys, setFlashKeys] = useState(new Set())
  const maxTsSeenRef = useRef(null)

  const names = watchlist ? Object.keys(watchlist) : []
  const { data: byAsset, loading: dataLoading } = useWatchlistData(names)

  const hijack = radar?.hijack && radar?.nearest

  // Flash the matching Briefing card when a NEW playbook/exhaustion event
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

  return (
    <div className="briefing">
      {hijack ? (
        <MacroHijackBanner event={radar.nearest} />
      ) : (
        <TickerTape onSelect={setQuickLook} />
      )}

      <header className="briefing-header">
        <h1 className="briefing-title">Briefing</h1>
        <div className="briefing-header-right">
          <HealthDot />
          <VoltBell />
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
      />

      <MacroWeekTrack events={macroEvents} loading={macroLoading} />

      {quickLook && (
        <QuickLookModal
          symbol={quickLook.symbol}
          quote={quickLook.quote}
          onClose={() => setQuickLook(null)}
        />
      )}
    </div>
  )
}
