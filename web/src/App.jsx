import { useEffect, useState } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import TabBar from './components/TabBar.jsx'
import Briefing from './screens/Briefing.jsx'
import Bias from './screens/Bias.jsx'
import Chart from './screens/Chart.jsx'
import News from './screens/News.jsx'
import Positions from './screens/Positions.jsx'
import LoginScreen from './screens/LoginScreen.jsx'
import OnboardingBaskets from './screens/OnboardingBaskets.jsx'
import ToastHost from './components/ToastHost.jsx'
import { useAuth } from './lib/useAuth.js'
import { useWatchlist } from './lib/useWatchlist.js'
import { isOnboardingSkipped } from './lib/onboarding.js'
import './App.css'

function App() {
  const { gateEnabled, ready, signedIn, user } = useAuth()
  const { watchlist } = useWatchlist(!gateEnabled || (ready && signedIn))
  const [onboardingDone, setOnboardingDone] = useState(false)

  // Only play the Portal's dissolve transition for a sign-in that happens
  // DURING this session — not for a session already restored from
  // localStorage on a cold app relaunch (that should land straight on the
  // HUB with no flash of the gate).
  const [sawPortal, setSawPortal] = useState(false)
  const [portalDissolved, setPortalDissolved] = useState(false)
  useEffect(() => {
    if (gateEnabled && ready && !signedIn) setSawPortal(true)
  }, [gateEnabled, ready, signedIn])

  if (gateEnabled && !ready) {
    return <div className="app-content" />
  }

  if (gateEnabled && !signedIn) {
    return (
      <>
        <LoginScreen />
        <ToastHost />
      </>
    )
  }

  const inPortalPhase = gateEnabled && sawPortal && !portalDissolved

  // Wait for the watchlist fetch and the /api/me identity to resolve before
  // deciding whether the basket picker is needed — otherwise the HUB
  // flashes empty for a frame, or a skip could be recorded under no user id.
  // Keep the (still static, not yet dissolving) portal up through this gap
  // rather than blanking it, so the dissolve only ever starts once there's
  // real content underneath to reveal.
  if (gateEnabled && (watchlist === null || !user)) {
    return inPortalPhase ? (
      <>
        <LoginScreen />
        <ToastHost />
      </>
    ) : (
      <div className="app-content" />
    )
  }

  // Auth already succeeded and the destination below is ready, so the
  // dissolve overlay renders ON TOP of the real next screen (onboarding or
  // the HUB) — fading it out IS the "unblur into the HUB", not a fade
  // through black into a fake backdrop.
  const dissolveOverlay = inPortalPhase ? (
    <LoginScreen dissolving onDissolved={() => setPortalDissolved(true)} />
  ) : null

  const needsOnboarding =
    gateEnabled &&
    !onboardingDone &&
    watchlist &&
    Object.keys(watchlist).length === 0 &&
    !isOnboardingSkipped(user?.id)

  if (needsOnboarding) {
    return (
      <>
        <OnboardingBaskets
          userId={user?.id}
          onDone={() => setOnboardingDone(true)}
          onSkip={() => setOnboardingDone(true)}
        />
        {dissolveOverlay}
        <ToastHost />
      </>
    )
  }

  return (
    <>
      <main className="app-content">
        <Routes>
          <Route path="/hub" element={<Briefing />} />
          <Route path="/" element={<Navigate to="/hub" replace />} />
          <Route path="/bias" element={<Bias />} />
          <Route path="/bias/:asset" element={<Bias />} />
          <Route path="/chart" element={<Chart />} />
          <Route path="/chart/:asset" element={<Chart />} />
          <Route path="/news" element={<News />} />
          <Route path="/news/:asset" element={<News />} />
          <Route path="/positions" element={<Positions />} />
        </Routes>
      </main>
      <TabBar />
      {dissolveOverlay}
      <ToastHost />
    </>
  )
}

export default App
