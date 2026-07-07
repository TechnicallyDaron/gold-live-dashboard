import { useWatchlist } from '../lib/useWatchlist.js'
import { useWatchlistData } from '../lib/useWatchlistData.js'
import { useMacro } from '../lib/useMacro.js'
import HealthDot from '../components/HealthDot.jsx'
import TickerTape from '../components/TickerTape.jsx'
import MacroBanner from '../components/MacroBanner.jsx'
import MacroWeekTrack from '../components/MacroWeekTrack.jsx'
import WatchlistCard from '../components/WatchlistCard.jsx'
import './Briefing.css'

export default function Briefing() {
  const { watchlist, error: watchlistError } = useWatchlist()
  const { data: macroEvents, loading: macroLoading } = useMacro()

  const names = watchlist ? Object.keys(watchlist) : []
  const { data: byAsset, loading: dataLoading } = useWatchlistData(names)

  return (
    <div className="briefing">
      <TickerTape />

      <header className="briefing-header">
        <h1 className="briefing-title">Briefing</h1>
        <HealthDot />
      </header>

      <MacroBanner events={macroEvents} loading={macroLoading} />

      <section className="briefing-watchlist">
        {watchlistError && (
          <div className="briefing-error">Could not load watchlist. Pull to retry.</div>
        )}
        {!watchlist && !watchlistError &&
          Array.from({ length: 3 }).map((_, i) => <WatchlistCard key={i} loading />)}
        {watchlist &&
          names.map((name) => (
            <WatchlistCard
              key={name}
              name={name}
              unit={watchlist[name].unit}
              entry={byAsset?.[name]}
              loading={!byAsset && names.length > 0 && dataLoading}
            />
          ))}
      </section>

      <MacroWeekTrack events={macroEvents} loading={macroLoading} />
    </div>
  )
}
