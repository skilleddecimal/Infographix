import { useCallback, useRef } from 'react'
import { useGenerationStore, useAuthStore } from '../stores'
import { generateApi, getApiError } from '../api'
import type { GenerateRequest } from '../api'

export function useGeneration() {
  const {
    generations,
    currentGeneration,
    selectedVariation,
    isGenerating,
    error,
    setGenerations,
    addGeneration,
    updateGeneration,
    setCurrentGeneration,
    setSelectedVariation,
    setIsGenerating,
    setError,
    clearCurrent,
  } = useGenerationStore()

  const { updateCredits } = useAuthStore()
  const pollingIdRef = useRef<number | null>(null)

  const generate = useCallback(
    async (data: GenerateRequest) => {
      setIsGenerating(true)
      setError(null)

      try {
        const response = await generateApi.create(data)

        addGeneration({
          id: response.id,
          prompt: response.prompt,
          status: response.status,
          archetype: response.archetype,
          dsl: response.dsl,
          variations: response.variations,
          createdAt: response.created_at,
          completedAt: response.completed_at,
          errorMessage: response.error_message,
        })

        // Poll for completion if pending/processing
        if (response.status === 'pending' || response.status === 'processing') {
          const pollInterval = setInterval(async () => {
            try {
              const updated = await generateApi.get(response.id)
              updateGeneration(response.id, {
                status: updated.status,
                archetype: updated.archetype,
                dsl: updated.dsl,
                variations: updated.variations,
                completedAt: updated.completed_at,
                errorMessage: updated.error_message,
              })

              if (updated.status === 'completed' || updated.status === 'failed') {
                clearInterval(pollInterval)
                pollingIdRef.current = null
                setIsGenerating(false)

                // Update credits
                const auth = useAuthStore.getState()
                if (auth.user && updated.status === 'completed') {
                  updateCredits(auth.user.creditsRemaining - 1)
                }
              }
            } catch {
              clearInterval(pollInterval)
              pollingIdRef.current = null
              setIsGenerating(false)
            }
          }, 1000)

          pollingIdRef.current = pollInterval
        } else {
          setIsGenerating(false)
        }

        return response
      } catch (err) {
        const apiError = getApiError(err)
        setError(apiError.message)
        setIsGenerating(false)
        throw err
      }
    },
    [addGeneration, updateGeneration, setIsGenerating, setError, updateCredits]
  )

  const fetchGenerations = useCallback(
    async (limit = 20, offset = 0) => {
      try {
        const response = await generateApi.list(limit, offset)
        setGenerations(
          response.map((g) => ({
            id: g.id,
            prompt: g.prompt,
            status: g.status,
            archetype: g.archetype,
            dsl: null,
            variations: null,
            createdAt: g.created_at,
            completedAt: null,
            errorMessage: null,
          }))
        )
      } catch (err) {
        const apiError = getApiError(err)
        setError(apiError.message)
      }
    },
    [setGenerations, setError]
  )

  const fetchGeneration = useCallback(
    async (id: string) => {
      try {
        const response = await generateApi.get(id)
        setCurrentGeneration({
          id: response.id,
          prompt: response.prompt,
          status: response.status,
          archetype: response.archetype,
          dsl: response.dsl,
          variations: response.variations,
          createdAt: response.created_at,
          completedAt: response.completed_at,
          errorMessage: response.error_message,
        })
        return response
      } catch (err) {
        const apiError = getApiError(err)
        setError(apiError.message)
        throw err
      }
    },
    [setCurrentGeneration, setError]
  )

  const createVariations = useCallback(
    async (id: string, count = 3) => {
      setIsGenerating(true)
      try {
        const response = await generateApi.createVariations(id, count)
        updateGeneration(id, {
          variations: response.variations,
        })
        setIsGenerating(false)
        return response
      } catch (err) {
        const apiError = getApiError(err)
        setError(apiError.message)
        setIsGenerating(false)
        throw err
      }
    },
    [updateGeneration, setIsGenerating, setError]
  )

  return {
    generations,
    currentGeneration,
    selectedVariation,
    isGenerating,
    error,
    generate,
    fetchGenerations,
    fetchGeneration,
    createVariations,
    setSelectedVariation,
    clearCurrent,
  }
}
