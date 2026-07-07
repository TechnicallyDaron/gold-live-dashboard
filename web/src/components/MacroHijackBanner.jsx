import './MacroHijackBanner.css'

export default function MacroHijackBanner({ event }) {
  return (
    <div className="hijack-banner">
      <span className="hijack-banner-icon">⚠️</span>
      <span className="hijack-banner-text">
        <strong>{event.event}</strong> hits in ~{event.minutes_remaining}m — big news can shake every asset.
      </span>
    </div>
  )
}
