import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '../../test/utils'
import userEvent from '@testing-library/user-event'
import { Input } from './Input'

describe('Input', () => {
  it('renders correctly', () => {
    render(<Input placeholder="Enter text" />)
    expect(screen.getByPlaceholderText('Enter text')).toBeInTheDocument()
  })

  it('renders with label', () => {
    render(<Input label="Email" placeholder="Enter email" />)
    expect(screen.getByLabelText('Email')).toBeInTheDocument()
  })

  it('handles value changes', async () => {
    const user = userEvent.setup()
    const handleChange = vi.fn()
    render(<Input onChange={handleChange} placeholder="Type here" />)

    const input = screen.getByPlaceholderText('Type here')
    await user.type(input, 'hello')
    expect(handleChange).toHaveBeenCalled()
  })

  it('shows error message', () => {
    render(<Input error="This field is required" />)
    expect(screen.getByText('This field is required')).toBeInTheDocument()
  })

  it('applies error styling', () => {
    render(<Input error="Invalid" data-testid="input" />)
    const input = screen.getByTestId('input')
    expect(input).toHaveClass('border-error-500')
  })

  it('shows helper text', () => {
    render(<Input helperText="Enter a valid email address" />)
    expect(screen.getByText('Enter a valid email address')).toBeInTheDocument()
  })

  it('error takes precedence over helper text', () => {
    render(
      <Input
        error="Error message"
        helperText="Helper text"
      />
    )
    expect(screen.getByText('Error message')).toBeInTheDocument()
    expect(screen.queryByText('Helper text')).not.toBeInTheDocument()
  })

  it('renders with left icon', () => {
    render(
      <Input
        leftIcon={<span data-testid="left-icon">@</span>}
        placeholder="Email"
      />
    )
    expect(screen.getByTestId('left-icon')).toBeInTheDocument()
  })

  it('renders with right icon', () => {
    render(
      <Input
        rightIcon={<span data-testid="right-icon">✓</span>}
        placeholder="Input"
      />
    )
    expect(screen.getByTestId('right-icon')).toBeInTheDocument()
  })

  it('is disabled when disabled prop is true', () => {
    render(<Input disabled placeholder="Disabled" />)
    expect(screen.getByPlaceholderText('Disabled')).toBeDisabled()
  })

  it('generates id from label', () => {
    render(<Input label="User Name" />)
    expect(screen.getByLabelText('User Name')).toHaveAttribute('id', 'user-name')
  })

  it('uses provided id over generated one', () => {
    render(<Input label="Email" id="custom-id" />)
    expect(screen.getByLabelText('Email')).toHaveAttribute('id', 'custom-id')
  })

  it('applies custom className', () => {
    render(<Input className="custom-class" data-testid="input" />)
    expect(screen.getByTestId('input')).toHaveClass('custom-class')
  })
})
