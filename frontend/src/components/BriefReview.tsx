import { useState } from 'react';
import { Brief } from '../api';
import DiagramPreview from './DiagramPreview';

interface BriefReviewProps {
  brief: Brief;
  onEdit: (brief: Brief) => void;
  onGenerate: () => void;
  onBack: () => void;
  loading: boolean;
  brandPreset?: string;
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '1.5rem',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '1rem',
  },
  title: {
    fontSize: '1.25rem',
    fontWeight: 600,
    color: '#333',
  },
  confidence: {
    fontSize: '0.9rem',
    padding: '0.25rem 0.75rem',
    borderRadius: '12px',
    background: '#e8f5e9',
    color: '#2e7d32',
  },
  section: {
    marginBottom: '1rem',
  },
  sectionTitle: {
    fontSize: '0.9rem',
    fontWeight: 600,
    color: '#666',
    marginBottom: '0.5rem',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.05em',
  },
  input: {
    width: '100%',
    padding: '0.75rem',
    borderRadius: '6px',
    border: '1px solid #ddd',
    fontSize: '1rem',
    fontFamily: 'inherit',
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
    gap: '0.75rem',
  },
  card: {
    padding: '0.75rem',
    borderRadius: '8px',
    background: '#f8f9fa',
    border: '1px solid #e9ecef',
  },
  cardLabel: {
    fontWeight: 600,
    marginBottom: '0.25rem',
  },
  cardMeta: {
    fontSize: '0.85rem',
    color: '#666',
  },
  tag: {
    display: 'inline-block',
    padding: '0.25rem 0.5rem',
    borderRadius: '4px',
    background: '#e3f2fd',
    color: '#1565c0',
    fontSize: '0.8rem',
    marginRight: '0.5rem',
  },
  buttons: {
    display: 'flex',
    gap: '1rem',
    marginTop: '1rem',
  },
  buttonPrimary: {
    padding: '0.75rem 2rem',
    borderRadius: '8px',
    border: 'none',
    background: '#0073E6',
    color: 'white',
    fontSize: '1rem',
    fontWeight: 600,
    cursor: 'pointer',
  },
  buttonSecondary: {
    padding: '0.75rem 2rem',
    borderRadius: '8px',
    border: '1px solid #ddd',
    background: 'white',
    color: '#333',
    fontSize: '1rem',
    fontWeight: 600,
    cursor: 'pointer',
  },
  buttonDisabled: {
    background: '#ccc',
    cursor: 'not-allowed',
  },
};

