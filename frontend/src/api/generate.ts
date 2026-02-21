import { apiClient } from './client'

export interface GenerateRequest {
  prompt: string
  content?: ContentItem[]
  brand_colors?: string[]
  brand_fonts?: string[]
  formality?: 'casual' | 'professional' | 'formal'
  num_variations?: number
}

export interface ContentItem {
  title: string
  description?: string
  icon?: string
}

export interface GenerationResponse {
  id: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  prompt: string
  archetype: string | null
  archetype_confidence: number | null
  dsl: object | null
  style: object | null
  variations: object[] | null
  error_message: string | null
  created_at: string
  completed_at: string | null
  processing_time_ms: number | null
}

export interface GenerationListResponse {
  id: string
  prompt: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  archetype: string | null
  created_at: string
}

export const generateApi = {
  create: async (data: GenerateRequest): Promise<GenerationResponse> => {
    const response = await apiClient.post<GenerationResponse>('/generate', data)
    return response.data
  },

  get: async (id: string): Promise<GenerationResponse> => {
    const response = await apiClient.get<GenerationResponse>(`/generate/${id}`)
    return response.data
  },

  list: async (
    limit = 20,
    offset = 0
  ): Promise<GenerationListResponse[]> => {
    const response = await apiClient.get<GenerationListResponse[]>('/generate', {
      params: { limit, offset },
    })
    return response.data
  },

  delete: async (id: string): Promise<void> => {
    await apiClient.delete(`/generate/${id}`)
  },

  createVariations: async (
    id: string,
    count = 3,
    strategy = 'diverse'
  ): Promise<GenerationResponse> => {
    const response = await apiClient.post<GenerationResponse>(
      `/generate/${id}/variations`,
      { count, strategy }
    )
    return response.data
  },
}
