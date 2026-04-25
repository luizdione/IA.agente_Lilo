import React, { useState, useEffect } from 'react';
import './StatusBar.css';

const StatusBar: React.FC = () => {
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="status-bar">
      <div className="status-left">
        <div className="status-item">
          <span className="status-icon">🟢</span>
          <span>Backend: Connected</span>
        </div>
        <div className="status-item">
          <span className="status-icon">🧠</span>
          <span>Ollama: Online</span>
        </div>
        <div className="status-item">
          <span className="status-icon">💾</span>
          <span>Memory: Active</span>
        </div>
      </div>

      <div className="status-right">
        <div className="status-item">
          <span>🔋 CPU: 45%</span>
        </div>
        <div className="status-item">
          <span>📊 RAM: 8.2GB</span>
        </div>
        <div className="status-item">
          <span>{time.toLocaleTimeString()}</span>
        </div>
      </div>
    </div>
  );
};

export default StatusBar;
