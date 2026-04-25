import React, { useState, useEffect } from 'react';
import './HelpViewer.css';

interface HelpViewerProps {
  docPath: string;
  onClose: () => void;
}

const HelpViewer: React.FC<HelpViewerProps> = ({ docPath, onClose }) => {
  const [content, setContent] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    const loadDoc = async () => {
      try {
        setLoading(true);
        const response = await fetch(docPath);
        if (response.ok) {
          const text = await response.text();
          setContent(text);
        } else {
          setContent('# Erro\n\nDocumentacao nao encontrada.');
        }
      } catch (error) {
        setContent('# Erro\n\nFalha ao carregar documentacao.');
      } finally {
        setLoading(false);
      }
    };

    loadDoc();
  }, [docPath]);

  return (
    <div className="help-viewer-overlay" onClick={onClose}>
      <div className="help-viewer-modal" onClick={(e) => e.stopPropagation()}>
        <div className="help-viewer-header">
          <h2>Documentacao LILO</h2>
          <button className="help-close-btn" onClick={onClose}>×</button>
        </div>
        <div className="help-viewer-content">
          {loading ? (
            <div className="help-loading">Carregando...</div>
          ) : (
            <pre>{content}</pre>
          )}
        </div>
      </div>
    </div>
  );
};

export default HelpViewer;
