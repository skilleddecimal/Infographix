import { useMemo } from 'react'
import { Spinner } from '../ui'

interface PreviewCanvasProps {
  dsl: object | null
  isLoading?: boolean
  error?: string | null
}

export function PreviewCanvas({ dsl, isLoading, error }: PreviewCanvasProps) {
  // Generate SVG from DSL
  const svgContent = useMemo(() => {
    if (!dsl || typeof dsl !== 'object') return null

    const scene = dsl as {
      canvas?: { width?: number; height?: number; background?: string }
      shapes?: Array<{
        id: string
        bbox?: { x: number; y: number; width: number; height: number }
        fill?: { color?: string; transparency?: number }
        text?: { content?: string; runs?: Array<{ text: string }> }
        auto_shape_type?: string
        type?: string
      }>
      theme?: Record<string, string>
    }

    const canvas = scene.canvas || { width: 960, height: 540, background: '#FFFFFF' }
    const shapes = scene.shapes || []
    const theme = scene.theme || {}

    // Calculate proportional sizes based on canvas dimensions
    // EMU coordinates are typically ~12 million, standard is ~960
    const scaleFactor = Math.max(canvas.width, canvas.height) / 1000
    const baseFontSize = 14 * scaleFactor
    const baseCornerRadius = 4 * scaleFactor

    const resolveColor = (color: string | undefined): string => {
      if (!color) return '#0D9488'
      if (color.startsWith('#')) return color
      if (color.startsWith('accent')) return theme[color] || '#0D9488'
      return color
    }

    return (
      <svg
        viewBox={`0 0 ${canvas.width} ${canvas.height}`}
        className="w-full h-full"
        style={{ background: canvas.background }}
      >
        {shapes.map((shape) => {
          const bbox = shape.bbox || { x: 0, y: 0, width: 100, height: 50 }
          const fillColor = resolveColor(shape.fill?.color)
          const opacity = shape.fill?.transparency ? 1 - shape.fill.transparency : 1
          const textContent = shape.text?.content || shape.text?.runs?.[0]?.text || ''
          const shapeType = shape.auto_shape_type || 'rect'

          // Render shape based on type
          const renderShape = () => {
            switch (shapeType) {
              case 'ellipse':
                return (
                  <ellipse
                    cx={bbox.x + bbox.width / 2}
                    cy={bbox.y + bbox.height / 2}
                    rx={bbox.width / 2}
                    ry={bbox.height / 2}
                    fill={fillColor}
                    fillOpacity={opacity}
                  />
                )
              case 'roundRect':
                return (
                  <rect
                    x={bbox.x}
                    y={bbox.y}
                    width={bbox.width}
                    height={bbox.height}
                    fill={fillColor}
                    fillOpacity={opacity}
                    rx={Math.min(bbox.width, bbox.height) * 0.08}
                  />
                )
              case 'trapezoid':
                // Render as polygon for funnel-like shapes
                const topInset = bbox.width * 0.1
                return (
                  <polygon
                    points={`${bbox.x + topInset},${bbox.y} ${bbox.x + bbox.width - topInset},${bbox.y} ${bbox.x + bbox.width},${bbox.y + bbox.height} ${bbox.x},${bbox.y + bbox.height}`}
                    fill={fillColor}
                    fillOpacity={opacity}
                  />
                )
              default:
                return (
                  <rect
                    x={bbox.x}
                    y={bbox.y}
                    width={bbox.width}
                    height={bbox.height}
                    fill={fillColor}
                    fillOpacity={opacity}
                    rx={baseCornerRadius}
                  />
                )
            }
          }

          return (
            <g key={shape.id}>
              {renderShape()}
              {textContent && (
                <text
                  x={bbox.x + bbox.width / 2}
                  y={bbox.y + bbox.height / 2}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fill="white"
                  fontSize={baseFontSize}
                  fontFamily="Inter, sans-serif"
                  fontWeight={500}
                >
                  {textContent}
                </text>
              )}
            </g>
          )
        })}
      </svg>
    )
  }, [dsl])

  if (error) {
    return (
      <div className="flex items-center justify-center h-full min-h-[300px] bg-error-50 rounded-xl border border-error-200">
        <div className="text-center">
          <svg
            className="w-12 h-12 mx-auto text-error-500 mb-3"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
            />
          </svg>
          <p className="text-error-700 font-medium">Generation Failed</p>
          <p className="text-error-600 text-sm mt-1">{error}</p>
        </div>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full min-h-[300px] bg-gray-50 rounded-xl border border-gray-200">
        <div className="text-center">
          <Spinner size="lg" className="mx-auto mb-3" />
          <p className="text-gray-600 font-medium">Generating your infographic...</p>
          <p className="text-gray-500 text-sm mt-1">This may take a few moments</p>
        </div>
      </div>
    )
  }

  if (!dsl) {
    return (
      <div className="flex items-center justify-center h-full min-h-[300px] bg-gray-50 rounded-xl border border-dashed border-gray-300">
        <div className="text-center">
          <svg
            className="w-12 h-12 mx-auto text-gray-400 mb-3"
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
          <p className="text-gray-600 font-medium">Preview will appear here</p>
          <p className="text-gray-500 text-sm mt-1">
            Enter a prompt and click Generate to start
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="relative bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className="aspect-video">{svgContent}</div>
    </div>
  )
}
