import { Outlet, Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

export function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/login')
  }

  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-survivor-dark text-white shadow-md">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2 text-survivor-orange font-bold text-xl tracking-tight">
            🔥 SurvivorPool
          </Link>
          {user && (
            <div className="flex items-center gap-4">
              {user.avatar_url && (
                <img
                  src={user.avatar_url}
                  alt={user.display_name}
                  className="w-8 h-8 rounded-full ring-2 ring-survivor-orange"
                />
              )}
              <span className="text-sm text-gray-300">{user.display_name}</span>
              <button
                onClick={handleLogout}
                className="text-sm text-gray-400 hover:text-white transition-colors"
              >
                Sign out
              </button>
            </div>
          )}
        </div>
      </header>
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Outlet />
      </main>
    </div>
  )
}
