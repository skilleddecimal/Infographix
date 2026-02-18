import { useState, useEffect, useCallback } from 'react';
import { Brief, previewDiagram } from '../api';

interface DiagramPreviewProps {
  brief: Brief;
  brandPreset?: string;
  onError?: (error: string) => void;
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    position: 'relative' as const,
    width: '100%',
    marginTop: '1rem',
  },
  previewWrapper: {
    border: '1px solid #e5e7eb',
    borderRadius: '8px',
    overflow: 'hidden',
    background: '#f9fafb',
  },
  svgContainer: {
    width: '100%',
    maxHeight: '400px',
    overflow: 'auto',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'flex-start',
    padding: '1rem',
  },
  loadingContainer: {
    display: 'flex',
    flexDirection: 'column' as const,
    alignItems: 'center',
    justifyContent: 'center',
    padding: '3rem',
    color: '#6b7280',
  },
  spinner: {
    width: '32px',
    height: '32px',
    border: '3px solid #e5e7eb',
    borderTopColor: '#0073E6',
    borderRadius: '50%',
    animation: 'spin 1s linear infinite',
  },
  loadingText: {
    marginTop: '0.75rem',
    fontSize: '0.875rem',
  },
  errorContainer: {
    padding: '2rem',
    textAlign: 'center' as const,
    color: '#dc2626',
  },
  refreshButton: {
    marginTop: '1rem',
    padding: '0.5rem 1rem',
    background: '#f3f4f6',
    border: '1px solid #d1d5db',
    borderRadius: '6px',
    cursor: 'pointer',
    fontSize: '0.875rem',
  },
  toolbar: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '0.5rem 1rem',
    borderBottom: '1px solid #e5e7eb',
    background: '#f9fafb',
    fontSize: '0.875rem',
    color: '#6b7280',
  },
  zoomControls: {
    display: 'flex',
    gap: '0.5rem',
    alignItems: 'center',
  },
  zoomButton: {
    padding: '0.25rem 0.5rem',
    background: 'white',
    border: '1px solid #d1d5db',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '0.75rem',
  },
  zoomLabel: {
    minWidth: '3rem',
    textAlign: 'center' as const,
  },
};

export default function DiagramPreview({ brief, brandPreset, onError }: DiagramPreviewProps) {
  const [svgContent, setSvgContent] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });
  const [zoom, setZoom] = useState(100);

  const fetchPreview = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await previewDiagram(brief, undefined, brandPreset, 'svg');

      if (response.success && response.svg) {
        setSvgContent(response.svg);
        setDimensions({
          width: response.width || 0,
          height: response.height || 0,
        });
      } else {
        const errorMsg = response.error || 'Failed to generate preview';
        setError(errorMsg);
        onError?.(errorMsg);
      }
    } catch (err: unknown) {
      const errorMsg = err instanceof Error ? err.message : 'Preview generation failed';
      setError(errorMsg);
      onError?.(errorMsg);
    } finally {
      setLoading(false);
    }
  }, [brief, brandPreset, onError]);

  useEffect(() => {
    // Debounce preview generation
    const timer = setTimeout(() => {
      if (brief.entities.length > 0) {
        fetchPreview();
      }
    }, 500);

    return () => clearTimeout(timer);
  }, [brief, brandPreset, fetchPreview]);

  const handleZoomIn = () => setZoom(prev => Math.min(200, prev + 25));
  const handleZoomOut = () => setZoom(prev => Math.max(25, prev - 25));
  const handleZoomReset = () => setZoom(100);

  if (loading) {
    return (
      <div style={styles.container}>
        <div style={styles.previewWrapper}>
          <div style={styles.loadingContainer}>
            <div style={styles.spinner} />
            <div style={styles.loadingText}>Generating preview...</div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={styles.container}>
        <div style={styles.previewWrapper}>
          <div style={styles.errorContainer}>
            <div>Preview Error: {error}</div>
            <button style={styles.refreshButton} onClick={fetchPreview}>
              Try Again
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!svgContent) {
    return (
      <div style={styles.container}>
        <div style={styles.previewWrapper}>
          <div style={styles.loadingContainer}>
            <div style={styles.loadingText}>Add entities to see preview</div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <div style={styles.previewWrapper}>
        <div style={styles.toolbar}>
          <span>
            Preview ({dimensions.width} x {dimensions.height}px)
          </span>
          <div style={styles.zoomControls}>
            <button style={styles.zoomButton} onClick={handleZoomOut}>-</button>
            <span style={styles.zoomLabel}>{zoom}%</span>
            <button style={styles.zoomButton} onClick={handleZoomIn}>+</button>
            <button style={styles.zoomButton} onClick={handleZoomReset}>Reset</button>
          </div>
        </div>
        <div style={styles.svgContainer}>
          <div
            style={{
              transform: `scale(${zoom / 100})`,
              transformOrigin: 'top center',
            }}
            dangerouslySetInnerHTML={{ __html: svgContent }}
          />
        </div>
      </div>
    </div>
  );
}
