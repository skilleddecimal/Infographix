interface PromptInputProps {
  value: string
  onChange: (value: string) => void
  onGenerate: () => void
  isGenerating: boolean
}

export function PromptInput({
  value,
  onChange,
  onGenerate,
  isGenerating,
}: PromptInputProps) {
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      onGenerate()
    }
  }

  return (
    <div className="bg-white rounded-2xl shadow-lg border border-gray-200 p-2">
      <div className="flex items-start gap-3">
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Describe the infographic you want to create..."
          className="flex-1 min-h-[80px] p-3 text-gray-900 placeholder-gray-400 resize-none focus:outline-none"
          disabled={isGenerating}
        />
        <button
          onClick={onGenerate}
          disabled={isGenerating || !value.trim()}
          className="px-6 py-3 bg-primary-600 hover:bg-primary-700 disabled:bg-gray-300 disabled:cursor-not-allowed text-white rounded-xl font-medium transition-colors flex items-center gap-2"
        >
          {isGenerating ? (
            <>
              <svg
                className="animate-spin h-5 w-5"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
              Generating...
            </>
          ) : (
            <>
              <svg
                className="w-5 h-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M13 10V3L4 14h7v7l9-11h-7z"
                />
              </svg>
              Generate
            </>
          )}
        </button>
      </div>
    </div>
  )
}
