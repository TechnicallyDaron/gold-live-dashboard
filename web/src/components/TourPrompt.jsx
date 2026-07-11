import './TourPrompt.css'

export default function TourPrompt({ onTake, onSkip }) {
  return (
    <div className="tour-prompt-overlay">
      <div className="tour-prompt-box">
        <span className="tour-prompt-title">Want a quick tour?</span>
        <p className="tour-prompt-body">60 seconds, we'll walk every page.</p>
        <div className="tour-prompt-actions">
          <button type="button" className="tour-prompt-btn tour-prompt-btn--ghost" onClick={onSkip}>
            Skip for now
          </button>
          <button type="button" className="tour-prompt-btn tour-prompt-btn--primary" onClick={onTake}>
            Take the tour
          </button>
        </div>
      </div>
    </div>
  )
}
