import './MacroWeekTrack.css'

export default function MacroWeekTrack({ events, loading }) {
  if (loading && !events) {
    return <div className="skeleton macro-week-skeleton" />
  }
  if (!events || events.length === 0) return null

  const ordered = [...events].sort((a, b) => (b.upcoming ? 1 : 0) - (a.upcoming ? 1 : 0))

  return (
    <section className="macro-week">
      <span className="macro-week-title">Macro Week</span>
      <div className="macro-week-track">
        {ordered.map((e, i) => (
          <div key={i} className="macro-cardlet">
            <div className="macro-cardlet-top">
              <span className="macro-cardlet-currency">{e.currency}</span>
              {e.upcoming && <span className="macro-cardlet-chip">Upcoming</span>}
            </div>
            <span className="macro-cardlet-time">{e.time_et} ET</span>
            <span className="macro-cardlet-event">{e.event}</span>
            <span className="macro-cardlet-fp">
              F {e.forecast} · P {e.previous}
            </span>
          </div>
        ))}
      </div>
    </section>
  )
}
