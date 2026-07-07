import { tiltColorVar } from '../lib/colors.js'
import './SentimentOverall.css'

export default function SentimentOverall({ data }) {
  if (data.raw) {
    return (
      <div className="sentiment-overall">
        <p className="sentiment-raw">{data.raw}</p>
      </div>
    )
  }

  if (!data.overall) {
    return (
      <div className="sentiment-overall">
        <p className="sentiment-empty">No headlines available to analyze.</p>
      </div>
    )
  }

  const color = tiltColorVar(data.overall.sentiment)

  return (
    <div className="sentiment-overall" style={{ borderLeftColor: color }}>
      <div className="sentiment-overall-top">
        <span className="sentiment-overall-label" style={{ color }}>
          {data.overall.sentiment}
        </span>
        <span className="sentiment-score-chip tabular-nums" style={{ color, borderColor: color }}>
          {data.overall.score > 0 ? '+' : ''}
          {data.overall.score}
        </span>
      </div>
      <p className="sentiment-overall-summary">{data.overall.summary}</p>
    </div>
  )
}
