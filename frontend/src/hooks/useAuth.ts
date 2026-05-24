import { createContext, useContext, useState, useCallback, ReactNode, createElement } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { api, setTokens, clearTokens, getAccessToken } from '../api/client'

export interface AuthUser {
  id: number
  email: string
  display_name: string
  avatar_url: string
  is_superadmin: boolean
}

function b64urlDecode(s: string): string {
  return atob(s.replace(/-/g, '+').replace(/_/g, '/').padEnd(s.length + (4 - (s.length % 4)) % 4, '='))
}

function decodeUser(access: string): AuthUser | null {
  try {
    const payload = JSON.parse(b64urlDecode(access.split('.')[1]))
    return {
      id: Number(payload.user_id),
      email: payload.email ?? '',
      display_name: payload.display_name ?? '',
      avatar_url: payload.avatar_url ?? '',
      is_superadmin: payload.is_superadmin ?? false,
    }
  } catch {
    return null
  }
}

interface AuthContextValue {
  user: AuthUser | null
  isAuthenticated: boolean
  loginWithGoogle: (idToken: string) => Promise<AuthUser>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()
  const [user, setUser] = useState<AuthUser | null>(() => {
    const token = getAccessToken()
    return token ? decodeUser(token) : null
  })

  const loginWithGoogle = useCallback(async (idToken: string) => {
    const { data } = await api.post('/auth/google/', { id_token: idToken })
    setTokens(data.access, data.refresh)
    const decoded = decodeUser(data.access) ?? data.user
    setUser(decoded)
    return decoded as AuthUser
  }, [])

  const logout = useCallback(() => {
    queryClient.clear()
    clearTokens()
    setUser(null)
  }, [queryClient])

  return createElement(AuthContext.Provider, {
    value: { user, isAuthenticated: !!user, loginWithGoogle, logout },
    children,
  })
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
