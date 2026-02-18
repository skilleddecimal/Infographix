import { BrandPreset } from '../api';

interface PromptInputProps {
  prompt: string;
  onPromptChange: (prompt: string) => void;
  onAnalyze: () => void;
  loading: boolean;
  brandPresets: BrandPreset[];
  selectedBrand: string;
  onBrandChange: (brand: string) => void;
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '1.5rem',
  },
  label: {
    display: 'block',
    fontWeight: 600,
    marginBottom: '0.5rem',
    color: '#333',
  },
  textarea: {
    width: '100%',
    padding: '1rem',
    borderRadius: '8px',
    border: '1px solid #ddd',
    fontSize: '1rem',
    fontFamily: 'inherit',
    resize: 'vertical' as const,
    minHeight: '120px',
    transition: 'border-color 0.2s',
  },
  row: {
    display: 'flex',
    gap: '1rem',
    alignItems: 'flex-end',
    flexWrap: 'wrap' as const,
  },
  selectGroup: {
    flex: 1,
    minWidth: '200px',
  },
  select: {
    width: '100%',
    padding: '0.75rem',
    borderRadius: '8px',
    border: '1px solid #ddd',
    fontSize: '1rem',
    fontFamily: 'inherit',
    background: 'white',
    cursor: 'pointer',
  },
  button: {
    padding: '0.75rem 2rem',
    borderRadius: '8px',
    border: 'none',
    background: '#0073E6',
    color: 'white',
    fontSize: '1rem',
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'background 0.2s',
    minWidth: '150px',
  },
  buttonDisabled: {
    background: '#ccc',
    cursor: 'not-allowed',
  },
  examples: {
    fontSize: '0.9rem',
    color: '#666',
  },
  exampleLink: {
    color: '#0073E6',
    cursor: 'pointer',
    textDecoration: 'underline',
  },
  colorPreview: {
    display: 'inline-block',
    width: '16px',
    height: '16px',
    borderRadius: '3px',
    marginRight: '8px',
    verticalAlign: 'middle',
    border: '1px solid #ddd',
  },
};

const examplePrompts = [
  'Create a 3-tier web architecture with React, Node.js API, and PostgreSQL',
  'Build a Marketecture of OpenText Business Units with MyAviator as the AI Layer',
  'Design a microservices architecture with API Gateway, Auth Service, and 3 backend services',
];

function PromptInput({
  prompt,
  onPromptChange,
  onAnalyze,
  loading,
  brandPresets,
  selectedBrand,
  onBrandChange,
}: PromptInputProps) {
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && e.ctrlKey && !loading && prompt.trim()) {
      onAnalyze();
    }
  };

  return (
    <div style={styles.container}>
      <div>
        <label style={styles.label}>Describe your diagram</label>
        <textarea
          style={styles.textarea}
          value={prompt}
          onChange={(e) => onPromptChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="e.g., Create a 3-tier web architecture with React frontend, Node.js API, and PostgreSQL database..."
          disabled={loading}
        />
        <div style={styles.examples}>
          <strong>Examples: </strong>
          {examplePrompts.map((ex, i) => (
            <span key={i}>
              <span
                style={styles.exampleLink}
                onClick={() => onPromptChange(ex)}
              >
                Example {i + 1}
              </span>
              {i < examplePrompts.length - 1 && ' | '}
            </span>
          ))}
        </div>
      </div>

      <div style={styles.row}>
        <div style={styles.selectGroup}>
          <label style={styles.label}>Brand Theme (optional)</label>
          <select
            style={styles.select}
            value={selectedBrand}
            onChange={(e) => onBrandChange(e.target.value)}
            disabled={loading}
          >
            <option value="">Default colors</option>
            {brandPresets.map((preset) => (
              <option key={preset.name} value={preset.name}>
                {preset.name.charAt(0).toUpperCase() + preset.name.slice(1)}
              </option>
            ))}
          </select>
        </div>

        {selectedBrand && brandPresets.find(p => p.name === selectedBrand) && (
          <div style={{ display: 'flex', gap: '4px', alignItems: 'center', paddingBottom: '0.75rem' }}>
            <span
              style={{
                ...styles.colorPreview,
                background: brandPresets.find(p => p.name === selectedBrand)?.primary,
              }}
            />
            <span
              style={{
                ...styles.colorPreview,
                background: brandPresets.find(p => p.name === selectedBrand)?.secondary,
              }}
            />
          </div>
        )}

        <button
          style={{
            ...styles.button,
            ...(loading || !prompt.trim() ? styles.buttonDisabled : {}),
          }}
          onClick={onAnalyze}
          disabled={loading || !prompt.trim()}
        >
          {loading ? 'Analyzing...' : 'Analyze'}
        </button>
      </div>

      <div style={{ fontSize: '0.85rem', color: '#999' }}>
        Tip: Press Ctrl+Enter to analyze
      </div>
    </div>
  );
}

export default PromptInput;
