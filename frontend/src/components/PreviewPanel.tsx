interface PreviewPanelProps {
  scene: object | null
}

export function PreviewPanel({ scene }: PreviewPanelProps) {
  if (!scene) {
    return null
  }

  return (
    <div className="mt-12">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-900">Preview</h2>
        <div className="flex gap-2">
          <button className="px-4 py-2 text-sm bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg transition-colors">
            Regenerate
          </button>
          <button className="px-4 py-2 text-sm bg-primary-600 hover:bg-primary-700 text-white rounded-lg transition-colors flex items-center gap-2">
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
                d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
              />
            </svg>
            Download PPTX
          </button>
        </div>
      </div>

      {/* Preview Canvas */}
      <div className="bg-white rounded-xl shadow-lg border border-gray-200 aspect-video flex items-center justify-center">
        <div className="text-center text-gray-500">
          <svg
            className="w-16 h-16 mx-auto mb-4 text-gray-300"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
            />
          </svg>
          <p>Slide preview will appear here</p>
          <p className="text-sm mt-1">
            Generation complete - rendering preview...
          </p>
        </div>
      </div>

      {/* Variations */}
      <div className="mt-6">
        <h3 className="text-sm font-medium text-gray-700 mb-3">Variations</h3>
        <div className="grid grid-cols-4 gap-3">
          {[1, 2, 3, 4].map((i) => (
            <div
              key={i}
              className="aspect-video bg-gray-100 rounded-lg border-2 border-transparent hover:border-primary-500 cursor-pointer transition-colors"
            />
          ))}
        </div>
      </div>
    </div>
  )
}
