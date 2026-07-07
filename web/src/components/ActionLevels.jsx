import './ActionLevels.css'

function fmt(n) {
  return n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function pctLabel(pct) {
  return `${pct >= 0 ? '+' : ''}${pct.toFixed(2)}%`
}

export default function ActionLevels({ bias, unit }) {
  return (
    <div className="action-levels">
      <div className="action-row">
        <span className="action-label">Arm</span>
        <span className="action-value tabular-nums">
          ${fmt(bias.arm_level)}
          {unit}
        </span>
        <span className="action-dist tabular-nums">{pctLabel(bias.dist_to_arm_pct)}</span>
      </div>
      <div className="action-row">
        <span className="action-label action-label--short">Invalidation</span>
        <span className="action-value action-value--short tabular-nums">
          ${fmt(bias.invalidation)}
          {unit}
        </span>
      </div>
      <div className="action-row">
        <span className="action-label action-label--long">Target (20 EMA)</span>
        <span className="action-value action-value--long tabular-nums">
          ${fmt(bias.target)}
          {unit}
        </span>
        <span className="action-dist tabular-nums">{pctLabel(bias.dist_to_target_pct)}</span>
      </div>
    </div>
  )
}
