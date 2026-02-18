import { useState, useEffect, useCallback } from 'react';
import { analyzePrompt, generateDiagram, getBrandPresets, Brief, BrandPreset } from './api';
import PromptInput from './components/PromptInput';
import BriefReview from './components/BriefReview';
import DownloadButton from './components/DownloadButton';

type AppState = 'input' | 'analyzing' | 'reviewing' | 'generating' | 'ready';

interface ErrorInfo {
  message: string;
  type: 'api' | 'network' | 'validation' | 'unknown';
  retryable: boolean;
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    maxWidth: '900px',
    margin: '0 auto',
    padding: '2rem',
    minHeight: '100vh',
  },
  header: {
    textAlign: 'center' as const,
    marginBottom: '2rem',
  },
  title: {
    fontSize: '2.5rem',
    fontWeight: 700,
    color: '#1a1a2e',
    marginBottom: '0.5rem',
  },
  subtitle: {
    fontSize: '1.1rem',
    color: '#666',
  },
  card: {
    background: 'white',
    borderRadius: '12px',
    padding: '2rem',
    boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)',
    marginBottom: '1.5rem',
    position: 'relative' as const,
  },
  errorContainer: {
    background: '#fef2f2',
    border: '1px solid #fecaca',
    borderRadius: '8px',
    padding: '1rem',
    marginBottom: '1rem',
    display: 'flex',
    alignItems: 'flex-start',
    gap: '0.75rem',
  },
  errorIcon: {
    fontSize: '1.25rem',
    flexShrink: 0,
  },
  errorContent: {
    flex: 1,
  },
  errorTitle: {
    fontWeight: 600,
    color: '#dc2626',
    marginBottom: '0.25rem',
  },
  errorMessage: {
    color: '#b91c1c',
    fontSize: '0.9rem',
  },
  errorActions: {
    display: 'flex',
    gap: '0.5rem',
    marginTop: '0.75rem',
  },
  errorButton: {
    padding: '0.375rem 0.75rem',
    borderRadius: '6px',
    border: 'none',
    fontSize: '0.85rem',
    cursor: 'pointer',
    fontWeight: 500,
  },
  retryButton: {
    background: '#dc2626',
    color: 'white',
  },
  dismissButton: {
    background: '#fecaca',
    color: '#991b1b',
  },
  warning: {
    background: '#fffbeb',
    border: '1px solid #fde68a',
    borderRadius: '8px',
    padding: '1rem',
    color: '#92400e',
    marginBottom: '1rem',
  },
  loadingOverlay: {
    position: 'absolute' as const,
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    background: 'rgba(255, 255, 255, 0.9)',
    borderRadius: '12px',
    display: 'flex',
    flexDirection: 'column' as const,
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 10,
  },
  spinner: {
    width: '48px',
    height: '48px',
    border: '4px solid #e5e7eb',
    borderTopColor: '#0073E6',
    borderRadius: '50%',
    animation: 'spin 1s linear infinite',
  },
  loadingText: {
    marginTop: '1rem',
    color: '#4b5563',
    fontWeight: 500,
  },
  loadingSubtext: {
    marginTop: '0.25rem',
    color: '#9ca3af',
    fontSize: '0.875rem',
  },
  footer: {
    textAlign: 'center' as const,
    marginTop: '2rem',
    color: '#999',
    fontSize: '0.9rem',
  },
};

// Add keyframes for spinner animation
const spinnerKeyframes = `
  @keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }
`;

function parseError(err: unknown): ErrorInfo {
  if (err instanceof Error) {
    const message = err.message;

    // Network errors
    if (message.includes('Network Error') || message.includes('fetch')) {
      return {
        message: 'Unable to connect to the server. Please check your connection.',
        type: 'network',
        retryable: true,
      };
    }

    // API errors
    if (message.includes('credit balance') || message.includes('API key')) {
      return {
        message: 'API configuration issue. Please check your Anthropic API key and credits.',
        type: 'api',
        retryable: false,
      };
    }

    if (message.includes('rate limit') || message.includes('429')) {
      return {
        message: 'Rate limit exceeded. Please wait a moment and try again.',
        type: 'api',
        retryable: true,
      };
    }

    // Validation errors
    if (message.includes('validation') || message.includes('invalid')) {
      return {
        message: message,
        type: 'validation',
        retryable: false,
      };
    }

    return {
      message: message,
      type: 'unknown',
      retryable: true,
    };
  }

  return {
    message: 'An unexpected error occurred. Please try again.',
    type: 'unknown',
    retryable: true,
  };
}

function LoadingOverlay({ state }: { state: AppState }) {
  const messages: Record<string, { title: string; subtitle: string }> = {
    analyzing: {
      title: 'Analyzing your prompt...',
      subtitle: 'Claude is parsing your diagram requirements',
    },
    generating: {
      title: 'Generating your diagram...',
      subtitle: 'Creating PowerPoint with precise layouts',
    },
  };

  const msg = messages[state];
  if (!msg) return null;

  return (
    <div style={styles.loadingOverlay}>
      <div style={styles.spinner} />
      <div style={styles.loadingText}>{msg.title}</div>
      <div style={styles.loadingSubtext}>{msg.subtitle}</div>
    </div>
  );
}

