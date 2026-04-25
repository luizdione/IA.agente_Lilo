import React from 'react';
import './Toolbar.css';

interface ToolbarProps {
  onToggleLeftSidebar: () => void;
  onToggleRightSidebar: () => void;
  leftSidebarOpen: boolean;
  rightSidebarOpen: boolean;
}

const Toolbar: React.FC<ToolbarProps> = ({
  onToggleLeftSidebar,
  onToggleRightSidebar,
  leftSidebarOpen,
  rightSidebarOpen
}) => {
  return (
    <div className="toolbar">
      <div className="toolbar-left">
        <button
          className={`toolbar-btn ${leftSidebarOpen ? 'active' : ''}`}
          onClick={onToggleLeftSidebar}
          title="Toggle Project Explorer"
        >
          📁
        </button>
        <div className="toolbar-separator" />
        <button className="toolbar-btn" title="New Task">
          ➕
        </button>
        <button className="toolbar-btn" title="Run">
          ▶️
        </button>
        <button className="toolbar-btn" title="Debug">
          🐛
        </button>
        <button className="toolbar-btn" title="Stop">
          ⏹️
        </button>
      </div>

      <div className="toolbar-center">
        <div className="search-box">
          <input
            type="text"
            placeholder="Search Everywhere (Ctrl+Shift+F)"
            className="search-input"
          />
        </div>
      </div>

      <div className="toolbar-right">
        <button className="toolbar-btn" title="Terminal">
          💻
        </button>
        <button className="toolbar-btn" title="Settings">
          ⚙️
        </button>
        <div className="toolbar-separator" />
        <button
          className={`toolbar-btn ${rightSidebarOpen ? 'active' : ''}`}
          onClick={onToggleRightSidebar}
          title="Toggle Agent Status"
        >
          🤖
        </button>
      </div>
    </div>
  );
};

export default Toolbar;
