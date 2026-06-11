import React from 'react';
import FileExplorer from './FileExplorer';
import './LeftSidebar.css';

interface LeftSidebarProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
}

const LeftSidebar: React.FC<LeftSidebarProps> = ({ activeTab, onTabChange }) => {
  const tabs = [
    { id: 'files', icon: '📁', label: 'Files' },
    { id: 'search', icon: '🔍', label: 'Search' },
    { id: 'git', icon: '🌿', label: 'Git' },
    { id: 'tasks', icon: '✓', label: 'Tasks' },
  ];

  return (
    <div className="left-sidebar">
      <div className="sidebar-tabs">
        {tabs.map((tab) => (
          <div
            key={tab.id}
            className={`sidebar-tab ${activeTab === tab.id ? 'active' : ''}`}
            onClick={() => onTabChange(tab.id)}
            title={tab.label}
          >
            {tab.icon}
          </div>
        ))}
      </div>
      <div className="sidebar-content">
        {activeTab === 'files' && <FileExplorer />}
        {activeTab === 'search' && <div className="tab-panel">Search Panel</div>}
        {activeTab === 'git' && <div className="tab-panel">Git Panel</div>}
        {activeTab === 'tasks' && <div className="tab-panel">Tasks Panel</div>}
      </div>
    </div>
  );
};

export default LeftSidebar;
