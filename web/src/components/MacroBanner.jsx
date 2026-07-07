import { api } from '../lib/api.js'
import { usePolling } from '../lib/usePolling.js'
import './MacroBanner.css'

export default function MacroBanner() {
  const { data, loading } = usePolling(() => api.macro(), [], 60000)

  if (loading) {
    return <div className="skeleton macro-banner-skeleton" />
  }

  const next = (data || []).find((e) => e.upcoming)
  if (!next) return null

  return (
    <div className="macro-banner">
      <span className="macro-banner-badge">NEXT</span>
      <div className="macro-banner-body">
        <span className="macro-banner-event">
          {next.currency} · {next.event}
        </span>
        <span className="macro-banner-time">{next.time_et} ET · F {next.forecast}</span>
      </div>
    </div>
  )
}
