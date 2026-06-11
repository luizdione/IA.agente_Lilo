import React from 'react';
import StatusPanel from './StatusPanel';
import './RightSidebar.css';

interface RightSidebarProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
}

const RightSidebar: React.FC<RightSidebarProps> = ({ activeTab, onTabChange }) => {
  const tabs = [
    { id: 'agent', icon: '🤖', label: 'Agent Status' },
    { id: 'logs', icon: '📝', label: 'Logs' },
    { id: 'tools', icon: '🔧', label: 'Tools' },
  ];

  return (
    <div className="right-sidebar">
      <div className="sidebar-content">
        {activeTab === 'agent' && <StatusPanel />}
        {activeTab === 'logs' && <div className="tab-panel">Logs Panel</div>}
        {activeTab === 'tools' && <div className="tab-panel">Tools Panel</div>}
      </div>
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
    </div>
  );
};

export default RightSidebar;
