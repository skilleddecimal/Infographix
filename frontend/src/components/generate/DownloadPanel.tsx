import { useState } from 'react'
import { Button } from '../ui'
import { downloadsApi, triggerDownload, type DownloadFormat } from '../../api'

interface DownloadPanelProps {
  generationId: string
  variationIndex?: number
  disabled?: boolean
}

const formats: { id: DownloadFormat; name: string; icon: string; pro?: boolean }[] = [
  {
    id: 'pptx',
    name: 'PowerPoint',
    icon: 'M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z',
  },
  {
    id: 'svg',
    name: 'SVG',
    icon: 'M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z',
    pro: true,
  },
  {
    id: 'png',
    name: 'PNG',
    icon: 'M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z',
    pro: true,
  },
  {
    id: 'pdf',
    name: 'PDF',
    icon: 'M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z',
    pro: true,
  },
]

export function DownloadPanel({
  generationId,
  variationIndex,
  disabled,
}: DownloadPanelProps) {
  const [downloading, setDownloading] = useState<DownloadFormat | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleDownload = async (format: DownloadFormat) => {
    setDownloading(format)
    setError(null)

    try {
      // Create download
      const response = await downloadsApi.create({
        generation_id: generationId,
        format,
        variation_index: variationIndex,
      })

      // Fetch file
      const blob = await downloadsApi.download(response.id)

      // Trigger browser download
      const filename = `infographic-${generationId.slice(0, 8)}.${format}`
      triggerDownload(blob, filename)
    } catch (err) {
      setError('Download failed. Please try again.')
      console.error('Download error:', err)
    } finally {
      setDownloading(null)
    }
  }

  return (
    <div className="space-y-3">
      <label className="text-sm font-medium text-gray-700">Download</label>
      <div className="flex flex-wrap gap-2">
        {formats.map((format) => (
          <Button
            key={format.id}
            variant="outline"
            size="sm"
            onClick={() => handleDownload(format.id)}
            disabled={disabled || downloading !== null}
            isLoading={downloading === format.id}
            leftIcon={
              <svg
                className="w-4 h-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d={format.icon}
                />
              </svg>
            }
          >
            {format.name}
            {format.pro && (
              <span className="ml-1 px-1.5 py-0.5 text-xs bg-primary-100 text-primary-700 rounded">
                Pro
              </span>
            )}
          </Button>
        ))}
      </div>
      {error && <p className="text-sm text-error-600">{error}</p>}
    </div>
  )
}
