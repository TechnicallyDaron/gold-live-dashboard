import { Route, Routes } from 'react-router-dom'
import TabBar from './components/TabBar.jsx'
import Briefing from './screens/Briefing.jsx'
import Bias from './screens/Bias.jsx'
import Positions from './screens/Positions.jsx'
import './App.css'

function App() {
  return (
    <>
      <main className="app-content">
        <Routes>
          <Route path="/" element={<Briefing />} />
          <Route path="/bias" element={<Bias />} />
          <Route path="/bias/:asset" element={<Bias />} />
          <Route path="/positions" element={<Positions />} />
        </Routes>
      </main>
      <TabBar />
    </>
  )
}

export default App
