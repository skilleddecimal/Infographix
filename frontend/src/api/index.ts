export { apiClient, getApiError } from './client'
export type { ApiError } from './client'

export { authApi } from './auth'
export type { LoginRequest, RegisterRequest, TokenResponse, UserResponse } from './auth'

export { generateApi } from './generate'
export type {
  GenerateRequest,
  ContentItem,
  GenerationResponse,
  GenerationListResponse,
} from './generate'

export { templatesApi } from './templates'
export type { Template, TemplateListResponse, CreateTemplateRequest } from './templates'

export { downloadsApi, triggerDownload } from './downloads'
export type { DownloadFormat, DownloadRequest, DownloadResponse } from './downloads'