function BriefReview({ brief, onEdit, onGenerate, onBack, loading, brandPreset }: BriefReviewProps) {
  const [editMode, setEditMode] = useState(false);
  const [editedTitle, setEditedTitle] = useState(brief.title);
  const [editedSubtitle, setEditedSubtitle] = useState(brief.subtitle || '');
  const [showPreview, setShowPreview] = useState(true);

  const handleSaveEdit = () => {
    onEdit({
      ...brief,
      title: editedTitle,
      subtitle: editedSubtitle || undefined,
    });
    setEditMode(false);
  };

  const confidenceColor = brief.confidence >= 0.8 ? '#2e7d32' :
                         brief.confidence >= 0.5 ? '#f57c00' : '#c62828';

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <div>
          <span style={styles.title}>Review Diagram Brief</span>
          <span style={{ ...styles.tag, marginLeft: '1rem' }}>
            {brief.diagram_type}
          </span>
        </div>
        <span style={{ ...styles.confidence, background: `${confidenceColor}20`, color: confidenceColor }}>
          Confidence: {(brief.confidence * 100).toFixed(0)}%
        </span>
      </div>

      <div style={styles.section}>
        <div style={styles.sectionTitle}>Title & Subtitle</div>
        {editMode ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            <input
              style={styles.input}
              value={editedTitle}
              onChange={(e) => setEditedTitle(e.target.value)}
              placeholder="Title"
            />
            <input
              style={styles.input}
              value={editedSubtitle}
              onChange={(e) => setEditedSubtitle(e.target.value)}
              placeholder="Subtitle (optional)"
            />
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <button style={styles.buttonSecondary} onClick={handleSaveEdit}>
                Save
              </button>
              <button style={styles.buttonSecondary} onClick={() => setEditMode(false)}>
                Cancel
              </button>
            </div>
          </div>
        ) : (
          <div>
            <div style={{ fontSize: '1.2rem', fontWeight: 600 }}>{brief.title}</div>
            {brief.subtitle && (
              <div style={{ color: '#666' }}>{brief.subtitle}</div>
            )}
            <button
              style={{ ...styles.buttonSecondary, padding: '0.25rem 0.5rem', fontSize: '0.85rem', marginTop: '0.5rem' }}
              onClick={() => setEditMode(true)}
            >
              Edit
            </button>
          </div>
        )}
      </div>

      <div style={styles.section}>
        <div style={styles.sectionTitle}>
          Entities ({brief.entities.length})
        </div>
        <div style={styles.grid}>
          {brief.entities.map((entity) => (
            <div key={entity.id} style={styles.card}>
              <div style={styles.cardLabel}>{entity.label}</div>
              {entity.layer_id && (
                <div style={styles.cardMeta}>Layer: {entity.layer_id}</div>
              )}
              {entity.description && (
                <div style={styles.cardMeta}>{entity.description}</div>
              )}
            </div>
          ))}
        </div>
      </div>

      {brief.layers.length > 0 && (
        <div style={styles.section}>
          <div style={styles.sectionTitle}>
            Layers ({brief.layers.length})
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
            {brief.layers.map((layer) => (
              <span
                key={layer.id}
                style={{
                  ...styles.tag,
                  background: layer.is_cross_cutting ? '#fff3e0' : '#e3f2fd',
                  color: layer.is_cross_cutting ? '#e65100' : '#1565c0',
                }}
              >
                {layer.label}
                {layer.is_cross_cutting && ' (cross-cutting)'}
                <span style={{ marginLeft: '0.5rem', opacity: 0.7 }}>
                  ({layer.entity_ids.length})
                </span>
              </span>
            ))}
          </div>
        </div>
      )}

      {brief.connections.length > 0 && (
        <div style={styles.section}>
          <div style={styles.sectionTitle}>
            Connections ({brief.connections.length})
          </div>
          <div style={{ fontSize: '0.9rem', color: '#666' }}>
            {brief.connections.map((conn, i) => (
              <span key={i}>
                {conn.from_id} → {conn.to_id}
                {conn.label && ` (${conn.label})`}
                {i < brief.connections.length - 1 && ', '}
              </span>
            ))}
          </div>
        </div>
      )}

      {(brief.brand_hint || brief.color_hint || brief.style_notes) && (
        <div style={styles.section}>
          <div style={styles.sectionTitle}>Style</div>
          <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
            {brief.brand_hint && (
              <span style={styles.tag}>Brand: {brief.brand_hint}</span>
            )}
            {brief.color_hint && (
              <span style={styles.tag}>
                <span
                  style={{
                    display: 'inline-block',
                    width: '12px',
                    height: '12px',
                    background: brief.color_hint,
                    borderRadius: '2px',
                    marginRight: '4px',
                    verticalAlign: 'middle',
                  }}
                />
                {brief.color_hint}
              </span>
            )}
            {brief.style_notes && (
              <span style={{ fontSize: '0.9rem', color: '#666' }}>
                {brief.style_notes}
              </span>
            )}
          </div>
        </div>
      )}

      <div style={styles.section}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={styles.sectionTitle}>Preview</div>
          <button
            style={{ ...styles.buttonSecondary, padding: '0.25rem 0.5rem', fontSize: '0.85rem' }}
            onClick={() => setShowPreview(!showPreview)}
          >
            {showPreview ? 'Hide Preview' : 'Show Preview'}
          </button>
        </div>
        {showPreview && (
          <DiagramPreview
            brief={brief}
            brandPreset={brandPreset || brief.brand_hint}
          />
        )}
      </div>

      <div style={styles.buttons}>
        <button
          style={styles.buttonSecondary}
          onClick={onBack}
          disabled={loading}
        >
          Back
        </button>
        <button
          style={{
            ...styles.buttonPrimary,
            ...(loading ? styles.buttonDisabled : {}),
          }}
          onClick={onGenerate}
          disabled={loading}
        >
          {loading ? 'Generating...' : 'Generate PPTX'}
        </button>
      </div>
    </div>
  );
}

export default BriefReview;
