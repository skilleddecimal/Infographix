import { create } from 'zustand'

export interface Generation {
  id: string
  prompt: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  archetype: string | null
  dsl: object | null
  variations: object[] | null
  createdAt: string
  completedAt: string | null
  errorMessage: string | null
}

interface GenerationState {
  generations: Generation[]
  currentGeneration: Generation | null
  selectedVariation: number
  isGenerating: boolean
  error: string | null

  // Actions
  setGenerations: (generations: Generation[]) => void
  addGeneration: (generation: Generation) => void
  updateGeneration: (id: string, updates: Partial<Generation>) => void
  setCurrentGeneration: (generation: Generation | null) => void
  setSelectedVariation: (index: number) => void
  setIsGenerating: (isGenerating: boolean) => void
  setError: (error: string | null) => void
  clearCurrent: () => void
}

export const useGenerationStore = create<GenerationState>((set) => ({
  generations: [],
  currentGeneration: null,
  selectedVariation: 0,
  isGenerating: false,
  error: null,

  setGenerations: (generations) => set({ generations }),

  addGeneration: (generation) =>
    set((state) => ({
      generations: [generation, ...state.generations],
      currentGeneration: generation,
    })),

  updateGeneration: (id, updates) =>
    set((state) => ({
      generations: state.generations.map((g) =>
        g.id === id ? { ...g, ...updates } : g
      ),
      currentGeneration:
        state.currentGeneration?.id === id
          ? { ...state.currentGeneration, ...updates }
          : state.currentGeneration,
    })),

  setCurrentGeneration: (generation) =>
    set({ currentGeneration: generation, selectedVariation: 0 }),

  setSelectedVariation: (index) => set({ selectedVariation: index }),

  setIsGenerating: (isGenerating) => set({ isGenerating }),

  setError: (error) => set({ error }),

  clearCurrent: () =>
    set({ currentGeneration: null, selectedVariation: 0, error: null }),
}))
