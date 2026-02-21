import { describe, it, expect } from 'vitest'
import { render, screen } from '../../test/utils'
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from './Card'

describe('Card', () => {
  it('renders children correctly', () => {
    render(<Card>Card content</Card>)
    expect(screen.getByText('Card content')).toBeInTheDocument()
  })

  it('renders with default variant', () => {
    render(<Card data-testid="card">Content</Card>)
    const card = screen.getByTestId('card')
    expect(card).toHaveClass('bg-white', 'border', 'border-gray-200')
  })

  it('renders with bordered variant', () => {
    render(<Card variant="bordered" data-testid="card">Content</Card>)
    const card = screen.getByTestId('card')
    expect(card).toHaveClass('border-2')
  })

  it('renders with elevated variant', () => {
    render(<Card variant="elevated" data-testid="card">Content</Card>)
    const card = screen.getByTestId('card')
    expect(card).toHaveClass('shadow-soft')
  })

  it('renders with different padding sizes', () => {
    const { rerender } = render(
      <Card padding="none" data-testid="card">Content</Card>
    )
    expect(screen.getByTestId('card')).not.toHaveClass('p-4', 'p-6', 'p-8')

    rerender(<Card padding="sm" data-testid="card">Content</Card>)
    expect(screen.getByTestId('card')).toHaveClass('p-4')

    rerender(<Card padding="md" data-testid="card">Content</Card>)
    expect(screen.getByTestId('card')).toHaveClass('p-6')

    rerender(<Card padding="lg" data-testid="card">Content</Card>)
    expect(screen.getByTestId('card')).toHaveClass('p-8')
  })

  it('renders with interactive styles', () => {
    render(<Card interactive data-testid="card">Content</Card>)
    const card = screen.getByTestId('card')
    expect(card).toHaveClass('cursor-pointer')
  })

  it('applies custom className', () => {
    render(<Card className="custom-class" data-testid="card">Content</Card>)
    expect(screen.getByTestId('card')).toHaveClass('custom-class')
  })
})

describe('CardHeader', () => {
  it('renders children correctly', () => {
    render(<CardHeader>Header content</CardHeader>)
    expect(screen.getByText('Header content')).toBeInTheDocument()
  })

  it('applies margin bottom', () => {
    render(<CardHeader data-testid="header">Header</CardHeader>)
    expect(screen.getByTestId('header')).toHaveClass('mb-4')
  })
})

describe('CardTitle', () => {
  it('renders as h3', () => {
    render(<CardTitle>Title</CardTitle>)
    expect(screen.getByRole('heading', { level: 3 })).toHaveTextContent('Title')
  })

  it('applies title styles', () => {
    render(<CardTitle data-testid="title">Title</CardTitle>)
    expect(screen.getByTestId('title')).toHaveClass('text-lg', 'font-semibold')
  })
})

describe('CardDescription', () => {
  it('renders correctly', () => {
    render(<CardDescription>Description text</CardDescription>)
    expect(screen.getByText('Description text')).toBeInTheDocument()
  })

  it('applies description styles', () => {
    render(<CardDescription data-testid="desc">Description</CardDescription>)
    expect(screen.getByTestId('desc')).toHaveClass('text-sm', 'text-gray-500')
  })
})

describe('CardContent', () => {
  it('renders children correctly', () => {
    render(<CardContent>Content here</CardContent>)
    expect(screen.getByText('Content here')).toBeInTheDocument()
  })
})

describe('CardFooter', () => {
  it('renders children correctly', () => {
    render(<CardFooter>Footer content</CardFooter>)
    expect(screen.getByText('Footer content')).toBeInTheDocument()
  })

  it('applies footer styles', () => {
    render(<CardFooter data-testid="footer">Footer</CardFooter>)
    expect(screen.getByTestId('footer')).toHaveClass('mt-4', 'pt-4', 'border-t')
  })
})

describe('Card composition', () => {
  it('renders full card structure', () => {
    render(
      <Card data-testid="card">
        <CardHeader>
          <CardTitle>Card Title</CardTitle>
          <CardDescription>Card description</CardDescription>
        </CardHeader>
        <CardContent>Main content</CardContent>
        <CardFooter>Footer actions</CardFooter>
      </Card>
    )

    expect(screen.getByTestId('card')).toBeInTheDocument()
    expect(screen.getByText('Card Title')).toBeInTheDocument()
    expect(screen.getByText('Card description')).toBeInTheDocument()
    expect(screen.getByText('Main content')).toBeInTheDocument()
    expect(screen.getByText('Footer actions')).toBeInTheDocument()
  })
})
