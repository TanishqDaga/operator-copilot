import { Navigate, Route, Routes } from 'react-router-dom'
import Shell from './components/Shell'
import { HOME } from './lib/session'
import { useApp } from './lib/store'
import Anomaly from './screens/Anomaly'
import Dashboard from './screens/Dashboard'
import Login from './screens/Login'
import ManagerDashboard from './screens/ManagerDashboard'
import Safety from './screens/Safety'
import ShiftStart from './screens/ShiftStart'
import Summary from './screens/Summary'
import Timeline from './screens/Timeline'
import Training from './screens/Training'

function Home() {
  const { state, role } = useApp()
  if (!role) return <Navigate to="/login" replace />
  if (role === 'manager') return <Navigate to={HOME.manager} replace />
  if (!state) return null
  return <Navigate to={state.shift.active ? '/dashboard' : '/start'} replace />
}

/** Demo role gate (frontend only — the backend re-checks manager APIs via roles.py). */
function RequireRole({ roles, children }) {
  const { role } = useApp()
  if (!role) return <Navigate to="/login" replace />
  if (!roles.includes(role)) return <Navigate to={HOME[role]} replace />
  return children
}

const OP = ['operator']
const ANY = ['operator', 'manager']

export default function App() {
  return (
    <Routes>
      <Route path="login" element={<Login />} />
      <Route element={<Shell />}>
        <Route index element={<Home />} />
        <Route path="manager" element={<RequireRole roles={['manager']}><ManagerDashboard /></RequireRole>} />
        <Route path="start" element={<RequireRole roles={OP}><ShiftStart /></RequireRole>} />
        <Route path="dashboard" element={<RequireRole roles={OP}><Dashboard /></RequireRole>} />
        <Route path="safety" element={<RequireRole roles={OP}><Safety /></RequireRole>} />
        <Route path="timeline" element={<RequireRole roles={ANY}><Timeline /></RequireRole>} />
        <Route path="anomaly" element={<RequireRole roles={OP}><Anomaly /></RequireRole>} />
        <Route path="training" element={<RequireRole roles={OP}><Training /></RequireRole>} />
        <Route path="summary" element={<RequireRole roles={ANY}><Summary /></RequireRole>} />
        <Route path="*" element={<Home />} />
      </Route>
    </Routes>
  )
}
