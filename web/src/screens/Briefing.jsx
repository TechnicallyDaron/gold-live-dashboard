import { useState } from 'react'
import { useWatchlist } from '../lib/useWatchlist.js'
import { useWatchlistData } from '../lib/useWatchlistData.js'
import { useMacro } from '../lib/useMacro.js'
import { useMacroRadar } from '../lib/useMacroRadar.js'
import HealthDot from '../components/HealthDot.jsx'
import TickerTape from '../components/TickerTape.jsx'
import MacroHijackBanner from '../components/MacroHijackBanner.jsx'
import MacroWeekTrack from '../components/MacroWeekTrack.jsx'
import WatchlistGrid from '../components/WatchlistGrid.jsx'
import QuickLookModal from '../components/QuickLookModal.jsx'
import './Briefing.css'

export default function Briefing() {
  const { watchlist, error: watchlistError } = useWatchlist()
  const { data: macroEvents, loading: macroLoading } = useMacro()
  const { data: radar } = useMacroRadar()
  const [quickLook, setQuickLook] = useState(null)

  const names = watchlist ? Object.keys(watchlist) : []
  const { data: byAsset, loading: dataLoading } = useWatchlistData(names)

  const hijack = radar?.hijack && radar?.nearest

  return (
    <div className="briefing">
      {hijack ? (
        <MacroHijackBanner event={radar.nearest} />
      ) : (
        <TickerTape onSelect={setQuickLook} />
      )}

      <header className="briefing-header">
        <h1 className="briefing-title">Briefing</h1>
        <HealthDot />
      </header>

      {watchlistError && (
        <div className="briefing-error">Could not load watchlist. Pull to retry.</div>
      )}

      <WatchlistGrid
        watchlist={watchlist || {}}
        names={names}
        byAsset={byAsset}
        loading={dataLoading}
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
