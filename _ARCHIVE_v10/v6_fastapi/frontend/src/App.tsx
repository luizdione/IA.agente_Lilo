import React, { useState } from 'react';
import MenuBar from './components/MenuBar';
import Toolbar from './components/Toolbar';
import LeftSidebar from './components/LeftSidebar';
import RightSidebar from './components/RightSidebar';
import ChatInterface from './components/ChatInterface';
import StatusBar from './components/StatusBar';
import './App.css';

function App() {
  const [leftSidebarOpen, setLeftSidebarOpen] = useState(true);
  const [rightSidebarOpen, setRightSidebarOpen] = useState(true);
  const [activeLeftTab, setActiveLeftTab] = useState('files');
  const [activeRightTab, setActiveRightTab] = useState('agent');

  return (
    <div className="app-container">
      {/* Menu Bar Superior (File, Edit, View, etc) */}
      <MenuBar />

      {/* Toolbar com ações rápidas */}
      <Toolbar
        onToggleLeftSidebar={() => setLeftSidebarOpen(!leftSidebarOpen)}
        onToggleRightSidebar={() => setRightSidebarOpen(!rightSidebarOpen)}
        leftSidebarOpen={leftSidebarOpen}
        rightSidebarOpen={rightSidebarOpen}
      />

      {/* Área Principal */}
      <div className="app-main">
        {/* Sidebar Esquerda (estilo PyCharm) */}
        {leftSidebarOpen && (
          <LeftSidebar
            activeTab={activeLeftTab}
            onTabChange={setActiveLeftTab}
          />
        )}

        {/* Conteúdo Central */}
        <main className="content-area">
          <ChatInterface />
        </main>

        {/* Sidebar Direita (estilo PyCharm) */}
        {rightSidebarOpen && (
          <RightSidebar
            activeTab={activeRightTab}
            onTabChange={setActiveRightTab}
          />
        )}
      </div>

      {/* Status Bar Inferior */}
      <StatusBar />
    </div>
  );
}

export default App;
