import { Routes, Route, Navigate, NavLink } from 'react-router-dom'
import OrgPage from './pages/OrgPage'
import TeamProfilesPage from './pages/TeamProfilesPage'
import AuditLogPage from './pages/AuditLogPage'
import SubscriptionPage from './pages/SubscriptionPage'
import HelpPage from './pages/HelpPage'
import LoginPage from './pages/LoginPage'
import { useAuthStore } from './api/auth'

function NavBar() {
  const logout = useAuthStore(s => s.logout)
  const linkCls = ({ isActive }: { isActive: boolean }) =>
    isActive ? 'nav-link active' : 'nav-link'

  return (
    <nav className="sidebar">
      <div className="logo">Grit Admin</div>
      <NavLink to="/org" className={linkCls}>Organisation</NavLink>
      <NavLink to="/profiles" className={linkCls}>Team Profiles</NavLink>
      <NavLink to="/audit" className={linkCls}>Audit Log</NavLink>
      <NavLink to="/subscription" className={linkCls}>Subscription</NavLink>
      <NavLink to="/help" className={linkCls}>Help</NavLink>
      <button onClick={logout} className="logout-btn">Sign out</button>
    </nav>
  )
}

export default function App() {
  const token = useAuthStore(s => s.token)

  if (!token) {
    return (
      <Routes>
        <Route path="*" element={<LoginPage />} />
      </Routes>
    )
  }

  return (
    <div className="app-layout">
      <NavBar />
      <main className="content">
        <Routes>
          <Route path="/" element={<Navigate to="/org" replace />} />
          <Route path="/org" element={<OrgPage />} />
          <Route path="/profiles" element={<TeamProfilesPage />} />
          <Route path="/audit" element={<AuditLogPage />} />
          <Route path="/subscription" element={<SubscriptionPage />} />
          <Route path="/help" element={<HelpPage />} />
          <Route path="*" element={<Navigate to="/org" replace />} />
        </Routes>
      </main>
    </div>
  )
}
