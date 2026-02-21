import { apiClient } from './client'

export type DownloadFormat = 'pptx' | 'svg' | 'png' | 'pdf'

export interface DownloadRequest {
  generation_id: string
  format: DownloadFormat
  variation_index?: number
}

export interface DownloadResponse {
  id: string
  download_url: string
  expires_at: string
}

export const downloadsApi = {
  create: async (data: DownloadRequest): Promise<DownloadResponse> => {
    const response = await apiClient.post<DownloadResponse>('/downloads', data)
    return response.data
  },

  download: async (id: string): Promise<Blob> => {
    const response = await apiClient.get(`/downloads/${id}/file`, {
      responseType: 'blob',
    })
    return response.data
  },

  getFormats: async (
    generationId: string
  ): Promise<{ format: string; available: boolean }[]> => {
    const response = await apiClient.get(`/downloads/formats/${generationId}`)
    return response.data
  },
}

// Utility function to trigger download
export const triggerDownload = (blob: Blob, filename: string) => {
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}
