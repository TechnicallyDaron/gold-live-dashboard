import { useState } from 'react'
import { tiltColorVar } from '../lib/colors.js'
import './NewsCard.css'

function formatPublished(raw) {
  if (!raw) return ''
  const d = new Date(raw)
  if (Number.isNaN(d.getTime())) return raw
  return d.toLocaleString(undefined, {
    month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit',
  })
}

export default function NewsCard({ item, impact }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="news-card">
      <a className="news-card-link" href={item.link} target="_blank" rel="noopener noreferrer">
        <span className="news-card-title">{item.title}</span>
        <span className="news-card-time">{formatPublished(item.published)}</span>
      </a>

      {impact && (
        <div className="news-card-macro">
          <button
            type="button"
            className="news-card-macro-toggle"
            onClick={() => setExpanded((e) => !e)}
          >
            <span
              className="news-card-tilt-badge"
              style={{ color: tiltColorVar(impact.tilt), borderColor: tiltColorVar(impact.tilt) }}
            >
              {impact.tilt}
            </span>
            <span className="news-card-macro-label">
              Macro read {expanded ? '▾' : '▸'}
            </span>
          </button>
          {expanded && <p className="news-card-impact">{impact.impact}</p>}
        </div>
      )}
    </div>
  )
}
