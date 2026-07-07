import './RangeToggle.css'

const RANGES = [
  { label: '3M', days: 90 },
  { label: '1Y', days: 365 },
  { label: '5Y', days: 1300 },
]

export default function RangeToggle({ days, onChange }) {
  return (
    <div className="range-toggle">
      {RANGES.map((r) => (
        <button
          key={r.days}
          type="button"
          className={r.days === days ? 'range-btn range-btn--active' : 'range-btn'}
          onClick={() => onChange(r.days)}
        >
          {r.label}
        </button>
      ))}
    </div>
  )
}
