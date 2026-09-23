import { Navigate, Route, Routes } from 'react-router-dom'
import Shell from './components/Shell'
import { useApp } from './lib/store'
import Anomaly from './screens/Anomaly'
import Dashboard from './screens/Dashboard'
import Safety from './screens/Safety'
import ShiftStart from './screens/ShiftStart'
import Summary from './screens/Summary'
import Timeline from './screens/Timeline'
import TrainingHub from './screens/training/TrainingHub'

function Home() {
  const { state } = useApp()
  if (!state) return null
  return <Navigate to={state.shift.active ? '/dashboard' : '/start'} replace />
}

export default function App() {
  return (
    <Routes>
      <Route element={<Shell />}>
        <Route index element={<Home />} />
        <Route path="start" element={<ShiftStart />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="safety" element={<Safety />} />
        <Route path="timeline" element={<Timeline />} />
        <Route path="anomaly" element={<Anomaly />} />
        <Route path="training/*" element={<TrainingHub />} />
        <Route path="summary" element={<Summary />} />
        <Route path="*" element={<Home />} />
      </Route>
    </Routes>
  )
}
