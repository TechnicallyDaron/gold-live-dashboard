import './MacroWeekTrack.css'

export default function MacroWeekTrack({ events, loading }) {
  if (loading && !events) {
    return <div className="skeleton macro-week-skeleton" />
  }
  if (!events || events.length === 0) return null

  const ordered = [...events].sort((a, b) => (b.upcoming ? 1 : 0) - (a.upcoming ? 1 : 0))

  return (
    <div className="macro-week">
      {ordered.map((e, i) => (
        <div key={i} className={e.upcoming ? 'macro-chip macro-chip--upcoming' : 'macro-chip'}>
          <span className="macro-chip-currency">{e.currency}</span>
          <span className="macro-chip-event">{e.event}</span>
          <span className="macro-chip-time">{e.time_et}</span>
        </div>
      ))}
    </div>
  )
}
