import { useEffect, useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { TOUR_STEPS } from '../lib/tourSteps.js'
import { isStandalone } from '../lib/platform.js'
import './TourOverlay.css'

const TARGET_TIMEOUT_MS = 2500
const TARGET_POLL_MS = 100
const SPOTLIGHT_PAD = 10
const TAB_BAR_SAFE = 84

function computeCardStyle(rect) {
  const viewportH = window.visualViewport?.height ?? window.innerHeight
  const viewportW = window.innerWidth
  const margin = 16
  const cardWidth = Math.min(340, viewportW - margin * 2)
  const spaceBelow = viewportH - TAB_BAR_SAFE - rect.bottom
  const spaceAbove = rect.top - margin

  let left = rect.left + rect.width / 2 - cardWidth / 2
  left = Math.max(margin, Math.min(left, viewportW - cardWidth - margin))

  if (spaceBelow >= 140 || spaceBelow >= spaceAbove) {
    const top = Math.max(rect.bottom + 16, margin)
    return { width: cardWidth, left, top }
  }
  const bottom = Math.max(viewportH - rect.top + 16, TAB_BAR_SAFE)
  return { width: cardWidth, left, bottom }
}

export default function TourOverlay({ onClose }) {
  const navigate = useNavigate()
  const location = useLocation()
  const steps = useRef(TOUR_STEPS.filter((s) => s.conditional !== 'install' || !isStandalone())).current
  const [index, setIndex] = useState(0)
  const [rect, setRect] = useState(null)

  const step = steps[index]
  const isLast = index === steps.length - 1

  useEffect(() => {
    if (step.route && !location.pathname.startsWith(step.route)) {
      navigate(step.route)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [index])

  useEffect(() => {
    let cancelled = false
    let pollTimer = null
    let elapsed = 0
    setRect(null)

    if (!step.target) return undefined

    function updateRect() {
      const el = document.querySelector(step.target)
      if (el) setRect(el.getBoundingClientRect())
      return el
    }

    function poll() {
      if (cancelled) return
      const el = updateRect()
      if (el) return
      elapsed += TARGET_POLL_MS
      if (elapsed >= TARGET_TIMEOUT_MS) return
      pollTimer = setTimeout(poll, TARGET_POLL_MS)
    }
    poll()

    window.addEventListener('resize', updateRect)
    window.addEventListener('scroll', updateRect, true)
    return () => {
      cancelled = true
      if (pollTimer) clearTimeout(pollTimer)
      window.removeEventListener('resize', updateRect)
      window.removeEventListener('scroll', updateRect, true)
    }
  }, [index, location.pathname, step.target])

  const goNext = () => (isLast ? onClose('finished') : setIndex((i) => i + 1))
  const goBack = () => index > 0 && setIndex((i) => i - 1)
  const exit = () => onClose('exited')

  const body = typeof step.body === 'function' ? step.body() : step.body
  const centered = !rect

  const spotlightStyle = rect
    ? {
        top: rect.top - SPOTLIGHT_PAD,
        left: rect.left - SPOTLIGHT_PAD,
        width: rect.width + SPOTLIGHT_PAD * 2,
        height: rect.height + SPOTLIGHT_PAD * 2,
      }
    : null

  return (
    <div className="tour-overlay">
      <div
        className={spotlightStyle ? 'tour-backdrop tour-backdrop--cutout' : 'tour-backdrop'}
        style={spotlightStyle || undefined}
      />
      <div
        className={centered ? 'tour-card tour-card--center' : 'tour-card'}
        style={centered ? undefined : computeCardStyle(rect)}
      >
        <button type="button" className="tour-card-close" aria-label="Exit tour" onClick={exit}>
          ×
        </button>
        <p className="tour-card-body">{body}</p>
        <div className="tour-card-footer">
          <div className="tour-dots">
            {steps.map((s, i) => (
              <span key={s.id} className={i === index ? 'tour-dot tour-dot--active' : 'tour-dot'} />
            ))}
          </div>
          <div className="tour-card-actions">
            {index > 0 && (
              <button type="button" className="tour-btn tour-btn--ghost" onClick={goBack}>
                Back
              </button>
            )}
            <button type="button" className="tour-btn tour-btn--primary" onClick={goNext}>
              {isLast ? step.finishLabel || 'Done' : 'Next'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
