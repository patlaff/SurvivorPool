import { useState, useCallback } from 'react'
import { api, setTokens, clearTokens, getAccessToken } from '../api/client'

export interface AuthUser {
  id: number
  email: string
  display_name: string
  avatar_url: string
}

function decodeUser(access: string): AuthUser | null {
  try {
    const payload = JSON.parse(atob(access.split('.')[1]))
    return { id: Number(payload.user_id), email: '', display_name: '', avatar_url: '' }
  } catch {
    return null
  }
}

export function useAuth() {
  const [user, setUser] = useState<AuthUser | null>(() => {
    const token = getAccessToken()
    return token ? decodeUser(token) : null
  })

  const loginWithGoogle = useCallback(async (idToken: string) => {
    const { data } = await api.post('/auth/google/', { id_token: idToken })
    setTokens(data.access, data.refresh)
    setUser(data.user)
    return data.user as AuthUser
  }, [])

  const logout = useCallback(() => {
    clearTokens()
    setUser(null)
  }, [])

  return {
    user,
    isAuthenticated: !!user,
    loginWithGoogle,
    logout,
  }
}
