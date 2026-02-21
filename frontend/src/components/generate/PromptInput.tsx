import { useState, KeyboardEvent } from 'react'
import { Button } from '../ui'

interface PromptInputProps {
  onGenerate: (prompt: string) => void
  isGenerating: boolean
  disabled?: boolean
}

const examplePrompts = [
  'Create a 5-stage sales funnel showing awareness to purchase',
  'Design a 4-step onboarding process with icons',
  'Show a 3-tier priority pyramid',
  'Make a timeline of Q1-Q4 milestones',
  'Create a comparison chart: Plan A vs Plan B',
]

export function PromptInput({
  onGenerate,
  isGenerating,
  disabled,
}: PromptInputProps) {
  const [prompt, setPrompt] = useState('')

  const handleSubmit = () => {
    if (prompt.trim() && !isGenerating && !disabled) {
      onGenerate(prompt.trim())
    }
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  return (
    <div className="space-y-4">
      {/* Main input */}
      <div className="relative">
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Describe the infographic you want to create..."
          rows={3}
          disabled={isGenerating || disabled}
          className="w-full px-4 py-3 pr-24 text-gray-900 placeholder-gray-400 bg-white border border-gray-300 rounded-xl resize-none focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 disabled:bg-gray-50 disabled:cursor-not-allowed transition-colors"
        />
        <div className="absolute right-3 bottom-3">
          <Button
            onClick={handleSubmit}
            disabled={!prompt.trim() || isGenerating || disabled}
            isLoading={isGenerating}
            size="sm"
          >
            Generate
          </Button>
        </div>
      </div>

      {/* Example prompts */}
      <div>
        <p className="text-sm text-gray-500 mb-2">Try an example:</p>
        <div className="flex flex-wrap gap-2">
          {examplePrompts.map((example) => (
            <button
              key={example}
              onClick={() => setPrompt(example)}
              disabled={isGenerating || disabled}
              className="px-3 py-1.5 text-sm text-gray-600 bg-gray-100 hover:bg-gray-200 rounded-full transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {example.length > 40 ? example.slice(0, 40) + '...' : example}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
