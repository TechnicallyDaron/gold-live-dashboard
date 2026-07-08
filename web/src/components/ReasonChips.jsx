import './ReasonChips.css'

export default function ReasonChips({ reasons }) {
  if (!reasons || reasons.length === 0) return null
  return (
    <ul className="reason-chips">
      {reasons.map((r, i) => (
        <li key={i} className="reason-chip">
          {r}
        </li>
      ))}
    </ul>
  )
}
