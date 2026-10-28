import React from 'react';
import {
  ShieldAlert,
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
    { id: 'overview', label: 'Overview', icon: <LayoutDashboard size={18} /> },
    { id: 'risk-map', label: 'Risk Map', icon: <Map size={18} /> },
    {
      id: 'consequence-graph',
      label: 'Consequence Graph',
      icon: <Network size={18} />,
      badge: 'M3',
    },
    {
      id: 'interventions',
      label: 'Interventions',
      icon: <ShieldCheck size={18} />,
      badge: 'M4',
    },
    {
      id: 'emergency-chatbot',
      label: 'Emergency Chatbot',
      icon: <MessageSquare size={18} />,
      badge: 'M5',
    },
    { id: 'audit-log', label: 'Audit Log', icon: <FileText size={18} /> },
  ];

  return (
    <aside className="sidebar">
      {/* Brand Header */}
      <div className="sidebar-brand">
        <div className="sidebar-brand-icon">
          <ShieldAlert size={24} className="text-cyan" />
        </div>
        <div className="sidebar-brand-text">
          <div className="brand-title">CLIMAFORGE</div>
          <div className="brand-subtitle">Operations Center</div>
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
                >
                  <span className="nav-icon">{item.icon}</span>
                  <span className="nav-label">{item.label}</span>
                  {item.badge && <span className="nav-badge">{item.badge}</span>}
                  {isActive && <ChevronRight size={14} className="nav-active-arrow" />}
                </button>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* Footer System Status */}
      <div className="sidebar-footer">
        <div className="system-status-indicator">
          <span
            className={`status-dot-sm ${
              backendOnline ? 'dot-online' : 'dot-offline'
            }`}
          />
          <div className="system-status-text">
            <span className="system-status-label">API SERVER</span>
            <span className="system-status-val">
              {backendOnline ? 'Connected' : 'Offline'}
            </span>
          </div>
        </div>
        <div className="version-tag">M1: Operational Dashboard</div>
      </div>
    </aside>
  );
};
