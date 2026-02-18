import { getDownloadUrl } from '../api';

interface DownloadButtonProps {
  fileId: string;
  title: string;
  onReset: () => void;
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column' as const,
    alignItems: 'center',
    gap: '1.5rem',
    padding: '2rem',
    textAlign: 'center' as const,
  },
  icon: {
    width: '80px',
    height: '80px',
    borderRadius: '50%',
    background: '#e8f5e9',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '2.5rem',
  },
  title: {
    fontSize: '1.5rem',
    fontWeight: 600,
    color: '#333',
  },
  subtitle: {
    color: '#666',
    fontSize: '1rem',
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
    background: '#2e7d32',
    color: 'white',
    fontSize: '1rem',
    fontWeight: 600,
    cursor: 'pointer',
    textDecoration: 'none',
    display: 'inline-flex',
    alignItems: 'center',
    gap: '0.5rem',
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
};

function DownloadButton({ fileId, title, onReset }: DownloadButtonProps) {
  const downloadUrl = getDownloadUrl(fileId);

  return (
    <div style={styles.container}>
      <div style={styles.icon}>
        <span role="img" aria-label="success">&#9989;</span>
      </div>

      <div>
        <div style={styles.title}>Diagram Ready!</div>
        <div style={styles.subtitle}>
          Your PowerPoint presentation "{title}" has been generated.
        </div>
      </div>

      <div style={styles.buttons}>
        <a
          href={downloadUrl}
          download={`${title}.pptx`}
          style={styles.buttonPrimary}
        >
          <span role="img" aria-label="download">&#128229;</span>
          Download PPTX
        </a>

        <button
          style={styles.buttonSecondary}
          onClick={onReset}
        >
          Create Another
        </button>
      </div>

      <div style={{ fontSize: '0.85rem', color: '#999', marginTop: '1rem' }}>
        File ID: {fileId}
      </div>
    </div>
  );
}

export default DownloadButton;
