import { biasColorVar } from '../lib/colors.js'
import './VerdictBanner.css'

export default function VerdictBanner({ bias }) {
  const color = biasColorVar(bias.color)
  return (
    <div className="verdict-banner" style={{ borderLeftColor: color }}>
      <span className="verdict-banner-state" style={{ color }}>
        {bias.state}
      </span>
      <p className="verdict-banner-headline">{bias.headline}</p>
    </div>
  )
}
