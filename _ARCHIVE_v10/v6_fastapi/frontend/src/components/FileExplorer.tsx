import React, { useState, useEffect } from 'react';
import { listDirectory } from '../services/api';
import './FileExplorer.css';

interface FileItem {
  path: string;
  name: string;
  type: 'file' | 'directory';
  size: number;
  modified: string;
}

const FileExplorer: React.FC = () => {
  const [files, setFiles] = useState<FileItem[]>([]);
  const [currentPath, setCurrentPath] = useState('/workspace');
  const [loading, setLoading] = useState(false);

  const loadDirectory = async (path: string) => {
    setLoading(true);
    try {
      const response = await listDirectory(path, false);
      setFiles(response.data.items);
      setCurrentPath(path);
    } catch (error) {
      console.error('Erro ao carregar diretório:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDirectory(currentPath);
  }, []);

  const handleItemClick = (item: FileItem) => {
    if (item.type === 'directory') {
      loadDirectory(item.path);
    }
  };

  const formatSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="file-explorer">
      <div className="explorer-header">
        <h3>📁 Arquivos</h3>
        <button
          className="btn-refresh"
          onClick={() => loadDirectory(currentPath)}
          disabled={loading}
        >
          🔄
        </button>
      </div>

      <div className="current-path">
        <span className="path-label">Local:</span>
        <span className="path-value">{currentPath}</span>
      </div>

      <div className="file-list">
        {loading ? (
          <div className="loading-indicator">Carregando...</div>
        ) : files.length === 0 ? (
          <div className="empty-state">Diretório vazio</div>
        ) : (
          files.map((item, idx) => (
            <div
              key={idx}
              className={`file-item file-item-${item.type}`}
              onClick={() => handleItemClick(item)}
            >
              <div className="file-icon">
                {item.type === 'directory' ? '📁' : '📄'}
              </div>
              <div className="file-info">
                <div className="file-name">{item.name}</div>
                <div className="file-meta">
                  {item.type === 'file' && (
                    <span className="file-size">{formatSize(item.size)}</span>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default FileExplorer;