function ErrorDisplay({
  error,
  onRetry,
  onDismiss
}: {
  error: ErrorInfo;
  onRetry?: () => void;
  onDismiss: () => void;
}) {
  const errorTitles: Record<ErrorInfo['type'], string> = {
    api: 'API Error',
    network: 'Connection Error',
    validation: 'Validation Error',
    unknown: 'Error',
  };

  return (
    <div style={styles.errorContainer}>
      <span style={styles.errorIcon}>&#9888;</span>
      <div style={styles.errorContent}>
        <div style={styles.errorTitle}>{errorTitles[error.type]}</div>
        <div style={styles.errorMessage}>{error.message}</div>
        <div style={styles.errorActions}>
          {error.retryable && onRetry && (
            <button
              style={{ ...styles.errorButton, ...styles.retryButton }}
              onClick={onRetry}
            >
              Try Again
            </button>
          )}
          <button
            style={{ ...styles.errorButton, ...styles.dismissButton }}
            onClick={onDismiss}
          >
            Dismiss
          </button>
        </div>
      </div>
    </div>
  );
}

function App() {
  const [state, setState] = useState<AppState>('input');
  const [prompt, setPrompt] = useState('');
  const [brief, setBrief] = useState<Brief | null>(null);
  const [fileId, setFileId] = useState<string | null>(null);
  const [brandPresets, setBrandPresets] = useState<BrandPreset[]>([]);
  const [selectedBrand, setSelectedBrand] = useState<string>('');
  const [error, setError] = useState<ErrorInfo | null>(null);
  const [warnings, setWarnings] = useState<string[]>([]);

  const loading = state === 'analyzing' || state === 'generating';

  useEffect(() => {
    // Inject spinner keyframes
    const styleSheet = document.createElement('style');
    styleSheet.textContent = spinnerKeyframes;
    document.head.appendChild(styleSheet);
    return () => {
      document.head.removeChild(styleSheet);
    };
  }, []);

  useEffect(() => {
    // Load brand presets on mount
    getBrandPresets()
      .then(setBrandPresets)
      .catch(err => {
        console.error('Failed to load brand presets:', err);
        // Non-critical error, don't show to user
      });
  }, []);

  const handleAnalyze = useCallback(async () => {
    if (!prompt.trim()) return;

    setState('analyzing');
    setError(null);
    setWarnings([]);

    try {
      const response = await analyzePrompt(prompt);
      if (response.success && response.brief) {
        setBrief(response.brief);
        setWarnings(response.warnings);
        setState('reviewing');
      } else {
        setError(parseError(new Error(response.error || 'Failed to analyze prompt')));
        setState('input');
      }
    } catch (err: unknown) {
      setError(parseError(err));
      setState('input');
    }
  }, [prompt]);

  const handleGenerate = useCallback(async () => {
    if (!brief) return;

    setState('generating');
    setError(null);

    try {
      const response = await generateDiagram(
        brief,
        undefined,
        selectedBrand || undefined
      );
      if (response.success && response.file_id) {
        setFileId(response.file_id);
        setWarnings(response.warnings);
        setState('ready');
      } else {
        setError(parseError(new Error(response.error || 'Failed to generate diagram')));
        setState('reviewing');
      }
    } catch (err: unknown) {
      setError(parseError(err));
      setState('reviewing');
    }
  }, [brief, selectedBrand]);

  const handleReset = useCallback(() => {
    setState('input');
    setBrief(null);
    setFileId(null);
    setError(null);
    setWarnings([]);
    setPrompt('');
  }, []);

  const handleBriefEdit = useCallback((editedBrief: Brief) => {
    setBrief(editedBrief);
  }, []);

  const handleDismissError = useCallback(() => {
    setError(null);
  }, []);

  const handleRetry = useCallback(() => {
    setError(null);
    if (state === 'input' || state === 'analyzing') {
      handleAnalyze();
    } else if (state === 'reviewing' || state === 'generating') {
      handleGenerate();
    }
  }, [state, handleAnalyze, handleGenerate]);

  return (
    <div style={styles.container}>
      <header style={styles.header}>
        <h1 style={styles.title}>InfographAI</h1>
        <p style={styles.subtitle}>AI-powered infographic and diagram generation</p>
      </header>

      {error && (
        <ErrorDisplay
          error={error}
          onRetry={error.retryable ? handleRetry : undefined}
          onDismiss={handleDismissError}
        />
      )}

      {warnings.length > 0 && (
        <div style={styles.warning}>
          <strong>&#9888; Warnings:</strong>
          <ul style={{ marginTop: '0.5rem', marginBottom: 0, paddingLeft: '1.5rem' }}>
            {warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      <div style={styles.card}>
        {loading && <LoadingOverlay state={state} />}

        {(state === 'input' || state === 'analyzing') && (
          <PromptInput
            prompt={prompt}
            onPromptChange={setPrompt}
            onAnalyze={handleAnalyze}
            loading={loading}
            brandPresets={brandPresets}
            selectedBrand={selectedBrand}
            onBrandChange={setSelectedBrand}
          />
        )}

        {(state === 'reviewing' || state === 'generating') && brief && (
          <BriefReview
            brief={brief}
            onEdit={handleBriefEdit}
            onGenerate={handleGenerate}
            onBack={() => setState('input')}
            loading={loading}
            brandPreset={selectedBrand}
          />
        )}

        {state === 'ready' && fileId && (
          <DownloadButton
            fileId={fileId}
            title={brief?.title || 'diagram'}
            onReset={handleReset}
          />
        )}
      </div>

      <footer style={styles.footer}>
        InfographAI v1.0 | Powered by Claude
      </footer>
    </div>
  );
}

export default App;
