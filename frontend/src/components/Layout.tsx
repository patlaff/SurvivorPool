import { useState } from 'react'
import { Outlet, Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { useDarkMode } from '../hooks/useDarkMode'

export function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const { dark, toggle } = useDarkMode()
  const [menuOpen, setMenuOpen] = useState(false)

  function handleLogout() {
    logout()
    navigate('/login')
    setMenuOpen(false)
  }

  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-survivor-dark text-white shadow-md">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <Link to="/info" className="flex items-center gap-2 text-survivor-orange font-bold text-xl tracking-tight">
            🔥 SurvivorPool
          </Link>

          {/* Desktop nav */}
          {user && (
            <div className="hidden md:flex items-center gap-4">
              <Link to="/" className="text-sm text-gray-300 hover:text-white transition-colors">
                My Leagues
              </Link>
              <Link to="/info" className="text-sm text-gray-300 hover:text-white transition-colors">
                How to Play
              </Link>
              {user.is_superadmin && (
                <Link to="/admin" className="text-xs font-semibold text-survivor-orange border border-survivor-orange rounded px-2 py-0.5 hover:bg-survivor-orange hover:text-white transition-colors">
                  Admin
                </Link>
              )}
              {user.avatar_url && (
                <img
                  src={user.avatar_url}
                  alt={user.display_name}
                  className="w-8 h-8 rounded-full ring-2 ring-survivor-orange"
                />
              )}
              <span className="text-sm text-gray-300">{user.display_name}</span>
              <button
                onClick={toggle}
                aria-label={dark ? 'Switch to light mode' : 'Switch to dark mode'}
                title={dark ? 'Light mode' : 'Dark mode'}
                className="text-gray-400 hover:text-white transition-colors"
              >
                {dark ? (
                  <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364-6.364-.707.707M6.343 17.657l-.707.707M17.657 17.657l.707.707M6.343 6.343l-.707-.707M12 8a4 4 0 100 8 4 4 0 000-8z" />
                  </svg>
                ) : (
                  <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M21 12.79A9 9 0 1111.21 3a7 7 0 009.79 9.79z" />
                  </svg>
                )}
              </button>
              <button
                onClick={handleLogout}
                className="text-sm text-gray-400 hover:text-white transition-colors"
              >
                Sign out
              </button>
            </div>
          )}

          {/* Mobile hamburger button */}
          {user && (
            <button
              className="md:hidden text-gray-300 hover:text-white transition-colors p-1"
              onClick={() => setMenuOpen(prev => !prev)}
              aria-label={menuOpen ? 'Close menu' : 'Open menu'}
            >
              {menuOpen ? (
                <svg xmlns="http://www.w3.org/2000/svg" className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              ) : (
                <svg xmlns="http://www.w3.org/2000/svg" className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              )}
            </button>
          )}
        </div>

        {/* Mobile dropdown menu */}
        {user && menuOpen && (
          <div className="md:hidden bg-survivor-dark border-t border-gray-700 px-4 py-4 flex flex-col gap-4">
            <div className="flex items-center gap-3">
              {user.avatar_url && (
                <img
                  src={user.avatar_url}
                  alt={user.display_name}
                  className="w-8 h-8 rounded-full ring-2 ring-survivor-orange"
                />
              )}
              <span className="text-sm text-gray-300">{user.display_name}</span>
            </div>
            <Link
              to="/"
              className="text-sm text-gray-300 hover:text-white transition-colors"
              onClick={() => setMenuOpen(false)}
            >
              My Leagues
            </Link>
            <Link
              to="/info"
              className="text-sm text-gray-300 hover:text-white transition-colors"
              onClick={() => setMenuOpen(false)}
            >
              How to Play
            </Link>
            {user.is_superadmin && (
              <Link
                to="/admin"
                className="text-xs font-semibold text-survivor-orange border border-survivor-orange rounded px-2 py-0.5 hover:bg-survivor-orange hover:text-white transition-colors self-start"
                onClick={() => setMenuOpen(false)}
              >
                Admin
              </Link>
            )}
            <div className="flex items-center gap-4 pt-2 border-t border-gray-700">
              <button
                onClick={toggle}
                aria-label={dark ? 'Switch to light mode' : 'Switch to dark mode'}
                title={dark ? 'Light mode' : 'Dark mode'}
                className="text-gray-400 hover:text-white transition-colors"
              >
                {dark ? (
                  <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364-6.364-.707.707M6.343 17.657l-.707.707M17.657 17.657l.707.707M6.343 6.343l-.707-.707M12 8a4 4 0 100 8 4 4 0 000-8z" />
                  </svg>
                ) : (
                  <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M21 12.79A9 9 0 1111.21 3a7 7 0 009.79 9.79z" />
                  </svg>
                )}
              </button>
              <button
                onClick={handleLogout}
                className="text-sm text-gray-400 hover:text-white transition-colors"
              >
                Sign out
              </button>
            </div>
          </div>
        )}
      </header>
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Outlet />
      </main>
    </div>
  )
}
