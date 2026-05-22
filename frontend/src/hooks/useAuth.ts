import { useState, useCallback } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { api, setTokens, clearTokens, getAccessToken } from '../api/client'

export interface AuthUser {
  id: number
  email: string
  display_name: string
  avatar_url: string
  is_superadmin: boolean
}

function decodeUser(access: string): AuthUser | null {
  try {
    const payload = JSON.parse(atob(access.split('.')[1]))
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

export function useAuth() {
  const queryClient = useQueryClient()
  const [user, setUser] = useState<AuthUser | null>(() => {
    const token = getAccessToken()
    return token ? decodeUser(token) : null
  })

  const loginWithGoogle = useCallback(async (idToken: string) => {
    const { data } = await api.post('/auth/google/', { id_token: idToken })
    setTokens(data.access, data.refresh)
    // Decode from the new token so is_superadmin and all claims are accurate
    const user = decodeUser(data.access) ?? data.user
    setUser(user)
    return user as AuthUser
  }, [])

  const logout = useCallback(() => {
    queryClient.clear()
    clearTokens()
    setUser(null)
  }, [queryClient])

  return {
    user,
    isAuthenticated: !!user,
    loginWithGoogle,
    logout,
  }
}
