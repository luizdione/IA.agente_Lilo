import React, { useState, useEffect } from 'react';
import { getAgentStatus } from '../services/api';
import './StatusPanel.css';

interface AgentStatus {
  active: boolean;
  task?: string;
  phase?: string;
  iteration?: number;
  status?: string;
  message?: string;
}

const StatusPanel: React.FC = () => {
  const [status, setStatus] = useState<AgentStatus | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchStatus = async () => {
    try {
      const data = await getAgentStatus();
      setStatus(data);
    } catch (error) {
      console.error('Erro ao buscar status:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 2000); // Atualizar a cada 2s

    return () => clearInterval(interval);
  }, []);

  const getPhaseEmoji = (phase?: string) => {
    switch (phase) {
      case 'plan': return '📋';
      case 'act': return '⚡';
      case 'observe': return '👁️';
      case 'refine': return '🔧';
      case 'complete': return '✅';
      default: return '⏸️';
    }
  };

  const getStatusColor = (taskStatus?: string) => {
    switch (taskStatus) {
      case 'completed': return '#2ecc71';
      case 'failed': return '#e74c3c';
      case 'in_progress': return '#3498db';
      default: return '#95a5a6';
    }
  };

  return (
    <div className="status-panel">
      <div className="status-header">
        <h3>📊 Status</h3>
      </div>

      {loading ? (
        <div className="status-loading">Carregando...</div>
      ) : (
        <div className="status-content">
          <div className="status-item">
            <div className="status-label">Estado:</div>
            <div className="status-value">
              <span className={`status-badge ${status?.active ? 'active' : 'inactive'}`}>
                {status?.active ? '🟢 Ativo' : '⚫ Inativo'}
              </span>
            </div>
          </div>

          {status?.active && status.task && (
            <>
              <div className="status-item">
                <div className="status-label">Tarefa:</div>
                <div className="status-value task-text">{status.task}</div>
              </div>

              <div className="status-item">
                <div className="status-label">Fase:</div>
                <div className="status-value">
                  <span className="phase-badge">
                    {getPhaseEmoji(status.phase)} {status.phase || 'N/A'}
                  </span>
                </div>
              </div>

              <div className="status-item">
                <div className="status-label">Iteração:</div>
                <div className="status-value iteration">
                  {status.iteration ?? 0}
                </div>
              </div>

              <div className="status-item">
                <div className="status-label">Status:</div>
                <div className="status-value">
                  <span
                    className="status-indicator"
                    style={{ backgroundColor: getStatusColor(status.status) }}
                  >
                    {status.status || 'N/A'}
                  </span>
                </div>
              </div>
            </>
          )}

          {!status?.active && (
            <div className="status-message">
              {status?.message || 'Aguardando tarefa...'}
            </div>
          )}
        </div>
      )}

      <div className="status-footer">
        <div className="system-info">
          <div className="info-item">
            <span className="info-label">Backend:</span>
            <span className="info-value">🟢 Online</span>
          </div>
          <div className="info-item">
            <span className="info-label">Ollama:</span>
            <span className="info-value">🟢 Online</span>
          </div>
          <div className="info-item">
            <span className="info-label">Memória:</span>
            <span className="info-value">🟢 Online</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default StatusPanel;
