import axios, { AxiosError, AxiosInstance, InternalAxiosRequestConfig } from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1'

// Create axios instance
const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
})

// Request interceptor for adding auth token
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const authStorage = localStorage.getItem('auth-storage')
    if (authStorage) {
      try {
        const { state } = JSON.parse(authStorage)
        if (state?.accessToken) {
          config.headers.Authorization = `Bearer ${state.accessToken}`
        }
      } catch {
        // Invalid storage, ignore
      }
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor for handling errors and token refresh
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & {
      _retry?: boolean
    }

    // If 401 and not already retrying, try to refresh token
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      try {
        const authStorage = localStorage.getItem('auth-storage')
        if (authStorage) {
          const { state } = JSON.parse(authStorage)
          if (state?.refreshToken) {
            const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
              refresh_token: state.refreshToken,
            })

            const { access_token, refresh_token } = response.data

            // Update storage
            const newState = {
              ...state,
              accessToken: access_token,
              refreshToken: refresh_token,
            }
            localStorage.setItem(
              'auth-storage',
              JSON.stringify({ state: newState })
            )

            // Retry original request
            originalRequest.headers.Authorization = `Bearer ${access_token}`
            return apiClient(originalRequest)
          }
        }
      } catch {
        // Refresh failed, clear auth
        localStorage.removeItem('auth-storage')
        window.location.href = '/login'
      }
    }

    return Promise.reject(error)
  }
)

export { apiClient }

// API error type
export interface ApiError {
  message: string
  detail?: string
  status?: number
}

export const getApiError = (error: unknown): ApiError => {
  if (axios.isAxiosError(error)) {
    return {
      message: error.response?.data?.detail || error.message,
      detail: error.response?.data?.detail,
      status: error.response?.status,
    }
  }
  return {
    message: error instanceof Error ? error.message : 'An unknown error occurred',
  }
}
