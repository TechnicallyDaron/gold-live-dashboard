import { useEffect, useState } from 'react'
import { api } from '../lib/api.js'
import { useWatchlistData } from '../lib/useWatchlistData.js'
import HealthDot from '../components/HealthDot.jsx'
import MacroBanner from '../components/MacroBanner.jsx'
import WatchlistCard from '../components/WatchlistCard.jsx'
import './Briefing.css'

export default function Briefing() {
  const [watchlist, setWatchlist] = useState(null)
  const [watchlistError, setWatchlistError] = useState(null)

  useEffect(() => {
    let cancelled = false
    api
      .watchlist()
      .then((wl) => !cancelled && setWatchlist(wl))
      .catch((err) => !cancelled && setWatchlistError(err))
    return () => {
      cancelled = true
    }
  }, [])

  const names = watchlist ? Object.keys(watchlist) : []
  const { data: byAsset, loading: dataLoading } = useWatchlistData(names)

  return (
    <div className="briefing">
      <header className="briefing-header">
        <h1 className="briefing-title">Briefing</h1>
        <HealthDot />
      </header>

      <MacroBanner />

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
    </div>
  )
}
