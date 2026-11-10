import React from 'react';
import {
  RefreshCw,
  Server,
  AlertTriangle,
  ChevronDown,
  Shield,
  LogIn,
  LogOut,
} from 'lucide-react';
import type { HealthCheckResult } from '../services/api';
import type { ScenarioSummaryItem } from '../types/api';
import type { UserProfile, RoleName } from '../types/auth';
import { normalizeRole } from '../types/auth';
import type { NavigationTab } from './Sidebar';

interface HeaderProps {
  activeTab: NavigationTab;
  healthResult: HealthCheckResult | null;
  isCheckingHealth: boolean;
  onRefreshHealth: () => void;
  scenarioName?: string;
  scenarios?: ScenarioSummaryItem[];
  selectedScenarioId?: string;
  onSelectScenario?: (id: string) => void;
  isLoadingScenario?: boolean;
  user?: UserProfile | null;
  onOpenLogin?: () => void;
  onLogout?: () => void;
}

const TAB_TITLES: Record<NavigationTab, { label: string; title: string; subtitle: string }> = {
  overview: {
    label: 'Overview',
    title: 'Operations Overview & Scenario Monitor',
    subtitle: 'Zonal risk aggregation, critical asset distribution, and telemetry overview',
  },
  'risk-map': {
    label: 'Risk Map',
    title: 'Tactical Risk Map & Zonal Inundation Schematic',
    subtitle: 'Spatial distribution of hydraulic risk, watercourse proximity, and asset locations',
  },
  'consequence-graph': {
    label: 'Consequence Graph',
    title: 'Consequence Graph & Critical Cascade Infrastructure',
    subtitle: 'Directed failure propagation dependencies across critical facilities (Milestone 3 Preview)',
  },
  interventions: {
    label: 'Interventions',
    title: 'Candidate Interventions & Logistics Catalog',
    subtitle: 'Mitigation actions, barrier deployments, and resource demands (Milestone 4)',
  },
  'emergency-chatbot': {
    label: 'Emergency Chatbot',
    title: 'Autonomous Citizen Emergency Guidance',
    subtitle: 'Pre-calamity warning, verified live navigation, and offline SOS outbox (Milestone 5 Preview)',
  },
  'audit-log': {
    label: 'Audit Log',
    title: 'System Operational & UI Session Audit Log',
    subtitle: 'Authentic chronological record of backend lifecycle events and operator actions',
  },
};

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  healthResult,
  isCheckingHealth,
  onRefreshHealth,
  scenarioName,
  scenarios,
  selectedScenarioId,
  onSelectScenario,
  isLoadingScenario,
  user,
  onOpenLogin,
  onLogout,
}) => {
  const currentTabInfo = TAB_TITLES[activeTab];
  const activeScenario = scenarios?.find((s) => s.scenario_id === selectedScenarioId);
  const isHighSeverity =
    activeScenario?.severity === 'CRITICAL' ||
    activeScenario?.severity === 'ELEVATED' ||
    (scenarioName ? scenarioName.toLowerCase().includes('alert') : false);

  const canonicalRole: RoleName | null = user ? normalizeRole(user.role) : null;
  const isAuthenticated = Boolean(user && user.is_active);

  return (
    <header className="dashboard-header">
      {/* Top Banner */}
      <div className="prototype-banner">
        <div className="banner-content">
          <AlertTriangle size={13} className="banner-icon" />
          <span className="banner-tag">SYNTHETIC / ILLUSTRATIVE DATA ONLY</span>
          <span className="banner-desc">
            CLIMAFORGE demonstration prototype. Not for real-world emergency dispatch or evacuation operations.
          </span>
        </div>
      </div>

      {/* Main Header Bar */}
      <div className="header-bar">
        <div className="header-left">
          <h1 className="header-tab-title">{currentTabInfo.label}</h1>
          <span className="header-separator">/</span>

          {/* Scenario Selector Pill */}
          {scenarios && onSelectScenario ? (
            <div className="scenario-selector-pill" title="Active simulation scenario">
              <span
                className={`scenario-pill-dot ${
                  isHighSeverity ? 'dot-critical' : 'dot-stable'
                }`}
              />
              <select
                className="scenario-pill-select"
                value={selectedScenarioId}
                onChange={(e) => onSelectScenario(e.target.value)}
                disabled={isLoadingScenario}
                aria-label="Select simulation scenario"
              >
                {scenarios.map((sc) => (
                  <option key={sc.scenario_id} value={sc.scenario_id}>
                    {sc.name} ({sc.severity})
                  </option>
                ))}
              </select>
              <ChevronDown size={13} className="scenario-pill-chevron" />
            </div>
          ) : scenarioName ? (
            <div className="scenario-selector-pill">
              <span
                className={`scenario-pill-dot ${
                  isHighSeverity ? 'dot-critical' : 'dot-stable'
                }`}
              />
              <span className="scenario-pill-text">{scenarioName}</span>
            </div>
          ) : null}

          {/* Status Tag */}
          <span className="synthetic-data-pill">
            <span className="synthetic-dot" />
            Synthetic simulation data
          </span>
        </div>

        <div className="header-actions">
          {/* User / Authentication Pill */}
          {isAuthenticated ? (
            <div className="user-profile-pill" title={`Signed in as ${user?.email}`}>
              <Shield size={13} className="user-profile-icon" />
              <span className={`user-role-badge role-${(canonicalRole || 'viewer').toLowerCase()}`}>
                {canonicalRole || user?.role}
              </span>
              <span className="user-email-text">{user?.email}</span>
              {onLogout && (
                <button
                  type="button"
                  className="btn-header-auth"
                  onClick={onLogout}
                  title="Sign out of station"
                  aria-label="Sign out"
                >
                  <LogOut size={13} />
                </button>
              )}
            </div>
          ) : (
            <button
              type="button"
              className="btn btn-sm btn-header-login"
              onClick={onOpenLogin}
              title="Authenticate station session"
            >
              <LogIn size={13} />
              <span>Sign In</span>
            </button>
          )}

          {/* Connection Status Pill */}
          <div
            className={`connection-pill ${
              isCheckingHealth
                ? 'pill-checking'
                : healthResult?.success
                ? 'pill-online'
                : 'pill-offline'
            }`}
          >
            <Server size={13} />
            <span className="connection-text">
              {isCheckingHealth
                ? 'Checking...'
                : healthResult?.success
                ? 'Core Online'
                : 'Core Disconnected'}
            </span>
            {healthResult?.latencyMs !== undefined && (
              <span className="latency-badge">{healthResult.latencyMs}ms</span>
            )}
          </div>

          {/* Quick Check Health Button */}
          <button
            type="button"
            className="btn-icon-secondary"
            onClick={onRefreshHealth}
            disabled={isCheckingHealth}
            title="Ping backend health endpoint"
            aria-label="Refresh backend health"
          >
            <RefreshCw size={14} className={isCheckingHealth ? 'spin-animation' : ''} />
          </button>
        </div>
      </div>
    </header>
  );
};
