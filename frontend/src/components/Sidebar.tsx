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
  LogIn,
  LogOut,
  Lock,
  CloudRain,
} from 'lucide-react';
import type { UserProfile, PermissionName, RoleName } from '../types/auth';
import { userHasPermission, normalizeRole } from '../types/auth';

export type NavigationTab =
  | 'overview'
  | 'risk-map'
  | 'consequence-graph'
  | 'interventions'
  | 'emergency-chatbot'
  | 'environmental'
  | 'audit-log';

interface NavItemConfig {
  id: NavigationTab;
  label: string;
  icon: React.ReactNode;
  badge?: string;
  requiredPermission?: PermissionName;
}

interface SidebarProps {
  activeTab: NavigationTab;
  onSelectTab: (tab: NavigationTab) => void;
  backendOnline: boolean;
  user?: UserProfile | null;
  onOpenLogin?: () => void;
  onLogout?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  onSelectTab,
  backendOnline,
  user,
  onOpenLogin,
  onLogout,
}) => {
  const navItems: NavItemConfig[] = [
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
      requiredPermission: 'chatbot.ask',
    },
    {
      id: 'environmental',
      label: 'Environmental Intel',
      icon: <CloudRain size={17} />,
      badge: 'LIVE',
      requiredPermission: 'scenario.read',
    },
    {
      id: 'audit-log',
      label: 'Audit Log',
      icon: <FileText size={17} />,
      requiredPermission: 'audit.read',
    },
  ];

  const canonicalRole: RoleName | null = user ? normalizeRole(user.role) : null;
  const isAuthenticated = Boolean(user && user.is_active);

  // Compute initials for avatar
  const initials = user?.full_name
    ? user.full_name
        .split(' ')
        .map((p) => p[0])
        .slice(0, 2)
        .join('')
        .toUpperCase()
    : user?.email
    ? user.email.slice(0, 2).toUpperCase()
    : 'OP';

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
              // If user is authenticated, check granular permission; if unauthenticated, allow public browsing
              const isAllowed = !item.requiredPermission || !isAuthenticated || userHasPermission(user ?? null, item.requiredPermission);

              return (
                <li key={item.id} className="nav-item">
                  <button
                    type="button"
                    className={`nav-button ${isActive ? 'active' : ''} ${!isAllowed ? 'nav-disabled' : ''}`}
                    onClick={() => onSelectTab(item.id)}
                    aria-current={isActive ? 'page' : undefined}
                    title={!isAllowed ? `Requires permission: ${item.requiredPermission}` : undefined}
                  >
                    <span className="nav-icon">{item.icon}</span>
                    <span className="nav-label">{item.label}</span>
                    {item.badge && <span className="nav-badge">{item.badge}</span>}
                    {!isAllowed && <Lock size={12} className="nav-lock-icon" />}
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
          <div className={`station-avatar ${isAuthenticated ? 'avatar-authenticated' : 'avatar-unauthenticated'}`}>
            {initials}
          </div>
          <div className="station-meta">
            <span className="station-operator">
              {user?.full_name || user?.email || 'Public Demonstrator'}
            </span>
            <div className="station-role-container">
              <span className={`station-role-badge role-${(canonicalRole || 'viewer').toLowerCase()}`}>
                {canonicalRole || (isAuthenticated ? user?.role : 'VIEWER')}
              </span>
              {isAuthenticated && (
                <span className="station-status-indicator">Active</span>
              )}
            </div>
          </div>
        </div>

        {/* Quick Auth Trigger Button */}
        <div className="station-auth-action">
          {isAuthenticated ? (
            <button
              type="button"
              className="btn btn-sm btn-ghost sidebar-auth-btn"
              onClick={onLogout}
              title="Sign out of station session"
            >
              <LogOut size={13} />
              <span>Sign Out</span>
            </button>
          ) : (
            <button
              type="button"
              className="btn btn-sm btn-primary sidebar-auth-btn"
              onClick={onOpenLogin}
              title="Authenticate station credentials"
            >
              <LogIn size={13} />
              <span>Sign In</span>
            </button>
          )}
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
