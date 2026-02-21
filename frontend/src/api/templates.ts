import { apiClient } from './client'

export interface Template {
  id: string
  name: string
  description: string | null
  archetype: string | null
  category: string | null
  thumbnail_url: string | null
  is_public: boolean
  use_count: number
  created_at: string
}

export interface TemplateListResponse {
  templates: Template[]
  total: number
  has_more: boolean
}

export interface CreateTemplateRequest {
  name: string
  description?: string
  archetype?: string
  category?: string
  dsl_template: object
  parameters?: object
}

export const templatesApi = {
  list: async (
    params: {
      category?: string
      archetype?: string
      include_public?: boolean
      limit?: number
      offset?: number
    } = {}
  ): Promise<TemplateListResponse> => {
    const response = await apiClient.get<TemplateListResponse>('/templates', {
      params,
    })
    return response.data
  },

  get: async (id: string): Promise<Template & { dsl_template: object }> => {
    const response = await apiClient.get(`/templates/${id}`)
    return response.data
  },

  create: async (data: CreateTemplateRequest): Promise<Template> => {
    const response = await apiClient.post<Template>('/templates', data)
    return response.data
  },

  update: async (
    id: string,
    data: Partial<CreateTemplateRequest>
  ): Promise<Template> => {
    const response = await apiClient.put<Template>(`/templates/${id}`, data)
    return response.data
  },

  delete: async (id: string): Promise<void> => {
    await apiClient.delete(`/templates/${id}`)
  },

  getCategories: async (): Promise<string[]> => {
    const response = await apiClient.get<string[]>('/templates/categories')
    return response.data
  },
}
