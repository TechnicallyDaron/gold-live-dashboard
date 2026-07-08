import { Route, Routes } from 'react-router-dom'
import TabBar from './components/TabBar.jsx'
import Briefing from './screens/Briefing.jsx'
import Bias from './screens/Bias.jsx'
import Chart from './screens/Chart.jsx'
import News from './screens/News.jsx'
import Positions from './screens/Positions.jsx'
import ToastHost from './components/ToastHost.jsx'
import './App.css'

function App() {
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
