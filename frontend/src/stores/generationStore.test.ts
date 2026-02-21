import { describe, it, expect, beforeEach } from 'vitest'
import { useGenerationStore, Generation } from './generationStore'

const mockGeneration: Generation = {
  id: 'gen-123',
  prompt: 'Create a funnel diagram',
  status: 'completed',
  archetype: 'funnel',
  dsl: { type: 'funnel', items: [] },
  variations: null,
  createdAt: '2024-01-01T00:00:00Z',
  completedAt: '2024-01-01T00:01:00Z',
  errorMessage: null,
}

const mockGeneration2: Generation = {
  id: 'gen-456',
  prompt: 'Create a timeline',
  status: 'pending',
  archetype: null,
  dsl: null,
  variations: null,
  createdAt: '2024-01-02T00:00:00Z',
  completedAt: null,
  errorMessage: null,
}

describe('generationStore', () => {
  beforeEach(() => {
    useGenerationStore.setState({
      generations: [],
      currentGeneration: null,
      selectedVariation: 0,
      isGenerating: false,
      error: null,
    })
  })

  describe('setGenerations', () => {
    it('sets the generations list', () => {
      useGenerationStore.getState().setGenerations([mockGeneration, mockGeneration2])

      const state = useGenerationStore.getState()
      expect(state.generations).toHaveLength(2)
      expect(state.generations[0]).toEqual(mockGeneration)
    })
  })

  describe('addGeneration', () => {
    it('adds generation to the beginning of the list', () => {
      useGenerationStore.getState().setGenerations([mockGeneration])
      useGenerationStore.getState().addGeneration(mockGeneration2)

      const state = useGenerationStore.getState()
      expect(state.generations).toHaveLength(2)
      expect(state.generations[0]).toEqual(mockGeneration2)
    })

    it('sets the new generation as current', () => {
      useGenerationStore.getState().addGeneration(mockGeneration)

      expect(useGenerationStore.getState().currentGeneration).toEqual(mockGeneration)
    })
  })

  describe('updateGeneration', () => {
    it('updates generation in the list', () => {
      useGenerationStore.getState().setGenerations([mockGeneration])
      useGenerationStore.getState().updateGeneration('gen-123', { status: 'failed' })

      expect(useGenerationStore.getState().generations[0].status).toBe('failed')
    })

    it('updates current generation if it matches', () => {
      useGenerationStore.getState().addGeneration(mockGeneration)
      useGenerationStore.getState().updateGeneration('gen-123', {
        status: 'failed',
        errorMessage: 'An error occurred',
      })

      const current = useGenerationStore.getState().currentGeneration
      expect(current?.status).toBe('failed')
      expect(current?.errorMessage).toBe('An error occurred')
    })

    it('does not update current generation if id does not match', () => {
      useGenerationStore.getState().addGeneration(mockGeneration)
      useGenerationStore.getState().updateGeneration('gen-999', { status: 'failed' })

      expect(useGenerationStore.getState().currentGeneration?.status).toBe('completed')
    })
  })

  describe('setCurrentGeneration', () => {
    it('sets the current generation', () => {
      useGenerationStore.getState().setCurrentGeneration(mockGeneration)

      expect(useGenerationStore.getState().currentGeneration).toEqual(mockGeneration)
    })

    it('resets selected variation to 0', () => {
      useGenerationStore.setState({ selectedVariation: 2 })
      useGenerationStore.getState().setCurrentGeneration(mockGeneration)

      expect(useGenerationStore.getState().selectedVariation).toBe(0)
    })
  })

  describe('setSelectedVariation', () => {
    it('sets the selected variation index', () => {
      useGenerationStore.getState().setSelectedVariation(2)

      expect(useGenerationStore.getState().selectedVariation).toBe(2)
    })
  })

  describe('setIsGenerating', () => {
    it('updates generating state', () => {
      useGenerationStore.getState().setIsGenerating(true)
      expect(useGenerationStore.getState().isGenerating).toBe(true)

      useGenerationStore.getState().setIsGenerating(false)
      expect(useGenerationStore.getState().isGenerating).toBe(false)
    })
  })

  describe('setError', () => {
    it('sets error message', () => {
      useGenerationStore.getState().setError('Something went wrong')

      expect(useGenerationStore.getState().error).toBe('Something went wrong')
    })

    it('clears error message', () => {
      useGenerationStore.getState().setError('Error')
      useGenerationStore.getState().setError(null)

      expect(useGenerationStore.getState().error).toBeNull()
    })
  })

  describe('clearCurrent', () => {
    it('clears current generation and resets state', () => {
      useGenerationStore.getState().addGeneration(mockGeneration)
      useGenerationStore.getState().setSelectedVariation(2)
      useGenerationStore.getState().setError('Error')

      useGenerationStore.getState().clearCurrent()

      const state = useGenerationStore.getState()
      expect(state.currentGeneration).toBeNull()
      expect(state.selectedVariation).toBe(0)
      expect(state.error).toBeNull()
    })
  })
})
