"""
Script para gerar todos os componentes do novo layout LILO
Executa automaticamente a criação de todos os arquivos necessários
"""

import os
from pathlib import Path

COMPONENTS_DIR = Path(__file__).parent / "src" / "components"
COMPONENTS_DIR.mkdir(parents=True, exist_ok=True)

# Definição de todos os componentes
COMPONENTS = {
    "MenuBar.tsx": """import React, { useState } from 'react';
import './MenuBar.css';

interface MenuBarProps {}

const MenuBar: React.FC<MenuBarProps> = () => {
  const [activeMenu, setActiveMenu] = useState<string | null>(null);

  const menus = {
    File: ['New File', 'Open...', 'Open Recent', '---', 'Save', 'Save As...', '---', 'Settings', '---', 'Exit'],
    Edit: ['Undo', 'Redo', '---', 'Cut', 'Copy', 'Paste', '---', 'Find...', 'Replace...'],
    View: ['Appearance', 'Tool Windows', '---', 'Toggle Left Sidebar', 'Toggle Right Sidebar'],
    Navigate: ['Search Everywhere', 'Go to File...', 'Go to Line...', '---', 'Back', 'Forward'],
    Code: ['Generate...', 'Refactor', 'Optimize Imports', '---', 'Comment', 'Uncomment'],
    Run: ['Run Task', 'Debug', '---', 'Stop', 'Restart'],
    Tools: ['Terminal', 'Python Console', '---', 'Tasks', 'Generate Docs'],
    Help: ['Documentation', 'Keyboard Shortcuts', '---', 'About LILO']
  };

  const toggleMenu = (menu: string) => {
    setActiveMenu(activeMenu === menu ? null : menu);
  };

  return (
    <div className="menu-bar">
      <div className="menu-items">
        {Object.keys(menus).map((menu) => (
          <div
            key={menu}
            className={`menu-item ${activeMenu === menu ? 'active' : ''}`}
            onClick={() => toggleMenu(menu)}
            onMouseEnter={() => activeMenu && setActiveMenu(menu)}
          >
            {menu}
            {activeMenu === menu && (
              <div className="menu-dropdown">
                {menus[menu as keyof typeof menus].map((item, idx) => (
                  item === '---' ? (
                    <div key={idx} className="menu-separator" />
                  ) : (
                    <div key={idx} className="menu-dropdown-item">
                      {item}
                    </div>
                  )
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
      <div className="menu-title">
        <span className="menu-icon">🤖</span>
        <span>LILO Agent v6.0</span>
      </div>
    </div>
  );
};

export default MenuBar;
""",

    "MenuBar.css": """.menu-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 28px;
  background-color: #2d2d30;
  border-bottom: 1px solid #1e1e1e;
  font-size: 13px;
  color: #cccccc;
  user-select: none;
  z-index: 1000;
}

.menu-items {
  display: flex;
  gap: 2px;
  padding-left: 8px;
}

.menu-item {
  position: relative;
  padding: 4px 12px;
  cursor: pointer;
  transition: background-color 0.1s;
}

.menu-item:hover,
.menu-item.active {
  background-color: #3e3e42;
}

.menu-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  min-width: 200px;
  background-color: #2d2d30;
  border: 1px solid #454545;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
  z-index: 10000;
  padding: 4px 0;
}

.menu-dropdown-item {
  padding: 6px 12px;
  cursor: pointer;
  font-size: 13px;
}

.menu-dropdown-item:hover {
  background-color: #094771;
  color: white;
}

.menu-separator {
  height: 1px;
  background-color: #454545;
  margin: 4px 0;
}

.menu-title {
  padding-right: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}

.menu-icon {
  font-size: 16px;
}
""",

    "Toolbar.tsx": """import React from 'react';
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
""",

    "Toolbar.css": """.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 40px;
  background-color: #2d2d30;
  border-bottom: 1px solid #1e1e1e;
  padding: 0 8px;
  gap: 12px;
}

.toolbar-left,
.toolbar-right {
  display: flex;
  gap: 4px;
  align-items: center;
}

.toolbar-center {
  flex: 1;
  display: flex;
  justify-content: center;
  max-width: 600px;
}

.toolbar-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  color: #cccccc;
  font-size: 16px;
  cursor: pointer;
  border-radius: 4px;
  transition: background-color 0.1s;
}

.toolbar-btn:hover {
  background-color: #3e3e42;
}

.toolbar-btn.active {
  background-color: #094771;
}

.toolbar-separator {
  width: 1px;
  height: 24px;
  background-color: #454545;
  margin: 0 4px;
}

.search-box {
  width: 100%;
  max-width: 500px;
}

.search-input {
  width: 100%;
  height: 28px;
  background-color: #3c3c3c;
  border: 1px solid #454545;
  border-radius: 4px;
  padding: 0 12px;
  color: #cccccc;
  font-size: 13px;
  outline: none;
}

.search-input:focus {
  border-color: #007acc;
  background-color: #1e1e1e;
}

.search-input::placeholder {
  color: #767676;
}
""",

    "LeftSidebar.tsx": """import React from 'react';
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
""",

    "LeftSidebar.css": """.left-sidebar {
  display: flex;
  width: 320px;
  height: 100%;
  background-color: #252526;
  border-right: 1px solid #1e1e1e;
}

.sidebar-tabs {
  width: 48px;
  background-color: #2d2d30;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 8px 0;
  gap: 4px;
  border-right: 1px solid #1e1e1e;
}

.sidebar-tab {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  cursor: pointer;
  border-radius: 4px;
  transition: background-color 0.1s;
}

.sidebar-tab:hover {
  background-color: #3e3e42;
}

.sidebar-tab.active {
  background-color: #094771;
}

.sidebar-content {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.tab-panel {
  flex: 1;
  padding: 16px;
  color: #cccccc;
  overflow: auto;
}
""",

    "RightSidebar.tsx": """import React from 'react';
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
""",

    "RightSidebar.css": """.right-sidebar {
  display: flex;
  width: 320px;
  height: 100%;
  background-color: #252526;
  border-left: 1px solid #1e1e1e;
}

.sidebar-content {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.sidebar-tabs {
  width: 48px;
  background-color: #2d2d30;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 8px 0;
  gap: 4px;
  border-left: 1px solid #1e1e1e;
}

.sidebar-tab {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  cursor: pointer;
  border-radius: 4px;
  transition: background-color 0.1s;
}

.sidebar-tab:hover {
  background-color: #3e3e42;
}

.sidebar-tab.active {
  background-color: #094771;
}
""",

    "StatusBar.tsx": """import React, { useState, useEffect } from 'react';
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
""",

    "StatusBar.css": """.status-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 22px;
  background-color: #007acc;
  color: white;
  font-size: 12px;
  padding: 0 12px;
  user-select: none;
  z-index: 1000;
}

.status-left,
.status-right {
  display: flex;
  gap: 16px;
  align-items: center;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.status-icon {
  font-size: 10px;
}

.status-item:hover {
  background-color: rgba(255, 255, 255, 0.1);
  cursor: pointer;
  padding: 2px 4px;
  border-radius: 2px;
}
"""
}

def generate_all_components():
    """Gera todos os componentes"""
    print("=" * 60)
    print("Gerando Componentes do Novo Layout LILO")
    print("=" * 60)
    print()

    created = 0
    errors = []

    for filename, content in COMPONENTS.items():
        filepath = COMPONENTS_DIR / filename

        try:
            filepath.write_text(content, encoding='utf-8')
            print(f"OK Criado: {filename}")
            created += 1
        except Exception as e:
            errors.append(f"ERRO em {filename}: {e}")

    print()
    print("=" * 60)
    print(f"Geracao concluida!")
    print(f"   Componentes criados: {created}/{len(COMPONENTS)}")

    if errors:
        print(f"   Erros: {len(errors)}")
        for error in errors:
            print(f"  {error}")

    print("=" * 60)

if __name__ == "__main__":
    generate_all_components()
