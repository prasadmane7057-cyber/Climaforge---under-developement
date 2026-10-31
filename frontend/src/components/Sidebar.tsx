import React from 'react';
import {
  Waves,
  LayoutDashboard,
  Map,
  Network,
  ShieldCheck,
  MessageSquare,
  FileText,
  ChevronRight,
} from 'lucide-react';

export type NavigationTab =
  | 'overview'
  | 'risk-map'
  | 'consequence-graph'
  | 'interventions'
  | 'emergency-chatbot'
  | 'audit-log';

interface SidebarProps {
  activeTab: NavigationTab;
  onSelectTab: (tab: NavigationTab) => void;
  backendOnline: boolean;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  onSelectTab,
  backendOnline,
}) => {
  const navItems: { id: NavigationTab; label: string; icon: React.ReactNode; badge?: string }[] = [
    { id: 'overview', label: 'Overview', icon: <LayoutDashboard size={17} /> },
    { id: 'risk-map', label: 'Risk Map', icon: <Map size={17} /> },
    {
      id: 'consequence-graph',
      label: 'Consequence Graph',
      icon: <Network size={17} />,
      badge: 'M3',
    },
    {
      id: 'interventions',
      label: 'Interventions',
      icon: <ShieldCheck size={17} />,
      badge: 'M4',
    },
    {
      id: 'emergency-chatbot',
      label: 'Emergency Chatbot',
      icon: <MessageSquare size={17} />,
      badge: 'M5',
    },
    { id: 'audit-log', label: 'Audit Log', icon: <FileText size={17} /> },
  ];

  return (
    <aside className="sidebar">
      {/* Brand Header */}
      <div className="sidebar-top">
        <div className="sidebar-brand">
          <div className="sidebar-brand-icon">
            <Waves size={18} />
          </div>
          <div className="sidebar-brand-text">
            <span className="brand-title">CLIMAFORGE</span>
            <span className="brand-subtitle">Hazard Decision Support</span>
          </div>
        </div>

        {/* Navigation List */}
        <nav className="sidebar-nav">
          <div className="nav-group-title">COMMAND NAVIGATION</div>
          <ul className="nav-list">
            {navItems.map((item) => {
              const isActive = activeTab === item.id;
              return (
                <li key={item.id} className="nav-item">
                  <button
                    type="button"
                    className={`nav-button ${isActive ? 'active' : ''}`}
                    onClick={() => onSelectTab(item.id)}
                    aria-current={isActive ? 'page' : undefined}
                  >
                    <span className="nav-icon">{item.icon}</span>
                    <span className="nav-label">{item.label}</span>
                    {item.badge && <span className="nav-badge">{item.badge}</span>}
                    {isActive && <ChevronRight size={13} className="nav-active-arrow" />}
                  </button>
                </li>
              );
            })}
          </ul>
        </nav>
      </div>

      {/* Footer System Status & Station Profile */}
      <div className="sidebar-footer">
        <div className="station-profile">
          <div className="station-avatar">OP</div>
          <div className="station-meta">
            <span className="station-operator">Command Operator</span>
            <span className="station-role">Operational Station (Active)</span>
          </div>
        </div>

        <div className="station-system-status">
          <div className="status-indicator-inline">
            <span
              className={`status-dot-sm ${
                backendOnline ? 'dot-online' : 'dot-offline'
              }`}
            />
            <span className="status-label">
              API Core: {backendOnline ? 'Connected' : 'Offline'}
            </span>
          </div>
          <span className="status-version">v2.0 &bull; Algo 0&ndash;13</span>
        </div>
      </div>
    </aside>
  );
};
