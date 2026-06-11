import React, { useState } from 'react';
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
    Help: ['Quick Start', 'Documentation', 'Integration Guide', 'Layout Guide', '---', 'Keyboard Shortcuts', '---', 'About LILO']
  };

  const toggleMenu = (menu: string) => {
    setActiveMenu(activeMenu === menu ? null : menu);
  };

  const handleMenuItemClick = (item: string) => {
    // Handle menu item actions
    const docMap: {[key: string]: string} = {
      'Quick Start': '/ajuda_atualizacao/QUICKSTART.md',
      'Documentation': '/ajuda_atualizacao/DOCUMENTATION.md',
      'Integration Guide': '/ajuda_atualizacao/INTEGRATION_GUIDE.md',
      'Layout Guide': '/ajuda_atualizacao/LAYOUT_README.md'
    };

    if (docMap[item]) {
      // Open documentation in new window
      window.open(docMap[item], '_blank');
    }

    setActiveMenu(null);
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
                    <div
                      key={idx}
                      className="menu-dropdown-item"
                      onClick={() => handleMenuItemClick(item)}
                    >
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
        <span className="menu-icon">LILO</span>
        <span>Agent v6.0</span>
      </div>
    </div>
  );
};

export default MenuBar;
