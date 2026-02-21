import { clsx } from 'clsx'

interface VariationGridProps {
  variations: object[]
  selectedIndex: number
  onSelect: (index: number) => void
  disabled?: boolean
}

export function VariationGrid({
  variations,
  selectedIndex,
  onSelect,
  disabled,
}: VariationGridProps) {
  if (variations.length === 0) {
    return null
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <label className="text-sm font-medium text-gray-700">
          Variations ({variations.length})
        </label>
        <span className="text-xs text-gray-500">
          Click to preview different styles
        </span>
      </div>
      <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 gap-3">
        {variations.map((variation, index) => {
          // Simple thumbnail render
          const scene = variation as {
            shapes?: Array<{
              id: string
              bbox?: { x: number; y: number; width: number; height: number }
              fill?: { color?: string }
            }>
            theme?: Record<string, string>
          }
          const shapes = scene.shapes || []
          const theme = scene.theme || {}

          const resolveColor = (color: string | undefined): string => {
            if (!color) return '#0D9488'
            if (color.startsWith('#')) return color
            if (color.startsWith('accent')) return theme[color] || '#0D9488'
            return color
          }

          return (
            <button
              key={index}
              onClick={() => onSelect(index)}
              disabled={disabled}
              className={clsx(
                'relative aspect-video rounded-lg border-2 overflow-hidden transition-all',
                selectedIndex === index
                  ? 'border-primary-500 ring-2 ring-primary-500/20'
                  : 'border-gray-200 hover:border-gray-300',
                disabled && 'opacity-50 cursor-not-allowed'
              )}
            >
              <svg viewBox="0 0 160 90" className="w-full h-full bg-white">
                {shapes.slice(0, 5).map((shape, i) => {
                  const bbox = shape.bbox || { x: 0, y: 0, width: 30, height: 20 }
                  // Scale down for thumbnail
                  const scale = 160 / 960
                  return (
                    <rect
                      key={i}
                      x={bbox.x * scale}
                      y={bbox.y * scale}
                      width={bbox.width * scale}
                      height={bbox.height * scale}
                      fill={resolveColor(shape.fill?.color)}
                      rx={2}
                    />
                  )
                })}
              </svg>
              {selectedIndex === index && (
                <div className="absolute top-1 right-1 w-5 h-5 bg-primary-500 rounded-full flex items-center justify-center">
                  <svg
                    className="w-3 h-3 text-white"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={3}
                      d="M5 13l4 4L19 7"
                    />
                  </svg>
                </div>
              )}
              <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/50 to-transparent p-1">
                <span className="text-xs text-white font-medium">#{index + 1}</span>
              </div>
            </button>
          )
        })}
      </div>
    </div>
  )
}
