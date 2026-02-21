import { clsx } from 'clsx'

interface Archetype {
  id: string
  name: string
  description: string
  icon: string
}

const archetypes: Archetype[] = [
  {
    id: 'funnel',
    name: 'Funnel',
    description: 'Sales funnels, conversion flows',
    icon: 'M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z',
  },
  {
    id: 'timeline',
    name: 'Timeline',
    description: 'Chronological events, roadmaps',
    icon: 'M13 7h8m0 0v8m0-8l-8 8-4-4-6 6',
  },
  {
    id: 'pyramid',
    name: 'Pyramid',
    description: 'Hierarchies, priorities',
    icon: 'M3 21h18M12 3l9 18H3L12 3z',
  },
  {
    id: 'process',
    name: 'Process',
    description: 'Step-by-step workflows',
    icon: 'M13 5l7 7-7 7M5 5l7 7-7 7',
  },
  {
    id: 'cycle',
    name: 'Cycle',
    description: 'Continuous processes, loops',
    icon: 'M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15',
  },
  {
    id: 'comparison',
    name: 'Comparison',
    description: 'Side-by-side comparisons',
    icon: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z',
  },
]

interface ArchetypeSelectorProps {
  selected: string | null
  onSelect: (id: string) => void
  disabled?: boolean
}

export function ArchetypeSelector({
  selected,
  onSelect,
  disabled,
}: ArchetypeSelectorProps) {
  return (
    <div className="space-y-3">
      <label className="block text-sm font-medium text-gray-700">
        Diagram Type (optional)
      </label>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        {archetypes.map((archetype) => (
          <button
            key={archetype.id}
            onClick={() => onSelect(archetype.id)}
            disabled={disabled}
            className={clsx(
              'flex flex-col items-center p-4 rounded-xl border-2 transition-all',
              selected === archetype.id
                ? 'border-primary-500 bg-primary-50'
                : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50',
              disabled && 'opacity-50 cursor-not-allowed'
            )}
          >
            <svg
              className={clsx(
                'w-8 h-8 mb-2',
                selected === archetype.id ? 'text-primary-600' : 'text-gray-400'
              )}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d={archetype.icon}
              />
            </svg>
            <span
              className={clsx(
                'text-sm font-medium',
                selected === archetype.id ? 'text-primary-700' : 'text-gray-700'
              )}
            >
              {archetype.name}
            </span>
            <span className="text-xs text-gray-500 text-center mt-1">
              {archetype.description}
            </span>
          </button>
        ))}
      </div>
    </div>
  )
}
