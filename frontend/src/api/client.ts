import axios from 'axios'

const ACCESS_KEY = 'sp_access'
const REFRESH_KEY = 'sp_refresh'

export function getAccessToken() { return localStorage.getItem(ACCESS_KEY) }
export function getRefreshToken() { return localStorage.getItem(REFRESH_KEY) }
export function setTokens(access: string, refresh: string) {
  localStorage.setItem(ACCESS_KEY, access)
  localStorage.setItem(REFRESH_KEY, refresh)
}
export function clearTokens() {
  localStorage.removeItem(ACCESS_KEY)
  localStorage.removeItem(REFRESH_KEY)
}

export const api = axios.create({ baseURL: '/api/v1' })

api.interceptors.request.use((config) => {
  const token = getAccessToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

let refreshing: Promise<string> | null = null

api.interceptors.response.use(
  (r) => r,
  async (error) => {
    const original = error.config
    if (error.response?.status !== 401 || original._retry) {
      return Promise.reject(error)
    }
    original._retry = true

    if (!refreshing) {
      refreshing = axios
        .post('/api/v1/auth/token/refresh/', { refresh: getRefreshToken() })
        .then((r) => {
          setTokens(r.data.access, r.data.refresh ?? getRefreshToken()!)
          return r.data.access
        })
        .catch(() => {
          clearTokens()
          window.location.href = '/login'
          return Promise.reject(error)
        })
        .finally(() => { refreshing = null })
    }

    try {
      const access = await refreshing
      original.headers.Authorization = `Bearer ${access}`
      return api(original)
    } catch {
      return Promise.reject(error)
    }
  },
)
