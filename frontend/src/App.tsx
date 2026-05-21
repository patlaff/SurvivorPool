import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { ProtectedRoute } from './components/ProtectedRoute'
import { Layout } from './components/Layout'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import CreateLeaguePage from './pages/CreateLeaguePage'
import LeaguePage from './pages/LeaguePage'
import DraftPage from './pages/DraftPage'
import RosterPage from './pages/RosterPage'
import RosterViewPage from './pages/RosterViewPage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route element={<ProtectedRoute />}>
          <Route element={<Layout />}>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/leagues/new" element={<CreateLeaguePage />} />
            <Route path="/leagues/:slug" element={<LeaguePage />} />
            <Route path="/leagues/:slug/draft" element={<DraftPage />} />
            <Route path="/leagues/:slug/roster" element={<RosterPage />} />
            <Route path="/leagues/:slug/roster/:userId" element={<RosterViewPage />} />
          </Route>
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
