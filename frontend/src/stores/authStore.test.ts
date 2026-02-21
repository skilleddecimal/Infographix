import { describe, it, expect, beforeEach } from 'vitest'
import { useAuthStore, User } from './authStore'

const mockUser: User = {
  id: 'user-123',
  email: 'test@example.com',
  name: 'Test User',
  plan: 'free',
  creditsRemaining: 10,
  isVerified: true,
}

describe('authStore', () => {
  beforeEach(() => {
    // Reset store state before each test
    useAuthStore.setState({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: true,
    })
  })

  describe('setUser', () => {
    it('sets the user and marks as authenticated', () => {
      useAuthStore.getState().setUser(mockUser)

      const state = useAuthStore.getState()
      expect(state.user).toEqual(mockUser)
      expect(state.isAuthenticated).toBe(true)
    })

    it('clears user and marks as unauthenticated when null', () => {
      useAuthStore.getState().setUser(mockUser)
      useAuthStore.getState().setUser(null)

      const state = useAuthStore.getState()
      expect(state.user).toBeNull()
      expect(state.isAuthenticated).toBe(false)
    })
  })

  describe('setTokens', () => {
    it('sets access and refresh tokens', () => {
      useAuthStore.getState().setTokens('access-token', 'refresh-token')

      const state = useAuthStore.getState()
      expect(state.accessToken).toBe('access-token')
      expect(state.refreshToken).toBe('refresh-token')
      expect(state.isAuthenticated).toBe(true)
    })
  })

  describe('logout', () => {
    it('clears all auth state', () => {
      useAuthStore.getState().setUser(mockUser)
      useAuthStore.getState().setTokens('access-token', 'refresh-token')
      useAuthStore.getState().logout()

      const state = useAuthStore.getState()
      expect(state.user).toBeNull()
      expect(state.accessToken).toBeNull()
      expect(state.refreshToken).toBeNull()
      expect(state.isAuthenticated).toBe(false)
    })
  })

  describe('setLoading', () => {
    it('updates loading state', () => {
      useAuthStore.getState().setLoading(false)
      expect(useAuthStore.getState().isLoading).toBe(false)

      useAuthStore.getState().setLoading(true)
      expect(useAuthStore.getState().isLoading).toBe(true)
    })
  })

  describe('updateCredits', () => {
    it('updates user credits', () => {
      useAuthStore.getState().setUser(mockUser)
      useAuthStore.getState().updateCredits(5)

      expect(useAuthStore.getState().user?.creditsRemaining).toBe(5)
    })

    it('does nothing when user is null', () => {
      useAuthStore.getState().updateCredits(5)
      expect(useAuthStore.getState().user).toBeNull()
    })
  })
})
