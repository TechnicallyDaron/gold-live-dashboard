import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useWatchlist } from '../lib/useWatchlist.js'
import { useNews } from '../lib/useNews.js'
import { useSentiment } from '../lib/useSentiment.js'
import AssetSwitcher from '../components/AssetSwitcher.jsx'
import NewsCard from '../components/NewsCard.jsx'
import SentimentOverall from '../components/SentimentOverall.jsx'
import './News.css'

export default function News() {
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
    navigate(`/news/${encodeURIComponent(name)}`, { replace: true })
  }

  const { items, error, loading } = useNews(selected)
  const { entry: sentiment, analyze } = useSentiment(selected)

  const impactFor = (i) => sentiment?.data?.impacts?.find((x) => x.i === i)

  return (
    <div className="news-screen">
      <header className="news-header">
        <h1 className="news-title">News</h1>
      </header>

      {names.length > 0 && (
        <AssetSwitcher names={names} selected={selected} onSelect={handleSelect} />
      )}

      {(!sentiment || sentiment.status === 'idle') && (
        <button type="button" className="ai-macro-btn" onClick={analyze}>
          🤖 Analyze
        </button>
      )}

      {sentiment?.status === 'loading' && <div className="skeleton sentiment-skeleton" />}

      {sentiment?.status === 'error' && (
        <div className="news-ai-error">
          {sentiment.detail}
          <button type="button" className="news-ai-retry" onClick={analyze}>
            Retry
          </button>
        </div>
      )}

      {sentiment?.status === 'success' && <SentimentOverall data={sentiment.data} />}

      {loading && !items &&
        Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="skeleton news-card-skeleton" />
        ))}

      {error && !items && (
        <div className="news-error">Could not load news for {selected}. Pull to retry.</div>
      )}

      {items && items.length === 0 && (
        <p className="news-empty">No recent headlines for {selected}.</p>
      )}

      {items &&
        items.map((item, i) => (
          <NewsCard key={i} item={item} impact={impactFor(i)} />
        ))}
    </div>
  )
}
