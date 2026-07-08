import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useWatchlist } from '../lib/useWatchlist.js'
import { useHistory } from '../lib/useHistory.js'
import AssetSwitcher from '../components/AssetSwitcher.jsx'
import RangeToggle from '../components/RangeToggle.jsx'
import LightweightChart from '../components/LightweightChart.jsx'
import VoltBell from '../components/VoltBell.jsx'
import UserBadge from '../components/UserBadge.jsx'
import './Chart.css'

export default function Chart() {
  const { asset: assetParam } = useParams()
  const navigate = useNavigate()
  const { watchlist } = useWatchlist()
  const names = watchlist ? Object.keys(watchlist) : []

  const [selected, setSelected] = useState(assetParam || null)
  const [days, setDays] = useState(365)

  useEffect(() => {
    if (assetParam) {
      setSelected(assetParam)
    } else if (!selected && names.length > 0) {
      setSelected(names[0])
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [assetParam, names.length])

  const handleSelect = (name) => {
    setSelected(name)
    navigate(`/chart/${encodeURIComponent(name)}`, { replace: true })
  }

  const { data: history, error, loading } = useHistory(selected, days)

  return (
    <div className="chart-screen">
      <header className="chart-header">
        <h1 className="chart-title">Chart</h1>
        <div className="header-icons-row">
          <VoltBell />
          <UserBadge />
        </div>
      </header>

      {names.length > 0 && (
        <AssetSwitcher names={names} selected={selected} onSelect={handleSelect} />
      )}

      <RangeToggle days={days} onChange={setDays} />

      {loading && !history && <div className="skeleton chart-skeleton" />}

      {error && !history && (
        <div className="chart-feed-down">
          <span className="chart-feed-down-title">FEED DOWN</span>
          <p>Could not load chart history for {selected}. Will retry automatically.</p>
        </div>
      )}

      {history && <LightweightChart rows={history.rows} unit={history.unit} />}
    </div>
  )
}
