import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useWatchlist } from '../lib/useWatchlist.js'
import { useBias } from '../lib/useBias.js'
import { useBacktestStrip } from '../lib/useBacktestStrip.js'
import AssetSwitcher from '../components/AssetSwitcher.jsx'
import VerdictBanner from '../components/VerdictBanner.jsx'
import MetricsGrid from '../components/MetricsGrid.jsx'
import ActionLevels from '../components/ActionLevels.jsx'
import BacktestStrip from '../components/BacktestStrip.jsx'
import FullBacktestSection from '../components/FullBacktestSection.jsx'
import './Bias.css'

export default function Bias() {
  const { asset: assetParam } = useParams()
  const navigate = useNavigate()
  const { watchlist } = useWatchlist()
  const names = watchlist ? Object.keys(watchlist) : []

  const [selected, setSelected] = useState(assetParam || null)

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
    navigate(`/bias/${encodeURIComponent(name)}`, { replace: true })
  }

  const { data: bias, error: biasError, loading: biasLoading } = useBias(selected)
  const { results: backtestResults, loading: backtestLoading } = useBacktestStrip(selected)

  return (
    <div className="bias-screen">
      <header className="bias-header">
        <h1 className="bias-title">Bias</h1>
      </header>

      {names.length > 0 && (
        <AssetSwitcher names={names} selected={selected} onSelect={handleSelect} />
      )}

      {biasLoading && !bias && (
        <>
          <div className="skeleton bias-verdict-skeleton" />
          <div className="skeleton bias-grid-skeleton" />
          <div className="skeleton bias-levels-skeleton" />
        </>
      )}

      {biasError && !bias && (
        <div className="bias-feed-down">
          <span className="bias-feed-down-title">FEED DOWN</span>
          <p>Could not load bias for {selected}. Will retry automatically.</p>
        </div>
      )}

      {bias && (
        <>
          <VerdictBanner bias={bias} />
          <MetricsGrid bias={bias} unit={bias.unit} />
          <ActionLevels bias={bias} unit={bias.unit} />
          <BacktestStrip results={backtestResults} loading={backtestLoading} />
          <FullBacktestSection results={backtestResults} loading={backtestLoading} />
        </>
      )}
    </div>
  )
}
