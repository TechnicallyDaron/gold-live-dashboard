import './NewsCard.css'

function formatPublished(raw) {
  if (!raw) return ''
  const d = new Date(raw)
  if (Number.isNaN(d.getTime())) return raw
  return d.toLocaleString(undefined, {
    month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit',
  })
}

export default function NewsCard({ item }) {
  return (
    <a
      className="news-card"
      href={item.link}
      target="_blank"
      rel="noopener noreferrer"
    >
      <span className="news-card-title">{item.title}</span>
      <span className="news-card-time">{formatPublished(item.published)}</span>
    </a>
  )
}
