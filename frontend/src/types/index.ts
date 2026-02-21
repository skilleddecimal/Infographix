// Shape types matching backend DSL schema

export type ShapeType = 'autoShape' | 'freeform' | 'text' | 'image' | 'group' | 'connector'

export interface BoundingBox {
  x: number
  y: number
  width: number
  height: number
}

export interface Transform {
  rotation: number
  flipH: boolean
  flipV: boolean
  scaleX: number
  scaleY: number
}

export interface SolidFill {
  type: 'solid'
  color: string
  alpha: number
}

export interface GradientStop {
  position: number
  color: string
  alpha: number
}

export interface GradientFill {
  type: 'gradient'
  gradientType: 'linear' | 'radial' | 'path'
  angle: number
  stops: GradientStop[]
}

export interface NoFill {
  type: 'none'
}

export type Fill = SolidFill | GradientFill | NoFill

export interface Stroke {
  color: string
  width: number
  alpha: number
  dashStyle: 'solid' | 'dash' | 'dot' | 'dashDot' | 'longDash'
}

export interface Shadow {
  type: 'outer' | 'inner'
  color: string
  alpha: number
  blurRadius: number
  distance: number
  angle: number
}

export interface Effects {
  shadow?: Shadow
}

export interface TextRun {
  text: string
  fontFamily: string
  fontSize: number
  bold: boolean
  italic: boolean
  underline: boolean
  color: string
}

export interface TextContent {
  runs: TextRun[]
  alignment: 'left' | 'center' | 'right' | 'justify'
  verticalAlignment: 'top' | 'middle' | 'bottom'
}

export interface Shape {
  id: string
  type: ShapeType
  name?: string
  groupPath: string[]
  zIndex: number
  bbox: BoundingBox
  transform: Transform
  autoShapeType?: string
  fill: Fill
  stroke?: Stroke
  effects: Effects
  text?: TextContent
  children?: Shape[]
}

export interface Canvas {
  width: number
  height: number
  background: Fill
}

export interface ThemeColors {
  dark1: string
  light1: string
  dark2: string
  light2: string
  accent1: string
  accent2: string
  accent3: string
  accent4: string
  accent5: string
  accent6: string
}

export interface SlideMetadata {
  title?: string
  slideNumber: number
  layoutName?: string
  archetype?: string
  tags: string[]
}

export interface SlideScene {
  canvas: Canvas
  shapes: Shape[]
  theme: ThemeColors
  metadata: SlideMetadata
}
