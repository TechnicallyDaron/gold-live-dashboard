import { useEffect, useState } from 'react'
import TourPrompt from './TourPrompt.jsx'
import TourOverlay from './TourOverlay.jsx'
import { hasSeenTour, markTourSeen } from '../lib/tourState.js'
import { subscribeTourStart } from '../lib/tourBus.js'

// Mounted once in App.jsx (outside <Routes>, alongside ToastHost) so it
// survives tab navigation while the overlay drives the actual tabs.
export default function TourManager({ userId, autoPromptTrigger }) {
  const [mode, setMode] = useState('idle') // idle | prompt | active
  const [runId, setRunId] = useState(0)

  useEffect(() => {
    if (autoPromptTrigger && userId && !hasSeenTour(userId)) {
      setMode('prompt')
    }
    // Fires once per session when onboarding hands off to the HUB — not on
    // every render, so a later skip/finish doesn't get immediately re-armed.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoPromptTrigger, userId])

  useEffect(
    () =>
      subscribeTourStart(() => {
        setRunId((n) => n + 1)
        setMode('active')
      }),
    [],
  )

  if (mode === 'prompt') {
    return (
      <TourPrompt
        onTake={() => setMode('active')}
        onSkip={() => {
          markTourSeen(userId)
          setMode('idle')
        }}
      />
    )
  }

  if (mode === 'active') {
    return (
      <TourOverlay
        key={runId}
        onClose={() => {
          markTourSeen(userId)
          setMode('idle')
        }}
      />
    )
  }

  return null
}
