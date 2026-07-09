import { useState } from 'react'
import { Route, Routes } from 'react-router-dom'
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

  // Wait for the watchlist fetch and the /api/me identity to resolve before
  // deciding whether the basket picker is needed — otherwise the HUB
  // flashes empty for a frame, or a skip could be recorded under no user id.
  if (gateEnabled && (watchlist === null || !user)) {
    return <div className="app-content" />
  }

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
        <ToastHost />
      </>
    )
  }

  return (
    <>
      <main className="app-content">
        <Routes>
          <Route path="/" element={<Briefing />} />
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
      <ToastHost />
    </>
  )
}

export default App
