import { useState, useCallback, useEffect } from 'react'
import { useAuthStore } from '../stores'
import { authApi, getApiError } from '../api'
import type { LoginRequest, RegisterRequest } from '../api'

export function useAuth() {
  const {
    user,
    isAuthenticated,
    isLoading,
    setUser,
    setTokens,
    logout: storeLogout,
    setLoading,
  } = useAuthStore()

  const [error, setError] = useState<string | null>(null)

  // Initialize auth state on mount
  useEffect(() => {
    const initAuth = async () => {
      const authStorage = localStorage.getItem('auth-storage')
      if (authStorage) {
        try {
          const { state } = JSON.parse(authStorage)
          if (state?.accessToken) {
            const userData = await authApi.getMe()
            setUser({
              id: userData.id,
              email: userData.email,
              name: userData.name,
              plan: userData.plan,
              creditsRemaining: userData.credits_remaining,
              isVerified: userData.is_verified,
            })
          }
        } catch {
          storeLogout()
        }
      }
      setLoading(false)
    }

    initAuth()
  }, [setUser, storeLogout, setLoading])

  const login = useCallback(
    async (data: LoginRequest) => {
      setError(null)
      try {
        const tokens = await authApi.login(data)
        setTokens(tokens.access_token, tokens.refresh_token)

        const userData = await authApi.getMe()
        setUser({
          id: userData.id,
          email: userData.email,
          name: userData.name,
          plan: userData.plan,
          creditsRemaining: userData.credits_remaining,
          isVerified: userData.is_verified,
        })

        return { success: true }
      } catch (err) {
        const apiError = getApiError(err)
        setError(apiError.message)
        return { success: false, error: apiError.message }
      }
    },
    [setTokens, setUser]
  )

  const register = useCallback(
    async (data: RegisterRequest) => {
      setError(null)
      try {
        const tokens = await authApi.register(data)
        setTokens(tokens.access_token, tokens.refresh_token)

        const userData = await authApi.getMe()
        setUser({
          id: userData.id,
          email: userData.email,
          name: userData.name,
          plan: userData.plan,
          creditsRemaining: userData.credits_remaining,
          isVerified: userData.is_verified,
        })

        return { success: true }
      } catch (err) {
        const apiError = getApiError(err)
        setError(apiError.message)
        return { success: false, error: apiError.message }
      }
    },
    [setTokens, setUser]
  )

  const logout = useCallback(async () => {
    try {
      await authApi.logout()
    } catch {
      // Ignore logout errors
    }
    storeLogout()
  }, [storeLogout])

  return {
    user,
    isAuthenticated,
    isLoading,
    error,
    login,
    register,
    logout,
  }
}
