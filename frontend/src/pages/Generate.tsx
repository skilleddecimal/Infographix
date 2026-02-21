import { useState } from 'react'
import { Layout } from '../components/layout'
import { Card } from '../components/ui'
import {
  PromptInput,
  ArchetypeSelector,
  PreviewCanvas,
  VariationGrid,
  DownloadPanel,
} from '../components/generate'
import { useGeneration } from '../hooks'
import { useAuth } from '../hooks'

export function Generate() {
  const { user, isAuthenticated } = useAuth()
  const {
    currentGeneration,
    selectedVariation,
    isGenerating,
    error,
    generate,
    setSelectedVariation,
  } = useGeneration()

  const [selectedArchetype, setSelectedArchetype] = useState<string | null>(null)

  const handleGenerate = async (prompt: string) => {
    await generate({
      prompt,
      num_variations: 3,
    })
  }

  const currentDsl =
    currentGeneration?.variations && currentGeneration.variations.length > 0
      ? currentGeneration.variations[selectedVariation]
      : currentGeneration?.dsl ?? null

  const hasNoCredits = Boolean(user && user.creditsRemaining <= 0)

  return (
    <Layout hideFooter>
      <div className="container mx-auto px-4 py-8">
        <div className="grid lg:grid-cols-2 gap-8">
          {/* Left Column - Input */}
          <div className="space-y-6">
            {/* Header */}
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                Generate Infographic
              </h1>
              <p className="text-gray-600 mt-1">
                Describe what you want and let AI create it for you
              </p>
            </div>

            {/* Credits warning */}
            {hasNoCredits && (
              <Card className="bg-warning-50 border-warning-200">
                <div className="flex items-start gap-3">
                  <svg
                    className="w-5 h-5 text-warning-600 flex-shrink-0 mt-0.5"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path
                      fillRule="evenodd"
                      d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                      clipRule="evenodd"
                    />
                  </svg>
                  <div>
                    <p className="font-medium text-warning-800">
                      You've used all your credits
                    </p>
                    <p className="text-sm text-warning-700 mt-1">
                      Upgrade to Pro for 200 generations per month.
                    </p>
                  </div>
                </div>
              </Card>
            )}

            {/* Prompt Input */}
            <Card>
              <PromptInput
                onGenerate={handleGenerate}
                isGenerating={isGenerating}
                disabled={!isAuthenticated || hasNoCredits}
              />
            </Card>

            {/* Archetype Selector */}
            <Card>
              <ArchetypeSelector
                selected={selectedArchetype}
                onSelect={setSelectedArchetype}
                disabled={isGenerating}
              />
            </Card>

            {/* Status */}
            {currentGeneration && (
              <Card>
                <div className="flex items-center gap-3">
                  <div
                    className={`w-2 h-2 rounded-full ${
                      currentGeneration.status === 'completed'
                        ? 'bg-success-500'
                        : currentGeneration.status === 'failed'
                        ? 'bg-error-500'
                        : 'bg-warning-500 animate-pulse'
                    }`}
                  />
                  <div>
                    <p className="text-sm font-medium text-gray-900">
                      {currentGeneration.status === 'completed'
                        ? 'Generation Complete'
                        : currentGeneration.status === 'failed'
                        ? 'Generation Failed'
                        : 'Generating...'}
                    </p>
                    {currentGeneration.archetype && (
                      <p className="text-sm text-gray-500">
                        Type: {currentGeneration.archetype}
                      </p>
                    )}
                  </div>
                </div>
              </Card>
            )}
          </div>

          {/* Right Column - Preview */}
          <div className="space-y-6">
            {/* Preview */}
            <Card padding="none" className="overflow-hidden">
              <PreviewCanvas
                dsl={currentDsl}
                isLoading={isGenerating}
                error={error}
              />
            </Card>

            {/* Variations */}
            {currentGeneration?.variations &&
              currentGeneration.variations.length > 0 && (
                <Card>
                  <VariationGrid
                    variations={currentGeneration.variations}
                    selectedIndex={selectedVariation}
                    onSelect={setSelectedVariation}
                  />
                </Card>
              )}

            {/* Download */}
            {currentGeneration?.status === 'completed' && currentGeneration.id && (
              <Card>
                <DownloadPanel
                  generationId={currentGeneration.id}
                  variationIndex={
                    currentGeneration.variations ? selectedVariation : undefined
                  }
                />
              </Card>
            )}
          </div>
        </div>
      </div>
    </Layout>
  )
}
